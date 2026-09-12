"""The morning-briefing instruction, editable from Home Assistant.

The briefing is the sentence the device sends to the Assist pipeline when the
alarm goes off (and what the "Briefing sprechen" button reads). It lives on the
device next to the alarm, so it survives being set by voice, and is exposed here
so it can be changed without opening the web UI. An empty value turns it off.
"""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VoiceDotCoordinator
from .entity import VoiceDotEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VoiceDotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VoiceDotBriefingText(coordinator)])


class VoiceDotBriefingText(VoiceDotEntity, TextEntity):
    _attr_name = "Briefing"
    _attr_icon = "mdi:weather-sunset-up"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    # Home Assistant caps a state at 255 characters anyway; a briefing is a
    # short instruction, not an essay.
    _attr_native_max = 255

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "briefing")

    @property
    def native_value(self) -> str | None:
        return ((self.coordinator.data or {}).get("alarm") or {}).get("briefing") or ""

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.async_command(
            self.coordinator.client.set_alarm_briefing(value)
        )
