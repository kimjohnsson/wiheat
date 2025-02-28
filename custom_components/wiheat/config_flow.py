import voluptuous as vol
from homeassistant import config_entries
from aiohttp import ClientSession
from .const import DOMAIN
from .wiheat_api import WiHeatAPI

DATA_SCHEMA = vol.Schema({"email": str, "password": str})


class WiHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WiHeat."""

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            session = ClientSession()
            api = WiHeatAPI(user_input["email"], user_input["password"], session)

            # Ensure you await the login method, not add it to the executor job
            if await api.login():
                return self.async_create_entry(title="WiHeat", data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
