"""WiHeat sensor platform."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)

from .const import DOMAIN
from .generate_payload import NO_TARGET_TEMP


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up WiHeat sensor entities."""
    api = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WiHeatTemperatureSensor(api),
            WiHeatTargetTemperatureSensor(api),
            WiHeatOutdoorTemperatureSensor(api),
            WiHeatWifiSignalSensor(api),
        ]
    )


class WiHeatBaseSensor(SensorEntity):
    """Base class for WiHeat sensors to share device info.

    Values come from the shared API object, which the climate entity's poll
    keeps fresh; the sensors only read it.
    """

    _attr_has_entity_name = True

    def __init__(self, api, name, unique_id_suffix):
        self.api = api
        self._attr_name = name
        # Same strings as before this class was reworked, so entity IDs and
        # recorded history carry over.
        self._attr_unique_id = f"{api.user_id}-{api.device_name}-{unique_id_suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api.device_name)},
            "name": "Wi-Heat",
        }


class WiHeatTemperatureSensor(WiHeatBaseSensor):
    """Indoor temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 0

    def __init__(self, api):
        super().__init__(api, "Temperature", "temperature")

    async def async_update(self):
        self._attr_native_value = self.api.indoor_temperature


class WiHeatTargetTemperatureSensor(WiHeatBaseSensor):
    """Target temperature sensor. A setpoint, so no measurement state class."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 0

    def __init__(self, api):
        super().__init__(api, "Target temperature", "target-temperature")

    async def async_update(self):
        value = self.api.target_temperature
        # In Dry and Fan-only the pump holds no target and reports 128; that is
        # "no target", not a temperature, so the sensor shows unknown instead
        # of a 128 C spike in the history graph (seen live).
        self._attr_native_value = None if value == NO_TARGET_TEMP else value


class WiHeatOutdoorTemperatureSensor(WiHeatBaseSensor):
    """Outdoor temperature sensor.

    The pump only reports this intermittently; the value is None (unknown)
    in between, which is the honest state.
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 0

    def __init__(self, api):
        super().__init__(api, "Outdoor temperature", "outdoor-temperature")

    async def async_update(self):
        self._attr_native_value = self.api.outdoor_temperature


class WiHeatWifiSignalSensor(WiHeatBaseSensor):
    """WiFi signal strength sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, api):
        super().__init__(api, "WiFi signal", "wifi-signal")

    async def async_update(self):
        self._attr_native_value = self.api.wifi_signal
