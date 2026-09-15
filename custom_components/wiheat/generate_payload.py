"""Payload encoding for the Wi-Heat API.

Byte 3 of the ``data`` payload is a single *combined* field
(``mode_fan_speed`` in the API docs). It packs BOTH the fan speed and the
HVAC mode:

    byte3 = (fan_speed << 4) | hvac_mode

where ``fan_speed`` and ``hvac_mode`` use the same numeric values the status
response reports (fan: 2=auto, 3=low, 5=medium, 7=high; mode: 1=heat, 2=cool,
3=dry, 4=fan only).

Verified against every example in README.md, e.g. 0x31 = fan 3 (low) + mode 1
(heat), 0x22 = fan 2 (auto) + mode 2 (cool), 0x34 = fan 3 (low) + mode 4 (fan
only).

Encoding only one of the two — as the previous implementation did — silently
overwrites the other. Sending fan low (0x31) also set the mode to heat, which
is why cooling could not be kept while changing fan speed.
"""

temp_lookup = {
    10: "0x00",
    11: "0x49",
    12: "0x4a",
    13: "0x4b",
    14: "0x4c",
    15: "0x4d",
    16: "0x4e",
    17: "0x4f",
    18: "0x1",
    19: "0x2",
    20: "0x3",
    21: "0x4",
    22: "0x5",
    23: "0x6",
    24: "0x7",
    25: "0x8",
    26: "0x9",
    27: "0xa",
    28: "0xb",
    29: "0xc",
    30: "0xd",
    31: "0xe",
    32: "0xf",
}

power_state_lookup = {11: "0x11", 21: "0x21"}

# Numeric values as reported by, and accepted in, the status response.
FAN_SPEED_AUTO = 2
FAN_SPEED_LOW = 3
FAN_SPEED_MEDIUM = 5
FAN_SPEED_HIGH = 7
VALID_FAN_SPEEDS = (FAN_SPEED_AUTO, FAN_SPEED_LOW, FAN_SPEED_MEDIUM, FAN_SPEED_HIGH)

HVAC_HEAT = 1
HVAC_COOL = 2
HVAC_DRY = 3
HVAC_FAN_ONLY = 4
VALID_HVAC_MODES = (HVAC_HEAT, HVAC_COOL, HVAC_DRY, HVAC_FAN_ONLY)

# Temperature the pump reports when the active mode has no target (dry, fan only).
NO_TARGET_TEMP = 128
DEFAULT_TARGET_TEMP = 20

DEFAULT_SWING = "0x08"
ION_OFF = "0xF0"


def encode_mode_fan_speed(fan_speed, hvac_mode):
    """Encode the combined fan-speed/HVAC-mode byte."""
    if fan_speed not in VALID_FAN_SPEEDS:
        fan_speed = FAN_SPEED_AUTO
    if hvac_mode not in VALID_HVAC_MODES:
        hvac_mode = HVAC_HEAT
    return f"0x{(fan_speed << 4) | hvac_mode:02X}"


def normalize_target_temp(target_temp):
    """Clamp the target temperature to a value the pump accepts."""
    if target_temp is None or target_temp == NO_TARGET_TEMP:
        return DEFAULT_TARGET_TEMP
    return min(max(int(target_temp), min(temp_lookup)), max(temp_lookup))


def generate_payload(
    target_temp,
    power_state,
    fan_speed,
    hvac_mode,
    swing=DEFAULT_SWING,
    ion=ION_OFF,
):
    """Build the ``data`` payload sent to the Wi-Heat API."""
    target_temp = normalize_target_temp(target_temp)
    mode_fan_speed = encode_mode_fan_speed(fan_speed, hvac_mode)

    return (
        f"{temp_lookup[target_temp]}:"
        f"{power_state_lookup[power_state]}:"
        f"{mode_fan_speed}:"
        f"0x16:"
        f"{swing}:"
        f"0x80:"
        f"0x00:"
        f"{ion}"
    )
