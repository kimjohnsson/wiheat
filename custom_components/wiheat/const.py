"""Constants for the WiHeat Climate integration."""
import logging

API_URL = 'https://wi-heat.com/'
ID = 'home-assistant'
SESSION = 'A2B3C4D5E6'

DOMAIN = "wiheat"

CONF_CODE_FORMAT = "code_format"
CONF_CODE = "code"
CONF_TEMP = "temp"
UPDATE_INTERVAL = "timesync"

MIN_SCAN_INTERVAL = 60

API_ENDPOINT = {
    'getUserDetails': f'{API_URL}usr_API_2.php',
    'getData': f'{API_URL}API_2.php'
}

HEADERS = {
    'host': 'wi-heat.com',
    'accept': '*/*',
    'content-type': 'application/x-www-form-urlencoded',
    'accept-encoding': 'gzip, deflate, br',
}

QUERY = {
    'login': 'login',
    'getVpHwid': 'getVPhwid'
}

POWER_STATE = {
    '11': 'on',
    '21': 'off'
}

FAN_SPEED = {
    '2': 'auto',
    '3': 'minimum',
    '5': 'medium',
    '7': 'maximum'
}

PLASMACLUSTER = {
    'F4': 'on',
    'F0': 'off'
}

LOGGER = logging.getLogger(__package__)
