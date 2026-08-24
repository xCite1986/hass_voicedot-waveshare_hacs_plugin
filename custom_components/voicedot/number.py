"""Volume and speaking rate as numbers."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VoiceDotCoordinator
from .entity import VoiceDotEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VoiceDotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            VoiceDotVolume(coordinator),
            VoiceDotSpeed(coordinator),
            VoiceDotMultiWindow(coordinator),
            VoiceDotAutoVolumeMax(coordinator),
        ]
    )


class VoiceDotVolume(VoiceDotEntity, NumberEntity):
    _attr_name = "Lautstärke"
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "volume")

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("volume")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_command(self.coordinator.client.set_volume(int(value)))


class VoiceDotSpeed(VoiceDotEntity, NumberEntity):
    _attr_name = "Sprechtempo"
    _attr_icon = "mdi:speedometer"
    _attr_native_min_value = 75
    _attr_native_max_value = 135
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "tts_speed")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.config.get("tts_speed")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_command(
            self.coordinator.client.set_runtime(tts_speed=int(value))
        )


class VoiceDotMultiWindow(VoiceDotEntity, NumberEntity):
    """How long to wait for a louder VoiceDot before answering."""

    _attr_name = "Aushandlungsfenster"
    _attr_icon = "mdi:timer-sand"
    _attr_native_min_value = 80
    _attr_native_max_value = 600
    _attr_native_step = 20
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "multi_window_ms")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.config.get("multi_window_ms")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_command(
            self.coordinator.client.set_config(multi_window_ms=int(value))
        )


class VoiceDotAutoVolumeMax(VoiceDotEntity, NumberEntity):
    """Ceiling for the boost the room noise is allowed to add."""

    _attr_name = "Maximale Anhebung"
    _attr_icon = "mdi:volume-plus"
    _attr_native_min_value = 0
    _attr_native_max_value = 18
    _attr_native_step = 1
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "auto_volume_max_db")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.config.get("auto_volume_max_db")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_command(
            self.coordinator.client.set_config(auto_volume_max_db=int(value))
        )
