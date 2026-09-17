from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .wiheat_api import WiHeatAPI, WiHeatAuthError, WiHeatConnectionError

PLATFORMS = ["climate", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up WiHeat from a config entry."""
    api = WiHeatAPI(
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        async_get_clientsession(hass),
    )

    try:
        await api.login()
    except WiHeatAuthError as err:
        # Permanent: retrying a bad login is how you earn the 24 h ban.
        raise ConfigEntryError(str(err)) from err
    except WiHeatConnectionError as err:
        # Transient: Home Assistant retries with backoff.
        raise ConfigEntryNotReady(str(err)) from err

    # Entries created before the config flow set a unique ID get one now, so
    # the same account cannot be added twice.
    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=entry.data[CONF_EMAIL].lower()
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
