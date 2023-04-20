from __future__ import annotations

import logging

# from multiprocessing import pool
# from typing import Any
import voluptuous as vol
from homeassistant.components.sensor.const import SensorStateClass
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
)

# from homeassistant.const import STATE_UNKNOWN
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt

from . import DOMAIN
from .lib import poollab

_LOGGER = logging.getLogger(__name__)


# https://developers.home-assistant.io/docs/development_validation/
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/config_validation.py
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
    },
)


async def _dry_setup(hass, config, add_entities, discovery_info=None):
    api_key = config[CONF_API_KEY]
    poollab_api = poollab.PoolLabApi(api_key)
    poollab_data = await poollab_api.request()
    for a in poollab_data.Accounts:
        params = list(set([m.parameter for m in a.Measurements]))
        _LOGGER.debug(
            "Account: id: %s, Name %s, parameters %s", a.id, a.full_name, params
        )
        sorted_meas = sorted(a.Measurements, key=lambda x: x.timestamp, reverse=True)
        param_added = []
        for m in sorted_meas:
            if m.parameter not in param_added:
                _LOGGER.debug(
                    "Meas: id %s, date %s, parameter %s, scneario %s, value %s, unit %s",
                    m.id,
                    m.timestamp,
                    m.parameter,
                    m.scenario,
                    m.value,
                    m.unit,
                )
                param_added.append(m.parameter)
                add_entities([MeasurementSensor(a, m)])


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    await _dry_setup(hass, config, add_entities)
    return True


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Setup sensor platform for the ui"""
    config = config_entry.data
    await _dry_setup(hass, config, async_add_devices)
    return True


class MeasurementSensor(SensorEntity):
    """Base class for poollab sensor"""

    def __init__(self, account: poollab.Account, meas: poollab.Measurement) -> None:
        self._account = account
        self._latest_measurement = meas

    @property
    def _attr_unique_id(self) -> str:
        return "account%s_%s" % (
            self._account.id,
            self._latest_measurement.parameter.replace(" ", "_")
            .replace("-", "_")
            .lower(),
        )

    @property
    def _attr_name(self) -> str:
        return "%s %s" % (self._account.full_name, self._latest_measurement.parameter)

    @property
    def _attr_device_info(self) -> DeviceInfo:
        """Return a inique set of attributes for each vehicle."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._account.id)},
            name=self._account.full_name,
            model="%sm3" % self._account.volume,
            manufacturer="PoolLab",
        )

    @property
    def _attr_native_value(self):
        return self._latest_measurement.value

    @property
    def _attr_native_unit_of_measurement(self) -> str:
        return self._latest_measurement.unit.split(" ")[0]

    @property
    def _attr_state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def _attr_extra_state_attributes(self):
        """Provide attributes for the entity"""
        return {
            "measured_at": self._latest_measurement.timestamp,
            "measure": self._latest_measurement.id,
            "ideal_low": self._latest_measurement.ideal_low,
            "ideal_high": self._latest_measurement.ideal_high,
            "device_serial": self._latest_measurement.device_serial,
            "operator_name": self._latest_measurement.operator_name,
            "comment": self._latest_measurement.comment,
        }

    def update(self):
        """Called from Home Assistant to update entity value"""
        now = dt.now()
