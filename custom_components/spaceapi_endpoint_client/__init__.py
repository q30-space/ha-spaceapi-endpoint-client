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

from .api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientError,
    validate_and_sanitize_api_key,
    validate_and_sanitize_host_url,
)
from .const import CONF_API_KEY, CONF_HOST, DOMAIN, LOGGER
from .coordinator import BlueprintDataUpdateCoordinator
from .data import IntegrationBlueprintData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import IntegrationBlueprintConfigEntry


def _platforms_for(entry_data: dict) -> list[Platform]:
    """Return the platforms that should be loaded for this entry."""
    platforms: list[Platform] = [Platform.BINARY_SENSOR]
    if entry_data.get(CONF_API_KEY):
        platforms.append(Platform.SWITCH)
    return platforms


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
        config_entry=entry,
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

    await hass.config_entries.async_forward_entry_setups(
        entry, _platforms_for(entry.data)
    )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(
        entry, _platforms_for(entry.data)
    )


async def async_reload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


CURRENT_ENTRY_VERSION = 2


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Migrate old entries to the latest schema."""
    if entry.version > CURRENT_ENTRY_VERSION:
        return False

    if entry.version == 1:
        try:
            new_data = {
                **entry.data,
                CONF_HOST: validate_and_sanitize_host_url(entry.data[CONF_HOST]),
                CONF_API_KEY: validate_and_sanitize_api_key(
                    entry.data.get(CONF_API_KEY)
                ),
            }
        except IntegrationBlueprintApiClientError:
            LOGGER.exception("Failed to migrate config entry %s to v2", entry.entry_id)
            return False
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        LOGGER.info("Migrated config entry %s to v2", entry.entry_id)

    return True
