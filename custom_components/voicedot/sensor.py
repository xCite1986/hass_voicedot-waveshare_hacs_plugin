"""Sensors: what the device is doing, plus the numbers worth trending."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    SIGNAL_STRENGTH_DECIBELS,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import VoiceDotCoordinator
from .entity import VoiceDotEntity


def _dig(data: dict[str, Any], *path: str) -> Any:
    node: Any = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _ends_in(seconds: Any) -> datetime | None:
    """Turns a remaining number of seconds into the moment it runs out."""
    try:
        secs = int(seconds)
    except (TypeError, ValueError):
        return None
    if secs < 0:
        return None
    return dt_util.utcnow() + timedelta(seconds=secs)


@dataclass(frozen=True, kw_only=True)
class VoiceDotSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]
    attributes: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


SENSORS: tuple[VoiceDotSensorDescription, ...] = (
    VoiceDotSensorDescription(
        key="alarm",
        name="Wecker",
        icon="mdi:alarm",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda d: (
            _ends_in(_dig(d, "alarm", "seconds_until"))
            if _dig(d, "alarm", "set")
            else None
        ),
        attributes=lambda d: {
            "zeit": _dig(d, "alarm", "time"),
            "taeglich": _dig(d, "alarm", "daily"),
            "klingelt": _dig(d, "alarm", "ringing"),
            "weckton": _dig(d, "alarm", "sound") or None,
            "briefing": _dig(d, "alarm", "briefing") or None,
        },
    ),
    VoiceDotSensorDescription(
        key="timer",
        name="Timer",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda d: (
            _ends_in(_dig(d, "timer", "remaining_s"))
            if _dig(d, "timer", "active")
            else None
        ),
        attributes=lambda d: {
            "restsekunden": _dig(d, "timer", "remaining_s"),
            "gesamtsekunden": _dig(d, "timer", "total_s"),
            "ton": _dig(d, "timer", "sound") or None,
        },
    ),
    VoiceDotSensorDescription(
        key="groups",
        name="Gruppen",
        icon="mdi:lightbulb-group",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: len(d.get("groups") or []),
        attributes=lambda d: {"gruppen": d.get("groups") or []},
    ),
    VoiceDotSensorDescription(
        key="radio",
        name="Radio",
        icon="mdi:radio",
        value=lambda d: (
            _dig(d, "radio", "station") if _dig(d, "radio", "active") else "aus"
        ),
    ),
    VoiceDotSensorDescription(
        key="volume_boost",
        name="Lautstärke-Anhebung",
        icon="mdi:volume-plus",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: _dig(d, "auto_volume", "boost_db"),
    ),
    VoiceDotSensorDescription(
        key="multi_peers",
        name="Nachbar-VoiceDots",
        icon="mdi:account-group",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: len(_dig(d, "multi", "peers") or []),
    ),
    VoiceDotSensorDescription(
        key="led_phase",
        name="Leuchtring",
        icon="mdi:led-on",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: _dig(d, "hardware", "led_phase"),
    ),
    VoiceDotSensorDescription(
        key="state",
        name="Status",
        icon="mdi:account-voice",
        value=lambda d: _voice_state(d),
    ),
    VoiceDotSensorDescription(
        key="transcript",
        name="Letzte Frage",
        icon="mdi:text-account",
        value=lambda d: (_dig(d, "assist", "transcript") or None),
    ),
    VoiceDotSensorDescription(
        key="answer",
        name="Letzte Antwort",
        icon="mdi:message-text",
        value=lambda d: (_dig(d, "assist", "assistant_text") or None),
    ),
    VoiceDotSensorDescription(
        key="wake_word",
        name="Stichwort",
        icon="mdi:ear-hearing",
        value=lambda d: (_dig(d, "wake_word", "word") or None),
    ),
    VoiceDotSensorDescription(
        key="detections",
        name="Erkennungen",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value=lambda d: _dig(d, "wake_word", "detections"),
    ),
    VoiceDotSensorDescription(
        key="room_noise",
        name="Rauschboden",
        native_unit_of_measurement="dBFS",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:volume-vibrate",
        value=lambda d: _dig(d, "audio", "room_noise_db"),
    ),
    VoiceDotSensorDescription(
        key="profile",
        name="Profil",
        icon="mdi:theme-light-dark",
        value=lambda d: _dig(d, "schedule", "period"),
    ),
    VoiceDotSensorDescription(
        key="uptime",
        name="Laufzeit",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("uptime"),
    ),
    VoiceDotSensorDescription(
        key="free_heap",
        name="Freier Heap",
        native_unit_of_measurement="B",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("free_heap"),
    ),
    VoiceDotSensorDescription(
        key="min_free_heap",
        name="Heap-Minimum",
        native_unit_of_measurement="B",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("min_free_heap"),
    ),
    VoiceDotSensorDescription(
        key="rssi",
        name="WLAN-Signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("rssi"),
    ),
)


def _voice_state(data: dict[str, Any]) -> str:
    """Mirrors the firmware's own view of what it is doing."""
    assist = data.get("assist") or {}
    if assist.get("recording"):
        return "listening"
    if assist.get("sending"):
        return "thinking"
    if (data.get("audio") or {}).get("speaker_test"):
        return "speaker_test"
    if assist.get("state") == "tts":
        return "speaking"
    if assist.get("state") == "error":
        return "error"
    return "idle"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VoiceDotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(VoiceDotSensor(coordinator, desc) for desc in SENSORS)


class VoiceDotSensor(VoiceDotEntity, SensorEntity):
    """One value out of /api/status."""

    entity_description: VoiceDotSensorDescription

    def __init__(self, coordinator: VoiceDotCoordinator, description: VoiceDotSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._steady_at: datetime | None = None

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        value = self.entity_description.value(data)

        if self.entity_description.device_class is SensorDeviceClass.TIMESTAMP:
            return self._steady(value)

        # Long answers would be rejected: HA caps a state at 255 characters.
        if isinstance(value, str) and len(value) > 250:
            return value[:247] + "..."
        return value

    def _steady(self, value: datetime | None) -> datetime | None:
        """Keeps a countdown from rewriting its own state on every poll.

        The device reports the seconds that are left, so the moment it runs out
        is recomputed every ten seconds and lands a second or two beside the
        last one. Only a real change is passed on; a running timer keeps the
        end it was given.
        """
        if value is None:
            self._steady_at = None
            return None
        if self._steady_at is not None:
            if abs((value - self._steady_at).total_seconds()) <= 5:
                return self._steady_at
        self._steady_at = value
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}

        if self.entity_description.attributes is not None:
            attrs = self.entity_description.attributes(data)
            return {k: v for k, v in (attrs or {}).items() if v is not None} or None

        # The full text lives in an attribute, which has no 255 char limit.
        if self.entity_description.key not in ("transcript", "answer"):
            return None
        full = self.entity_description.value(data)
        return {"full_text": full} if full else None
