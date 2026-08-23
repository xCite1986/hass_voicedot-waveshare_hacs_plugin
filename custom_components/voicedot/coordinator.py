"""Polling coordinator and the thin HTTP client for a VoiceDot."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_ACK_BUILD,
    API_ACK_TEST,
    API_ANNOUNCE,
    API_CONFIG,
    API_REBOOT,
    API_RUNTIME,
    API_SPEAKER_TEST,
    API_STATUS,
    API_VOLUME,
    API_WAKE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class VoiceDotClient:
    """Talks to one device.

    The firmware answers plain JSON on /api/status and /api/config and takes
    form encoded values everywhere else, so there is very little to do here.
    """

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        self._session = async_get_clientsession(hass)
        self.host = host

    @property
    def base(self) -> str:
        return f"http://{self.host}"

    async def _get_json(self, path: str) -> dict[str, Any]:
        async with async_timeout.timeout(10):
            resp = await self._session.get(f"{self.base}{path}")
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def _post(self, path: str, data: dict[str, Any] | None = None) -> str:
        async with async_timeout.timeout(15):
            resp = await self._session.post(f"{self.base}{path}", data=data)
            resp.raise_for_status()
            return await resp.text()

    async def status(self) -> dict[str, Any]:
        return await self._get_json(API_STATUS)

    async def config(self) -> dict[str, Any]:
        return await self._get_json(API_CONFIG)

    async def announce(self, text: str) -> str:
        return await self._post(API_ANNOUNCE, {"text": text})

    async def set_volume(self, percent: int) -> str:
        return await self._post(API_VOLUME, {"percent": int(percent)})

    async def set_runtime(self, **values: Any) -> str:
        return await self._post(API_RUNTIME, {k: str(v) for k, v in values.items()})

    async def set_config(self, **values: Any) -> str:
        return await self._post(API_CONFIG, {k: str(v) for k, v in values.items()})

    async def ack_test(self) -> str:
        return await self._post(API_ACK_TEST)

    async def ack_build(self) -> str:
        return await self._post(API_ACK_BUILD)

    async def start_wake(self) -> str:
        return await self._post(API_WAKE)

    async def speaker_test(self) -> str:
        return await self._post(API_SPEAKER_TEST)

    async def reboot(self) -> str:
        return await self._post(API_REBOOT)


class VoiceDotCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Keeps status and config in one place for all platforms."""

    def __init__(self, hass: HomeAssistant, client: VoiceDotClient, name: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {name}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.config: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.client.status()
            # The config changes far less often, but it is small and keeping
            # both in step avoids a second refresh path for the settings.
            self.config = await self.client.config()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"VoiceDot {self.client.host} nicht erreichbar: {err}") from err

        return status

    @property
    def device_id(self) -> str:
        return str(self.data.get("device_id") or self.client.host)

    @property
    def device_name(self) -> str:
        return str(self.data.get("device_name") or "VoiceDot")

    async def async_command(self, coro) -> None:
        """Runs a command and refreshes, so the UI does not lag behind."""
        await coro
        await self.async_request_refresh()
