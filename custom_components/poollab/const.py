"""Common constants for integration."""

from homeassistant.exceptions import HomeAssistantError

DOMAIN = "poollab"


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
