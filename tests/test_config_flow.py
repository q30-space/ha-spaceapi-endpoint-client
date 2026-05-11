"""Tests for the config flow (user, reconfigure, reauth)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.spaceapi_endpoint_client.api import (
    SpaceApiClientAuthenticationError,
    SpaceApiClientCommunicationError,
)
from custom_components.spaceapi_endpoint_client.const import (
    CONF_API_KEY,
    CONF_HOST,
    DOMAIN,
)

_HA_VERSION_TUPLE = tuple(int(p) for p in HA_VERSION.split(".")[:3])


@pytest.fixture
def mock_get_space_state():
    """Patch the API call so the flow's _test_credentials succeeds by default."""
    with patch(
        "custom_components.spaceapi_endpoint_client.api.SpaceApiClient.async_get_space_state",
        AsyncMock(return_value={"state": {"open": True}, "space": "Test"}),
    ) as mock:
        yield mock


@pytest.mark.skipif(
    _HA_VERSION_TUPLE < (2025, 1, 0),
    reason=(
        "HA's _run_safe_shutdown_loop executor thread trips "
        "pytest-homeassistant-custom-component 0.13.190's "
        "lingering-thread teardown check; the check is not "
        "enforced on newer plugin versions"
    ),
)
async def test_user_flow_happy_path(
    hass: HomeAssistant, mock_get_space_state: AsyncMock
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "  https://example.com/  ", CONF_API_KEY: "abc123"},
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    # Sanitized values are persisted, not the raw user input.
    assert result["data"][CONF_HOST] == "https://example.com"
    assert result["data"][CONF_API_KEY] == "abc123"


async def test_user_flow_invalid_url(
    hass: HomeAssistant,
    mock_get_space_state: AsyncMock,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "not-a-url", CONF_API_KEY: ""},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "invalid_url"}


async def test_user_flow_invalid_api_key_control_chars(
    hass: HomeAssistant,
    mock_get_space_state: AsyncMock,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "https://example.com", CONF_API_KEY: "abc\ndef"},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}


async def test_user_flow_auth_error(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.spaceapi_endpoint_client.api.SpaceApiClient.async_get_space_state",
        AsyncMock(side_effect=SpaceApiClientAuthenticationError("nope")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "https://example.com",
                CONF_API_KEY: "wrongkey",
            },
        )
    assert result["errors"] == {"base": "auth"}


async def test_user_flow_connection_error(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.spaceapi_endpoint_client.api.SpaceApiClient.async_get_space_state",
        AsyncMock(side_effect=SpaceApiClientCommunicationError("down")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "https://example.com", CONF_API_KEY: ""},
        )
    assert result["errors"] == {"base": "connection"}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_get_space_state: AsyncMock,
) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "https://example.com", CONF_API_KEY: ""},
        unique_id="https-example-com",
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "https://example.com", CONF_API_KEY: ""},
    )
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_updates_api_key(
    hass: HomeAssistant,
    mock_get_space_state: AsyncMock,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "https://example.com", CONF_API_KEY: "old"},
        unique_id="https-example-com",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: "newkey"}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "newkey"


async def test_reconfigure_flow_updates_host_and_key(
    hass: HomeAssistant,
    mock_get_space_state: AsyncMock,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "https://example.com", CONF_API_KEY: ""},
        unique_id="https-example-com",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "https://example.com", CONF_API_KEY: "abc123"},
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_API_KEY] == "abc123"
