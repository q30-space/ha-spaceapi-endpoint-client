"""Unit tests for the Python-version preflight guard in scripts/bump_ha.py.

The bump workflow resolves the latest HA from PyPI (with no Python
constraint) and then installs it on the runner. When HA's Requires-Python
floor moves past the runner's interpreter, the install step fails with an
opaque pip error. The guard catches that case up front, so these tests pin
its parsing and lookup behaviour.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bump_ha.py"
_spec = importlib.util.spec_from_file_location("bump_ha", _SCRIPT)
bump_ha = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bump_ha)


def test_python_floor_parses_full_version() -> None:
    assert bump_ha._python_floor(">=3.14.2") == (3, 14, 2)


def test_python_floor_parses_two_component_version() -> None:
    assert bump_ha._python_floor(">=3.14") == (3, 14, 0)


def test_python_floor_tolerates_whitespace_and_extra_clauses() -> None:
    assert bump_ha._python_floor(">= 3.14.2, <4.0") == (3, 14, 2)


def test_python_floor_skips_unparseable_or_missing() -> None:
    assert bump_ha._python_floor(None) is None
    assert bump_ha._python_floor("") is None
    assert bump_ha._python_floor("<4") is None


def test_required_python_reads_release_file_metadata() -> None:
    ha_data = {
        "info": {"version": "2026.6.4", "requires_python": ">=3.14.2"},
        "releases": {
            "2026.6.4": [{"requires_python": ">=3.14.2"}],
            "2024.1.0": [{"requires_python": ">=3.11"}],
        },
    }
    assert bump_ha._required_python(ha_data, "2026.6.4") == ">=3.14.2"
    assert bump_ha._required_python(ha_data, "2024.1.0") == ">=3.11"


def test_required_python_falls_back_to_info_for_latest() -> None:
    # Release file entry carries no requires_python; the info block does.
    ha_data = {
        "info": {"version": "2026.6.4", "requires_python": ">=3.14.2"},
        "releases": {"2026.6.4": [{}]},
    }
    assert bump_ha._required_python(ha_data, "2026.6.4") == ">=3.14.2"


def test_required_python_none_when_undeclared() -> None:
    ha_data = {"info": {"version": "9.9.9"}, "releases": {"1.0.0": [{}]}}
    assert bump_ha._required_python(ha_data, "1.0.0") is None


_HA_DATA = {
    "info": {"version": "2026.6.4", "requires_python": ">=3.14.2"},
    "releases": {"2026.6.4": [{"requires_python": ">=3.14.2"}]},
}


def test_preflight_blocks_when_runner_too_old() -> None:
    message = bump_ha._python_preflight(_HA_DATA, "2026.6.4", (3, 13, 5))
    assert message is not None
    assert ">=3.14.2" in message
    assert "3.13.5" in message
    assert "bump-ha.yml" in message


def test_preflight_passes_when_runner_new_enough() -> None:
    assert bump_ha._python_preflight(_HA_DATA, "2026.6.4", (3, 14, 2)) is None
    assert bump_ha._python_preflight(_HA_DATA, "2026.6.4", (3, 15, 0)) is None


def test_preflight_skips_when_floor_undeclared() -> None:
    ha_data = {"info": {"version": "1.0.0"}, "releases": {"1.0.0": [{}]}}
    assert bump_ha._python_preflight(ha_data, "1.0.0", (3, 9, 0)) is None
