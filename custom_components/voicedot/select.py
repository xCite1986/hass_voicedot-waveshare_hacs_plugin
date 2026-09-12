"""Pick the wake word model and the Assist pipeline."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
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
    async_add_entities(
        [
            VoiceDotWakeWordSelect(coordinator),
            VoiceDotPipelineSelect(coordinator),
            VoiceDotRadioSelect(coordinator),
            VoiceDotAlarmSoundSelect(coordinator),
            VoiceDotTimerSoundSelect(coordinator),
        ]
    )


class VoiceDotWakeWordSelect(VoiceDotEntity, SelectEntity):
    """Lists whatever models the model partition actually holds."""

    _attr_name = "Stichwort"
    _attr_icon = "mdi:ear-hearing"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "wake_model")

    def _models(self) -> list[dict]:
        return ((self.coordinator.data or {}).get("wake_word") or {}).get("models") or []

    @property
    def options(self) -> list[str]:
        return [m.get("words") or m.get("id") for m in self._models()]

    @property
    def current_option(self) -> str | None:
        active = ((self.coordinator.data or {}).get("wake_word") or {}).get("model")
        for model in self._models():
            if model.get("id") == active:
                return model.get("words") or model.get("id")
        return None

    async def async_select_option(self, option: str) -> None:
        for model in self._models():
            if (model.get("words") or model.get("id")) == option:
                await self.coordinator.async_command(
                    self.coordinator.client.set_config(wake_model=model["id"])
                )
                return


class VoiceDotPipelineSelect(VoiceDotEntity, SelectEntity):
    """Assist pipelines as reported by Home Assistant itself."""

    _attr_name = "Assist-Pipeline"
    _attr_icon = "mdi:sitemap"
    _attr_entity_category = EntityCategory.CONFIG

    DEFAULT = "HA-Standard"

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "pipeline")

    def _pipelines(self) -> list[dict]:
        return ((self.coordinator.data or {}).get("pipelines") or {}).get("list") or []

    @property
    def options(self) -> list[str]:
        return [self.DEFAULT] + [p.get("name") or p.get("id") for p in self._pipelines()]

    @property
    def current_option(self) -> str | None:
        active = self.coordinator.config.get("ha_pipeline")
        if not active:
            return self.DEFAULT
        for pipeline in self._pipelines():
            if pipeline.get("id") == active:
                return pipeline.get("name") or pipeline.get("id")
        return self.DEFAULT

    async def async_select_option(self, option: str) -> None:
        if option == self.DEFAULT:
            await self.coordinator.async_command(self.coordinator.client.set_config(ha_pipeline=""))
            return

        for pipeline in self._pipelines():
            if (pipeline.get("name") or pipeline.get("id")) == option:
                await self.coordinator.async_command(
                    self.coordinator.client.set_config(ha_pipeline=pipeline["id"])
                )
                return


class VoiceDotRadioSelect(VoiceDotEntity, SelectEntity):
    """The station list of the device, with "Aus" as the way to stop it.

    One control rather than a switch plus a picker: turning the radio on always
    means picking a station anyway.
    """

    _attr_name = "Radio"
    _attr_icon = "mdi:radio"

    OFF = "Aus"

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "radio_station")

    def _radio(self) -> dict:
        return (self.coordinator.data or {}).get("radio") or {}

    @property
    def options(self) -> list[str]:
        return [self.OFF] + list(self._radio().get("stations") or [])

    @property
    def current_option(self) -> str | None:
        radio = self._radio()
        if not radio.get("active"):
            return self.OFF
        return radio.get("station") or self.OFF

    @property
    def extra_state_attributes(self) -> dict:
        radio = self._radio()
        return {
            "status": radio.get("status"),
            "tls": radio.get("tls"),
            "stream_rate_hz": radio.get("rate"),
            "received_kbytes": radio.get("kbytes"),
            "seconds": radio.get("seconds"),
        }

    async def async_select_option(self, option: str) -> None:
        if option == self.OFF:
            await self.coordinator.async_command(self.coordinator.client.radio_stop())
            return
        await self.coordinator.async_command(self.coordinator.client.radio_play(option))


class _VoiceDotSoundSelect(VoiceDotEntity, SelectEntity):
    """Picks a tone from the device's uploaded sound library.

    The list of files comes from /api/status, so no extra request is needed;
    "Standard" maps to an empty name, which puts the device back on its built-in
    behaviour (a spoken timer, a silent-or-briefing alarm).
    """

    _attr_entity_category = EntityCategory.CONFIG

    DEFAULT = "Standard"
    _status_key = ""  # "alarm" or "timer"

    def _sounds(self) -> list[str]:
        return list((self.coordinator.data or {}).get("sounds") or [])

    def _current_sound(self) -> str:
        node = (self.coordinator.data or {}).get(self._status_key) or {}
        return node.get("sound") or ""

    @property
    def options(self) -> list[str]:
        opts = [self.DEFAULT] + self._sounds()
        # A tone that is still selected but no longer on the device keeps its
        # slot, so the picker never rejects the device's own current value.
        current = self._current_sound()
        if current and current not in opts:
            opts.append(current)
        return opts

    @property
    def current_option(self) -> str | None:
        return self._current_sound() or self.DEFAULT

    def _command(self, name: str) -> Any:
        raise NotImplementedError

    async def async_select_option(self, option: str) -> None:
        name = "" if option == self.DEFAULT else option
        await self.coordinator.async_command(self._command(name))


class VoiceDotAlarmSoundSelect(_VoiceDotSoundSelect):
    _attr_name = "Weckton"
    _attr_icon = "mdi:alarm-note"
    _status_key = "alarm"

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "alarm_sound")

    def _command(self, name: str) -> Any:
        return self.coordinator.client.set_alarm_sound(name)


class VoiceDotTimerSoundSelect(_VoiceDotSoundSelect):
    _attr_name = "Timer-Ton"
    _attr_icon = "mdi:timer-music"
    _status_key = "timer"

    def __init__(self, coordinator: VoiceDotCoordinator) -> None:
        super().__init__(coordinator, "timer_sound")

    def _command(self, name: str) -> Any:
        return self.coordinator.client.set_timer_sound(name)
