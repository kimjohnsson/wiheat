"""Tests for the combined mode/fan-speed byte in the Wi-Heat payload.

Run from the repo root, no Home Assistant install needed:

    python3 tests/test_payload_mode_fan.py

Covers the bug where selecting a fan speed also switched the pump to heat,
because byte 3 of the payload carries BOTH values:

    byte3 = (fan_speed << 4) | hvac_mode

Section 1 pins that encoding to every example documented in
custom_components/wiheat/README.md. Sections 3-9 drive the climate entity
against a fake pump.
"""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENT = REPO_ROOT / "custom_components" / "wiheat"

# Stubbed Home Assistant packages.
sys.path.insert(0, str(Path(__file__).resolve().parent / "stub_homeassistant"))


def _load_component():
    """Import the component's modules without running its __init__.py.

    The real __init__.py pulls in aiohttp and HA config-entry plumbing that
    these tests neither have nor need. Registering the package by hand gives
    the modules working relative imports without that cost.
    """
    pkg = types.ModuleType("wiheat_under_test")
    pkg.__path__ = [str(COMPONENT)]
    sys.modules["wiheat_under_test"] = pkg

    loaded = {}
    for name in ("const", "generate_payload", "climate"):
        spec = importlib.util.spec_from_file_location(
            f"wiheat_under_test.{name}", COMPONENT / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"wiheat_under_test.{name}"] = module
        spec.loader.exec_module(module)
        loaded[name] = module
    return loaded


_mods = _load_component()
generate_payload = _mods["generate_payload"]
climate = _mods["climate"]

encode_mode_fan_speed = generate_payload.encode_mode_fan_speed
WiHeatClimate = climate.WiHeatClimate

from homeassistant.components.climate.const import (  # noqa: E402
    HVACMode,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)

FAILURES = []


def check(name, got, want):
    ok = got == want
    if not ok:
        FAILURES.append(f"{name}: got {got!r}, want {want!r}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got}")


class FakePump:
    """Stand-in for WiHeatAPI that applies payloads the way the pump does."""

    device_name = "IVT"
    user_id = "1"

    def __init__(self, state):
        self.current_state = state
        self.sent = []

    async def set_hvac_state(self, payload):
        self.sent.append(payload)
        fields = payload.split(":")
        byte3 = int(fields[2], 16)
        power = 11 if fields[1] == "0x11" else 21
        target = self.current_state.split(":")[0]
        self.current_state = (
            f"{target}:{power}:{byte3 >> 4}:{byte3 & 0xF}:0:8:{fields[7][2:]}"
            f":1740765339?19:3:-48:0?NA"
        )
        return True

    async def get_hvac_status(self):
        return self.current_state


def entity(state):
    return WiHeatClimate(FakePump(state))


def pump_state(api):
    parts = api.current_state.split(":")
    return f"fan={parts[2]} mode={parts[3]} power={parts[1]}"


print("\n[1] byte3 encoding vs every example in custom_components/wiheat/README.md")
for fan, mode, expected, label in [
    (3, 1, "0x31", "fan Low      -> status 3:1"),
    (5, 1, "0x51", "fan Medium   -> status 5:1"),
    (7, 1, "0x71", "fan High     -> status 7:1"),
    (2, 1, "0x21", "fan Auto     -> status 2:1"),
    (3, 1, "0x31", "mode Heat    -> status 3:1"),
    (2, 2, "0x22", "mode Cool    -> status 2:2"),
    (2, 3, "0x23", "mode Dry     -> status 2:3"),
    (3, 4, "0x34", "mode FanOnly -> status 3:4"),
]:
    check(label, encode_mode_fan_speed(fan, mode), expected)

print("\n[2] all 16 fan x mode combinations survive a round trip")
bad = []
for fan in (2, 3, 5, 7):
    for mode in (1, 2, 3, 4):
        byte3 = int(encode_mode_fan_speed(fan, mode), 16)
        if (byte3 >> 4, byte3 & 0xF) != (fan, mode):
            bad.append((fan, mode))
check("round trip", bad, [])

print("\n[3] the reported bug: fan Low while cooling must stay cooling")
e = entity("22:11:2:2:0:8:F0:1740765339?19:3:-48:0?NA")
asyncio.run(e.async_set_fan_mode(FAN_LOW))
check("payload", e.api.sent[0], "0x5:0x11:0x32:0x16:0x08:0x80:0x00:0xF0")
check("pump", pump_state(e.api), "fan=3 mode=2 power=11")
check("entity mode", e._attr_hvac_mode, HVACMode.COOL)
check("entity fan", e._attr_fan_mode, FAN_LOW)

print("\n[4] setting a temperature while cooling must stay cooling")
e = entity("22:11:5:2:0:8:F0:1740765339?19:3:-48:0?NA")
asyncio.run(e.async_set_temperature(temperature=24))
check("pump", pump_state(e.api), "fan=5 mode=2 power=11")
check("entity mode", e._attr_hvac_mode, HVACMode.COOL)

print("\n[5] switching mode keeps the selected fan speed")
e = entity("22:11:7:1:0:8:F0:1740765339?19:3:-48:0?NA")
asyncio.run(e.async_set_hvac_mode(HVACMode.COOL))
check("pump", pump_state(e.api), "fan=7 mode=2 power=11")

print("\n[6] plasmacluster survives an unrelated change")
e = entity("22:11:2:2:0:8:F4:1740765339?19:3:-48:0?NA")
asyncio.run(e.async_set_fan_mode(FAN_HIGH))
check("ion byte", e.api.sent[0].split(":")[7], "0xF4")

print("\n[7] fan change in dry mode (target 128) must not raise KeyError")
e = entity("128:11:2:3:0:8:F0:1740765339?19:3:-48:0?NA")
asyncio.run(e.async_set_fan_mode(FAN_MEDIUM))
check("payload", e.api.sent[0], "0x3:0x11:0x53:0x16:0x08:0x80:0x00:0xF0")
check("pump", pump_state(e.api), "fan=5 mode=3 power=11")

print("\n[8] off then on resumes the previous mode instead of forcing heat")
e = entity("22:11:5:2:0:8:F0:1740765339?19:3:-48:0?NA")
asyncio.run(e.async_turn_off())
check("pump after off", pump_state(e.api), "fan=5 mode=2 power=21")
check("entity after off", e._attr_hvac_mode, HVACMode.OFF)
asyncio.run(e.async_turn_on())
check("pump after on", pump_state(e.api), "fan=5 mode=2 power=11")
check("entity after on", e._attr_hvac_mode, HVACMode.COOL)

print("\n[9] no status fetched yet: send nothing rather than guess")
e = entity(None)
asyncio.run(e.async_set_fan_mode(FAN_LOW))
check("payloads sent", e.api.sent, [])

print("\n" + "=" * 62)
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S):")
    for failure in FAILURES:
        print("  -", failure)
    sys.exit(1)
print("ALL CHECKS PASSED")
