# Wi-Heat

Integrate HVAC sensor in Home Assistant through the Wi-Heat API.

## Description

This integration uses the wi-heat api to poll HVAC data in Home Assistant. The Wi-Heat API has been reversed-engendered using an **IVT Nordic Inverter 12 PRN** (work still in progress).

<img style="width: 40%" src="https://github.com/kimjohnsson/wiheat/blob/main/images/sensors.png?raw=true"> <img style="width: 40%" src="https://github.com/kimjohnsson/wiheat/blob/main/images/hvac.png?raw=true">

## Installation

### Installation through HACS

Installation using Home Assistant Community Store (HACS) is recommended.

1. If HACS is not installed, follow HACS installation and configuration at <https://hacs.xyz/>.

2. Click the button below or visit HACS and search for "Wi-Heat" (make sure no type filter is set).

    [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kimjohnsson&repository=wiheat&category=integration)

3. Install the integration.

4. Restart Home Assistant!

After installing the integration using HACS you should be able to add the Wi-Heat integration in the Home Assistant integration page. The Wi-Heat integration requires you to sign in with your Wi-Heat account.

After successful login it can take up to 60 seconds before the integration displays the initial sensor data.
