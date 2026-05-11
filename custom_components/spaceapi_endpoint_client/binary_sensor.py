"""Binary sensor platform for spaceapi_endpoint_client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import SpaceApiEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SpaceApiDataUpdateCoordinator
    from .data import SpaceApiConfigEntry

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="space_status",
        name="Space Status",
        icon="mdi:rocket",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: SpaceApiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    async_add_entities(
        SpaceApiBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class SpaceApiBinarySensor(
    SpaceApiEntity,
    BinarySensorEntity,
):
    """Binary sensor reflecting the space's open/closed state."""

    def __init__(
        self,
        coordinator: SpaceApiDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.get("state", {}).get("open", False)
