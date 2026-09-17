"""Minimal stand-in for homeassistant.components.sensor (test use only)."""


class SensorEntity:
    _attr_native_value = None

    @property
    def native_value(self):
        return self._attr_native_value


class SensorDeviceClass:
    TEMPERATURE = "temperature"
    SIGNAL_STRENGTH = "signal_strength"


class SensorStateClass:
    MEASUREMENT = "measurement"
