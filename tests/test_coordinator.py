"""Tests for the PoolLab coordinator."""

from custom_components.poollab import PoolLabCoordinator
from custom_components.poollab.poollab import PoolLabApi


async def test_coordinator_init(hass):
    """Initialize the coordinator with its API and name."""
    api = PoolLabApi("API_TOKEN")
    coordinator = PoolLabCoordinator(hass, api)

    assert coordinator.api is api
    assert coordinator.name == "PoolLab API"
