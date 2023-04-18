from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant

# from poollab import PoolLabApi

DOMAIN = "poollab"
PLATFORMS = ["sensor"]


# class SessionApi:
#     def __init__(self, hass: HomeAssistant) -> None:
#         self._hass = hass
#         # self._api = api


# async def _dry_setup(hass: HomeAssistant, config: Config) -> bool:
#     if DOMAIN not in hass.data:
#         api = PoolLabApi()


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Setup up a configuration entry."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup up a config_flow entry."""
    entry_data = dict(entry.data)
    hass.data[DOMAIN][entry.entry_id] = entry_data
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading a config_flow entry"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
