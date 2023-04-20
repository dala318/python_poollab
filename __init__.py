"""Home Assistant integration for cloud API access to PoolLab measuremetns"""
from __future__ import annotations
import async_timeout
import logging
from datetime import timedelta
from gql.client import TransportQueryError

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .lib.poollab import PoolLabApi

DOMAIN = "poollab"
PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class PoolLabConfigException(HomeAssistantError):
    """Error to indicate there is an error in config."""


class PoolLabCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api: PoolLabApi) -> None:
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
            async with async_timeout.timeout(10):
                return await self.api.request()
        # except ApiAuthError as err:
        # except GraphQLErroras as err:
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
            hass, PoolLabApi(config_entry.data[CONF_API_KEY])
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

    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading a config_flow entry"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the HACS config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)
