# WiHeat API Documentation (Unofficial)

This documentation is based on reverse-engineering the WiHeat API through network traffic analysis. It may not be exhaustive and is subject to change as the API evolves.

**Base URL:** `https://wi-heat.com/`

**Endpoints:**

- `/usr_API_2.php`: Used for user authentication and retrieving device information.
- `/API_2.php`: Used for fetching HVAC status and sending control commands.

**Authentication:**

The WiHeat API uses a token-based authentication system.

1. **Login:**

- **Endpoint:** `/usr_API_2.php`
- **Method:** `POST`
- **Request Parameters:**
  - `epost`: User's email address.
  - `hwid`: Device hardware ID (empty for login).
  - `id`: Client identifier (e.g., "home-assistant").
  - `namn`: App information (empty for login).
  - `psw`: User's password.
  - `q`: API action (`"login"`).
  - `session`: Session token (appears to be static - "A2B3C4D5E6").
- **Response:** JSON object containing `status`, `id` (user ID), and `token`.

2. **Subsequent Requests:**

- Include the `token` obtained from the login response in the `psw` or `token` parameter of subsequent requests.

**API Actions:**

- **Get Device Details:**

  - **Endpoint:** `/usr_API_2.php`
  - **Method:** `POST`
  - **Request Parameters:**
    - `epost`: User ID (obtained from login).
    - `id`: Client identifier.
    - `psw`: Authentication token.
    - `q`: API action ("getVPhwid").
    - `session`: Session token.
  - **Response:** JSON array containing device name, `hwid`, and a device key.

- **Get HVAC Status:**

  - **Endpoint:** `/API_2.php`
  - **Method:** `POST`
  - **Request Parameters:**
    - `dir`: `"get"`
    - `hwid`: Device hardware ID.
    - `psw`: Device key (obtained from Get Device Details).
    - `token`: Authentication token.
    - `usr`: User ID concatenated with client identifier (e.g., "<id (user ID)>.home-assistant").
  - **Response:** Colon-separated string containing HVAC status data (see Data Format below).

- **Set HVAC State:**
  - **Endpoint:** `/API_2.php`
  - **Method:** `POST`
  - **Request Parameters:**
    - `data`: Encoded HVAC settings (see Data Format below).
    - `dir`: `"set"`
    - `hwid`: Device hardware ID.
    - `psw`: Device key.
    - `token`: Authentication token.
    - `usr`: User ID concatenated with client identifier.
  - **Response:** `"ACK"` on success.

**Data Format:**

- **HVAC Status Response:**

  ```
  Example:

  17:11:2:1:0:8:F0:1740765339?18:6:-48:0?NA
  target_temp:power_state:mode_fan_speed:hvac_mode:unknown:unknown:plasmacluster_state:timestamp?current_temp:outdoor_temp:wifi_signal:unknown?unknown
  ```

  - Values are colon-separated.
  - `current_temp`: Current temperature (degrees Celsius).
  - `power_state`: `11` for On, `21` for Off.
  - `mode_fan_speed`: Combination of mode and fan speed (see below).
  - `target_temp`: Target temperature (degrees Celsius).
  - `swing_mode`: Swing setting (see below).
  - `unknown`: Unknown values.
  - `plasmacluster_state`: `F0` for Off, `F4` for On.

- **Encoded HVAC Settings (`data` parameter):**
  `mode_category:power_state:mode_fan_speed:target_temp:swing_mode:unknown:unknown:plasmacluster_state`

  - Values are colon-separated hexadecimal bytes.
  - `mode_category`:
    - `0x03`: Heating/Cooling
    - `0x05`: Mode with Swing control
    - `0x06`: Auto
  - `power_state`:
    - `0x11`: On
    - `0x21`: Off
  - `mode_fan_speed`:
    - `0x21`: Heat (when `mode_category` is `0x03`) / Auto (when `mode_category` is `0x06`)
    - `0x22`: Cool (when `mode_category` is `0x03`)
    - `0x31`: Low fan speed
    - `0x51`: Medium fan speed
    - `0x71`: High fan speed
  - `target_temp`: Target temperature (hexadecimal).
  - `swing_mode`:
    - `0x08`: Auto swing
    - `0x09`: Up swing
    - `0x0C`: Middle swing
    - `0x0D`: Down swing
  - `unknown`: Unknown values (possibly constants).
  - `plasmacluster_state`:
    - `0xF0`: Off
    - `0xF4`: On

