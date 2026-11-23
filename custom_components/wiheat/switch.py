"""WiHeat switch platform: the ion (plasmacluster) function."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the WiHeat ion switch."""
    api = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WiHeatIonSwitch(api)])


class WiHeatIonSwitch(SwitchEntity):
    """Ion switch. State and commands go through the climate entity."""

    _attr_has_entity_name = True
    _attr_name = "Ion"
    _attr_icon = "mdi:creation"

    def __init__(self, api):
        self.api = api
        self._attr_unique_id = f"{api.user_id}-{api.device_name}-ion"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api.device_name)},
            "name": "Wi-Heat",
        }

    @property
    def _climate(self):
        # Platforms load concurrently, so this is looked up on use.
        return getattr(self.api, "climate_entity", None)

    @property
    def available(self):
        return self._climate is not None and self._climate.ion_on is not None

    @property
    def is_on(self):
        return self._climate.ion_on if self._climate is not None else None

    async def async_update(self):
        """Nothing to fetch: the climate entity polls the pump."""

    async def _async_set(self, enabled):
        if self._climate is None:
            raise HomeAssistantError("Wi-Heat is not ready yet")
        await self._climate.async_set_ion(enabled)
        self._climate.async_write_ha_state()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        await self._async_set(True)

    async def async_turn_off(self, **kwargs):
        await self._async_set(False)
