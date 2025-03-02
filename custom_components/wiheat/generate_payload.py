from homeassistant.components.climate.const import HVACMode

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

fan_speed_lookup = {
    2: "0x21",
    3: "0x31",
    5: "0x51",
    7: "0x71",
}

hvac_mode_lookup = {
    1: "0x31",
    2: "0x22",
    3: "0x23",
    4: "0x34",
}


def generate_payload(target_temp, power_state, fan_speed, hvac_mode=None):
    if hvac_mode is not None:
        mode = hvac_mode_lookup.get(hvac_mode)
    else:
        mode = fan_speed_lookup[fan_speed]

    if hvac_mode == HVACMode.COOL:
        unknownValue = "0x18"
    else:
        unknownValue = "0x08"

    if hvac_mode == HVACMode.FAN_ONLY:
        ion = "0xF4"
    else:
        ion = "0xF0"

    return f"{temp_lookup[target_temp]}:{power_state_lookup[power_state]}:{mode}:0x16:{unknownValue}:0x80:0x00:{ion}"
