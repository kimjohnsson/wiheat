"""WiHeat climate platform."""

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    HVACMode,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN
from .generate_payload import generate_payload


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up WiHeat climate entities."""
    api = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WiHeatClimate(api)])


class WiHeatClimate(ClimateEntity):
    """Representation of a WiHeat climate entity."""

    def __init__(self, api):
        self.api = api
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_has_entity_name = True
        self._attr_precision = 1.0
        self._attr_target_temperature_step = 1.0
        self._attr_max_temp = 32
        self._attr_min_temp = 10
        self._attr_name = self.api.device_name
        self._attr_unique_id = f"{self.api.user_id}-{self.api.device_name}"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
            HVACMode.DRY,
        ]
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
        self._attr_fan_mode = FAN_AUTO

        self._attr_supported_features = (
            ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )

        self._attr_device_info = {
            "identifiers": {(DOMAIN, api.device_name)},
            "name": "Wi-Heat",
        }

    async def async_update(self):
        data = await self.api.get_hvac_status()
        """Temperature"""
        self._attr_current_temperature = int(data.split("?")[1].split(":")[0])
        self._attr_target_temperature = (
            None if data.split(":")[0] == "128" else int(data.split(":")[0])
        )

        """Hvac Mode"""
        if data.split(":")[1] == "21":
            self._attr_hvac_mode = HVACMode.OFF
        elif data.split(":")[3] == "1":
            self._attr_hvac_mode = HVACMode.HEAT
        elif data.split(":")[3] == "2":
            self._attr_hvac_mode = HVACMode.COOL
        elif data.split(":")[3] == "3":
            self._attr_hvac_mode = HVACMode.DRY
        elif data.split(":")[3] == "4":
            self._attr_hvac_mode = HVACMode.FAN_ONLY

        """"Fan Mode"""
        if data.split(":")[2] == "3":
            self._attr_fan_mode = FAN_LOW
        elif data.split(":")[2] == "5":
            self._attr_fan_mode = FAN_MEDIUM
        elif data.split(":")[2] == "7":
            self._attr_fan_mode = FAN_HIGH
        else:
            self._attr_fan_mode = FAN_AUTO

    async def async_set_temperature(self, **kwargs):
        data = self.api.current_state.split(":")
        power_state = int(data[1])
        fan_mode = int(data[2])

        if "temperature" in kwargs:
            target_temp = int(kwargs["temperature"])
            if await self.api.set_hvac_state(
                generate_payload(target_temp, power_state, fan_mode)
            ):
                self._attr_target_temperature = target_temp
                await self.async_update()

    async def async_set_fan_mode(self, fan_mode):
        data = self.api.current_state.split(":")
        target_temp = int(data[0])
        power_state = int(data[1])
        current_fan_mode = int(data[2])

        if fan_mode == FAN_LOW:
            fan_speed = 3
        elif fan_mode == FAN_MEDIUM:
            fan_speed = 5
        elif fan_mode == FAN_HIGH:
            fan_speed = 7
        elif fan_mode == FAN_AUTO:
            fan_speed = 2
        else:
            fan_speed = current_fan_mode

        if await self.api.set_hvac_state(
            generate_payload(target_temp, power_state, fan_speed)
        ):
            self._attr_fan_mode = fan_mode
            await self.async_update()

    async def async_set_hvac_mode(self, hvac_mode):
        data = self.api.current_state.split(":")
        target_temp = int(data[0])
        power_state = int(data[1])
        fan_mode = int(data[2])
        current_hvac_mode = int(data[3])

        if target_temp == 128:
            target_temp = 20

        if hvac_mode == HVACMode.OFF:
            power_state = 21
        elif hvac_mode == HVACMode.HEAT:
            hvac = 1
        elif hvac_mode == HVACMode.COOL:
            hvac = 2
        elif hvac_mode == HVACMode.DRY:
            hvac = 3
        elif hvac_mode == HVACMode.FAN_ONLY:
            hvac = 4
        else:
            hvac = current_hvac_mode

        if hvac_mode != HVACMode.OFF:
            power_state = 11

        if power_state == 21:
            payload = generate_payload(target_temp, power_state, fan_mode)
        else:
            payload = generate_payload(target_temp, power_state, None, hvac)

        if await self.api.set_hvac_state(payload):
            self._attr_hvac_mode = hvac_mode
            await self.async_update()

    async def async_turn_off(self):
        data = self.api.current_state.split(":")
        target_temp = int(data[0])
        fan_mode = int(data[2])

        if await self.api.set_hvac_state(generate_payload(target_temp, 21, fan_mode)):
            self._attr_hvac_mode = HVACMode.OFF
            await self.async_update()

    async def async_turn_on(self):
        data = self.api.current_state.split(":")
        target_temp = int(data[0])
        fan_mode = int(data[2])

        if target_temp == 128:
            target_temp = 20

        if await self.api.set_hvac_state(generate_payload(target_temp, 11, fan_mode)):
            self._attr_hvac_mode = HVACMode.HEAT
            await self.async_update()
