"""WiHeat climate platform."""

import asyncio
import logging
import time

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    HVACMode,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN
from .generate_payload import (
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
    SWING_H_AUTO,
    SWING_H_CENTER,
    SWING_H_LEFT,
    SWING_H_RIGHT,
    SWING_H_SWING,
    SWING_V_AUTO,
    SWING_V_CENTER,
    SWING_V_DOWN,
    SWING_V_UP,
    generate_payload,
)

_LOGGER = logging.getLogger(__name__)

POWER_ON = 11
POWER_OFF = 21

# The pump refuses commands for a while after a mode switch (it stops the
# compressor to reverse the cycle) or after several commands in quick
# succession; seen three times on hardware, up to several minutes. Commands
# are serialized and spaced out, and a refusal gets one quick retry before it
# is reported to the user.
MIN_COMMAND_GAP = 3.0
RETRY_DELAY = 5.0
# The API session has no timeout of its own; without this a stalled cloud
# call would hold the service call open for minutes.
REQUEST_TIMEOUT = 10.0

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

# Fan speeds the pump actually accepts per HVAC mode, confirmed on hardware:
# Dry only runs at Auto: anything else comes back as an error. Fan-only is the
# opposite — it has no Auto and must be given Low/Medium/High explicitly.
FAN_MODES_ALL = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
FAN_MODES_DRY = [FAN_AUTO]
FAN_MODES_FAN_ONLY = [FAN_LOW, FAN_MEDIUM, FAN_HIGH]

# Vertical louvre position. HA calls the attribute `swing_mode`; the label
# shown to the user comes from translations ("Louvre direction"), because
# only "auto" actually swings. "center" is straight ahead.
SWING_AUTO = "auto"
SWING_UP = "up"
SWING_CENTER = "center"
SWING_DOWN = "down"
SWING_MODE_TO_VALUE = {
    SWING_AUTO: SWING_V_AUTO,
    SWING_UP: SWING_V_UP,
    SWING_CENTER: SWING_V_CENTER,
    SWING_DOWN: SWING_V_DOWN,
}
VALUE_TO_SWING_MODE = {v: k for k, v in SWING_MODE_TO_VALUE.items()}

# Down only works in Heat. Dry and Fan-only refuse it in the app too; in
# Cool the app can do it but the byte we have (0x0D) is accepted and ignored,
# or refused -- confirmed on hardware, twice. So it is only offered in Heat.
SWING_MODES_ALL = [SWING_AUTO, SWING_UP, SWING_CENTER, SWING_DOWN]
SWING_MODES_NO_DOWN = [SWING_AUTO, SWING_UP, SWING_CENTER]

# Horizontal louvre position; "swing" is the left-right sweep. Every option
# is available in every HVAC mode. There is no "auto" here: the nibble the
# app sends when it has not touched the horizontal axis (0x0) is not a
# position, so it is kept as "not set" (None) and never offered.
SWING_H_LEFT_MODE = "left"
SWING_H_CENTER_MODE = "center"
SWING_H_RIGHT_MODE = "right"
SWING_H_SWING_MODE = "swing"
SWING_H_MODE_TO_VALUE = {
    SWING_H_LEFT_MODE: SWING_H_LEFT,
    SWING_H_CENTER_MODE: SWING_H_CENTER,
    SWING_H_RIGHT_MODE: SWING_H_RIGHT,
    SWING_H_SWING_MODE: SWING_H_SWING,
}
VALUE_TO_SWING_H_MODE = {v: k for k, v in SWING_H_MODE_TO_VALUE.items()}
SWING_H_MODES_ALL = list(SWING_H_MODE_TO_VALUE)

# swing_horizontal_mode arrived in Home Assistant 2024.12. Older cores still
# get the vertical control; the horizontal one is simply not offered.
HAS_HORIZONTAL_SWING = hasattr(ClimateEntityFeature, "SWING_HORIZONTAL_MODE")


def _fan_modes_for(hvac_mode_value):
    if hvac_mode_value == HVAC_DRY:
        return FAN_MODES_DRY
    if hvac_mode_value == HVAC_FAN_ONLY:
        return FAN_MODES_FAN_ONLY
    return FAN_MODES_ALL


