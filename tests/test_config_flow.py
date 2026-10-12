"""Tests for PoolLab configuration forms."""

import json
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import CONF_API_KEY, CONF_SSL, CONF_URL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.poollab import config_flow
from custom_components.poollab.const import DOMAIN
from custom_components.poollab.poollab import API_ENDPOINT


@pytest.mark.parametrize("source", [SOURCE_USER, SOURCE_RECONFIGURE])
async def test_config_form_api_key_link(hass, source):
    """Both forms must supply a working URL for their translated description."""
    context = {"source": source}
    if source == SOURCE_RECONFIGURE:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="PoolLab",
            unique_id="test-api-key",
            version=config_flow.PoolLabConfigFlow.VERSION,
            minor_version=config_flow.PoolLabConfigFlow.MINOR_VERSION,
            data={
                CONF_API_KEY: "test-api-key",
                CONF_URL: API_ENDPOINT,
                CONF_SSL: True,
            },
        )
        entry.add_to_hass(hass)
        context["entry_id"] = entry.entry_id

    result = await hass.config_entries.flow.async_init(DOMAIN, context=context)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == source
    assert result["errors"] == {}

    translations = json.loads(
        (Path(config_flow.__file__).parent / "translations" / "en.json").read_text()
    )
    description = translations["config"]["step"][source]["description"]
    assert "https://" not in description
    rendered_description = description.format(**result["description_placeholders"])
    assert "https://labcom.cloud/pages/user-setting" in rendered_description
    hass.config_entries.flow.async_abort(result["flow_id"])
