"""planner tests."""

from unittest import mock

# from custom_components.poollab.poollab import PoolLabApi
# from pytest_homeassistant_custom_component.async_mock import patch
# from pytest_homeassistant_custom_component.common import (
#     MockModule,
#     MockPlatform,
#     mock_integration,
#     mock_platform,
# )
from custom_components.poollab import DOMAIN, PoolLabCoordinator
from custom_components.poollab.poollab import PoolLabApi
import pytest

from homeassistant import config_entries
from homeassistant.const import ATTR_NAME

# from homeassistant.components import sensor
# from homeassistant.core import HomeAssistant
# from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant

NAME = "My balancer"

CONF_ENTRY = config_entries.ConfigEntry(
    data={
        ATTR_NAME: NAME,
        "api_key": 5,
    },
    options={},
    domain=DOMAIN,
    version=1,
    minor_version=0,
    source="user",
    title=NAME,
    unique_id="123456",
    discovery_keys=None,
)


@pytest.mark.asyncio
async def test_coordinator_init(hass: HomeAssistant) -> None:
    """Test the coordinator initialization."""

    coordinator = PoolLabCoordinator(hass, PoolLabApi("API_TOKEN"))

    assert coordinator.name == "PoolLab API"
