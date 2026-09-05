"""VoiceDot Waveshare integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import (
    ATTR_DAILY,
    ATTR_DURATION,
    ATTR_TEXT,
    ATTR_TIME,
    CONF_HOST,
    DOMAIN,
    SERVICE_ANNOUNCE,
    SERVICE_CLEAR_ALARM,
    SERVICE_CLEAR_TIMER,
    SERVICE_SET_ALARM,
    SERVICE_SPEAK_BRIEFING,
    SERVICE_START_TIMER,
    SERVICES,
)
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

TARGET_SCHEMA = {
    vol.Optional("device_id"): vol.Any(cv.string, [cv.string]),
    vol.Optional("entity_id"): cv.entity_ids,
}

ANNOUNCE_SCHEMA = vol.Schema({vol.Required(ATTR_TEXT): cv.string, **TARGET_SCHEMA})

SET_ALARM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TIME): cv.time,
        vol.Optional(ATTR_DAILY): cv.boolean,
        **TARGET_SCHEMA,
    }
)

START_TIMER_SCHEMA = vol.Schema(
    {vol.Required(ATTR_DURATION): cv.time_period, **TARGET_SCHEMA}
)

BRIEFING_SCHEMA = vol.Schema({vol.Optional(ATTR_TEXT): cv.string, **TARGET_SCHEMA})

PLAIN_SCHEMA = vol.Schema(TARGET_SCHEMA)


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
            for service in SERVICES:
                hass.services.async_remove(DOMAIN, service)
    return unloaded


def _register_services(hass: HomeAssistant) -> None:
    """Registers the services once, no matter how many devices exist."""
    if hass.services.has_service(DOMAIN, SERVICE_ANNOUNCE):
        return

    async def _run(call: ServiceCall, what: str, action) -> None:
        targets = _resolve_targets(hass, call)

        if not targets:
            # No target given means every known VoiceDot, which is what people
            # expect from a doorbell automation in a small house.
            targets = list(hass.data.get(DOMAIN, {}).values())

        for coordinator in targets:
            try:
                await action(coordinator)
                await coordinator.async_request_refresh()
            except Exception as err:  # noqa: BLE001 - one bad device must not stop the rest
                _LOGGER.error("%s an %s fehlgeschlagen: %s", what, coordinator.client.host, err)

    async def _handle_announce(call: ServiceCall) -> None:
        text = call.data[ATTR_TEXT]
        await _run(call, "Ansage", lambda c: c.client.announce(text))

    async def _handle_set_alarm(call: ServiceCall) -> None:
        # cv.time gives a datetime.time; the firmware wants plain HH:MM.
        wanted = call.data[ATTR_TIME].strftime("%H:%M")
        daily = call.data.get(ATTR_DAILY)
        await _run(call, "Wecker stellen", lambda c: c.client.set_alarm(wanted, daily))

    async def _handle_clear_alarm(call: ServiceCall) -> None:
        await _run(call, "Wecker löschen", lambda c: c.client.clear_alarm())

    async def _handle_start_timer(call: ServiceCall) -> None:
        seconds = int(call.data[ATTR_DURATION].total_seconds())
        if seconds < 5 or seconds > 12 * 3600:
            # The firmware would refuse it too, but a service error says so in
            # the interface instead of only in the log.
            raise ServiceValidationError(
                "Der Timer läuft zwischen 5 Sekunden und 12 Stunden."
            )
        await _run(call, "Timer stellen", lambda c: c.client.start_timer(seconds))

    async def _handle_clear_timer(call: ServiceCall) -> None:
        await _run(call, "Timer löschen", lambda c: c.client.clear_timer())

    async def _handle_speak_briefing(call: ServiceCall) -> None:
        text = call.data.get(ATTR_TEXT)
        await _run(call, "Briefing", lambda c: c.client.speak_briefing(text))

    for service, handler, schema in (
        (SERVICE_ANNOUNCE, _handle_announce, ANNOUNCE_SCHEMA),
        (SERVICE_SET_ALARM, _handle_set_alarm, SET_ALARM_SCHEMA),
        (SERVICE_CLEAR_ALARM, _handle_clear_alarm, PLAIN_SCHEMA),
        (SERVICE_START_TIMER, _handle_start_timer, START_TIMER_SCHEMA),
        (SERVICE_CLEAR_TIMER, _handle_clear_timer, PLAIN_SCHEMA),
        (SERVICE_SPEAK_BRIEFING, _handle_speak_briefing, BRIEFING_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, service, handler, schema)


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
