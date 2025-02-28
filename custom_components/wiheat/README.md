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
  - `id`: Client identifier (e.g., "home-assistant").
  - `psw`: User's password.
  - `q`: API action (`"login"`).
  - `session`: Session token (appears to be static - "A2B3C4D5E6").
- **Response:** Object containing `status`, `id` (user ID), and `token`.

2. **Get Device Details:**

- **Endpoint:** `/usr_API_2.php`
- **Method:** `POST`
- **Request Parameters:**
  - `epost`: user ID (obtained from the login response).
  - `id`: Client identifier (e.g., "home-assistant").
  - `psw`: Token (obtained from the login response).
  - `q`: API action (`"getVPhwid"`).
  - `session`: Session token (appears to be static - "A2B3C4D5E6").
- **Response:** Array containing `device name`, `hwid` (Device hardware ID), `psw` (Device key).

**API Actions:**

- **Get HVAC Status:**

  - **Endpoint:** `/API_2.php`
  - **Method:** `POST`
  - **Request Parameters:**
    - `dir`: `"get"`
    - `hwid`: Device hardware ID (obtained from Get Device Details).
    - `psw`: Device key (obtained from Get Device Details).
    - `token`: Authentication token (obtained from the login response).
    - `usr`: User ID concatenated with client identifier (e.g., "<id (user ID)>.home-assistant").
  - **Response:** Colon-separated string containing HVAC status data (see Data Format below).

- **Set HVAC State:**
  - **Endpoint:** `/API_2.php`
  - **Method:** `POST`
  - **Request Parameters:**
    - `data`: Encoded HVAC settings (see Data Format below).
    - `dir`: `"set"`
    - `hwid`: Device hardware ID (obtained from Get Device Details).
    - `psw`: Device key (obtained from Get Device Details).
    - `token`: Authentication token (obtained from the login response).
    - `usr`: User ID concatenated with client identifier.
  - **Response:** `"ACK"` on success.

**Data Format:**

- **HVAC Status Response:**

  ```
  Example:

  17:11:2:1:0:8:F0:1740765339?18:6:-48:0?NA
  target_temp:power_state:fan_speed:hvac_mode:unknown:unknown:plasmacluster_state:timestamp?current_temp:outdoor_temp:wifi_signal:unknown?unknown
  ```

  - Values are colon and question mark separated.
  - `target_temp`: Target temperature (degrees Celsius).
  - `power_state`: `11` for On, `21` for Off.
  - `fan_speed`: `3` for Low, `5` for Medium, `7` for High, `2` for Auto.
  - `hvac_mode`: `1` for Heat, `2` for Cool, `3` for Dry, `4` for Fan only.
  - `unknown`: Unknown values.
  - `unknown`: Unknown values.
  - `plasmacluster_state`: `F0` for Off, `F4` for On.
  - `timestamp`: Timestamp in UTC.
  - `current_temp`: Current temperature (degrees Celsius).
  - `outdoor_temp`: Current temperature (degrees Celsius).
  - `wifi_signal`: Wifi signal dBm.
  - `unknown`: Unknown values.
  - `unknown`: Unknown values.

- **Encoded HVAC Settings (`data` parameter):**

```
Example:

0x5:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
target_temp:power_state:mode_fan_speed:unknown:swing_mode:unknown:plasmacluster_state
```

- Values are colon-separated hexadecimal bytes.
- `target_temp`:
  - `0x00`: 10
  - `0x4d`: 15
  - `0x4e`: 16
  - `0x4f`: 17
  - `0x1`: 18
  - `0x2`: 19
  - `0x3`: 20
  - `0x4`: 21
  - `0x5`: 22
- `power_state`:
  - `0x11`: On
  - `0x21`: Off
- `mode_fan_speed`:
  - `fan_speed`:
    - `0x31`: Low (3 in response)
    - `0x51`: Medium (5 in response)
    - `0x71`: High: (7 in response)
    - `0x21`: Auto: (2 in response)
  - `hvac_mode`
    - `0x31`: Heat (1 in response)
    - `0x22`: Cool (2 in response)
    - `0x23`: Dry (3 in response)
    - `0x34`: Fan only (4 in response)
- `unknown`: Unknown values
- `swing_mode`:
  - `vertical`:
    - `0x0D`: Down
    - `0x28`: Left
    - `0x0C`: Center
    - `0x09`: Up
    - `0x08`: Auto
  - `horizontal`:
    - `0x28`: Left
    - `0x18`: Center
    - `0x38`: Right
    - `0x88`: All
- `unknown`: Unknown values
- `plasmacluster_state`:
  - `0xF0`: Off
  - `0xF4`: On

**Notes:**

- This documentation is based on limited observations and may not be accurate for all WiHeat devices or API versions.
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
        "id": "home-assistant",
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
hwid = data[1]
device_key = data[2]

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
