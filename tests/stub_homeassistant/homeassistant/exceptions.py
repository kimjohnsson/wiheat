"""Minimal stand-in for homeassistant.exceptions (test use only)."""


class HomeAssistantError(Exception):
    def __init__(
        self,
        *args,
        translation_domain=None,
        translation_key=None,
        translation_placeholders=None,
    ):
        super().__init__(*args)
        self.translation_domain = translation_domain
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders
