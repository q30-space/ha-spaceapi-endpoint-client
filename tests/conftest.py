"""Common fixtures for the SpaceAPI Endpoint Client test suite."""

from __future__ import annotations

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Make the custom integration discoverable in every test."""
    return
