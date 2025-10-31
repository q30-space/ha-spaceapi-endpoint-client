"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from slugify import slugify

from .api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
    validate_and_sanitize_api_key,
    validate_and_sanitize_host_url,
)
from .const import CONF_API_KEY, CONF_HOST, DOMAIN, LOGGER


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            # Validate inputs before attempting connection
            # Validate host_url
            host_url = user_input[CONF_HOST]
            if not host_url or not isinstance(host_url, str):
                _errors[CONF_HOST] = "invalid_url"
            else:
                try:
                    validate_and_sanitize_host_url(host_url)
                except IntegrationBlueprintApiClientError:
                    _errors[CONF_HOST] = "invalid_url"

            # Validate api_key if provided
            api_key = user_input.get(CONF_API_KEY)
            if api_key:
                try:
                    validate_and_sanitize_api_key(api_key)
                except IntegrationBlueprintApiClientError:
                    _errors[CONF_API_KEY] = "invalid_api_key"

            # Only proceed with connection test if validation passed
            if not _errors:
                try:
                    await self._test_credentials(
                        host_url=user_input[CONF_HOST],
                        api_key=user_input.get(CONF_API_KEY),
                    )
                    # If connection test succeeds, create the config entry
                    await self.async_set_unique_id(
                        unique_id=slugify(user_input[CONF_HOST])
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"SpaceAPI ({user_input[CONF_HOST]})",
                        data=user_input,
                    )
                except IntegrationBlueprintApiClientAuthenticationError as exception:
                    LOGGER.warning(exception)
                    _errors["base"] = "auth"
                except IntegrationBlueprintApiClientCommunicationError as exception:
                    LOGGER.error(exception)
                    _errors["base"] = "connection"
                except IntegrationBlueprintApiClientError as exception:
                    LOGGER.exception(exception)
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
        client = IntegrationBlueprintApiClient(
            host_url=host_url,
            session=async_create_clientsession(self.hass),
            api_key=api_key or "",
        )
        await client.async_get_space_state()
