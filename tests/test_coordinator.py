"""planner tests."""

from unittest import mock

from custom_components.ev_load_balancing import EvLoadBalancingCoordinator

# from pytest_homeassistant_custom_component.async_mock import patch
# from pytest_homeassistant_custom_component.common import (
#     MockModule,
#     MockPlatform,
#     mock_integration,
#     mock_platform,
# )
from custom_components.poollab import DOMAIN
import pytest

from homeassistant import config_entries
from homeassistant.const import ATTR_NAME, ATTR_UNIT_OF_MEASUREMENT

# from homeassistant.components import sensor
# from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
async def test_coordinator_init(hass):
    """Test the coordinator initialization."""

    # coordinator = EvLoadBalancingCoordinator(hass, CONF_ENTRY)

    # assert coordinator.name == NAME
