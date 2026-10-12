"""Tests for the PoolLab coordinator."""

from datetime import timedelta

from custom_components.poollab import PoolLabCoordinator
from custom_components.poollab.poollab import PoolLabApi


async def test_coordinator_init(hass):
    """Initialize the coordinator with its API and polling interval."""
    api = PoolLabApi("API_TOKEN")
    coordinator = PoolLabCoordinator(hass, api)

    assert coordinator.api is api
    assert coordinator.name == "PoolLab API"
    assert coordinator.update_interval == timedelta(seconds=30)
