"""Minimal stand-in for homeassistant.components.climate (test use only)."""

from .const import HVACMode, FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH  # noqa: F401


class ClimateEntity:
    pass


class ClimateEntityFeature:
    FAN_MODE = 1
    TARGET_TEMPERATURE = 2
    TURN_OFF = 4
    TURN_ON = 8
