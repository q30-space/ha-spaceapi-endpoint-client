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

        host_url = coordinator.config_entry.data.get(CONF_HOST, "Unknown")

        device_name = f"SpaceAPI ({host_url})"
        if isinstance(coordinator.data, dict):
            space_name = coordinator.data.get("space")
            if isinstance(space_name, str) and space_name.strip():
                device_name = space_name

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            name=device_name,
            manufacturer="q30space",
            model="SpaceAPI v15",
            configuration_url=host_url,
        )
