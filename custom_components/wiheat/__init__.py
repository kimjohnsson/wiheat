import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from aiohttp import ClientSession
from .wiheat_api import WiHeatAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up WiHeat from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    session = ClientSession()
    api = WiHeatAPI(entry.data["email"], entry.data["password"], session)

    # Ensure you await the login method, not add it to the executor job
    if await api.login():
        hass.data[DOMAIN][entry.entry_id] = api
        await hass.config_entries.async_forward_entry_setups(
            entry, ["climate", "sensor"]
        )
        return True

    return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "climate")
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
