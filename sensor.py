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

from . import poollab, DOMAIN

_LOGGER = logging.getLogger(__name__)


# https://developers.home-assistant.io/docs/development_validation/
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/config_validation.py
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
    },
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    api_key = config[CONF_API_KEY]
    poollab_api = await poollab.api(api_key)
    for a in poollab_api.Accounts:
        params = list(set([m.parameter for m in a.Measurements]))
        _LOGGER.info(f"Account: Forename {a.forename}, parameters {params}")
        sorted_meas = sorted(a.Measurements, key=lambda x: x.timestamp, reverse=True)
        param_added = []
        for m in sorted_meas:
            if m.parameter not in param_added:
                _LOGGER.info(
                    f"Meas: id {m.id}, date {m.timestamp}, parameter {m.parameter}, scneario {m.scenario}, value {m.value}, unit {m.unit}"
                )
                param_added.append(m.parameter)
                add_entities([MeasurementSensor(a, m)])


class MeasurementSensor(SensorEntity):
    """Base class for poollab sensor"""

    def __init__(self, account: poollab.Account, meas: poollab.Measurement) -> None:
        self._account = account
        self._latest_measurement = meas

    # @property
    # def extra_state_attributes(self):
    #     """Provide attributes for the entity"""
    #     return {
    #         # "starts_at": self._starts_at,
    #         # "cost_at": self._cost_at,
    #         # "now_cost_rate": self._now_cost_rate,
    #     }

    # @property
    # def entity_id(self) -> str:
    #     return "poollab_account%s_%s" % (
    #         self._account.id,
    #         self._latest_measurement.parameter.replace(" ", "_")
    #         .replace("-", "_")
    #         .lower(),
    #     )

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
            # identifiers={
            #     (DOMAIN, self._account.volume),
            #     # ("gps", self._account.gps),
            #     # ("pooltext", self._account.pooltext),
            # },
            model=self._account.volume,
            manufacturer="PoolLab",
        )

    @property
    def _attr_native_value(self):
        return self._latest_measurement.value

    @property
    def _attr_state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    def update(self):
        """Called from Home Assistant to update entity value"""
        now = dt.now()
