"""Diagnostics support for Nordpool Planner."""

from __future__ import annotations

# import json
import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TO_REDACT = [
    CONF_API_KEY,
    "unique_id",
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return async_redact_data(
        {
            "entry_data": config_entry.data,
            "coordinator": hass.data[DOMAIN][config_entry.entry_id].get_diag(),
        },
        TO_REDACT,
    )
