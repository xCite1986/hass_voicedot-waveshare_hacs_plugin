"""VoiceDot Waveshare integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import ATTR_TEXT, CONF_HOST, DOMAIN, SERVICE_ANNOUNCE
from .coordinator import VoiceDotClient, VoiceDotCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.UPDATE,
]

ANNOUNCE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TEXT): cv.string,
        vol.Optional("device_id"): vol.Any(cv.string, [cv.string]),
        vol.Optional("entity_id"): cv.entity_ids,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one VoiceDot from a config entry."""
    client = VoiceDotClient(hass, entry.data[CONF_HOST])
    coordinator = VoiceDotCoordinator(hass, client, entry.title)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Changing the host in the options has to take effect straight away.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    _register_services(hass)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_ANNOUNCE)
    return unloaded


def _register_services(hass: HomeAssistant) -> None:
    """Registers voicedot.announce once, no matter how many devices exist."""
    if hass.services.has_service(DOMAIN, SERVICE_ANNOUNCE):
        return

    async def _handle_announce(call: ServiceCall) -> None:
        text = call.data[ATTR_TEXT]
        targets = _resolve_targets(hass, call)

        if not targets:
            # No target given means every known VoiceDot, which is what people
            # expect from a doorbell automation in a small house.
            targets = list(hass.data.get(DOMAIN, {}).values())

        for coordinator in targets:
            try:
                await coordinator.client.announce(text)
            except Exception as err:  # noqa: BLE001 - one bad device must not stop the rest
                _LOGGER.error("Ansage an %s fehlgeschlagen: %s", coordinator.client.host, err)

    hass.services.async_register(DOMAIN, SERVICE_ANNOUNCE, _handle_announce, ANNOUNCE_SCHEMA)


def _resolve_targets(hass: HomeAssistant, call: ServiceCall) -> list[VoiceDotCoordinator]:
    """Maps device/entity targets of a service call onto our coordinators."""
    stored: dict[str, VoiceDotCoordinator] = hass.data.get(DOMAIN, {})
    if not stored:
        return []

    wanted_entries: set[str] = set()

    device_ids = call.data.get("device_id") or []
    if isinstance(device_ids, str):
        device_ids = [device_ids]

    device_reg = dr.async_get(hass)
    for device_id in device_ids:
        device = device_reg.async_get(device_id)
        if device:
            wanted_entries.update(device.config_entries)

    for entity_id in call.data.get("entity_id", []):
        entity = hass.states.get(entity_id)
        if entity is None:
            continue
        entry = hass.data["entity_registry"].async_get(entity_id) if "entity_registry" in hass.data else None
        if entry and entry.config_entry_id:
            wanted_entries.add(entry.config_entry_id)

    return [coord for entry_id, coord in stored.items() if entry_id in wanted_entries]
