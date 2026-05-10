"""Switch platform for spaceapi_endpoint_client."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

from .api import SpaceApiClientError
from .const import API_SETTLE_DELAY, LOGGER
from .entity import SpaceApiEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SpaceApiDataUpdateCoordinator
    from .data import SpaceApiConfigEntry

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="spaceapi_endpoint_client",
        name="Space Status",
        icon="mdi:rocket",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: SpaceApiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities(
        SpaceApiSwitch(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class SpaceApiSwitch(SpaceApiEntity, SwitchEntity):
    """Switch that toggles the space's open/closed state via the SpaceAPI."""

    def __init__(
        self,
        coordinator: SpaceApiDataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )
        self._attr_assumed_state = False
        self._optimistic_state: bool | None = None
        self._lock = asyncio.Lock()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self._optimistic_state is not None:
            return self._optimistic_state
        return self.coordinator.data.get("state", {}).get("open", False)

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        await self._async_set_state(open_state=True)

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        await self._async_set_state(open_state=False)

    async def _async_set_state(self, *, open_state: bool) -> None:
        """Send a state change to the API with optimistic UI + debounce."""
        verb = "open" if open_state else "close"

        if self._lock.locked():
            LOGGER.debug(
                "Ignoring turn_%s request - switch operation already in progress",
                "on" if open_state else "off",
            )
            return

        client = self.coordinator.config_entry.runtime_data.client

        async with self._lock:
            self._optimistic_state = open_state
            self.async_write_ha_state()

            try:
                LOGGER.debug(
                    "Sending POST request to %s space (state=%s)", verb, open_state
                )
                await client.async_set_space_state(open_state=open_state)
                LOGGER.debug("POST request to %s space completed successfully", verb)
                await asyncio.sleep(API_SETTLE_DELAY)
                self._optimistic_state = None
                await self.coordinator.async_request_refresh()
            except SpaceApiClientError as err:
                LOGGER.error("Failed to send POST request to %s space: %s", verb, err)
                self._optimistic_state = None
                await self.coordinator.async_request_refresh()
                msg = f"Failed to turn {'on' if open_state else 'off'} space: {err}"
                raise HomeAssistantError(msg) from err
