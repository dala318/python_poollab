"""config_flow tests."""

from unittest import mock

from custom_components.poollab import config_flow
import pytest

# from pytest_homeassistant_custom_component.async_mock import patch
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import ATTR_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.helpers import selector


# @pytest.mark.asyncio
# async def test_flow_init(hass):
#     """Test the initial flow."""
#     result = await hass.config_entries.flow.async_init(
#         config_flow.DOMAIN, context={"source": "user"}
#     )

#     expected = {
#         "data_schema": SCHEMA_COPY,
#         # "data_schema": config_flow.DATA_SCHEMA,
#         "description_placeholders": None,
#         "errors": {},
#         "flow_id": mock.ANY,
#         "handler": "poollab",
#         "step_id": "user",
#         "type": "form",
#     }
#     assert expected == result
