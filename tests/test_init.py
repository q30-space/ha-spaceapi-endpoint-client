"""Tests for setup/unload/migration of the integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.spaceapi_endpoint_client.const import (
    CONF_API_KEY,
    CONF_HOST,
    DOMAIN,
)

API_PATCH_TARGET = (
    "custom_components.spaceapi_endpoint_client"
    ".api.SpaceApiClient.async_get_space_state"
)


@pytest.fixture
def fake_space_state() -> dict:
    return {"state": {"open": False}, "space": "Test Hackerspace"}


def _make_entry(hass: HomeAssistant, *, api_key: str = "") -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_HOST: "https://example.com", CONF_API_KEY: api_key},
        unique_id="https-example-com",
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_loads_only_binary_sensor_without_api_key(
    hass: HomeAssistant, fake_space_state: dict
) -> None:
    entry = _make_entry(hass)
    with patch(API_PATCH_TARGET, AsyncMock(return_value=fake_space_state)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.async_entity_ids("binary_sensor")
    assert not hass.states.async_entity_ids("switch")


async def test_setup_loads_switch_when_api_key_present(
    hass: HomeAssistant, fake_space_state: dict
) -> None:
    entry = _make_entry(hass, api_key="secret123")
    with patch(API_PATCH_TARGET, AsyncMock(return_value=fake_space_state)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.async_entity_ids("binary_sensor")
    assert hass.states.async_entity_ids("switch")


async def test_migration_v1_to_v2_sanitizes_data(
    hass: HomeAssistant, fake_space_state: dict
) -> None:
    """A v1 entry with whitespace should be rewritten to v2 with sanitized data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={CONF_HOST: "  https://example.com/  ", CONF_API_KEY: ""},
        unique_id="https-example-com",
    )
    entry.add_to_hass(hass)

    with patch(API_PATCH_TARGET, AsyncMock(return_value=fake_space_state)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    migrated = hass.config_entries.async_get_entry(entry.entry_id)
    assert migrated is not None
    assert migrated.version == 2
    assert migrated.data[CONF_HOST] == "https://example.com"
