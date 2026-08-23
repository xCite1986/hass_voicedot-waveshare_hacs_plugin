"""One-shot actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VoiceDotCoordinator
from .entity import VoiceDotEntity


@dataclass(frozen=True, kw_only=True)
class VoiceDotButtonDescription(ButtonEntityDescription):
    action: Callable[[VoiceDotCoordinator], object]


BUTTONS: tuple[VoiceDotButtonDescription, ...] = (
    VoiceDotButtonDescription(
        key="wake", name="Assist starten", icon="mdi:microphone",
        action=lambda c: c.client.start_wake(),
    ),
    VoiceDotButtonDescription(
        key="ack_test", name="Ansage anhören", icon="mdi:play-circle",
        action=lambda c: c.client.ack_test(), entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotButtonDescription(
        key="ack_build", name="Ansagen erzeugen", icon="mdi:refresh",
        action=lambda c: c.client.ack_build(), entity_category=EntityCategory.CONFIG,
    ),
    VoiceDotButtonDescription(
        key="speaker_test", name="Lautsprecher testen", icon="mdi:speaker",
        action=lambda c: c.client.speaker_test(), entity_category=EntityCategory.DIAGNOSTIC,
    ),
    VoiceDotButtonDescription(
        key="reboot", name="Neu starten", icon="mdi:restart",
        action=lambda c: c.client.reboot(), entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VoiceDotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(VoiceDotButton(coordinator, desc) for desc in BUTTONS)


class VoiceDotButton(VoiceDotEntity, ButtonEntity):
    entity_description: VoiceDotButtonDescription

    def __init__(self, coordinator: VoiceDotCoordinator, description: VoiceDotButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_command(self.entity_description.action(self.coordinator))
