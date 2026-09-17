"""WiHeat API handler."""

from __future__ import annotations

import json
import logging

import aiohttp

from .const import BASE_URL, CONF_CLIENT_ID, SESSION

_LOGGER = logging.getLogger(__name__)


class WiHeatError(Exception):
    """Base error for the Wi-Heat API."""


class WiHeatConnectionError(WiHeatError):
    """Could not reach the API, or it answered with something unexpected."""


class WiHeatAuthError(WiHeatError):
    """The API rejected the credentials."""


class WiHeatBannedError(WiHeatAuthError):
    """Too many login attempts; the API blocks logins for 24 hours."""


class WiHeatAPI:
    def __init__(self, email, password, session):
        self.email = email
        self.password = password
        self.session = session
        self.token = None
        self.user_id = None
        self.hwid = None
        self.device_key = None
        self.device_name = None
        self.current_state = None
        self._target_temperature = None
        self._indoor_temperature = None
        self._outdoor_temperature = None
        self._wifi_signal = None
        self.device_info_fetched = False

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def indoor_temperature(self):
        return self._indoor_temperature

    @property
    def outdoor_temperature(self):
        return self._outdoor_temperature

    @property
    def wifi_signal(self):
        return self._wifi_signal

    async def _post_json(self, path, data):
        """POST a form and decode the JSON body, mapping failures to typed errors."""
        try:
            async with self.session.post(f"{BASE_URL}/{path}", data=data) as response:
                body = await response.text()
        except (aiohttp.ClientError, OSError, TimeoutError) as err:
            raise WiHeatConnectionError(f"Could not reach Wi-Heat: {err}") from err

        try:
            return json.loads(body)
        except json.JSONDecodeError as err:
            _LOGGER.debug("Non-JSON response from %s: %s", path, body)
            raise WiHeatConnectionError(
                f"Unexpected response from Wi-Heat ({path})"
            ) from err

    async def login(self):
        """Log in and fetch the device details.

        Raises WiHeatBannedError, WiHeatAuthError or WiHeatConnectionError;
        returns True on success so existing callers can keep `if await login()`.
        """
        data = await self._post_json(
            "usr_API_2.php",
            {
                "epost": self.email,
                "id": CONF_CLIENT_ID,
                "psw": self.password,
                "q": "login",
                "session": SESSION,
            },
        )

        if isinstance(data, dict) and "token" in data:
            self.token = data["token"]
            self.user_id = data["id"]
            self.device_info_fetched = False
            await self.get_device_info()
            return True

        if isinstance(data, dict) and data.get("status") == "ban":
            raise WiHeatBannedError(
                "Too many login attempts; Wi-Heat blocks logins for 24 hours"
            )

        raise WiHeatAuthError("Wi-Heat rejected the email or password")

    async def get_device_info(self):
        if self.device_info_fetched:
            return False

        data = await self._post_json(
            "usr_API_2.php",
            {
                "epost": self.user_id,
                "id": CONF_CLIENT_ID,
                "psw": self.token,
                "q": "getVPhwid",
                "session": SESSION,
            },
        )

        # The API answers [device name, hwid, device key]; anything else is an
        # error object or a changed API, not something to unpack blindly.
        if not isinstance(data, list) or len(data) != 3:
            _LOGGER.debug("Unexpected device info response: %s", data)
            raise WiHeatConnectionError("Unexpected device info response from Wi-Heat")

        self.device_name, self.hwid, self.device_key = data
        self.device_info_fetched = True
        return True

    async def get_hvac_status(self):
        if not self.hwid or not self.device_key:
            raise ValueError("Device info not available. Ensure login was successful.")

        async with self.session.post(
            f"{BASE_URL}/API_2.php",
            data={
                "dir": "get",
                "hwid": self.hwid,
                "psw": self.device_key,
                "token": self.token,
                "usr": f"{self.user_id}.{CONF_CLIENT_ID}",
            },
        ) as response:
            self.current_state = await response.text()
            self._parse_current_state()
            return self.current_state

    async def set_hvac_state(self, payload):
        if not self.hwid or not self.device_key:
            raise ValueError("Device info not available. Ensure login was successful.")

        async with self.session.post(
            f"{BASE_URL}/API_2.php",
            data={
                "data": payload,
                "dir": "set",
                "hwid": self.hwid,
                "psw": self.device_key,
                "token": self.token,
                "usr": f"{self.user_id}.{CONF_CLIENT_ID}",
            },
        ) as response:
            return (await response.text()) == "ACK"

    def _parse_current_state(self):
        """Parse the current HVAC state."""

        self._target_temperature = None
        self._indoor_temperature = None
        self._outdoor_temperature = None
        self._wifi_signal = None

        if not self.current_state:
            return

        try:
            target, values = self.current_state.split("?", 1)
            values = values.split(":")

            self._target_temperature = self._safe_int(target.split(":")[0])
            self._indoor_temperature = self._safe_int(values[0])
            self._outdoor_temperature = self._safe_int(values[1])
            self._wifi_signal = self._safe_int(values[2])

        except (IndexError, ValueError, AttributeError):
            _LOGGER.debug("Unable to parse current state: %s", self.current_state)

    @staticmethod
    def _safe_int(value: str | None) -> int | None:
        """Convert a string to int or return None."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
