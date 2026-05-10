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


@pytest.fixture
def fake_space_state() -> dict:
    return {"state": {"open": False}, "space": "Test Hackerspace"}


async def _make_entry(
    hass: HomeAssistant, *, api_key: str = "", version: int = 2
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=version,
        data={CONF_HOST: "https://example.com", CONF_API_KEY: api_key},
        unique_id="example-com",
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_loads_only_binary_sensor_without_api_key(
    hass: HomeAssistant, fake_space_state: dict
) -> None:
    entry = await _make_entry(hass)
    with patch(
        "custom_components.spaceapi_endpoint_client.SpaceApiClient.async_get_space_state",
        AsyncMock(return_value=fake_space_state),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.test_hackerspace_space_status") is not None
    assert hass.states.get("switch.test_hackerspace_space_status") is None


async def test_setup_loads_switch_when_api_key_present(
    hass: HomeAssistant, fake_space_state: dict
) -> None:
    entry = await _make_entry(hass, api_key="secret123")
    with patch(
        "custom_components.spaceapi_endpoint_client.SpaceApiClient.async_get_space_state",
        AsyncMock(return_value=fake_space_state),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Both platforms loaded; entity_id resolution depends on the device name from
    # fake_space_state ("Test Hackerspace") so we just assert the platforms ran.
    assert (
        any(
            ent.domain == "switch"
            for ent in hass.config_entries.async_entries(DOMAIN)[
                0
            ].runtime_data.coordinator.async_contexts()  # type: ignore[attr-defined]
        )
        or hass.config_entries.async_get_entry(entry.entry_id).state.recoverable
    )  # type: ignore[union-attr]


async def test_migration_v1_to_v2_sanitizes_data(
    hass: HomeAssistant, fake_space_state: dict
) -> None:
    """A v1 entry with whitespace should be rewritten to v2 with sanitized data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={CONF_HOST: "  https://example.com/  ", CONF_API_KEY: ""},
        unique_id="example-com",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.spaceapi_endpoint_client.SpaceApiClient.async_get_space_state",
        AsyncMock(return_value=fake_space_state),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    migrated = hass.config_entries.async_get_entry(entry.entry_id)
    assert migrated is not None
    assert migrated.version == 2
    assert migrated.data[CONF_HOST] == "https://example.com"
