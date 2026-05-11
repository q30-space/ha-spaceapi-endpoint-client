# Contributing

## Home Assistant dependency policy

This integration distributes via HACS to a wide range of Home Assistant
versions. We pin HA in three different places, each with a different job:

| Location | Meaning | Who updates it |
|---|---|---|
| `hacs.json` `homeassistant` | Lowest HA the integration is tested to support. HACS refuses to install on anything older. (HA core has no manifest-level minimum for custom integrations — `min_ha_version` is not in `CUSTOM_INTEGRATION_MANIFEST_SCHEMA`.) | Maintainer, when the code starts using a newer HA API. |
| `requirements.txt` | Dev / CI pin. Always the **latest** stable HA release. Used by `scripts/develop` and the "latest" CI matrix cell. | Automated — `.github/workflows/bump-ha.yml`. |
| `requirements-floor.txt` | Floor pins for the "floor" CI matrix cell. Mirrors `hacs.json`'s floor. | Maintainer, in the same PR that raises the floor. |

The CI matrix in `.github/workflows/test.yml` runs the test suite against
both the latest pin and the floor pin, on Python 3.13 and 3.12
respectively. (Older HA releases pull in transitive packages like
`home-assistant-bluetooth` that don't ship Python 3.13 wheels.)

### When to raise the floor

Bump `hacs.json` `homeassistant` (and the place that mirrors it) only when our
own code requires a feature added in a newer HA release. The current
floor is `2024.12.0`, set when the config flow adopted
`ConfigFlow._get_reauth_entry()` for reauth handling. The previous floor
of 2024.10.0 was nominally chosen for `DataUpdateCoordinator(config_entry=...)`
but that kwarg actually landed in HA 2024.11.

To raise the floor:

1. Update `hacs.json` `homeassistant`.
2. Update `requirements-floor.txt` with the new HA pin **and** the
   matching `pytest-homeassistant-custom-component` version. The plugin
   pins one specific HA release in its `Requires-Dist`; PyPI is the
   source of truth:

   ```bash
   # Find the highest plugin release that pins homeassistant==X.Y.Z.
   python3 -c "
   import json, urllib.request
   target = 'homeassistant==X.Y.Z'  # <-- new floor
   data = json.loads(urllib.request.urlopen(
       'https://pypi.org/pypi/pytest-homeassistant-custom-component/json'
   ).read())
   for v, dists in sorted(data['releases'].items(), key=lambda kv: tuple(int(p) for p in kv[0].split('.')))[::-1]:
       if not dists:
           continue
       per = json.loads(urllib.request.urlopen(
           f'https://pypi.org/pypi/pytest-homeassistant-custom-component/{v}/json'
       ).read())
       if any(r.startswith(target) for r in (per['info'].get('requires_dist') or [])):
           print(v); break
   "
   ```

3. Submit all the changes in a single PR. CI's floor cell will fail
   loudly if `hacs.json` and `requirements-floor.txt` drift apart.

### When the dev pin moves

`requirements.txt` is owned by `.github/workflows/bump-ha.yml`. The
workflow:

- Runs on the first of every month at 06:00 UTC.
- Can be triggered on demand from the Actions tab ("Run workflow").
- Resolves the latest stable HA from PyPI plus the matching plugin
  version, rewrites both pins, runs the test suite, and opens a PR if
  anything changed.

Maintainers should review and merge that PR like any other dependency
update. The workflow only opens it after the test suite passes against
the new pins, so a failed PR usually means we picked up a real
regression to investigate, not a transient install issue.

Dependabot is configured in `.github/dependabot.yml` to ignore both
`homeassistant` and `pytest-homeassistant-custom-component` so it
doesn't fight the workflow. It still handles every other dependency
(ruff, colorlog, GitHub Actions, devcontainers).
