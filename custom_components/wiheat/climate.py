"""WiHeat climate platform."""

import logging

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
from .generate_payload import (
    DEFAULT_SWING,
    FAN_SPEED_AUTO,
    FAN_SPEED_HIGH,
    FAN_SPEED_LOW,
    FAN_SPEED_MEDIUM,
    HVAC_COOL,
    HVAC_DRY,
    HVAC_FAN_ONLY,
    HVAC_HEAT,
    ION_OFF,
    NO_TARGET_TEMP,
    generate_payload,
)

_LOGGER = logging.getLogger(__name__)

POWER_ON = 11
POWER_OFF = 21

FAN_MODE_TO_SPEED = {
    FAN_AUTO: FAN_SPEED_AUTO,
    FAN_LOW: FAN_SPEED_LOW,
    FAN_MEDIUM: FAN_SPEED_MEDIUM,
    FAN_HIGH: FAN_SPEED_HIGH,
}
SPEED_TO_FAN_MODE = {v: k for k, v in FAN_MODE_TO_SPEED.items()}

HVAC_MODE_TO_VALUE = {
    HVACMode.HEAT: HVAC_HEAT,
    HVACMode.COOL: HVAC_COOL,
    HVACMode.DRY: HVAC_DRY,
    HVACMode.FAN_ONLY: HVAC_FAN_ONLY,
}
VALUE_TO_HVAC_MODE = {v: k for k, v in HVAC_MODE_TO_VALUE.items()}

# Modes the pump does not hold a target temperature for.
MODES_WITHOUT_TARGET = (HVAC_DRY, HVAC_FAN_ONLY)


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

    def _read_state(self):
        """Decode the cached status string into the fields a payload needs.

        The status string looks like:
            target:power:fan:mode:unknown:swing:ion:timestamp?indoor:...

        Returns None when there is no usable state yet, so callers can bail out
        instead of sending a payload built from guesses.
        """
        if not self.api.current_state:
            return None

        parts = self.api.current_state.split("?")[0].split(":")
        if len(parts) < 7:
            _LOGGER.debug("Unexpected status format: %s", self.api.current_state)
            return None

        def _int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        ion = parts[6].strip().upper()
        ion = f"0x{ion}" if ion in ("F0", "F4") else ION_OFF

        return {
            "target_temp": _int(parts[0], NO_TARGET_TEMP),
            "power_state": _int(parts[1], POWER_ON),
            "fan_speed": _int(parts[2], FAN_SPEED_AUTO),
            "hvac_mode": _int(parts[3], HVAC_HEAT),
            # The swing field is not decoded from the status string; the pump
            # reports it in a format we have not confirmed. Auto is what the
            # integration has always sent.
            "swing": DEFAULT_SWING,
            "ion": ion,
        }

    async def _apply(self, state, **overrides):
        """Send a payload built from the full current state plus overrides."""
        new_state = {**state, **overrides}

        payload = generate_payload(
            new_state["target_temp"],
            new_state["power_state"],
            new_state["fan_speed"],
            new_state["hvac_mode"],
            swing=new_state["swing"],
            ion=new_state["ion"],
        )

        if await self.api.set_hvac_state(payload):
            await self.async_update()
            return True

        _LOGGER.warning("WiHeat did not acknowledge payload: %s", payload)
        return False

    async def async_update(self):
        data = await self.api.get_hvac_status()
        state = self._read_state()
        if state is None:
            return

        indoor = data.split("?")[1].split(":")[0]
        try:
            self._attr_current_temperature = int(indoor)
        except (TypeError, ValueError):
            self._attr_current_temperature = None

        self._attr_target_temperature = (
            None if state["target_temp"] == NO_TARGET_TEMP else state["target_temp"]
        )

        if state["power_state"] == POWER_OFF:
            self._attr_hvac_mode = HVACMode.OFF
        else:
            self._attr_hvac_mode = VALUE_TO_HVAC_MODE.get(
                state["hvac_mode"], self._attr_hvac_mode
            )

        self._attr_fan_mode = SPEED_TO_FAN_MODE.get(state["fan_speed"], FAN_AUTO)

    async def async_set_temperature(self, **kwargs):
        if "temperature" not in kwargs:
            return

        state = self._read_state()
        if state is None:
            return

        # Keep the current fan speed and HVAC mode — only the target changes.
        await self._apply(state, target_temp=int(kwargs["temperature"]))

    async def async_set_fan_mode(self, fan_mode):
        state = self._read_state()
        if state is None:
            return

        fan_speed = FAN_MODE_TO_SPEED.get(fan_mode, state["fan_speed"])

        # Keep the current HVAC mode — this is the fix for fan changes
        # flipping the pump into heat.
        await self._apply(state, fan_speed=fan_speed)

    async def async_set_hvac_mode(self, hvac_mode):
        state = self._read_state()
        if state is None:
            return

        if hvac_mode == HVACMode.OFF:
            await self._apply(state, power_state=POWER_OFF)
            return

        mode_value = HVAC_MODE_TO_VALUE.get(hvac_mode, state["hvac_mode"])

        target_temp = state["target_temp"]
        if mode_value in MODES_WITHOUT_TARGET:
            # Dry and fan only carry no target; the pump reports 128 back.
            target_temp = NO_TARGET_TEMP

        # Keep the current fan speed when switching mode.
        await self._apply(
            state,
            power_state=POWER_ON,
            hvac_mode=mode_value,
            target_temp=target_temp,
        )

    async def async_turn_off(self):
        state = self._read_state()
        if state is None:
            return
        await self._apply(state, power_state=POWER_OFF)

    async def async_turn_on(self):
        state = self._read_state()
        if state is None:
            return
        # Resume the mode the pump was last in rather than forcing heat.
        await self._apply(state, power_state=POWER_ON)
