"""Config flow: zeroconf discovery plus manual entry."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_HOST, DOMAIN
from .coordinator import VoiceDotClient


class VoiceDotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handles adding a VoiceDot."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str | None = None
        self._device_id: str | None = None

    async def _probe(self, host: str) -> dict[str, Any] | None:
        """Reads /api/status to confirm this really is a VoiceDot."""
        client = VoiceDotClient(self.hass, host)
        try:
            status = await client.status()
        except (aiohttp.ClientError, TimeoutError, ValueError):
            return None

        # device_id was added together with the mDNS service, so its presence
        # is a good marker for a firmware new enough for this integration.
        if "device_id" not in status:
            return None
        return status

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Called for every _voicedot._tcp announcement."""
        host = discovery_info.host
        props = discovery_info.properties or {}

        device_id = props.get("id")
        if device_id:
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        status = await self._probe(host)
        if status is None:
            return self.async_abort(reason="cannot_connect")

        self._host = host
        self._name = props.get("device") or status.get("device_name") or "VoiceDot"
        self._device_id = device_id or status.get("device_id")

        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Asks before adding a discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name or "VoiceDot",
                data={CONF_HOST: self._host},
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self._name or "VoiceDot", "host": self._host or ""},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual entry by host name or IP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            status = await self._probe(host)

            if status is None:
                errors["base"] = "cannot_connect"
            else:
                device_id = status.get("device_id")
                if device_id:
                    await self.async_set_unique_id(device_id)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                return self.async_create_entry(
                    title=status.get("device_name") or "VoiceDot",
                    data={CONF_HOST: host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default="voicedot.local"): str}),
            errors=errors,
        )
