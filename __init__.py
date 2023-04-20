from __future__ import annotations
from config.custom_components.hacs.enums import ConfigurationType

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .lib.poollab import PoolLabApi

DOMAIN = "poollab"
PLATFORMS = ["sensor"]


class PoolLabConfigException(HomeAssistantError):
    """Error to indicate there is an error in config."""


class PoolLabConfiguration:
    config_type: ConfigurationType | None = None

    def update_from_dict(self, data: dict) -> None:
        """Set attributes from dicts."""
        if not isinstance(data, dict):
            raise PoolLabConfigException("Configuration is not valid.")

        for key in data:
            self.__setattr__(key, data[key])


class PoolLabApiSessions:
    configuration = PoolLabConfiguration()

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._apis = []

    # def update_from_dict(self, data: dict) -> None:
    #     """Set attributes from dicts."""
    #     if not isinstance(data, dict):
    #         raise PoolLabConfigException("Configuration is not valid.")

    #     for key in data:
    #         self.__setattr__(key, data[key])


async def _async_dry_setup(
    hass: HomeAssistant,
    *,
    config: Config | None = None,
    config_entry: ConfigEntry | None = None,
) -> bool:
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = poollab = PoolLabApiSessions(hass)
    else:
        poollab: PoolLabApiSessions = hass.data[DOMAIN]

    if config is not None:
        if DOMAIN not in config:
            return True
        if poollab.configuration.config_type == ConfigurationType.CONFIG_ENTRY:
            return True
        poollab.configuration.update_from_dict(
            {
                "config_type": ConfigurationType.YAML,
                **config[DOMAIN],
                "config": config[DOMAIN],
            }
        )

    if config_entry is not None:
        if config_entry.source == SOURCE_IMPORT:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
            return False
        poollab.configuration.update_from_dict(
            {
                "config_entry": config_entry,
                "config_type": ConfigurationType.CONFIG_ENTRY,
                **config_entry.data,
                **config_entry.options,
            }
        )

    return True


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Setup up a configuration entry."""
    return await _async_dry_setup(hass=hass, config=config)
    hass.data.setdefault(DOMAIN, {})
    # if "sensor" in config and DOMAIN in config["sensor"]:
    #     return await _async_dry_setup(hass, config["sensor"][DOMAIN])
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))
    setup_result = await _async_dry_setup(hass=hass, config_entry=config_entry)
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    # poollab: PoolLabApiSessions = hass.data[DOMAIN]
    return setup_result  # and not poollab.system.disabled


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Setup up a config_flow entry."""
#     entry_data = dict(entry.data)
#     hass.data[DOMAIN][entry.entry_id] = entry_data
#     hass.config_entries.async_setup_platforms(entry, PLATFORMS)
#     return True


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
