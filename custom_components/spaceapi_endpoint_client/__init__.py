"""
Custom integration to integrate spaceapi_endpoint_client with Home Assistant.

For more details about this integration, please refer to
https://github.com/q30-space/ha-spaceapi-endpoint-client
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import IntegrationBlueprintApiClient
from .const import CONF_API_KEY, CONF_HOST, DOMAIN, LOGGER
from .coordinator import BlueprintDataUpdateCoordinator
from .data import IntegrationBlueprintData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import IntegrationBlueprintConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(minutes=1),
    )
    entry.runtime_data = IntegrationBlueprintData(
        client=IntegrationBlueprintApiClient(
            host_url=entry.data[CONF_HOST],
            session=async_get_clientsession(hass),
            api_key=entry.data.get(CONF_API_KEY),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    # Always load binary sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Conditionally load switch platform if API key is provided
    if entry.data.get(CONF_API_KEY):
        await hass.config_entries.async_forward_entry_setup(entry, Platform.SWITCH)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    # Unload binary sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Unload switch platform if it was loaded
    if entry.data.get(CONF_API_KEY):
        switch_unload = await hass.config_entries.async_unload_platforms(entry, [Platform.SWITCH])
        unload_ok = unload_ok and switch_unload
    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)