**Notes:**

- This documentation is based on limited observations and may not be accurate for all WiHeat devices or API versions.
- The API appears to lack official documentation, so this unofficial version may be helpful for developers.
- Use this information responsibly and at your own risk.

**Example Usage:**

```
Python
```

```
import requests

# Replace with your actual credentials
email = "your_email@example.com"
password = "your_password"

## 1. Login
response = requests.post(
    "https://wi-heat.com/usr_API_2.php",
    data={
        "epost": email,
        "hwid": "",
        "id": "home-assistant",
        "namn": "Home Assistant Integration",
        "psw": password,
        "q": "login",
        "session": "A2B3C4D5E6",
    },
)
response.raise_for_status()
data = response.json()
token = data["token"]
user_id = data["id"]

## 2. Get Device Details
response = requests.post(
    "https://wi-heat.com/usr_API_2.php",
    data={
        "epost": user_id,
        "id": "home-assistant",
        "psw": token,
        "q": "getVPhwid",
        "session": "A2B3C4D5E6",
    },
)
response.raise_for_status()
data = response.json()
hwid = data
device_key = data

## 3. Get HVAC Status
response = requests.post(
    "https://wi-heat.com/API_2.php",
    data={
        "dir": "get",
        "hwid": hwid,
        "psw": device_key,
        "token": token,
        "usr": f"{user_id}.home-assistant",
    },
)
response.raise_for_status()
status_data = response.text()

## 4. Set HVAC State (e.g., set temperature to 24 degrees)
response = requests.post(
    "https://wi-heat.com/API_2.php",
        data={
        "data": "0x6:0x11:0x21:0x18:0x08:0x80:0x00:0xF0", # 0x18 = 24 degrees
        "dir": "set",
        "hwid": hwid,
        "psw": device_key,
        "token": token,
        "usr": f"{user_id}.home-assistant",
    },
)
response.raise_for_status()
```

This is a basic example of how to interact with the WiHeat API. You can adapt this code to build your own applications or integrations.

### Edit request data

`target_temp:power_state:mode_fan_speed/heating_mode:unknown:swing_mode:unknown:unknown:plasmacluster_state`

POWER
ON `11` -> ``0x11`
OFF `21` -> `0x21`
ION
ON `F4` -> `0xF4`
OFF `F0` -> `0xF0`
TEMP
10 `10` -> `0x00`
15 `15` -> `0x4d`
16 `16` -> `0x4e`
17 `17` -> `0x4f`
18 `18` -> `0x1`
19 `19` -> `0x2`
20 `20` -> `0x3`
21 `21` -> `0x4`
22 `22` -> `0x5`
FAN
LOW `3` -> `0x31`
MEDIUM `5` -> `0x51`
HIGH `7` -> `0x71`
AUTO `2` -> `0x21`
SWING_VERTICAL
DOWN `UNKNOWN` -> `0x0D`
CENTER `UNKNOWN` -> `0x0C`
UP `UNKNOWN` -> `0x09`
AUTO `UNKNOWN` -> `0x08`
SWING_HORIZONTAL
LEFT `UNKNOWN` -> `0x28`
CENTER `UNKNOWN` -> `0x18`
RIGHT `UNKNOWN` -> `0x38`
ALL `UNKNOWN` -> `0x88`
HEATING_MODE
HEAT `1` -> `0x31`
COOL `2` -> `0x22`
HUMID (legionella?) `3` -> `0x23`
FAN `4` -> `0x34`
