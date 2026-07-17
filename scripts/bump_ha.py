#!/usr/bin/env python3
"""Bump the latest-HA pin in requirements.txt to the current PyPI stable.

Resolves the latest non-prerelease ``homeassistant`` version from PyPI, then
finds the highest ``pytest-homeassistant-custom-component`` release whose
``Requires-Dist`` pins exactly that version, and rewrites the two pins in
``requirements.txt``.

Exits 0 with no changes if the file already names the latest pair. Exits 0
*with* changes if it rewrote the file. Exits non-zero on lookup failure.
Designed to run from the repo root, with no third-party dependencies, so it
works in a plain CI runner.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PYPI_HA = "https://pypi.org/pypi/homeassistant/json"
PYPI_PLUGIN = "https://pypi.org/pypi/pytest-homeassistant-custom-component/json"
REQUIREMENTS = Path("requirements.txt")
PRERELEASE = re.compile(r"[a-zA-Z]")


def _fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def _latest_stable(versions: list[str]) -> str:
    """Pick the highest version that has no alphabetic suffix (no 'b', 'rc')."""
    stable = [v for v in versions if not PRERELEASE.search(v)]
    # PyPI returns them roughly in release order but not strictly sorted.
    # HA versions look like YYYY.M.P; lexicographic sort works once
    # zero-padded — instead just trust info.version which is the latest.
    if not stable:
        msg = "No stable HA release found on PyPI"
        raise RuntimeError(msg)
    return stable[-1]


def _required_python(ha_data: dict, ha_version: str) -> str | None:
    """Return the ``Requires-Python`` specifier declared for ``ha_version``.

    Prefer the per-release file metadata; fall back to the project-level
    ``info`` block when ``ha_version`` is the latest release. Returns None
    when PyPI declares no Python constraint (older HA releases don't).
    """
    for dist in ha_data["releases"].get(ha_version) or []:
        spec = dist.get("requires_python")
        if spec:
            return spec
    info = ha_data.get("info", {})
    if info.get("version") == ha_version:
        return info.get("requires_python")
    return None


def _python_floor(requires_python: str | None) -> tuple[int, ...] | None:
    """Extract the ``>=`` lower bound from a ``Requires-Python`` specifier.

    HA declares a single ``>=X.Y[.Z]`` floor. We deliberately parse only
    that clause: if the spec is missing or shaped unexpectedly we return
    None, so the preflight skips rather than false-blocking a valid bump.
    """
    if not requires_python:
        return None
    match = re.search(r">=\s*(\d+)\.(\d+)(?:\.(\d+))?", requires_python)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def _python_preflight(
    ha_data: dict, ha_version: str, current: tuple[int, ...]
) -> str | None:
    """Return an error message if ``current`` Python can't install ``ha_version``.

    The bump workflow resolves the newest HA from PyPI (which applies no
    Python constraint) and then installs it, so a runner older than HA's
    ``Requires-Python`` floor only fails two steps later with an opaque pip
    "No matching distribution" error. This spots it up front. Returns None
    when the runner is new enough, or when PyPI declares no parseable floor.
    """
    floor = _python_floor(_required_python(ha_data, ha_version))
    if not floor or current >= floor:
        return None
    need = ".".join(str(part) for part in floor)
    have = ".".join(str(part) for part in current)
    return (
        f"homeassistant=={ha_version} requires Python >={need}, but this "
        f"runner has Python {have}. Update python-version in "
        f".github/workflows/bump-ha.yml (and the 'latest' cell of test.yml) "
        f"to >={need} before this workflow can install it."
    )


def _matching_plugin(plugin_data: dict, ha_version: str) -> str:
    """Find the highest plugin release whose Requires-Dist pins ``ha_version``.

    PyPI's project-level JSON only carries Requires-Dist for the *latest*
    release, so we fetch the per-version JSON for plugin releases whose
    upload date is in the same calendar month as the HA release. Plugin
    releases happen daily and track HA releases tightly, so the same-month
    filter keeps the lookup to ~30 fetches at most.
    """
    target = f"homeassistant=={ha_version}"
    year, month = ha_version.split(".")[:2]
    month_prefix = f"{year}-{int(month):02d}"

    matches: list[str] = []
    for version, dists in plugin_data["releases"].items():
        if not dists or not dists[0].get("upload_time", "").startswith(month_prefix):
            continue
        per_version = _fetch(
            f"https://pypi.org/pypi/pytest-homeassistant-custom-component/{version}/json"
        )
        requires = per_version["info"].get("requires_dist") or []
        if any(req.startswith(target) for req in requires):
            matches.append(version)
    if not matches:
        msg = f"No pytest-homeassistant-custom-component release pins {target}"
        raise RuntimeError(msg)
    matches.sort(key=lambda v: tuple(int(p) for p in v.split(".")))
    return matches[-1]


def _rewrite(path: Path, ha_version: str, plugin_version: str) -> bool:
    """Update the two pins in-place. Return True if the file changed."""
    original = path.read_text()
    updated = re.sub(
        r"^homeassistant==.*$",
        f"homeassistant=={ha_version}",
        original,
        flags=re.MULTILINE,
    )
    updated = re.sub(
        r"^pytest-homeassistant-custom-component==.*$",
        f"pytest-homeassistant-custom-component=={plugin_version}",
        updated,
        flags=re.MULTILINE,
    )
    if updated == original:
        return False
    path.write_text(updated)
    return True


def main() -> int:
    ha_data = _fetch(PYPI_HA)
    ha_latest = _latest_stable(list(ha_data["releases"].keys()))

    # Fail fast if this runner is too old to install the HA we just resolved.
    problem = _python_preflight(ha_data, ha_latest, sys.version_info[:3])
    if problem:
        print(problem, file=sys.stderr)
        return 1

    plugin_data = _fetch(PYPI_PLUGIN)
    plugin_version = _matching_plugin(plugin_data, ha_latest)

    changed = _rewrite(REQUIREMENTS, ha_latest, plugin_version)
    print(f"homeassistant=={ha_latest}")
    print(f"pytest-homeassistant-custom-component=={plugin_version}")
    print("changed" if changed else "no change")
    # Emit machine-readable lines for the workflow's later steps.
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a") as out:
            out.write(f"ha_version={ha_latest}\n")
            out.write(f"plugin_version={plugin_version}\n")
            out.write(f"changed={'true' if changed else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
