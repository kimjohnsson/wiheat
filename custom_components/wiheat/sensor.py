"""WiHeat Temperature Sensor platform."""

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .const import DOMAIN


def async_setup_entry(hass, entry, async_add_entities):
    """Set up WiHeat temperature sensor entities."""
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
    """Base class for WiHeat sensors to share device info."""

    def __init__(self, api, name, unique_id, device_class, unit):
        self.api = api
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state = None

        self._attr_device_info = {
            "identifiers": {(DOMAIN, api.device_name)},
            "name": "Wi-Heat",
        }

    def update_state(self, value):
        self._attr_state = value

    @property
    def state(self):
        return self._attr_state


class WiHeatTemperatureSensor(WiHeatBaseSensor):
    """Indoor temperature sensor."""

    def __init__(self, api):
        super().__init__(
            api,
            "Temperature",
            f"{api.user_id}-{api.device_name}-temperature",
            SensorDeviceClass.TEMPERATURE,
            "°C",
        )

    async def async_update(self):
        if not self.api.current_state:
            self._attr_state = None
        else:
            self.update_state(int(self.api.current_state.split("?")[1].split(":")[0]))


class WiHeatTargetTemperatureSensor(WiHeatBaseSensor):
    """Target temperature sensor."""

    def __init__(self, api):
        super().__init__(
            api,
            "Target temperature",
            f"{api.user_id}-{api.device_name}-target-temperature",
            SensorDeviceClass.TEMPERATURE,
            "°C",
        )

    async def async_update(self):
        if not self.api.current_state:
            self._attr_state = None
        else:
            self.update_state(int(self.api.current_state.split(":")[0]))


class WiHeatOutdoorTemperatureSensor(WiHeatBaseSensor):
    """Outdoor temperature sensor."""

    def __init__(self, api):
        super().__init__(
            api,
            "Outdoor temperature",
            f"{api.user_id}-{api.device_name}-outdoor-temperature",
            SensorDeviceClass.TEMPERATURE,
            "°C",
        )

    async def async_update(self):
        if not self.api.current_state:
            self._attr_state = None
        else:
            self.update_state(int(self.api.current_state.split("?")[1].split(":")[1]))


class WiHeatWifiSignalSensor(WiHeatBaseSensor):
    """WiFi signal strength sensor."""

    def __init__(self, api):
        super().__init__(
            api,
            "WiFi signal",
            f"{api.user_id}-{api.device_name}-wifi-signal",
            None,
            "dBm",
        )
        self._attr_icon = "mdi:signal"

    async def async_update(self):
        if not self.api.current_state:
            self._attr_state = None
        else:
            self.update_state(int(self.api.current_state.split("?")[1].split(":")[2]))
