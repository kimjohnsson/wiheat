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
  - `0x49`: 11
  - `0x4a`: 12
  - `0x4b`: 13
  - `0x4c`: 14
  - `0x4d`: 15
  - `0x4e`: 16
  - `0x4f`: 17
  - `0x1`: 18
  - `0x2`: 19
  - `0x3`: 20
  - `0x4`: 21
  - `0x5`: 22
  - `0x6`: 23
  - `0x7`: 24
  - `0x8`: 25
  - `0x9`: 26
  - `0xa`: 27
  - `0xb`: 28
  - `0xc`: 29
  - `0xd`: 30
  - `0xe`: 31
  - `0xf`: 32
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

## Example Request Data

This is some examples of what is sent in the data attribute when making changes in the wi-heat app together with the updated data when getting the current state of the HVAC system.

- **Changing temperature**
  - 10
    ```
    0x00:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    10:11:2:1:0:8:F0:1740924693?19:10:-46:0?NA
    ```
  - 11
    ```
    0x49:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    11:11:2:1:0:8:F0:1740924028?18:10:-46:0?NA
    ```
  - 12
    ```
    0x4a:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    12:11:2:1:0:8:F0:1740924056?18:10:-46:0?NA
    ```
  - 13
    ```
    0x4b:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    13:11:2:1:0:8:F0:1740924087?18:10:-46:0?NA
    ```
  - 14
    ```
    0x4c:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    14:11:2:1:0:8:F0:1740924116?17:10:-45:0?NA
    ```
  - 15
    ```
    0x4d:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    15:11:2:1:0:8:F0:1740761779?23:3:-48:0?NA
    ```
  - 16
    ```
    0x4e:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    16:11:2:1:0:8:F0:1740761739?22:3:-49:0?NA
    ```
  - 17
    ```
    0x4f:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    17:11:2:1:0:8:F0:1740761098?18:3:-49:0?NA
    ```
  - 17
    ```
    0x4f:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    17:11:2:1:0:8:F0:1740761098?18:3:-49:0?NA
    ```
  - 18
    ```
    0x1:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    18:11:2:1:0:8:F0:1740760769?18:8:-49:0?NA
    ```
  - 19
    ```
    0x2:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    19:11:2:1:0:8:F0:1740761266?19:3:-49:0?NA
    ```
  - 20
    ```
    0x3:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    20:11:2:1:0:8:F0:1740761437?17:3:-50:0?NA
    ```
  - 21
    ```
    0x4:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    21:11:2:1:0:8:F0:1740761582?20:3:-48:0?NA
    ```
  - 22
    ```
    0x5:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    22:11:2:1:0:8:F0:1740761652?22:3:-49:0?NA
    ```
  - 23
    ```
    0x6:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    23:11:2:1:0:8:F0:1740924184?17:10:-45:0?NA
    ```
  - 24
    ```
    0x7:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    24:11:2:1:0:8:F0:1740924211?17:12:-45:0?NA
    ```
  - 25
    ```
    0x8:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    25:11:2:1:0:8:F0:1740924237?17:12:-45:0?NA
    ```
  - 26
    ```
    0x9:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    26:11:2:1:0:8:F0:1740924264?17:12:-45:0?NA
    ```
  - 27
    ```
    0xa:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    27:11:2:1:0:8:F0:1740924291?17:12:-45:0?NA
    ```
  - 28
    ```
    0xb:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    28:11:2:1:0:8:F0:1740924319?18:10:-46:0?NA
    ```
  - 29
    ```
    0xc:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    29:11:2:1:0:8:F0:1740924349?18:10:-46:0?NA
    ```
  - 30
    ```
    0xd:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    30:11:2:1:0:8:F0:1740924382?18:10:-46:0?NA
    ```
  - 31
    ```
    0xe:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    31:11:2:1:0:8:F0:1740924409?19:10:-44:0?NA
    ```
  - 32
    ```
    0xf:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    32:11:2:1:0:8:F0:1740924439?19:10:-44:0?NA
    ```
- **Changing On/Off**
  - Off
    ```
    0x4f:0x21:0x21:0x16:0x08:0x80:0x00:0xF0
    17:21:2:1:0:8:F0:1740762817?19:8:-49:0?NA
    ```
  - On
    ```
    0x4f:0x11:0x21:0x16:0x18:0x80:0x00:0xF0
    17:11:2:1:0:8:F0:1740762856?19:8:-49:0?NA
    ```
- **Changing plasmacluster**
  - Ion off
    ```
    0x4f:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    17:11:2:1:0:8:F0:1740763548?18:6:-49:0?NA
    ```
  - Ion on
    ```
    0x4f:0x11:0x21:0x16:0x08:0x80:0x00:0xF4
    17:11:2:1:0:8:F4:1740763513?18:7:-49:0?NA
    ```
- **Changing fan speed**
  - Low
    ```
    0x4f:0x11:0x31:0x16:0x08:0x80:0x00:0xF0
    17:11:3:1:0:8:F0:1740763866?19:2:-48:0?NA
    ```
  - Medium
    ```
    0x4f:0x11:0x51:0x16:0x08:0x80:0x00:0xF0
    17:11:5:1:0:8:F0:1740763903?19:2:-48:0?NA
    ```
  - High
    ```
    0x4f:0x11:0x71:0x16:0x08:0x80:0x00:0xF0
    17:11:7:1:0:8:F0:1740763933?19:2:-48:0?NA
    ```
  - Auto
    ```
    0x4f:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
    17:11:2:1:0:8:F0:1740763970?18:4:-47:0?NA
    ```
- **Changing swing mode**
  - Vertical
    - Up
      ```
      0x4f:0x11:0x21:0x16:0x09:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740764863?18:2:-48:0?NA
      ```
    - Center
      ```
      0x4f:0x11:0x21:0x16:0x0C:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740764831?18:2:-48:0?NA
      ```
    - Down
      ```
      0x4f:0x11:0x21:0x16:0x0D:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740764767?18:2:-48:0?NA
      ```
    - Auto
      ```
      0x4f:0x11:0x21:0x16:0x08:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740764910?19:1:-48:0?NA
      ```
  - Horizontal
    - Left
      ```
      0x4f:0x11:0x21:0x16:0x28:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740765274?18:5:-48:0?NA
      ```
    - Center
      ```
      0x4f:0x11:0x21:0x16:0x18:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740764910?19:1:-48:0?NA
      ```
    - Right
      ```
      0x4f:0x11:0x21:0x16:0x38:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740765312?18:5:-48:0?NA
      ```
    - All
      ```
      0x4f:0x11:0x21:0x16:0x88:0x80:0x00:0xF0
      17:11:2:1:0:8:F0:1740765339?18:6:-48:0?NA
      ```
- **Changing HVAC mode**
  - Heat
    ```
    0x3:0x11:0x31:0x16:0x08:0x80:0x00:0xF4
    20:11:3:1:0:8:F4:1740765909?19:2:-48:0?NA
    ```
  - Cool
    ```
    0x3:0x11:0x22:0x16:0x18:0x80:0x00:0xF0
    20:11:2:2:0:8:F0:1740765802?19:1:-50:0?NA
    ```
  - Dry
    ```
    0x1:0x11:0x23:0x16:0x08:0x80:0x00:0xF0
    128:11:2:3:0:8:F0:1740765836?19:1:-50:0?NA
    ```
  - Fan only
    ```
    0x1:0x11:0x34:0x16:0x08:0x80:0x00:0xF4
    128:11:3:4:0:8:F4:1740765879?19:2:-48:0?NA
    ```
