"""Switch platform for spaceapi_endpoint_client."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

from .const import LOGGER
from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BlueprintDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="spaceapi_endpoint_client",
        name="Space Status",
        icon="mdi:door-open",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities(
        IntegrationBlueprintSwitch(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class IntegrationBlueprintSwitch(IntegrationBlueprintEntity, SwitchEntity):
    """spaceapi_endpoint_client switch class."""

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_assumed_state = False
        self._optimistic_state: bool | None = None
        self._is_switching = False  # Lock to prevent concurrent state changes

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        # Use optimistic state if available, otherwise use coordinator data
        if self._optimistic_state is not None:
            return self._optimistic_state
        return self.coordinator.data.get("state", {}).get("open", False)

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        # Check if already switching to prevent rapid-fire clicks
        if self._is_switching:
            LOGGER.debug(
                "Ignoring turn_on request - switch operation already in progress"
            )
            return

        # Set lock to prevent concurrent operations
        self._is_switching = True

        # Set optimistic state immediately for responsive UI
        self._optimistic_state = True
        self.async_write_ha_state()

        try:
            # Send the API request
            LOGGER.debug("Sending POST request to open space (state=True)")
            await (
                self.coordinator.config_entry.runtime_data.client.async_set_space_state(
                    open_state=True
                )
            )
            LOGGER.debug("POST request to open space completed successfully")
            # Wait a bit for the API to process the change
            await asyncio.sleep(0.5)
            # Clear optimistic state and refresh from server
            self._optimistic_state = None
            await self.coordinator.async_request_refresh()
        except Exception as err:
            # If API call fails, revert optimistic state and refresh
            LOGGER.error("Failed to send POST request to open space: %s", err)
            self._optimistic_state = None
            await self.coordinator.async_request_refresh()
            msg = f"Failed to turn on space: {err}"
            raise HomeAssistantError(msg) from err
        finally:
            # Always release the lock
            self._is_switching = False

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        # Check if already switching to prevent rapid-fire clicks
        if self._is_switching:
            LOGGER.debug(
                "Ignoring turn_off request - switch operation already in progress"
            )
            return

        # Set lock to prevent concurrent operations
        self._is_switching = True

        # Set optimistic state immediately for responsive UI
        self._optimistic_state = False
        self.async_write_ha_state()

        try:
            # Send the API request
            LOGGER.debug("Sending POST request to close space (state=False)")
            await (
                self.coordinator.config_entry.runtime_data.client.async_set_space_state(
                    open_state=False
                )
            )
            LOGGER.debug("POST request to close space completed successfully")
            # Wait a bit for the API to process the change
            await asyncio.sleep(0.5)
            # Clear optimistic state and refresh from server
            self._optimistic_state = None
            await self.coordinator.async_request_refresh()
        except Exception as err:
            # If API call fails, revert optimistic state and refresh
            LOGGER.error("Failed to send POST request to close space: %s", err)
            self._optimistic_state = None
            await self.coordinator.async_request_refresh()
            msg = f"Failed to turn off space: {err}"
            raise HomeAssistantError(msg) from err
        finally:
            # Always release the lock
            self._is_switching = False
