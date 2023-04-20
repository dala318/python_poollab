from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.entity import DeviceInfo

from . import DOMAIN
from .lib import poollab

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup sensor platform for the ui"""
    config = config_entry.data
    # poollab = hass.data[DOMAIN]
    # await _async_dry_setup(hass, config, async_add_devices)
    api_coordinator = hass.data[DOMAIN][config_entry.entry_id]
    poollab_data = await api_coordinator.api.request()

    # coordinator = MyCoordinator(hass, my_api)

    # api_key = config[CONF_API_KEY]
    # poollab_api = poollab.PoolLabApi(api_key)
    # poollab_data = await poollab_api.request()
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
                async_add_entities([MeasurementSensor(a, m, config_entry.entry_id)])
    return True


class MeasurementSensor(SensorEntity):
    """Base class for poollab sensor"""

    def __init__(
        self, account: poollab.Account, meas: poollab.Measurement, entry_id: str
    ) -> None:
        self._account = account
        self._latest_measurement = meas
        self._entry_id = entry_id

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

    # def update(self):
    #     """Called from Home Assistant to update entity value"""
    #     now = dt.now()
