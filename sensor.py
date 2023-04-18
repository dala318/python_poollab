from __future__ import annotations

import logging

# from multiprocessing import pool
from typing import Any
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt

from . import poollab

_LOGGER = logging.getLogger(__name__)

API_KEY = "api_key"


# https://developers.home-assistant.io/docs/development_validation/
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/config_validation.py
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(API_KEY): cv.string,
    },
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    api_key = config[API_KEY]
    # poollab_api = poollab.api(api_key)
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
                add_entities([MeasurementSensor(m.parameter, m.value, m.unit)])
    pass


class MeasurementSensor(SensorEntity):
    """Base class for poollab sensor"""

    def __init__(self, meas_type, value, unit) -> None:
        self._meas_type = meas_type
        self._value = value
        self._unit = unit

    @property
    def extra_state_attributes(self):
        """Provide attributes for the entity"""
        return {
            # "starts_at": self._starts_at,
            # "cost_at": self._cost_at,
            # "now_cost_rate": self._now_cost_rate,
        }

    def _update(self):
        # Evaluate data
        now = dt.now()
