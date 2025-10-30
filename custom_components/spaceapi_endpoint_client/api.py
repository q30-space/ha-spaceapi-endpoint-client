"""Sample API Client."""

from __future__ import annotations

import socket
from typing import Any

import aiohttp
import async_timeout


class IntegrationBlueprintApiClientError(Exception):
    """Exception to indicate a general API error."""


class IntegrationBlueprintApiClientCommunicationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate a communication error."""


class IntegrationBlueprintApiClientAuthenticationError(
    IntegrationBlueprintApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise IntegrationBlueprintApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


class IntegrationBlueprintApiClient:
    """SpaceAPI Client."""

    def __init__(
        self,
        host_url: str,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
    ) -> None:
        """Initialize SpaceAPI Client."""
        self._host_url = host_url.rstrip("/")
        self._api_key = api_key or ""
        self._session = session

    async def async_get_space_state(self) -> Any:
        """Get space state from the API."""
        return await self._api_wrapper(
            method="get",
            url=f"{self._host_url}/api/space",
        )

    async def async_set_space_state(self, *, open_state: bool) -> Any:
        """Set space state via the API."""
        if not self._api_key:
            msg = "API key is required to set space state"
            raise IntegrationBlueprintApiClientAuthenticationError(msg)
        message = "Space was switched on" if open_state else "Space was switched off"
        return await self._api_wrapper(
            method="post",
            url=f"{self._host_url}/api/space/state",
            data={
                "open": open_state,
                "message": message,
                "trigger_person": "Home Assistant SpaceAPI",
            },
            headers={
                "X-API-Key": self._api_key,
                "Content-Type": "application/json",
            },
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _verify_response_or_raise(response)
                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise IntegrationBlueprintApiClientCommunicationError(
                msg,
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise IntegrationBlueprintApiClientError(
                msg,
            ) from exception
