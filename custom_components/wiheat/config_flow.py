import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DOMAIN
from .wiheat_api import (
    WiHeatAPI,
    WiHeatAuthError,
    WiHeatBannedError,
    WiHeatConnectionError,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


class WiHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WiHeat."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
            self._abort_if_unique_id_configured()

            api = WiHeatAPI(
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                async_get_clientsession(self.hass),
            )
            try:
                await api.login()
            except WiHeatBannedError:
                errors["base"] = "too_many_attempts"
            except WiHeatAuthError:
                errors["base"] = "invalid_auth"
            except WiHeatConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Wi-Heat", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
