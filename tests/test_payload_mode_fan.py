"""Tests for the combined mode/fan-speed byte in the Wi-Heat payload.

Run from the repo root, no Home Assistant install needed:

    python3 tests/test_payload_mode_fan.py

Covers the bug where selecting a fan speed also switched the pump to heat,
because byte 3 of the payload carries BOTH values:

    byte3 = (fan_speed << 4) | hvac_mode

Section 1 pins that encoding to every example documented in
custom_components/wiheat/README.md. Sections 3-14 drive the climate entity
against a fake pump.

Sections 15-23 cover byte 5 (swing), which is packed the same way —
(horizontal << 4) | vertical — but is never echoed back in the status string,
so the entity has to remember what it last sent.
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

# The real entity spaces commands out and retries after a pause to stay clear
# of the pump's busy-lock; the fake pump has no such problem and the tests
# should not take minutes.
climate.MIN_COMMAND_GAP = 0
climate.RETRY_DELAY = 0

# One event loop for the whole file. The entity creates its asyncio.Lock in
# __init__; on Python < 3.10 a Lock binds to the loop current at creation,
# and `asyncio.run` would make a fresh loop per call. Home Assistant itself
# constructs entities inside its running loop, so this only matters here.
LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)


def run(coro):
    return LOOP.run_until_complete(coro)


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
run(e.async_set_fan_mode(FAN_LOW))
check("payload", e.api.sent[0], "0x5:0x11:0x32:0x16:0x08:0x80:0x00:0xF0")
check("pump", pump_state(e.api), "fan=3 mode=2 power=11")
check("entity mode", e._attr_hvac_mode, HVACMode.COOL)
check("entity fan", e._attr_fan_mode, FAN_LOW)

print("\n[4] setting a temperature while cooling must stay cooling")
e = entity("22:11:5:2:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_temperature(temperature=24))
check("pump", pump_state(e.api), "fan=5 mode=2 power=11")
check("entity mode", e._attr_hvac_mode, HVACMode.COOL)

print("\n[5] switching mode keeps the selected fan speed")
e = entity("22:11:7:1:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_hvac_mode(HVACMode.COOL))
check("pump", pump_state(e.api), "fan=7 mode=2 power=11")

print("\n[6] plasmacluster survives an unrelated change")
e = entity("22:11:2:2:0:8:F4:1740765339?19:3:-48:0?NA")
run(e.async_set_fan_mode(FAN_HIGH))
check("ion byte", e.api.sent[0].split(":")[7], "0xF4")

print("\n[7] fan change in fan-only mode (target 128) must not raise KeyError")
e = entity("128:11:2:4:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_fan_mode(FAN_MEDIUM))
check("payload", e.api.sent[0], "0x3:0x11:0x54:0x16:0x08:0x80:0x00:0xF0")
check("pump", pump_state(e.api), "fan=5 mode=4 power=11")

print("\n[8] off then on resumes the previous mode instead of forcing heat")
e = entity("22:11:5:2:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_turn_off())
check("pump after off", pump_state(e.api), "fan=5 mode=2 power=21")
check("entity after off", e._attr_hvac_mode, HVACMode.OFF)
run(e.async_turn_on())
check("pump after on", pump_state(e.api), "fan=5 mode=2 power=11")
check("entity after on", e._attr_hvac_mode, HVACMode.COOL)

print("\n[9] no status fetched yet: send nothing rather than guess")
e = entity(None)
run(e.async_set_fan_mode(FAN_LOW))
check("payloads sent", e.api.sent, [])

print("\n[10] dry only runs at auto: other fan speeds are refused, not sent")
e = entity("22:11:2:3:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_fan_mode(FAN_LOW))
check("payloads sent", e.api.sent, [])
check("fan_modes offered", e._attr_fan_modes, [climate.FAN_AUTO])

print("\n[11] fan-only never runs at auto: auto is refused, not sent")
e = entity("22:11:3:4:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_fan_mode(climate.FAN_AUTO))
check("payloads sent", e.api.sent, [])
check("fan_modes offered", e._attr_fan_modes, [FAN_LOW, FAN_MEDIUM, FAN_HIGH])

print("\n[12] switching into dry forces fan speed to auto")
e = entity("22:11:7:1:0:8:F0:1740765339?19:3:-48:0?NA")  # fan High, Heat
run(e.async_set_hvac_mode(HVACMode.DRY))
check("pump", pump_state(e.api), "fan=2 mode=3 power=11")

print("\n[13] switching into fan-only forces fan speed off auto (to low)")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")  # fan Auto, Heat
run(e.async_set_hvac_mode(HVACMode.FAN_ONLY))
check("pump", pump_state(e.api), "fan=3 mode=4 power=11")

print("\n[14] a stale status echoed right after a SET must not corrupt the next command")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")  # fan Auto, Heat

class StaleEchoOnce:
    """Wraps a FakePump so the *next* get_hvac_status() after a SET returns
    the pre-command status, mimicking a pump whose cloud status lags behind
    the command it just acknowledged."""

    def __init__(self, pump):
        self._pump = pump
        self._pre_set_state = pump.current_state
        self.sent = pump.sent

    async def set_hvac_state(self, payload):
        self._pre_set_state = self._pump.current_state
        return await self._pump.set_hvac_state(payload)

    async def get_hvac_status(self):
        # Always hands back what the pump reported *before* the last SET.
        return self._pre_set_state

    @property
    def current_state(self):
        return self._pump.current_state


e.api = StaleEchoOnce(e.api)
run(e.async_set_hvac_mode(HVACMode.COOL))
run(e.async_set_fan_mode(FAN_LOW))
check("payload", e.api.sent[-1], "0x5:0x11:0x32:0x16:0x08:0x80:0x00:0xF0")
check("entity mode stayed cool", e._attr_hvac_mode, HVACMode.COOL)

# ---------------------------------------------------------------------------
# Swing. Byte 5 is (horizontal << 4) | vertical, and the pump never echoes it
# back, so the entity has to remember what it sent. Note that FakePump above
# also does not copy byte 5 into its status — which is exactly what the real
# pump does, so these tests exercise the real constraint.
# ---------------------------------------------------------------------------

encode_swing = generate_payload.encode_swing
gp = generate_payload


def swing_byte(payload):
    return payload.split(":")[4]


print("\n[15] byte5 encoding vs every swing example in the README")
for h, v, expected, label in [
    (gp.SWING_H_AUTO, gp.SWING_V_UP, "0x09", "vertical Up"),
    (gp.SWING_H_AUTO, gp.SWING_V_CENTER, "0x0C", "vertical Center"),
    (gp.SWING_H_AUTO, gp.SWING_V_DOWN, "0x0D", "vertical Down"),
    (gp.SWING_H_AUTO, gp.SWING_V_AUTO, "0x08", "vertical Auto"),
    (gp.SWING_H_LEFT, gp.SWING_V_AUTO, "0x28", "horizontal Left"),
    (gp.SWING_H_CENTER, gp.SWING_V_AUTO, "0x18", "horizontal Center"),
    (gp.SWING_H_RIGHT, gp.SWING_V_AUTO, "0x38", "horizontal Right"),
    (gp.SWING_H_SWING, gp.SWING_V_AUTO, "0x88", "horizontal All/swing"),
]:
    check(label, encode_swing(h, v), expected)

print("\n[16] all 20 horizontal x vertical combinations survive a round trip")
bad = []
for h in gp.VALID_SWING_HORIZONTAL:
    for v in gp.VALID_SWING_VERTICAL:
        byte5 = int(encode_swing(h, v), 16)
        if (byte5 >> 4, byte5 & 0xF) != (h, v):
            bad.append((h, v))
check("round trip", bad, [])

print("\n[17] before swing is ever set, every command still sends 0x08 (no regression)")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_fan_mode(FAN_HIGH))
run(e.async_set_temperature(temperature=24))
run(e.async_set_hvac_mode(HVACMode.COOL))
check("byte5 on every payload", [swing_byte(p) for p in e.api.sent], ["0x08"] * 3)
check("entity swing", (e._attr_swing_mode, e._attr_swing_horizontal_mode), ("auto", None))
check("horizontal options offered (no auto)", e._attr_swing_horizontal_modes, ["left", "center", "right", "swing"])

print("\n[18] the bug: swing must survive unrelated commands")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_swing_mode(climate.SWING_DOWN))
run(e.async_set_swing_horizontal_mode(climate.SWING_H_LEFT_MODE))
check("swing payload", swing_byte(e.api.sent[-1]), "0x2D")
run(e.async_set_fan_mode(FAN_MEDIUM))
run(e.async_set_temperature(temperature=21))
run(e.async_turn_off())
run(e.async_turn_on())
check("byte5 kept on fan/temp/off/on", [swing_byte(p) for p in e.api.sent[2:]], ["0x2D"] * 4)
check("pump status still does not report swing", e.api.current_state.split(":")[4:6], ["0", "8"])
run(e.async_update())
check("poll does not reset swing", (e._attr_swing_mode, e._attr_swing_horizontal_mode), ("down", "left"))

print("\n[19] entering dry with the louvre down forces it to auto, keeps horizontal")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_swing_mode(climate.SWING_DOWN))
run(e.async_set_swing_horizontal_mode(climate.SWING_H_LEFT_MODE))
run(e.async_set_hvac_mode(HVACMode.DRY))
check("payload", e.api.sent[-1], "0x3:0x11:0x23:0x16:0x28:0x80:0x00:0xF0")
check("entity swing", (e._attr_swing_mode, e._attr_swing_horizontal_mode), ("auto", "left"))
check("swing_modes offered in dry", e._attr_swing_modes, ["auto", "up", "center"])

print("\n[20] down is only offered in heat; refused (not sent) in cool, dry and fan-only")
for mode in (2, 3, 4):
    e = entity(f"22:11:3:{mode}:0:8:F0:1740765339?19:3:-48:0?NA")
    check(f"mode {mode}: swing_modes offered", e._attr_swing_modes, ["auto", "up", "center"])
    run(e.async_set_swing_mode(climate.SWING_DOWN))
    check(f"mode {mode}: payloads sent", e.api.sent, [])
    run(e.async_set_swing_mode(climate.SWING_UP))
    check(f"mode {mode}: up accepted", swing_byte(e.api.sent[-1]), "0x09")
e = entity("22:11:3:1:0:8:F0:1740765339?19:3:-48:0?NA")
check("heat: down offered", e._attr_swing_modes, ["auto", "up", "center", "down"])
run(e.async_set_swing_mode(climate.SWING_DOWN))
check("heat: down sent", swing_byte(e.api.sent[-1]), "0x0D")

print("\n[20b] leaving heat with the louvre down forces it to auto")
e = entity("22:11:3:1:0:8:F0:1740765339?19:3:-48:0?NA")
run(e.async_set_swing_mode(climate.SWING_DOWN))
run(e.async_set_hvac_mode(HVACMode.COOL))
check("payload into cool", swing_byte(e.api.sent[-1]), "0x08")
check("entity swing", e._attr_swing_mode, "auto")

print("\n[21] swing is restored across a restart")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")
e._last_state = types.SimpleNamespace(
    attributes={"swing_mode": "down", "swing_horizontal_mode": "right"}
)
run(e.async_added_to_hass())
check("restored", (e._attr_swing_mode, e._attr_swing_horizontal_mode), ("down", "right"))
run(e.async_set_fan_mode(FAN_LOW))
check("first command after restart sends restored swing", swing_byte(e.api.sent[-1]), "0x3D")

print("\n[22] restored down + pump switched to dry from the app: poll falls back to auto")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")
e._last_state = types.SimpleNamespace(attributes={"swing_mode": "down"})
run(e.async_added_to_hass())
e.api.current_state = "128:11:2:3:0:8:F0:1740765339?19:3:-48:0?NA"  # app put it in dry
run(e.async_update())
check("swing after poll", e._attr_swing_mode, "auto")
check("nothing sent by the poll", e.api.sent, [])

print("\n[23] garbage in the restored state is ignored")
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")
e._last_state = types.SimpleNamespace(attributes={"swing_mode": "sideways", "swing_horizontal_mode": 7})
run(e.async_added_to_hass())
check("defaults kept", (e._attr_swing_mode, e._attr_swing_horizontal_mode), ("auto", None))

print("\n[24] a refused command is retried once, then raises a translated error")
from homeassistant.exceptions import HomeAssistantError  # noqa: E402


class RefusingPump(FakePump):
    async def set_hvac_state(self, payload):
        self.sent.append(payload)
        return False


e = WiHeatClimate(RefusingPump("22:11:2:2:0:8:F0:1740765339?19:3:-48:0?NA"))
try:
    run(e.async_set_swing_mode(climate.SWING_UP))
    raised = None
except HomeAssistantError as err:
    raised = err
check("raised HomeAssistantError", isinstance(raised, HomeAssistantError), True)
check("translated, no raw bytes in the message", (raised.translation_key, str(raised)), ("pump_busy", ""))
check("attempted twice (one retry)", len(e.api.sent), 2)
check("swing not updated", e._attr_swing_mode, "auto")
check("mode not updated", e._attr_hvac_mode, HVACMode.COOL)

print("\n[24b] a refusal followed by an ACK on retry succeeds silently")


class FlakyPump(FakePump):
    refusals = 1

    async def set_hvac_state(self, payload):
        if self.refusals:
            self.refusals -= 1
            self.sent.append(payload)
            return False
        return await super().set_hvac_state(payload)


e = WiHeatClimate(FlakyPump("22:11:2:2:0:8:F0:1740765339?19:3:-48:0?NA"))
run(e.async_set_swing_mode(climate.SWING_UP))
check("sent twice", len(e.api.sent), 2)
check("swing updated after retry", e._attr_swing_mode, "up")

print("\n[24c] a cloud error or a stalled call is treated as a refusal, never leaks")


class ExplodingPump(FakePump):
    async def set_hvac_state(self, payload):
        self.sent.append(payload)
        raise OSError("connection reset by peer")


e = WiHeatClimate(ExplodingPump("22:11:2:2:0:8:F0:1740765339?19:3:-48:0?NA"))
try:
    run(e.async_set_fan_mode(FAN_HIGH))
    raised = None
except HomeAssistantError as err:
    raised = err
except Exception as err:  # noqa: BLE001
    raised = err
check("only HomeAssistantError escapes", type(raised).__name__, "HomeAssistantError")
check("retried once", len(e.api.sent), 2)


class StalledPump(FakePump):
    async def set_hvac_state(self, payload):
        self.sent.append(payload)
        await asyncio.sleep(60)


climate.REQUEST_TIMEOUT = 0.05
e = WiHeatClimate(StalledPump("22:11:2:2:0:8:F0:1740765339?19:3:-48:0?NA"))
try:
    run(e.async_set_fan_mode(FAN_HIGH))
    raised = None
except HomeAssistantError as err:
    raised = err
check("stalled call times out into HomeAssistantError", type(raised).__name__, "HomeAssistantError")
check("state untouched", e._attr_fan_mode, "auto")
climate.REQUEST_TIMEOUT = 10.0

print("\n[25] commands are spaced out by MIN_COMMAND_GAP")
climate.MIN_COMMAND_GAP = 0.2
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")
import time as _time  # noqa: E402


async def _two_commands():
    await e.async_set_fan_mode(FAN_LOW)
    await e.async_set_fan_mode(FAN_HIGH)


t0 = _time.monotonic()
run(_two_commands())
elapsed = _time.monotonic() - t0
check("second command waited for the gap", elapsed >= 0.2, True)
check("both sent", [p.split(":")[2] for p in e.api.sent], ["0x31", "0x71"])
climate.MIN_COMMAND_GAP = 0

print("\n[25b] two commands arriving together: the second builds on the first's result")
# Review finding on PR #6: the payload used to be built from `_state` *before*
# taking the lock, so a second call could re-send the first call's old mode.
e = entity("22:11:2:1:0:8:F0:1740765339?19:3:-48:0?NA")  # Heat, fan Auto


async def _together():
    await asyncio.gather(
        e.async_set_hvac_mode(HVACMode.COOL),
        e.async_set_fan_mode(FAN_LOW),
    )


run(_together())
check("two payloads sent", len(e.api.sent), 2)
check("second payload carries Cool (0x32), not the stale Heat (0x31)",
      e.api.sent[1].split(":")[2], "0x32")
check("pump ends in Cool at fan Low", pump_state(e.api), "fan=3 mode=2 power=11")
check("entity agrees", (e._attr_hvac_mode, e._attr_fan_mode), (HVACMode.COOL, FAN_LOW))
check("lock exists from construction", type(entity(None)._send_lock).__name__, "Lock")

print("\n" + "=" * 62)
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S):")
    for failure in FAILURES:
        print("  -", failure)
    sys.exit(1)
print("ALL CHECKS PASSED")
