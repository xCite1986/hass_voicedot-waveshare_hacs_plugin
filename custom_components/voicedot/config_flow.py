"""Config flow: zeroconf discovery, manual entry and a host that can be changed."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_HOST, DOMAIN
from .coordinator import VoiceDotClient


async def _probe(hass, host: str) -> dict[str, Any] | None:
    """Reads /api/status to confirm this really is a reachable VoiceDot."""
    client = VoiceDotClient(hass, host)
    try:
        status = await client.status()
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return None

    # device_id arrived together with the mDNS service, so its presence also
    # tells us the firmware is new enough for this integration.
    if "device_id" not in status:
        return None
    return status


class VoiceDotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handles adding a VoiceDot."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> VoiceDotOptionsFlow:
        return VoiceDotOptionsFlow()

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Called for every _voicedot._tcp announcement."""
        props = discovery_info.properties or {}

        # Prefer the mDNS name over the IP address: it survives a DHCP change.
        # But only if Home Assistant can actually resolve it - in a container
        # without host networking .local names often do not work, and then the
        # address is the only thing that gets us through.
        hostname = (discovery_info.hostname or "").rstrip(".")
        candidates = [c for c in (hostname, discovery_info.host) if c]

        status = None
        host = None
        for candidate in candidates:
            status = await _probe(self.hass, candidate)
            if status is not None:
                host = candidate
                break

        if status is None or host is None:
            return self.async_abort(reason="cannot_connect")

        device_id = props.get("id") or status.get("device_id")
        if device_id:
            await self.async_set_unique_id(str(device_id))
            # A known device gets its host refreshed, so an entry that was set
            # up with an IP moves over to the name by itself.
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._host = host
        self._name = props.get("device") or status.get("device_name") or "VoiceDot"

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
            status = await _probe(self.hass, host)

            if status is None:
                errors["base"] = "cannot_connect"
            else:
                device_id = status.get("device_id")
                if device_id:
                    await self.async_set_unique_id(str(device_id))
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


class VoiceDotOptionsFlow(OptionsFlow):
    """Lets the host be changed later, for instance from an IP to the mDNS name."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = self.config_entry.data.get(CONF_HOST, "")

        if user_input is not None:
            host = user_input[CONF_HOST].strip()

            if host == current:
                return self.async_create_entry(data={})

            if await _probe(self.hass, host) is None:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_HOST: host},
                )
                # The reload is triggered by the update listener in __init__.
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=current): str}),
            errors=errors,
            description_placeholders={"current": current},
        )
