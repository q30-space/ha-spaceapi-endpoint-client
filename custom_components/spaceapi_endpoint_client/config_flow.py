"""Config flow for the SpaceAPI Endpoint Client integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from slugify import slugify

from .api import (
    SpaceApiClient,
    SpaceApiClientAuthenticationError,
    SpaceApiClientCommunicationError,
    SpaceApiClientError,
    validate_and_sanitize_api_key,
    validate_and_sanitize_host_url,
)
from .const import CONF_API_KEY, CONF_HOST, DOMAIN, LOGGER


class SpaceApiFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for the SpaceAPI Endpoint Client integration."""

    VERSION = 2

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors: dict[str, str] = {}
        sanitized_host: str | None = None
        sanitized_key: str = ""
        if user_input is not None:
            try:
                sanitized_host = validate_and_sanitize_host_url(
                    user_input.get(CONF_HOST, "")
                )
            except SpaceApiClientError:
                _errors[CONF_HOST] = "invalid_url"

            try:
                sanitized_key = validate_and_sanitize_api_key(
                    user_input.get(CONF_API_KEY)
                )
            except SpaceApiClientError:
                _errors[CONF_API_KEY] = "invalid_api_key"

            if not _errors and sanitized_host is not None:
                try:
                    await self._test_credentials(
                        host_url=sanitized_host,
                        api_key=sanitized_key or None,
                    )
                    await self.async_set_unique_id(unique_id=slugify(sanitized_host))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"SpaceAPI ({sanitized_host})",
                        data={
                            CONF_HOST: sanitized_host,
                            CONF_API_KEY: sanitized_key,
                        },
                    )
                except SpaceApiClientAuthenticationError as exception:
                    LOGGER.warning("Auth failed during config flow: %s", exception)
                    _errors["base"] = "auth"
                except SpaceApiClientCommunicationError as exception:
                    LOGGER.error("Connection failed during config flow: %s", exception)
                    _errors["base"] = "connection"
                except SpaceApiClientError:
                    LOGGER.exception("Unexpected error during config flow")
                    _errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or {}).get(CONF_HOST, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                    vol.Optional(
                        CONF_API_KEY,
                        default=(user_input or {}).get(CONF_API_KEY, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_credentials(
        self, host_url: str, api_key: str | None = None
    ) -> None:
        """Validate credentials."""
        client = SpaceApiClient(
            host_url=host_url,
            session=async_create_clientsession(self.hass),
            api_key=api_key or "",
        )
        await client.async_get_space_state()
