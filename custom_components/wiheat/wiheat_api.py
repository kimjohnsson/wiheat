"""WiHeat API handler."""

import json
import logging
from .const import BASE_URL, CONF_CLIENT_ID, SESSION

_LOGGER = logging.getLogger(__name__)


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
        self.device_info_fetched = False

    async def login(self):
        async with self.session.post(
            f"{BASE_URL}/usr_API_2.php",
            data={
                "epost": self.email,
                "id": CONF_CLIENT_ID,
                "psw": self.password,
                "q": "login",
                "session": SESSION,
            },
        ) as response:
            body = await response.text()

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            _LOGGER.error("Error decoding JSON: %s", e)
            _LOGGER.error("Response body: %s", body)
            return False

        if "token" in data:
            self.token = data["token"]
            self.user_id = data["id"]

            self.device_info_fetched = False
            await self.get_device_info()
            return True

        if data.get("status") == "ban":
            _LOGGER.error(
                "Too many login attempts, please wait 24 hours and try again."
            )

        return False

    async def get_device_info(self):
        if self.device_info_fetched:
            return False

        async with self.session.post(
            f"{BASE_URL}/usr_API_2.php",
            data={
                "epost": self.user_id,
                "id": CONF_CLIENT_ID,
                "psw": self.token,
                "q": "getVPhwid",
                "session": SESSION,
            },
        ) as response:
            body = await response.text()

            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                _LOGGER.error("Error decoding JSON: %s", e)
                _LOGGER.error("Response body: %s", body)
                return False

        self.device_name, self.hwid, self.device_key = data
        self.device_info_fetched = True

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
            return self.current_state

    async def set_hvac_state(self, target_temp):
        if not self.hwid or not self.device_key:
            raise ValueError("Device info not available. Ensure login was successful.")

        async with self.session.post(
            f"{BASE_URL}/API_2.php",
            data={
                "data": f"0x6:0x11:0x21:0x{target_temp:02X}:0x08:0x80:0x00:0xF0",
                "dir": "set",
                "hwid": self.hwid,
                "psw": self.device_key,
                "token": self.token,
                "usr": f"{self.user_id}.{CONF_CLIENT_ID}",
            },
        ) as response:
            return (await response.text()) == "ACK"
