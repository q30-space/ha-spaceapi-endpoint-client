"""Unit tests for the SpaceAPI client wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.spaceapi_endpoint_client.api import (
    MAX_API_KEY_LENGTH,
    SpaceApiClient,
    SpaceApiClientAuthenticationError,
    SpaceApiClientCommunicationError,
    SpaceApiClientError,
    validate_and_sanitize_api_key,
    validate_and_sanitize_host_url,
)


class TestValidateHostUrl:
    """validate_and_sanitize_host_url."""

    def test_strips_whitespace_and_trailing_slash(self) -> None:
        assert (
            validate_and_sanitize_host_url("  https://example.com/  ")
            == "https://example.com"
        )

    def test_rejects_missing_scheme(self) -> None:
        with pytest.raises(SpaceApiClientError):
            validate_and_sanitize_host_url("example.com")

    def test_rejects_unsupported_scheme(self) -> None:
        with pytest.raises(SpaceApiClientError):
            validate_and_sanitize_host_url("ftp://example.com")

    def test_rejects_empty(self) -> None:
        with pytest.raises(SpaceApiClientError):
            validate_and_sanitize_host_url("   ")

    def test_rejects_non_string(self) -> None:
        with pytest.raises(SpaceApiClientError):
            validate_and_sanitize_host_url(None)  # type: ignore[arg-type]


class TestValidateApiKey:
    """validate_and_sanitize_api_key."""

    def test_returns_empty_for_none(self) -> None:
        assert validate_and_sanitize_api_key(None) == ""

    def test_returns_empty_for_blank(self) -> None:
        assert validate_and_sanitize_api_key("   ") == ""

    def test_strips_outer_whitespace(self) -> None:
        assert validate_and_sanitize_api_key(" abc123 ") == "abc123"

    def test_rejects_control_characters(self) -> None:
        with pytest.raises(SpaceApiClientError):
            validate_and_sanitize_api_key("abc\x00def")
        with pytest.raises(SpaceApiClientError):
            validate_and_sanitize_api_key("abc\ndef")

    def test_rejects_overlength(self) -> None:
        with pytest.raises(SpaceApiClientError):
            validate_and_sanitize_api_key("a" * (MAX_API_KEY_LENGTH + 1))

    def test_accepts_typical_hex(self) -> None:
        key = "a" * 64
        assert validate_and_sanitize_api_key(key) == key


def _mock_session_returning(
    json_payloads: dict[str, dict] | None = None,
    raise_for_url: dict[str, Exception] | None = None,
) -> MagicMock:
    """Build a fake aiohttp session that responds based on URL."""
    json_payloads = json_payloads or {}
    raise_for_url = raise_for_url or {}

    async def request(method: str, url: str, **_: object) -> MagicMock:
        if url in raise_for_url:
            raise raise_for_url[url]
        response = MagicMock()
        response.status = 200
        response.raise_for_status = MagicMock()
        response.json = AsyncMock(return_value=json_payloads.get(url, {}))
        return response

    session = MagicMock()
    session.request = AsyncMock(side_effect=request)
    return session


class TestAsyncGetSpaceState:
    """async_get_space_state with the fallback logic."""

    async def test_primary_endpoint_success(self) -> None:
        session = _mock_session_returning(
            json_payloads={"https://example.com/api/space": {"state": {"open": True}}}
        )
        client = SpaceApiClient(host_url="https://example.com", session=session)
        result = await client.async_get_space_state()
        assert result == {"state": {"open": True}}

    async def test_falls_back_to_host_url_when_no_api_key(self) -> None:
        import aiohttp

        session = _mock_session_returning(
            json_payloads={"https://example.com": {"state": {"open": False}}},
            raise_for_url={
                "https://example.com/api/space": aiohttp.ClientError("boom"),
            },
        )
        client = SpaceApiClient(host_url="https://example.com", session=session)
        result = await client.async_get_space_state()
        assert result == {"state": {"open": False}}

    async def test_no_fallback_when_api_key_present(self) -> None:
        import aiohttp

        session = _mock_session_returning(
            raise_for_url={
                "https://example.com/api/space": aiohttp.ClientError("boom"),
            },
        )
        client = SpaceApiClient(
            host_url="https://example.com", session=session, api_key="abc123"
        )
        with pytest.raises(SpaceApiClientCommunicationError):
            await client.async_get_space_state()

    async def test_no_fallback_on_auth_error(self) -> None:
        async def request(method: str, url: str, **_: object) -> MagicMock:
            response = MagicMock()
            response.status = 401
            response.raise_for_status = MagicMock()
            response.json = AsyncMock(return_value={})
            return response

        session = MagicMock()
        session.request = AsyncMock(side_effect=request)
        client = SpaceApiClient(host_url="https://example.com", session=session)
        with pytest.raises(SpaceApiClientAuthenticationError):
            await client.async_get_space_state()


class TestAsyncSetSpaceState:
    """async_set_space_state."""

    async def test_missing_api_key_raises_generic_error(self) -> None:
        # Critical: must NOT raise the auth-error subclass, otherwise the
        # coordinator would translate it into a spurious reauth flow.
        session = _mock_session_returning()
        client = SpaceApiClient(host_url="https://example.com", session=session)
        with pytest.raises(SpaceApiClientError) as excinfo:
            await client.async_set_space_state(open_state=True)
        assert not isinstance(excinfo.value, SpaceApiClientAuthenticationError)
