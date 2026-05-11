"""Custom types for spaceapi_endpoint_client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import SpaceApiClient
    from .coordinator import SpaceApiDataUpdateCoordinator


type SpaceApiConfigEntry = ConfigEntry[SpaceApiData]


@dataclass
class SpaceApiData:
    """Runtime data shared across the SpaceAPI integration."""

    client: SpaceApiClient
    coordinator: SpaceApiDataUpdateCoordinator
    integration: Integration
