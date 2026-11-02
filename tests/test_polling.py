"""Verify polling, effective request timeouts, and sensor update filtering."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.const import CONF_API_KEY, CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.poollab import DOMAIN, PoolLabCoordinator
from custom_components.poollab.poollab import API_ENDPOINT, CloudAccount, PoolLabApi
from custom_components.poollab.sensor import MeasurementSensor


@pytest.fixture
def cloud_data():
    """A response containing two independent measurements."""
    return {
        "CloudAccount": {
            "id": 1,
            "Accounts": [{
                "id": 2,
                "forename": "Pool",
                "Measurements": [
                    {
                        "id": 3,
                        "parameter": "PL pH",
                        "scenario": "429-pH-PoolLab",
                        "unit": "pH",
                        "value": "7.2",
                        "timestamp": 1720000000,
                    },
                    {
                        "id": 4,
                        "parameter": "PL Chlorine Free",
                        "unit": "mg/l",
                        "value": "1.0",
                        "timestamp": 1720000000,
                    },
                ],
            }],
            "WaterTreatmentProducts": [],
        },
    }


@pytest.mark.asyncio
async def test_request_timeouts(cloud_data):
    """The HTTP and GraphQL layers must both allow a 30-second request."""
    session = AsyncMock()
    session.execute.return_value = cloud_data
    with (
        patch("custom_components.poollab.poollab.AIOHTTPTransport") as transport,
        patch("custom_components.poollab.poollab.Client") as client,
    ):
        client.return_value.__aenter__.return_value = session
        result = await PoolLabApi("test-token").request()

    assert result == CloudAccount(cloud_data)
    assert transport.call_args.kwargs["timeout"] == 30
    assert client.call_args.kwargs["execute_timeout"] == 30
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinator_polling(hass, cloud_data):
    """Unchanged polls are quiet; failures and recovery still notify."""
    api = Mock(spec=PoolLabApi)
    api.request = AsyncMock(return_value=CloudAccount(cloud_data))
    coordinator = PoolLabCoordinator(hass, api)
    assert coordinator.update_interval == timedelta(minutes=15)
    with patch("custom_components.poollab.asyncio.timeout") as timeout:
        await coordinator.async_refresh()
    timeout.assert_called_once_with(30)

    listener = Mock()
    remove_listener = coordinator.async_add_listener(listener)
    try:
        api.request.return_value = CloudAccount(deepcopy(cloud_data))
        await coordinator.async_refresh()
        listener.assert_not_called()

        api.request.side_effect = TimeoutError()
        await coordinator.async_refresh()
        listener.assert_called_once_with()
        assert not coordinator.last_update_success
        listener.reset_mock()

        await coordinator.async_refresh()
        listener.assert_not_called()

        api.request.side_effect = None
        await coordinator.async_refresh()
        listener.assert_called_once_with()
        assert coordinator.last_update_success
    finally:
        remove_listener()
        await coordinator.async_shutdown()


@pytest.fixture
def measurement_sensor(hass, cloud_data):
    """A real sensor whose write calls can be observed."""
    api = Mock(spec=PoolLabApi)
    coordinator = PoolLabCoordinator(hass, api)
    coordinator.async_set_updated_data(CloudAccount(cloud_data))
    account = coordinator.data.Accounts[0]
    sensor = MeasurementSensor(coordinator, account, account.Measurements[0])
    return sensor


@pytest.mark.asyncio
async def test_unrelated_measurement_does_not_write(measurement_sensor, cloud_data):
    """Neither equal snapshots nor changes to another sensor cause a write."""
    sensor = measurement_sensor
    with patch.object(sensor, "async_write_ha_state") as write:
        sensor.coordinator.async_set_updated_data(CloudAccount(deepcopy(cloud_data)))
        sensor._handle_coordinator_update()
        changed = deepcopy(cloud_data)
        changed["CloudAccount"]["Accounts"][0]["Measurements"][1]["value"] = "2.0"
        sensor.coordinator.async_set_updated_data(CloudAccount(changed))
        sensor._handle_coordinator_update()
    write.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value", "attribute"),
    [
        ("id", 5, "measure"),
        ("timestamp", 1720000060, "measured_at"),
        ("value", "7.4", None),
        ("comment", "Corrected comment", "comment"),
        ("ideal_high", "7.6", "ideal_high"),
    ],
)
@pytest.mark.asyncio
async def test_measurement_changes_write(
    measurement_sensor, cloud_data, field, value, attribute
):
    """New measurements and metadata corrections remain visible."""
    sensor = measurement_sensor
    before = (
        sensor.native_value
        if attribute is None
        else sensor.extra_state_attributes[attribute]
    )
    changed = deepcopy(cloud_data)
    changed["CloudAccount"]["Accounts"][0]["Measurements"][0][field] = value
    sensor.coordinator.async_set_updated_data(CloudAccount(changed))
    with patch.object(sensor, "async_write_ha_state") as write:
        sensor._handle_coordinator_update()
        sensor._handle_coordinator_update()
    write.assert_called_once_with()
    after = (
        sensor.native_value
        if attribute is None
        else sensor.extra_state_attributes[attribute]
    )
    assert before != after


@pytest.mark.asyncio
async def test_sensor_availability_recovers(measurement_sensor, cloud_data):
    """An unchanged reading must still be written after connection recovery."""
    sensor = measurement_sensor
    writes = []
    with patch.object(
        sensor, "async_write_ha_state", side_effect=lambda: writes.append(sensor.available)
    ):
        sensor.coordinator.last_update_success = False
        sensor._handle_coordinator_update()
        sensor._handle_coordinator_update()
        sensor.coordinator.async_set_updated_data(CloudAccount(deepcopy(cloud_data)))
        sensor._handle_coordinator_update()
        sensor._handle_coordinator_update()
    assert writes == [False, True]
    assert sensor.native_value == 7.2


@pytest.mark.parametrize("same_value", [False, True])
@pytest.mark.asyncio
async def test_partial_sync_preserves_unmeasured_timestamps(
    hass, cloud_data, freezer, same_value
):
    """A partial sync must not report an unmeasured sensor again (#67)."""
    first_day = deepcopy(cloud_data)
    first_day["CloudAccount"]["Accounts"][0]["Measurements"].append({
        "id": 5,
        "parameter": "PL Cyanuric Acid",
        "scenario": "431-Cyanuric-Acid",
        "unit": "mg/l",
        "value": "30",
        "timestamp": 1720000000,
    })
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-token", CONF_URL: API_ENDPOINT},
        version=1,
        minor_version=3,
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.poollab.PoolLabApi.request",
        return_value=CloudAccount(first_day),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][entry.entry_id]
        original = {
            state.attributes["parameter"]: (
                state.last_changed,
                state.last_updated,
                state.last_reported,
                state.attributes["measured_at"],
            )
            for state in hass.states.async_all("sensor")
            if "parameter" in state.attributes
        }
        assert len(original) == 3

        second_day = deepcopy(first_day)
        measurements = second_day["CloudAccount"]["Accounts"][0]["Measurements"]
        for measurement in measurements[:2]:
            measurement["id"] += 10
            measurement["timestamp"] += 86400
            if not same_value:
                measurement["value"] = str(float(measurement["value"]) + 0.1)

        freezer.tick(timedelta(milliseconds=1))
        coordinator.async_set_updated_data(CloudAccount(second_day))
        await hass.async_block_till_done()

        updated = {
            state.attributes["parameter"]: state
            for state in hass.states.async_all("sensor")
            if "parameter" in state.attributes
        }
        cya = updated["PL Cyanuric Acid"]
        assert (
            cya.last_changed,
            cya.last_updated,
            cya.last_reported,
            cya.attributes["measured_at"],
        ) == original["PL Cyanuric Acid"]
        for parameter in ("PL pH", "PL Chlorine Free"):
            state = updated[parameter]
            before = original[parameter]
            if same_value:
                assert state.last_changed == before[0]
            else:
                assert state.last_changed > before[0]
            assert state.last_updated > before[1]
            assert state.last_reported > before[2]
            assert state.attributes["measured_at"] == before[3] + timedelta(days=1)

        assert await hass.config_entries.async_unload(entry.entry_id)