def _swing_modes_for(hvac_mode_value):
    if hvac_mode_value == HVAC_HEAT:
        return SWING_MODES_ALL
    return SWING_MODES_NO_DOWN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up WiHeat climate entities."""
    api = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WiHeatClimate(api)])


class WiHeatClimate(ClimateEntity, RestoreEntity):
    """Representation of a WiHeat climate entity."""

    _attr_translation_key = "wiheat"

    def __init__(self, api):
        self.api = api
        # Decoded state (target_temp, power_state, fan_speed, hvac_mode, ion)
        # this entity last sent or fetched. `_apply()` updates it
        # optimistically from the payload it just sent instead of re-fetching
        # from the pump — see `_apply()` for why. Seed it from whatever the
        # API already has cached, in case a status was fetched before this
        # entity was constructed.
        self._state = self._decode_status(api.current_state)
        # Serializes every read-modify-write of `_state` in `_apply()`, not
        # just the network call -- see there.
        self._send_lock = asyncio.Lock()
        self._last_send = 0.0
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
        self._attr_fan_modes = FAN_MODES_ALL
        self._attr_fan_mode = FAN_AUTO

        # Swing is not reported by the pump, so these attributes are the only
        # record of it. Vertical starts at auto and horizontal at "not set";
        # together that is byte 0x08, which is what the integration has
        # always sent. Both are restored across restarts.
        self._attr_swing_modes = SWING_MODES_ALL
        self._attr_swing_mode = SWING_AUTO
        self._attr_swing_horizontal_modes = SWING_H_MODES_ALL
        self._attr_swing_horizontal_mode = None

        self._attr_supported_features = (
            ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.SWING_MODE
        )
        if HAS_HORIZONTAL_SWING:
            self._attr_supported_features |= (
                ClimateEntityFeature.SWING_HORIZONTAL_MODE
            )

        self._attr_device_info = {
            "identifiers": {(DOMAIN, api.device_name)},
            "name": "Wi-Heat",
        }

        if self._state is not None:
            self._apply_state_to_attrs(self._state)

    async def async_added_to_hass(self):
        """Restore the last swing position; the pump cannot tell us."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None:
            return
        swing = last.attributes.get("swing_mode")
        if swing in SWING_MODES_ALL:
            self._attr_swing_mode = swing
        swing_h = last.attributes.get("swing_horizontal_mode")
        if swing_h in SWING_H_MODES_ALL:
            self._attr_swing_horizontal_mode = swing_h
        # The mode-specific restriction is applied on the next poll, in
        # `_apply_state_to_attrs`, once we know which mode the pump is in.

    @staticmethod
    def _decode_status(status_string):
        """Decode a raw status string into the fields a payload needs.

        The status string looks like:
            target:power:fan:mode:unknown:unknown:ion:timestamp?indoor:...

        Swing is not in it — positions 4 and 5 read `0:8` no matter what was
        sent — so it is deliberately absent from the returned dict.

        Returns None when the string is missing or unparseable, so callers
        can bail out instead of sending a payload built from guesses.
        """
        if not status_string:
            return None

        parts = status_string.split("?")[0].split(":")
        if len(parts) < 7:
            _LOGGER.debug("Unexpected status format: %s", status_string)
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
            "ion": ion,
        }

    def _apply_state_to_attrs(self, state):
        """Reflect a decoded state dict onto the HA-visible entity attrs."""
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
        self._attr_fan_modes = _fan_modes_for(state["hvac_mode"])

        # The mode may have been changed from the app or the remote, which
        # never passes through `async_set_hvac_mode`. If the position we are
        # holding is not valid for the mode the pump is now in, fall back to
        # auto so the next command does not send something the pump rejects.
        self._attr_swing_modes = _swing_modes_for(state["hvac_mode"])
        if self._attr_swing_mode not in self._attr_swing_modes:
            self._attr_swing_mode = SWING_AUTO

    async def _send(self, payload, attempt):
        """One attempt at the cloud. Returns False for a refusal *or* a failure.

        This is the boundary to a third-party cloud service: a timeout, a
        dropped connection or a 5xx must all end up as "the pump did not take
        the command", not as a stray exception. Anything else escaping here
        surfaces in Home Assistant as "Unexpected exception" in the websocket
        API and knocks the frontend's connection over -- seen on hardware.
        """
        try:
            acknowledged = await asyncio.wait_for(
                self.api.set_hvac_state(payload), timeout=REQUEST_TIMEOUT
            )
        except Exception as err:  # noqa: BLE001 -- external I/O boundary
            _LOGGER.warning(
                "WiHeat command failed (attempt %d): %s: %s",
                attempt,
                type(err).__name__,
                err,
            )
            return False
        if not acknowledged:
            _LOGGER.warning(
                "WiHeat did not acknowledge payload (attempt %d): %s",
                attempt,
                payload,
            )
        return acknowledged

    def _swing_horizontal_value(self):
        if self._attr_swing_horizontal_mode is None:
            return SWING_H_AUTO
        return SWING_H_MODE_TO_VALUE[self._attr_swing_horizontal_mode]

    async def _apply(self, **overrides):
        """Send a payload built from the last known state plus overrides.

        On success, the new state is cached directly from the payload we
        just sent rather than by re-fetching from the pump. A GET right
        after a SET is not safe to trust: the pump's cloud status can take
        a few seconds to catch up, so an immediate re-fetch can read back
        the *previous* state and overwrite our record of the mode we just
        set. A later action (e.g. a fan-speed change) would then read that
        stale mode and re-send it — silently flipping the pump back. The
        next regular poll (`async_update`) reconciles with the real pump
        once it has had time to settle.

        Swing is not part of `self._state` because the pump never reports
        it; it is taken from the entity attributes unless overridden.

        A refused command raises, so the user sees an error instead of the
        control silently snapping back.

        The whole read-modify-write runs under `_send_lock`: two service
        calls arriving together (say "Cool" and "fan Low") must not both
        build their payload from the same starting state, or the second one
        would re-send the first one's *old* mode and undo it. The second call
        waits, then builds from the state the first call left behind.
        """
        async with self._send_lock:
            if self._state is None:
                return False

            swing_vertical = overrides.pop(
                "swing_vertical", SWING_MODE_TO_VALUE[self._attr_swing_mode]
            )
            swing_horizontal = overrides.pop(
                "swing_horizontal", self._swing_horizontal_value()
            )
            new_state = {**self._state, **overrides}

            payload = generate_payload(
                new_state["target_temp"],
                new_state["power_state"],
                new_state["fan_speed"],
                new_state["hvac_mode"],
                swing_horizontal=swing_horizontal,
                swing_vertical=swing_vertical,
                ion=new_state["ion"],
            )

            for attempt in (1, 2):
                wait = MIN_COMMAND_GAP - (time.monotonic() - self._last_send)
                if wait > 0:
                    await asyncio.sleep(wait)
                acknowledged = await self._send(payload, attempt)
                self._last_send = time.monotonic()
                if acknowledged:
                    break
                if attempt == 1:
                    await asyncio.sleep(RETRY_DELAY)

            if not acknowledged:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="pump_busy"
                )

            self._state = new_state
            self._attr_swing_mode = VALUE_TO_SWING_MODE[swing_vertical]
            self._attr_swing_horizontal_mode = VALUE_TO_SWING_H_MODE.get(
                swing_horizontal
            )
            self._apply_state_to_attrs(new_state)

        return True

    async def async_update(self):
        await self.api.get_hvac_status()
        state = self._decode_status(self.api.current_state)
        if state is None:
            return
        self._state = state
        # Already parsed (and None-safe) by the API when it fetched the status.
        self._attr_current_temperature = self.api.indoor_temperature
        self._apply_state_to_attrs(state)

    async def async_set_temperature(self, **kwargs):
        if "temperature" not in kwargs:
            return

        # Keep the current fan speed and HVAC mode — only the target changes.
        await self._apply(target_temp=int(kwargs["temperature"]))

    async def async_set_fan_mode(self, fan_mode):
        if self._state is None:
            return

        valid_modes = _fan_modes_for(self._state["hvac_mode"])
        if fan_mode not in valid_modes:
            _LOGGER.debug(
                "Ignoring fan mode %s: not valid while in this HVAC mode (valid: %s)",
                fan_mode,
                valid_modes,
            )
            return

        fan_speed = FAN_MODE_TO_SPEED.get(fan_mode, self._state["fan_speed"])

        # Keep the current HVAC mode — this is the fix for fan changes
        # flipping the pump into heat.
        await self._apply(fan_speed=fan_speed)

    async def async_set_swing_mode(self, swing_mode):
        if self._state is None:
            return

        valid_modes = _swing_modes_for(self._state["hvac_mode"])
        if swing_mode not in valid_modes:
            _LOGGER.debug(
                "Ignoring swing mode %s: not valid while in this HVAC mode (valid: %s)",
                swing_mode,
                valid_modes,
            )
            return

        await self._apply(swing_vertical=SWING_MODE_TO_VALUE[swing_mode])

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode):
        if self._state is None or swing_horizontal_mode not in SWING_H_MODE_TO_VALUE:
            return

        await self._apply(
            swing_horizontal=SWING_H_MODE_TO_VALUE[swing_horizontal_mode]
        )

    async def async_set_hvac_mode(self, hvac_mode):
        if self._state is None:
            return

        if hvac_mode == HVACMode.OFF:
            await self._apply(power_state=POWER_OFF)
            return

        mode_value = HVAC_MODE_TO_VALUE.get(hvac_mode, self._state["hvac_mode"])

        target_temp = self._state["target_temp"]
        if mode_value in MODES_WITHOUT_TARGET:
            # Dry and fan only carry no target; the pump reports 128 back.
            target_temp = NO_TARGET_TEMP

        # Keep the current fan speed when switching mode, unless it is not
        # valid for the new mode: Dry only runs at Auto, Fan-only never does.
        fan_speed = self._state["fan_speed"]
        if mode_value == HVAC_DRY:
            fan_speed = FAN_SPEED_AUTO
        elif mode_value == HVAC_FAN_ONLY and fan_speed == FAN_SPEED_AUTO:
            fan_speed = FAN_SPEED_LOW

        # Same for the louvre: only Heat can point straight down.
        swing_vertical = SWING_MODE_TO_VALUE[self._attr_swing_mode]
        if mode_value != HVAC_HEAT and swing_vertical == SWING_V_DOWN:
            swing_vertical = SWING_V_AUTO

        await self._apply(
            power_state=POWER_ON,
            hvac_mode=mode_value,
            target_temp=target_temp,
            fan_speed=fan_speed,
            swing_vertical=swing_vertical,
        )

    async def async_turn_off(self):
        await self._apply(power_state=POWER_OFF)

    async def async_turn_on(self):
        # Resume the mode the pump was last in rather than forcing heat.
        await self._apply(power_state=POWER_ON)
