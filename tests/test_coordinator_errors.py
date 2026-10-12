"""Regression tests for PoolLab API error messages."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.poollab import PoolLabCoordinator
from custom_components.poollab.poollab import PoolLabApi


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (
            TimeoutError(),
            "PoolLab cloud request timed out; "
            "no new measurements were fetched. Home Assistant will retry automatically.",
        ),
        (
            RuntimeError(),
            "PoolLab API request failed (RuntimeError): no error message provided. "
            "Home Assistant will retry automatically.",
        ),
        (
            ConnectionError("Connection lost"),
            "PoolLab API request failed (ConnectionError): Connection lost. "
            "Home Assistant will retry automatically.",
        ),
    ],
)
async def test_api_failure_has_useful_message(hass, error, expected_message):
    """Report the failure type even when the exception message is empty."""
    api = Mock(spec=PoolLabApi)
    api.request = AsyncMock(side_effect=error)
    coordinator = PoolLabCoordinator(hass, api)

    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_poollab()

    assert str(exc_info.value) == expected_message
    assert exc_info.value.__cause__ is error
    api.request.assert_awaited_once()


async def test_request_deadline_has_timeout_message(hass, monkeypatch):
    """An expired request deadline must use the timeout-specific message."""
    timeout = asyncio.timeout
    monkeypatch.setattr(
        "custom_components.poollab.asyncio.timeout", lambda _: timeout(0)
    )

    async def pending_request():
        await asyncio.sleep(0)

    api = Mock(spec=PoolLabApi)
    api.request = AsyncMock(side_effect=pending_request)
    coordinator = PoolLabCoordinator(hass, api)

    with pytest.raises(UpdateFailed, match="cloud request timed out;"):
        await coordinator._async_update_poollab()

    assert api.request.await_count == 1
