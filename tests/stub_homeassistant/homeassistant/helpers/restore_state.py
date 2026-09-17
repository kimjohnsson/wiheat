"""Minimal stand-in for homeassistant.helpers.restore_state (test use only).

Tests set ``entity._last_state`` to an object with an ``attributes`` dict and
then await ``async_added_to_hass()`` to exercise the restore path.
"""


class RestoreEntity:
    _last_state = None

    async def async_added_to_hass(self):
        pass

    async def async_get_last_state(self):
        return self._last_state
