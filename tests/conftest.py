"""Common fixtures for the SpaceAPI Endpoint Client test suite."""

from __future__ import annotations

import threading

import pytest
from homeassistant.const import __version__ as _ha_version

pytest_plugins = ["pytest_homeassistant_custom_component"]


_HA_VERSION_TUPLE = tuple(int(p) for p in _ha_version.split(".")[:3])

# pytest-homeassistant-custom-component 0.13.190 (paired with our HA 2024.12.0
# floor) enforces a strict lingering-thread check in verify_cleanup that fires
# before the hass fixture stops HA. HA's own _run_safe_shutdown_loop executor
# thread, started during normal integration setup, is still alive at check
# time. Newer plugin versions paired with the "latest" cell drop the check.
#
# Filter that thread out of threading.enumerate() on the floor cell only.
# Both threads_before and the post-check enumeration exclude it, so the
# diff stays clean. The patch lifts when the floor is raised past 2025.1.
if _HA_VERSION_TUPLE < (2025, 1, 0):
    _real_enumerate = threading.enumerate

    def _filtered_enumerate() -> list[threading.Thread]:
        return [t for t in _real_enumerate() if "_run_safe_shutdown_loop" not in t.name]

    threading.enumerate = _filtered_enumerate


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Make the custom integration discoverable in every test."""
    return
