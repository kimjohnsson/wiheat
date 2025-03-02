# Wi-Heat

Integrate HVAC sensor in Home Assistant through the Wi-Heat API.

## Description

This integration uses the wi-heat api to poll HVAC data in Home Assistant. The Wi-Heat API has been reversed-engendered using an **IVT Nordic Inverter 12 PRN** (work still in progress).

**Currently it is only possible to get data from the HVAC system.**
Any attempt in controlling the HVAC system from Home Assistant will result in an `unknown error`.

<img src="https://github.com/kimjohnsson/wiheat/blob/main/images/sensors.png?raw=true">
<img src="https://github.com/kimjohnsson/wiheat/blob/main/images/hvac.png?raw=true">

## Installation

### Using HACS

This integration isn't yet added to the HACS store. But you can still add it to Home Assistant by following the [custom repositories instructions](https://www.hacs.xyz/docs/faq/custom_repositories/) using the repository link: `https://github.com/kimjohnsson/wiheat.git`.

After installing the integration using HACS you should be able to add the Wi-Heat integration in the Home Assistant integration page. The Wi-Heat integration requires you to sign in with your Wi-Heat account.

After successful login it can take up to 60 seconds before the integration displays the initial sensor data.
