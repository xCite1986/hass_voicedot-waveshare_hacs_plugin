"""Settings that are simply on or off."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VoiceDotCoordinator
from .entity import VoiceDotEntity


@dataclass(frozen=True, kw_only=True)
class VoiceDotSwitchDescription(SwitchEntityDescription):
    config_key: str
    api_key: str


SWITCHES: tuple[VoiceDotSwitchDescription, ...] = (
    VoiceDotSwitchDescription(
        key="wake_word", name="Wake-Word", icon="mdi:ear-hearing",
        config_key="wake_word", api_key="wake_word",
    ),
    VoiceDotSwitchDescription(
        key="ack", name="Ansage nach Wake-Word", icon="mdi:message-badge",
        config_key="ack_enabled", api_key="ack_enabled",
        entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotSwitchDescription(
        key="vad", name="Automatisches Satzende", icon="mdi:waveform",
        config_key="vad", api_key="vad",
        entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotSwitchDescription(
        key="follow_up", name="Rückfragen fortsetzen", icon="mdi:comment-question",
        config_key="follow_up", api_key="follow_up",
        entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotSwitchDescription(
        key="schedule", name="Tag/Nacht-Profil", icon="mdi:theme-light-dark",
        config_key="schedule_enabled", api_key="schedule_enabled",
        entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotSwitchDescription(
        key="clean_markdown", name="Markdown entfernen", icon="mdi:format-clear",
        config_key="clean_markdown", api_key="clean_markdown",
        entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotSwitchDescription(
        key="multi", name="Aushandlung mit anderen VoiceDots", icon="mdi:account-group",
        config_key="multi_enabled", api_key="multi_enabled",
        entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotSwitchDescription(
        key="auto_volume", name="Lautstärke nach Umgebungslärm", icon="mdi:volume-vibrate",
        config_key="auto_volume", api_key="auto_volume",
        entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotSwitchDescription(
        key="update_check", name="Selbst nach Updates sehen", icon="mdi:cloud-search",
        config_key="update_check", api_key="update_check",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VoiceDotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(VoiceDotSwitch(coordinator, desc) for desc in SWITCHES)


class VoiceDotSwitch(VoiceDotEntity, SwitchEntity):
    entity_description: VoiceDotSwitchDescription

    def __init__(self, coordinator: VoiceDotCoordinator, description: VoiceDotSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.config.get(self.entity_description.config_key)

    async def _write(self, value: bool) -> None:
        await self.coordinator.async_command(
            self.coordinator.client.set_config(**{self.entity_description.api_key: "1" if value else "0"})
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._write(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._write(False)
