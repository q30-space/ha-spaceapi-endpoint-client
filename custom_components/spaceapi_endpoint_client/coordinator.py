"""DataUpdateCoordinator for spaceapi_endpoint_client."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SpaceApiClientAuthenticationError,
    SpaceApiClientError,
)


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class SpaceApiDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the API."""

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            return await self.config_entry.runtime_data.client.async_get_space_state()
        except SpaceApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(str(exception)) from exception
        except SpaceApiClientError as exception:
            raise UpdateFailed(str(exception)) from exception
