"""WiHeat Temperature Sensor platform."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .const import DOMAIN

def async_setup_entry(hass, entry, async_add_entities):
  """Set up WiHeat temperature sensor entities."""
  api = hass.data[DOMAIN][entry.entry_id]
  async_add_entities([
    WiHeatTemperatureSensor(api),
    WiHeatOutdoorTemperatureSensor(api),
    WiHeatWifiSignalSensor(api)
  ])

class WiHeatTemperatureSensor(SensorEntity):
  """Representation of a WiHeat temperature sensor."""
  
  def __init__(self, api):
    self.api = api
    self._attr_name = "Temperature"
    self._attr_unique_id = f"{self.api.user_id}-{self.api.device_name}-temperature"
    self._attr_device_class = SensorDeviceClass.TEMPERATURE
    self._attr_native_unit_of_measurement = "°C"
    self._attr_state = None 
  
  def update(self):
    if not self.api.current_state:
      self._attr_state = None
    else:
      self._attr_state = int(self.api.current_state.split('?')[1].split(':')[0])

  @property
  def state(self):
    """Return the current state of the sensor (current temperature)."""
    return self._attr_state

class WiHeatOutdoorTemperatureSensor(SensorEntity):
  """Representation of a WiHeat outdoor temperature sensor."""
  
  def __init__(self, api):
    self.api = api
    self._attr_name = "Outdoor temperature"
    self._attr_unique_id = f"{self.api.user_id}-{self.api.device_name}-outdoor-temperature"
    self._attr_device_class = SensorDeviceClass.TEMPERATURE
    self._attr_native_unit_of_measurement = "°C"
    self._attr_state = None 
  
  def update(self):
    if not self.api.current_state:
      self._attr_state = None
    else:
      self._attr_state = int(self.api.current_state.split('?')[1].split(':')[1])

  @property
  def state(self):
    """Return the current state of the sensor (current outdoor temperature)."""
    return self._attr_state

class WiHeatWifiSignalSensor(SensorEntity):
  """Representation of a WiHeat Wifi signal strength sensor."""
  
  def __init__(self, api):
    self.api = api
    self._attr_name = "Wifi signal"
    self._attr_unique_id = f"{self.api.user_id}-{self.api.device_name}-wifi-signal"
    self._attr_native_unit_of_measurement = "dBm"
    self._attr_icon = "mdi:signal"
    self._attr_state = None 
  
  def update(self):
    if not self.api.current_state:
      self._attr_state = None
    else:
      self._attr_state = int(self.api.current_state.split('?')[1].split(':')[2])

  @property
  def state(self):
    """Return the current state of the sensor (current outdoor temperature)."""
    return self._attr_state
