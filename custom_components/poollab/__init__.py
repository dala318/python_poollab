"""Home Assistant integration for cloud API access to PoolLab measurements."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from gql.client import TransportQueryError

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .poollab import API_ENDPOINT, PoolLabApi

DOMAIN = "poollab"
PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class PoolLabConfigException(HomeAssistantError):
    """Error to indicate there is an error in config."""


class PoolLabCoordinator(DataUpdateCoordinator):
    """Coordinator for the PoolLab API."""

    def __init__(self, hass: HomeAssistant, api: PoolLabApi) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="PoolLab API",
            update_interval=timedelta(seconds=30),
            update_method=self._async_update_data,
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with asyncio.timeout(10):
                return await self.api.request()
        except TransportQueryError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            raise UpdateFailed(f"Unknown error communicating with API: {err}") from err


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if config_entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][config_entry.entry_id] = poollab = PoolLabCoordinator(
            hass,
            PoolLabApi(
                token=config_entry.data[CONF_API_KEY], url=config_entry.data[CONF_URL]
            ),
        )
    else:
        poollab = hass.data[DOMAIN][config_entry.entry_id]
    await poollab.async_config_entry_first_refresh()

    if config_entry is not None:
        if config_entry.source == SOURCE_IMPORT:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
            return False

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading a config_flow entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    version = config_entry.version
    _LOGGER.debug("Migrating from version %s", version)

    new_data = {**config_entry.data}

    if version == 1:
        config_entry.version = 2
        new_data[CONF_URL] = API_ENDPOINT
        hass.config_entries.async_update_entry(config_entry, data=new_data)
        _LOGGER.info("Migration to version %s successful", config_entry.version)
        return True

    return False
