"""Shared base entity: one HA device per VoiceDot."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VoiceDotCoordinator


class VoiceDotEntity(CoordinatorEntity[VoiceDotCoordinator]):
    """Everything an entity of ours has in common."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VoiceDotCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.device_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_id)},
            name=self.coordinator.device_name,
            manufacturer="Waveshare",
            model="ESP32-S3-AUDIO-Board",
            sw_version=data.get("firmware"),
            configuration_url=f"http://{self.coordinator.client.host}",
            connections=set(),
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success
