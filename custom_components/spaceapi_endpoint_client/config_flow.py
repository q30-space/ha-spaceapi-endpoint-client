"""Config flow for the SpaceAPI Endpoint Client integration."""

from __future__ import annotations

from typing import Any

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


def _user_schema(host_default: Any, api_key_default: Any) -> vol.Schema:
    """Build the host/api_key form schema with the supplied defaults."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host_default): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL),
            ),
            vol.Optional(CONF_API_KEY, default=api_key_default): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
            ),
        },
    )


def _reauth_schema() -> vol.Schema:
    """Build a reauth-only schema (just the API key)."""
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
            ),
        },
    )


class SpaceApiFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for the SpaceAPI Endpoint Client integration."""

    VERSION = 2

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        sanitized_host: str | None = None
        sanitized_key: str = ""

        if user_input is not None:
            sanitized_host, sanitized_key, errors = self._sanitize(user_input)

            if not errors and sanitized_host is not None:
                errors = await self._test_or_collect_errors(
                    host_url=sanitized_host, api_key=sanitized_key
                )
                if not errors:
                    await self.async_set_unique_id(unique_id=slugify(sanitized_host))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"SpaceAPI ({sanitized_host})",
                        data={
                            CONF_HOST: sanitized_host,
                            CONF_API_KEY: sanitized_key,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(
                host_default=(user_input or {}).get(CONF_HOST, vol.UNDEFINED),
                api_key_default=(user_input or {}).get(CONF_API_KEY, vol.UNDEFINED),
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry (host or API key)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            sanitized_host, sanitized_key, errors = self._sanitize(user_input)

            if not errors and sanitized_host is not None:
                # Allow editing the host even to a different URL, but enforce
                # uniqueness against other entries (skipping the one we're editing).
                await self.async_set_unique_id(unique_id=slugify(sanitized_host))
                self._abort_if_unique_id_mismatch(
                    reason="reconfigure_unique_id_mismatch"
                )

                errors = await self._test_or_collect_errors(
                    host_url=sanitized_host, api_key=sanitized_key
                )
                if not errors:
                    return self.async_update_reload_and_abort(
                        entry,
                        title=f"SpaceAPI ({sanitized_host})",
                        data_updates={
                            CONF_HOST: sanitized_host,
                            CONF_API_KEY: sanitized_key,
                        },
                    )

        defaults = user_input or entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(
                host_default=defaults.get(CONF_HOST, vol.UNDEFINED),
                api_key_default=defaults.get(CONF_API_KEY, vol.UNDEFINED),
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict,  # noqa: ARG002 — required by HA but unused
    ) -> config_entries.ConfigFlowResult:
        """Trigger the reauth confirmation step."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Re-collect the API key for an existing entry."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                sanitized_key = validate_and_sanitize_api_key(
                    user_input.get(CONF_API_KEY)
                )
            except SpaceApiClientError:
                errors[CONF_API_KEY] = "invalid_api_key"
                sanitized_key = ""

            if not errors:
                errors = await self._test_or_collect_errors(
                    host_url=entry.data[CONF_HOST], api_key=sanitized_key
                )
                if not errors:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_API_KEY: sanitized_key},
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_reauth_schema(),
            errors=errors,
            description_placeholders={"host": entry.data.get(CONF_HOST, "")},
        )

    @staticmethod
    def _sanitize(
        user_input: dict,
    ) -> tuple[str | None, str, dict[str, str]]:
        """Run the sanitizers and collect per-field errors."""
        errors: dict[str, str] = {}
        sanitized_host: str | None = None
        sanitized_key: str = ""

        try:
            sanitized_host = validate_and_sanitize_host_url(
                user_input.get(CONF_HOST, "")
            )
        except SpaceApiClientError:
            errors[CONF_HOST] = "invalid_url"

        try:
            sanitized_key = validate_and_sanitize_api_key(user_input.get(CONF_API_KEY))
        except SpaceApiClientError:
            errors[CONF_API_KEY] = "invalid_api_key"

        return sanitized_host, sanitized_key, errors

    async def _test_or_collect_errors(
        self, *, host_url: str, api_key: str
    ) -> dict[str, str]:
        """Try the credentials and return form errors instead of raising."""
        try:
            await self._test_credentials(host_url=host_url, api_key=api_key or None)
        except SpaceApiClientAuthenticationError as exception:
            LOGGER.warning("Auth failed during config flow: %s", exception)
            return {"base": "auth"}
        except SpaceApiClientCommunicationError as exception:
            LOGGER.error("Connection failed during config flow: %s", exception)
            return {"base": "connection"}
        except SpaceApiClientError:
            LOGGER.exception("Unexpected error during config flow")
            return {"base": "unknown"}
        return {}

    async def _test_credentials(
        self, host_url: str, api_key: str | None = None
    ) -> None:
        """Validate credentials by reading the space state."""
        client = SpaceApiClient(
            host_url=host_url,
            session=async_create_clientsession(self.hass),
            api_key=api_key or "",
        )
        await client.async_get_space_state()
