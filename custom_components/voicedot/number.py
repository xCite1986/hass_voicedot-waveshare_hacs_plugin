"""Volume and speaking rate as numbers."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VoiceDotCoordinator
from .entity import VoiceDotEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VoiceDotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VoiceDotVolume(coordinator), VoiceDotSpeed(coordinator)])


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
