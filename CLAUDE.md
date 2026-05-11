# CLAUDE.md

Project context for AI agents working on `ha-spaceapi-endpoint-client`.

## What this is

A Home Assistant custom integration distributed via HACS. It connects to a [SpaceAPI](https://spaceapi.io/) endpoint to monitor (and optionally control) a hackerspace's open/closed status. Source layout:

```
custom_components/spaceapi_endpoint_client/   # the integration
tests/                                        # pytest-homeassistant-custom-component suite
.github/workflows/                            # lint, validate, test, cut-release, bump-ha
scripts/                                      # ci, develop, lint, setup, bump_ha.py
```

End users install via HACS (it copies `custom_components/spaceapi_endpoint_client/` into their HA config dir). Releases are cut from `main` via the `cut-release.yml` workflow_dispatch — that workflow bumps `manifest.json` and tags; HACS picks the tag up automatically.

## Home Assistant dependency policy — read CONTRIBUTING.md first

There are **three** HA version pins, each with a different job:

| Location | Meaning |
|---|---|
| `hacs.json` `homeassistant` | The supported floor. Raised only when code requires a newer HA. (HA core has no manifest-level minimum for custom integrations.) |
| `requirements.txt` | Latest stable HA, owned by `.github/workflows/bump-ha.yml`. Used by `scripts/develop` and the "latest" CI matrix cell. |
| `requirements-floor.txt` | Floor pins (HA + paired `pytest-homeassistant-custom-component`) for the "floor" CI matrix cell. Mirrors `hacs.json`'s floor. |

**Do not bump `homeassistant` or `pytest-homeassistant-custom-component` manually in `requirements.txt`** — the bump workflow owns that pair. Dependabot is configured to ignore both. CONTRIBUTING.md has the procedure for raising the floor (the `pytest-homeassistant-custom-component` version that pairs with a given HA release must be looked up on PyPI).

## Local development

```bash
python3 -m venv .venv                       # Python 3.14 required for the latest pin
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q                          # full test suite, ~1s
```

The CI matrix runs the same suite a second time against `requirements-floor.txt` on Python 3.12. Older HA releases pull in transitive packages (`home-assistant-bluetooth`) that don't ship Python 3.13/3.14 wheels — that's why the floor cell uses 3.12.

Lint via `ruff format . && ruff check .` (or `scripts/lint`, which auto-fixes). The lint CI job installs only `ruff` (not the full requirements) so it stays fast and decoupled from the HA Python-version requirement.

## Testing patterns

- `tests/conftest.py` enables custom-integration discovery via the `auto_enable_custom_integrations` fixture.
- Patch the API at the source class — `custom_components.spaceapi_endpoint_client.api.SpaceApiClient.async_get_space_state` — not via re-imports in `__init__.py` or `config_flow.py`. The reauth/reconfigure flows trigger `async_reload`, and the patch must be visible to the setup path too.
- After flows that call `async_update_reload_and_abort`, `await hass.async_block_till_done()` to drain the reload task before assertions, or the `verify_cleanup` fixture in pytest-homeassistant-custom-component will fail teardown.
- `MockConfigEntry.unique_id` must match `slugify(host_url)` — for `https://example.com` that's `https-example-com`, not `example-com`.

## Conventions

- Linter is strict (`select = ["ALL"]` in `.ruff.toml`) but `tests/**` and `scripts/**` have per-file ignores for the rules that don't apply to test code or CLI helpers.
- `IntegrationBlueprint*` and `Blueprint*` template names have all been renamed to `SpaceApi*`. Don't reintroduce them.
- The integration's data flow: `BinarySensor`/`Switch` → `SpaceApiEntity` (base class with device_info) → `SpaceApiDataUpdateCoordinator` → `SpaceApiClient` (in `api.py`).
- `runtime_data` is the modern HA pattern; `entry.runtime_data` carries the `SpaceApiData` dataclass with `client`, `coordinator`, and `integration`.

## Things easy to get wrong

- **Don't include the `requirements.txt` HA pin in lint.yml installs** — HA requires Python 3.14.2+, the lint runner's Python may not match, and lint doesn't need HA anyway. Only install `ruff`.
- **Don't merge a PR that touches `hacs.json`'s `homeassistant` floor without also updating `requirements-floor.txt` in the same PR.** The CI floor cell will catch the mismatch but the merge order matters.
- **The fallback in `async_get_space_state` (no API key → GET `host_url` directly) is intentional.** Don't "fix" it; users with raw `spaceapi.json` URLs depend on it.
- **The "missing API key" error in `async_set_space_state` must NOT be `SpaceApiClientAuthenticationError`** — that subclass triggers HA's reauth flow, which is wrong for a local config gap. Use the base `SpaceApiClientError`.
