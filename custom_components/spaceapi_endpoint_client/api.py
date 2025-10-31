"""Sample API Client."""

from __future__ import annotations

import re
import socket
from typing import Any
from urllib.parse import urlparse

import aiohttp
import async_timeout

from .const import LOGGER

# Constants
MAX_API_KEY_LENGTH = 256


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


def validate_and_sanitize_host_url(host_url: str) -> str:
    """Validate and sanitize host URL."""
    if not host_url or not isinstance(host_url, str):
        msg = "Host URL must be a non-empty string"
        raise IntegrationBlueprintApiClientError(msg)

    # Strip whitespace
    host_url = host_url.strip()

    if not host_url:
        msg = "Host URL cannot be empty"
        raise IntegrationBlueprintApiClientError(msg)

    # Parse URL
    try:
        parsed = urlparse(host_url)
    except Exception as exception:
        msg = f"Invalid URL format: {exception}"
        raise IntegrationBlueprintApiClientError(msg) from exception

    # Validate scheme - only allow http and https
    if parsed.scheme not in ("http", "https"):
        if parsed.scheme:
            msg = f"URL scheme must be http or https, got: {parsed.scheme}"
        else:
            msg = "URL must include a scheme (http:// or https://)"
        raise IntegrationBlueprintApiClientError(msg)

    # Validate netloc (domain) exists
    if not parsed.netloc:
        msg = "URL must include a valid domain"
        raise IntegrationBlueprintApiClientError(msg)

    # Strip trailing slashes
    return host_url.rstrip("/")


def validate_and_sanitize_api_key(api_key: str | None) -> str:
    """Validate and sanitize API key."""
    if api_key is None:
        return ""

    if not isinstance(api_key, str):
        msg = "API key must be a string"
        raise IntegrationBlueprintApiClientError(msg)

    # Strip whitespace
    api_key = api_key.strip()

    if not api_key:
        return ""

    # Remove control characters (newlines, null bytes, etc.)
    # Allow: alphanumeric, dash, underscore, equals sign
    sanitized = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", api_key)

    # Check for unusual characters (but allow them for compatibility)
    safe_pattern = re.compile(r"^[a-zA-Z0-9_\-=]+$")
    if not safe_pattern.match(sanitized):
        LOGGER.warning(
            "API key contains unusual characters. "
            "Consider using a key generated with 'openssl rand -hex 32'"
        )

    # Validate reasonable length (1-256 characters)
    if len(sanitized) < 1 or len(sanitized) > MAX_API_KEY_LENGTH:
        msg = f"API key must be between 1 and {MAX_API_KEY_LENGTH} characters"
        raise IntegrationBlueprintApiClientError(msg)

    return sanitized


class IntegrationBlueprintApiClient:
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
        # First, try the API endpoint
        try:
            return await self._api_wrapper(
                method="get",
                url=f"{self._host_url}/api/space",
            )
        except IntegrationBlueprintApiClientAuthenticationError:
            # Never fallback on authentication errors
            raise
        except IntegrationBlueprintApiClientCommunicationError as exception:
            # Only fallback if no API key is provided
            if not self._api_key:
                LOGGER.debug(
                    "API endpoint /api/space failed, trying fallback to direct host_url"
                )
                try:
                    # Fallback: try GET request directly to host_url
                    return await self._api_wrapper(
                        method="get",
                        url=self._host_url,
                    )
                except Exception as fallback_exception:
                    # If fallback also fails, propagate the original error
                    # but chain it with the fallback exception for debugging
                    raise exception from fallback_exception
            # If API key is provided, don't fallback - raise the original error
            raise

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
