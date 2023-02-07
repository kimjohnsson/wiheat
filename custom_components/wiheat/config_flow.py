"""Adds config flow for WiHeat integration."""
from __future__ import annotations
import urllib

from collections.abc import Mapping
from typing import Any

from aiohttp.client_exceptions import ContentTypeError
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import API_ENDPOINT, DOMAIN, UPDATE_INTERVAL, HEADERS, ID, SESSION, QUERY


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

DATA_SCHEMA_AUTH = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def validate_input(
    hass: core.HomeAssistant, username: str, password: str
) -> None:
    """Validate the user input allows us to connect."""
    hwid = ''
    siteName = ''
    psw = ''

    websession = async_get_clientsession(hass)
    login = await websession.post(
        API_ENDPOINT['getUserDetails'],
        headers=HEADERS,
        body=f'epost={urllib.parse.quote(username)}&hwid={hwid}&id={ID}&namn=iOSver%3A3.1lang%3AEn&psw={password}&q={QUERY["login"]}&session={SESSION}',
    )
    try:
        token_data = await login.json()
    finally:
        token = token_data["token"]
        userId = token_data["id"]
        print(login)

    try:
        response = await websession.post(
            API_ENDPOINT['getUserDetails'],
            headers=HEADERS,
            body=f'epost={userId}&id={ID}&namn=&psw={token}&q={QUERY["getVpHwid"]}&session={SESSION}'
        )
        vpData = await response.json()
    finally:
        siteName = vpData[0]
        hwid = vpData[1]
        psw = vpData[2]
        print(vpData)


class WiHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WiHeat integration."""

    VERSION = 1

    entry: config_entries.ConfigEntry | None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> WiHeatOptionFlow:
        """Get the options flow for this handler."""
        return WiHeatOptionFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            try:
                await validate_input(self.hass, username, password)
            except CannotConnect:
                errors = {"base": "connection_error"}
            except AuthenticationError:
                errors = {"base": "auth_error"}
            else:
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                    options={
                        UPDATE_INTERVAL: 60,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
        )


class WiHeatOptionFlow(config_entries.OptionsFlow):
    """Handle a options config flow for WiHeat integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize config flow."""
        self.config_entry: config_entries.ConfigEntry = config_entry

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Manage the WiHeat options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    UPDATE_INTERVAL,
                    description={
                        "suggested_value": self.config_entry.options.get(
                            UPDATE_INTERVAL, 60
                        )
                    },
                ): cv.positive_int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class AuthenticationError(exceptions.HomeAssistantError):
    """Error to indicate authentication failure."""
