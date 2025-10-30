"""BlueprintEntity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_HOST
from .coordinator import BlueprintDataUpdateCoordinator


class IntegrationBlueprintEntity(CoordinatorEntity[BlueprintDataUpdateCoordinator]):
    """BlueprintEntity class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: BlueprintDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id

        # Get the host URL to use as device name
        host_url = coordinator.config_entry.data.get(CONF_HOST, "Unknown")

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            name=f"SpaceAPI ({host_url})",
            manufacturer="SpaceAPI",
            model="SpaceAPI v15",
            configuration_url=host_url,
        )
