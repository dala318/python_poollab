"""Regression tests for config-flow reloads (issue #68)."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_RECONFIGURE
from homeassistant.const import CONF_API_KEY, CONF_SSL, CONF_URL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.poollab.config_flow import PoolLabConfigFlow
from custom_components.poollab.const import DOMAIN
from custom_components.poollab.poollab import API_ENDPOINT


@pytest.mark.parametrize("source", [SOURCE_REAUTH, SOURCE_RECONFIGURE])
@pytest.mark.parametrize("change_credentials", [True, False])
async def test_config_flow_reloads_once(hass, source, change_credentials, caplog):
    """Reauth and reconfigure must reload once, even for unchanged credentials."""
    original_data = {
        CONF_API_KEY: "test-api-key",
        CONF_URL: API_ENDPOINT,
        CONF_SSL: True,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PoolLab",
        unique_id="test-api-key",
        version=PoolLabConfigFlow.VERSION,
        minor_version=PoolLabConfigFlow.MINOR_VERSION,
        data=original_data,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.poollab.PoolLabCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    context = {"source": source, "entry_id": entry.entry_id}
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context=context, data=original_data if source == SOURCE_REAUTH else None
    )
    assert result["type"] == FlowResultType.FORM

    user_input = {
        **original_data,
        CONF_API_KEY: "updated-api-key" if change_credentials else "test-api-key",
    }
    with (
        patch(
            "custom_components.poollab.config_flow.PoolLabApi.test",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch.object(
            hass.config_entries,
            "async_reload",
            new_callable=AsyncMock,
            return_value=True,
        ) as reload_entry,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    expected_reason = (
        "reauth_successful" if source == SOURCE_REAUTH else "reconfigure_successful"
    )
    assert result["reason"] == expected_reason
    assert entry.data == user_input
    reload_entry.assert_awaited_once_with(entry.entry_id)
    assert "has an update listener and should use it" not in caplog.text
