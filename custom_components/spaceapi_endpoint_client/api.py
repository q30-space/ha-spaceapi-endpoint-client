"""Sample API Client."""

from __future__ import annotations

import asyncio
import re
import socket
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .const import LOGGER

# Constants
MAX_API_KEY_LENGTH = 256


class SpaceApiClientError(Exception):
    """Exception to indicate a general API error."""


class SpaceApiClientCommunicationError(
    SpaceApiClientError,
):
    """Exception to indicate a communication error."""


class SpaceApiClientAuthenticationError(
    SpaceApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise SpaceApiClientAuthenticationError(
            msg,
        )
    response.raise_for_status()


def validate_and_sanitize_host_url(host_url: str) -> str:
    """Validate and sanitize host URL."""
    if not host_url or not isinstance(host_url, str):
        msg = "Host URL must be a non-empty string"
        raise SpaceApiClientError(msg)

    # Strip whitespace
    host_url = host_url.strip()

    if not host_url:
        msg = "Host URL cannot be empty"
        raise SpaceApiClientError(msg)

    # Parse URL
    try:
        parsed = urlparse(host_url)
    except Exception as exception:
        msg = f"Invalid URL format: {exception}"
        raise SpaceApiClientError(msg) from exception

    # Validate scheme - only allow http and https
    if parsed.scheme not in ("http", "https"):
        if parsed.scheme:
            msg = f"URL scheme must be http or https, got: {parsed.scheme}"
        else:
            msg = "URL must include a scheme (http:// or https://)"
        raise SpaceApiClientError(msg)

    # Validate netloc (domain) exists
    if not parsed.netloc:
        msg = "URL must include a valid domain"
        raise SpaceApiClientError(msg)

    # Strip trailing slashes
    return host_url.rstrip("/")


_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x1F\x7F-\x9F]")


def validate_and_sanitize_api_key(api_key: str | None) -> str:
    """Validate and sanitize API key."""
    if api_key is None:
        return ""

    if not isinstance(api_key, str):
        msg = "API key must be a string"
        raise SpaceApiClientError(msg)

    # Strip surrounding whitespace; an outright empty key means "no key configured"
    api_key = api_key.strip()
    if not api_key:
        return ""

    # Reject control chars rather than silently stripping them — silent stripping
    # produces a key that doesn't match what the user pasted, which then fails
    # authentication with no visible cause.
    offending = sorted({hex(ord(c)) for c in _CONTROL_CHAR_PATTERN.findall(api_key)})
    if offending:
        LOGGER.warning("API key contains control characters: %s", ", ".join(offending))
        msg = "API key contains control characters"
        raise SpaceApiClientError(msg)

    # Length check (range chosen for typical hex/base64 keys)
    if len(api_key) > MAX_API_KEY_LENGTH:
        msg = f"API key must be between 1 and {MAX_API_KEY_LENGTH} characters"
        raise SpaceApiClientError(msg)

    return api_key


class SpaceApiClient:
    """SpaceAPI Client."""

    def __init__(
        self,
        host_url: str,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
    ) -> None:
        """Initialize SpaceAPI Client."""
        # Validate and sanitize inputs
        self._host_url = validate_and_sanitize_host_url(host_url)
        self._api_key = validate_and_sanitize_api_key(api_key)
        self._session = session

    async def async_get_space_state(self) -> Any:
        """Get space state from the API."""
        try:
            return await self._api_wrapper(
                method="get",
                url=f"{self._host_url}/api/space",
            )
        except SpaceApiClientAuthenticationError:
            raise
        except SpaceApiClientCommunicationError as exception:
            # Fallback to a direct GET on the host URL only in read-only mode.
            # When a key is configured the user expects API-server semantics, so
            # we surface the original error instead of silently degrading.
            if self._api_key:
                raise
            LOGGER.debug(
                "API endpoint /api/space failed, trying fallback to direct host_url"
            )
            try:
                return await self._api_wrapper(
                    method="get",
                    url=self._host_url,
                )
            except SpaceApiClientError as fallback_exception:
                msg = (
                    f"Both /api/space ({exception}) and direct host fallback "
                    f"({fallback_exception}) failed"
                )
                raise SpaceApiClientCommunicationError(msg) from exception

    async def async_set_space_state(self, *, open_state: bool) -> Any:
        """Set space state via the API."""
        if not self._api_key:
            # Local configuration error, not a server-rejected credential. Using
            # the auth-error class here would trigger HA's reauth flow, which is
            # the wrong UX since the user never had a key in the first place.
            msg = "API key is required to set space state"
            raise SpaceApiClientError(msg)
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
            async with asyncio.timeout(10):
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
            raise SpaceApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise SpaceApiClientCommunicationError(
                msg,
            ) from exception
        except SpaceApiClientError:
            # Already shaped for the caller (e.g. auth error)
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exception:
            msg = f"Unexpected error fetching information - {exception}"
            raise SpaceApiClientError(
                msg,
            ) from exception
