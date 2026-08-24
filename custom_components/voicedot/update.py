"""Firmware updates straight from the GitHub releases of the project."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RELEASES_URL
from .coordinator import VoiceDotCoordinator
from .entity import VoiceDotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VoiceDotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VoiceDotUpdate(coordinator)])


class VoiceDotUpdate(VoiceDotEntity, UpdateEntity):
    """Installed against available firmware, with an install button.

    The versions come from the device's own cache, never from GitHub directly:
    the unauthenticated API allows 60 requests per hour and address, and this
    coordinator polls every ten seconds.
    """

    _attr_name = "Firmware"
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_title = "VoiceDot"

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "firmware_update")

    @property
    def _update(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("update") or {}

    @property
    def installed_version(self) -> str | None:
        return self._update.get("installed") or None

    @property
    def latest_version(self) -> str | None:
        latest = self._update.get("latest")
        if not latest:
            # Without a known release, saying "no update" is the honest answer -
            # returning None would show the entity as unknown instead.
            return self.installed_version
        return latest.lstrip("vV")

    @property
    def release_url(self) -> str | None:
        latest = self._update.get("latest")
        return f"{RELEASES_URL}/tag/{latest}" if latest else RELEASES_URL

    @property
    def in_progress(self) -> bool:
        return bool(self._update.get("in_progress"))

    @property
    def update_percentage(self) -> int | None:
        percent = self._update.get("progress", -1)
        return percent if isinstance(percent, int) and percent >= 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "status": self._update.get("status"),
            "checked_seconds_ago": self._update.get("age_s"),
            "releases": [r.get("tag") for r in self._update.get("releases", [])],
        }

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        # The device knows the releases by their tag, which carries the "v".
        tag = self._update.get("latest")
        if version:
            tag = version if version.startswith("v") else f"v{version}"

        # Fresh list first: the cache may be twelve hours old, and installing a
        # version whose download URL has since changed would only fail.
        await self.coordinator.client.update_check()
        await self.coordinator.client.update_install(tag)
        await self.coordinator.async_request_refresh()
