"""WiHeat switch platform."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from .const import CONF_POLLING, DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the WiHeat polling switch."""
    api = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WiHeatPollingSwitch(api, entry)])


class WiHeatPollingSwitch(SwitchEntity):
    """Pause polling of the pump without unloading the integration.

    Turning this off stops the climate entity from calling the cloud API on
    its scan interval. The last known values stay in place instead of turning
    into unavailable, and turning it back on resumes polling on the next
    cycle. Handy off-season: an outdoor unit that is switched off has nothing
    new to report, but the API still costs a request every 30 seconds.
    """

    _attr_has_entity_name = True
    _attr_name = "Polling"
    _attr_icon = "mdi:cloud-sync"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, api, entry):
        self.api = api
        self.entry = entry
        self._attr_unique_id = f"{api.user_id}-{api.device_name}-polling"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api.device_name)},
            "name": "Wi-Heat",
        }

    @property
    def is_on(self):
        """Return True when polling is enabled."""
        return self.api.polling_enabled

    async def async_turn_on(self, **kwargs):
        """Resume polling."""
        self._set_polling(True)

    async def async_turn_off(self, **kwargs):
        """Pause polling."""
        self._set_polling(False)

    def _set_polling(self, value: bool) -> None:
        """Apply the setting and persist it across restarts."""
        self.api.polling_enabled = value
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, CONF_POLLING: value}
        )
        self.async_write_ha_state()
