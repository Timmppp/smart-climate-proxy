"""Runtime manager for one Smart Climate Proxy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import math
from typing import Any

from homeassistant.components.climate.const import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import *

_LOGGER = logging.getLogger(__name__)
INVALID_STATES = {"unknown", "unavailable", "none", "null", None}


@dataclass
class CorrectionResult:
    changed: bool
    reason: str


class SmartClimateProxyManager:
    """Manage state, learning and service calls for one proxy."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store: Store[dict[str, Any]]) -> None:
        self.hass = hass
        self.entry = entry
        self.store = store
        self._remove_callbacks: list = []
        self.entities: list[Any] = []
        self.climate_entity: Any = None

        self.learning: dict[str, dict[str, float]] = {"heat": {}, "cool": {}}
        self.runtime_options: dict[str, Any] = {}
        self.target_temperature: float = float(self.option(CONF_TARGET_TEMPERATURE))

        now = dt_util.utcnow()
        self.mode_since: datetime = now
        self.device_setpoint_since: datetime = now
        self.target_since: datetime = now
        self.in_range_since: datetime | None = None
        self.outside_range_since: datetime | None = None
        self.last_correction_time: datetime | None = None
        self.last_valid_room_temperature: float | None = None
        self.last_valid_room_temperature_time: datetime | None = None
        self.manual_override_until: datetime | None = None
        self.expected_device_setpoint: float | None = None
        self.expected_device_setpoint_until: datetime | None = None
        self.last_mode: str | None = None
        self.last_device_setpoint: float | None = None
        self.last_target_temperature: float | None = None
        self.last_correction_reason: str = "not_evaluated_yet"
        self.last_learning_update: str | None = None
        self.fallback_active: bool = False
        self.fallback_reason: str | None = None
        self.last_evaluation_reason: str | None = None
        self.last_evaluation_time: datetime | None = None

    def config(self) -> dict[str, Any]:
        return {**DEFAULTS, **self.entry.data, **self.entry.options, **self.runtime_options}

    def option(self, key: str) -> Any:
        return self.config().get(key, DEFAULTS.get(key))

    async def async_set_option(self, key: str, value: Any) -> None:
        if key in NUMERIC_OPTIONS:
            value = float(value)
            if key in {CONF_CORRECTION_INTERVAL_MINUTES, CONF_MANUAL_OVERRIDE_MINUTES}:
                value = int(value)
        if key in SWITCH_OPTIONS:
            value = bool(value)
        if key == CONF_TARGET_TEMPERATURE:
            await self.async_set_target_temperature(float(value))
            return
        self.runtime_options[key] = value
        await self.async_save()
        await self.async_evaluate(f"option_{key}_changed")
        self.async_write_state()

    @property
    def name(self) -> str:
        return self.config().get(CONF_NAME, self.entry.title)

    @property
    def target_climate(self) -> str:
        return self.config()[CONF_TARGET_CLIMATE]

    @property
    def temperature_sensor(self) -> str:
        return self.config()[CONF_TEMPERATURE_SENSOR]

    @property
    def quiet_switch(self) -> str | None:
        value = self.config().get(CONF_QUIET_SWITCH)
        return value or None

    @property
    def apply_to_device(self) -> bool:
        return bool(self.option(CONF_APPLY_TO_DEVICE))

    @property
    def learning_enabled(self) -> bool:
        return bool(self.option(CONF_LEARNING_ENABLED))

    @property
    def manual_override_enabled(self) -> bool:
        return bool(self.option(CONF_MANUAL_OVERRIDE_ENABLED))

    async def async_load(self) -> None:
        data = await self.store.async_load() or {}
        self.learning = data.get("learning", {"heat": {}, "cool": {}})
        self.runtime_options = data.get("runtime_options", {})
        self.target_temperature = float(data.get("target_temperature", self.option(CONF_TARGET_TEMPERATURE)))

    async def async_save(self) -> None:
        await self.store.async_save(
            {
                "learning": self.learning,
                "runtime_options": self.runtime_options,
                "target_temperature": self.target_temperature,
            }
        )

    async def async_unload(self) -> None:
        for remove in self._remove_callbacks:
            remove()
        self._remove_callbacks.clear()
        await self.async_save()

    async def async_start(self) -> None:
        tracked = [self.target_climate, self.temperature_sensor]
        if self.quiet_switch:
            tracked.append(self.quiet_switch)
        self._remove_callbacks.append(async_track_state_change_event(self.hass, tracked, self._handle_state_change))
        self._remove_callbacks.append(async_track_time_interval(self.hass, self._handle_periodic, timedelta(minutes=5)))
        await self.async_evaluate("startup")

    @callback
    def _handle_state_change(self, event) -> None:
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        now = dt_util.utcnow()
        if new and new.entity_id == self.target_climate:
            self._track_device_changes(old, new, now)
        self.hass.async_create_task(self.async_evaluate("state_change"))

    @callback
    def _handle_periodic(self, now) -> None:
        self.hass.async_create_task(self.async_evaluate("periodic"))

    def _track_device_changes(self, old, new, now: datetime) -> None:
        mode = new.state
        setpoint = self.device_setpoint

        if mode != self.last_mode:
            self.mode_since = now
            self.last_mode = mode

        if setpoint != self.last_device_setpoint:
            self.device_setpoint_since = now
            if self._is_unexpected_device_change(setpoint, now):
                self.manual_override_until = now + timedelta(minutes=int(self.option(CONF_MANUAL_OVERRIDE_MINUTES)))
                _LOGGER.info("Manual override detected for %s until %s", self.name, self.manual_override_until)
            self.last_device_setpoint = setpoint

    def _is_unexpected_device_change(self, setpoint: float | None, now: datetime) -> bool:
        if not self.apply_to_device or not self.manual_override_enabled or setpoint is None:
            return False
        if self.expected_device_setpoint is None or self.expected_device_setpoint_until is None:
            return True
        if now <= self.expected_device_setpoint_until and math.isclose(setpoint, self.expected_device_setpoint, abs_tol=0.05):
            return False
        return True

    @property
    def target_state(self):
        return self.hass.states.get(self.target_climate)

    @property
    def sensor_state(self):
        return self.hass.states.get(self.temperature_sensor)

    @property
    def room_temperature(self) -> float | None:
        state = self.sensor_state
        if state is None or state.state in INVALID_STATES:
            return None
        try:
            value = float(str(state.state).replace(",", "."))
        except (TypeError, ValueError):
            return None
        self.last_valid_room_temperature = value
        self.last_valid_room_temperature_time = dt_util.utcnow()
        return value

    @property
    def device_setpoint(self) -> float | None:
        state = self.target_state
        if state is None:
            return None
        value = state.attributes.get("temperature")
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    @property
    def device_mode(self) -> str | None:
        state = self.target_state
        if state is None or state.state in INVALID_STATES:
            return None
        return str(state.state)

    @property
    def lower_limit(self) -> float:
        return self.target_temperature - float(self.option(CONF_LOWER_TOLERANCE))

    @property
    def upper_limit(self) -> float:
        return self.target_temperature + float(self.option(CONF_UPPER_TOLERANCE))

    @property
    def manual_override_active(self) -> bool:
        return self.manual_override_until is not None and dt_util.utcnow() < self.manual_override_until

    async def async_set_target_temperature(self, temperature: float) -> None:
        if not math.isclose(float(temperature), self.target_temperature, abs_tol=0.05):
            self.target_temperature = float(temperature)
            self.target_since = dt_util.utcnow()
            await self.async_save()
        await self.async_evaluate("target_temperature_changed")
        self.async_write_state()

    async def async_reset_learning(self) -> None:
        self.learning = {"heat": {}, "cool": {}}
        self.last_learning_update = "reset"
        await self.async_save()
        self.async_write_state()

    def async_write_state(self) -> None:
        for entity in self.entities:
            entity.async_write_ha_state()

    async def async_evaluate(self, reason: str) -> None:
        now = dt_util.utcnow()
        self.last_evaluation_reason = reason
        self.last_evaluation_time = now
        room = self.room_temperature
        mode = self.device_mode
        setpoint = self.device_setpoint

        if self.last_target_temperature is None or not math.isclose(self.target_temperature, self.last_target_temperature, abs_tol=0.05):
            self.target_since = now
            self.last_target_temperature = self.target_temperature

        if setpoint is not None and setpoint != self.last_device_setpoint:
            self.device_setpoint_since = now
            self.last_device_setpoint = setpoint

        if mode != self.last_mode:
            self.mode_since = now
            self.last_mode = mode

        if room is None:
            self.fallback_active = True
            self.fallback_reason = "external_sensor_unavailable"
            self.last_correction_reason = "sensor_unavailable_no_correction"
            self.async_write_state()
            return

        self.fallback_active = False
        self.fallback_reason = None

        if self.lower_limit <= room <= self.upper_limit:
            if self.in_range_since is None:
                self.in_range_since = now
            self.outside_range_since = None
        else:
            self.in_range_since = None
            if self.outside_range_since is None:
                self.outside_range_since = now

        await self._maybe_learn(now, room, mode, setpoint)

        if not self.apply_to_device:
            self.last_correction_reason = "dry_run"
            self.async_write_state()
            return

        result = await self._maybe_correct(now, room, mode, setpoint)
        self.last_correction_reason = result.reason
        self.async_write_state()

    async def _maybe_learn(self, now: datetime, room: float, mode: str | None, setpoint: float | None) -> None:
        if not self.learning_enabled or self.manual_override_active:
            return
        if mode not in ("heat", "cool") or setpoint is None:
            return
        if not (self.lower_limit <= room <= self.upper_limit):
            return

        required = timedelta(hours=float(self.option(CONF_LEARNING_STABLE_HOURS)))
        if self.in_range_since is None or now - self.in_range_since < required:
            return
        if now - self.mode_since < required or now - self.device_setpoint_since < required or now - self.target_since < required:
            return

        bucket = self.learning_bucket(self.target_temperature)
        old_value = self.learning.get(mode, {}).get(bucket)
        rounded_setpoint = self.round_to_device_step(setpoint)
        if old_value is None or not math.isclose(float(old_value), rounded_setpoint, abs_tol=0.05):
            self.learning.setdefault(mode, {})[bucket] = rounded_setpoint
            self.last_learning_update = f"{mode} {bucket} -> {rounded_setpoint}"
            await self.async_save()

    async def _maybe_correct(self, now: datetime, room: float, mode: str | None, setpoint: float | None) -> CorrectionResult:
        if self.manual_override_active:
            return CorrectionResult(False, "manual_override_active")
        if mode not in ("heat", "cool"):
            return CorrectionResult(False, "unsupported_hvac_mode")
        if setpoint is None:
            return CorrectionResult(False, "device_setpoint_unknown")
        if self.lower_limit <= room <= self.upper_limit:
            return CorrectionResult(False, "inside_tolerance")

        threshold = timedelta(minutes=int(self.option(CONF_CORRECTION_INTERVAL_MINUTES)))
        if self.last_correction_time and now - self.last_correction_time < threshold:
            return CorrectionResult(False, "minimum_correction_interval")
        if self.outside_range_since is None or now - self.outside_range_since < threshold:
            return CorrectionResult(False, "outside_tolerance_waiting")

        new_setpoint = self.calculate_corrected_setpoint(room, mode, setpoint)
        if math.isclose(new_setpoint, setpoint, abs_tol=0.05):
            return CorrectionResult(False, "calculated_setpoint_unchanged")

        await self.async_set_device_temperature(new_setpoint)
        self.last_correction_time = now
        self.device_setpoint_since = now
        return CorrectionResult(True, f"corrected_{setpoint}_to_{new_setpoint}")

    def calculate_corrected_setpoint(self, room: float, mode: str, current_setpoint: float) -> float:
        if room < self.lower_limit:
            error = self.lower_limit - room
            direction = 1
        elif room > self.upper_limit:
            error = room - self.upper_limit
            direction = -1
        else:
            return current_setpoint

        adaptive_units = math.floor(error)
        if adaptive_units < 1:
            adaptive_units = 1
        step = float(self.option(CONF_SETPOINT_STEP)) * adaptive_units
        new_value = current_setpoint + (direction * step)
        return self.apply_limits(mode, self.round_to_device_step(new_value))

    def apply_limits(self, mode: str, value: float) -> float:
        if not self.option(CONF_USE_CUSTOM_LIMITS):
            return value
        if mode == "heat":
            return min(max(value, float(self.option(CONF_HEAT_MIN_SETPOINT))), float(self.option(CONF_HEAT_MAX_SETPOINT)))
        if mode == "cool":
            return min(max(value, float(self.option(CONF_COOL_MIN_SETPOINT))), float(self.option(CONF_COOL_MAX_SETPOINT)))
        return value

    def round_to_device_step(self, value: float) -> float:
        step = float(self.option(CONF_SETPOINT_STEP)) or 1.0
        return round(round(value / step) * step, 2)

    def learning_bucket(self, value: float) -> str:
        resolution = float(self.option(CONF_LEARNING_RESOLUTION)) or 1.0
        bucket = math.floor((float(value) / resolution) + 0.5) * resolution
        if math.isclose(bucket, round(bucket), abs_tol=0.001):
            return str(int(round(bucket)))
        return str(round(bucket, 2))

    def learned_setpoint_for_current_target(self, mode: str | None = None) -> float | None:
        mode = mode or self.device_mode
        if mode not in ("heat", "cool"):
            return None
        return self.learning.get(mode, {}).get(self.learning_bucket(self.target_temperature))

    async def async_set_device_temperature(self, temperature: float) -> None:
        self.expected_device_setpoint = temperature
        self.expected_device_setpoint_until = dt_util.utcnow() + timedelta(seconds=20)
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": self.target_climate, "temperature": temperature},
            blocking=True,
        )

    async def async_call_climate_service(self, service: str, data: dict[str, Any]) -> None:
        data = dict(data)
        data["entity_id"] = self.target_climate
        await self.hass.services.async_call("climate", service, data, blocking=True)

    async def async_call_quiet_switch(self, turn_on: bool) -> None:
        if not self.quiet_switch:
            return
        await self.hass.services.async_call(
            "switch",
            "turn_on" if turn_on else "turn_off",
            {"entity_id": self.quiet_switch},
            blocking=True,
        )

    def controller_state(self) -> str:
        room = self.room_temperature
        mode = self.device_mode
        if room is None:
            return "sensor_unavailable"
        if self.manual_override_active:
            return "manual_override"
        if mode not in ("heat", "cool"):
            return "unsupported_hvac_mode"
        if self.lower_limit <= room <= self.upper_limit:
            return "inside_tolerance"
        if not self.apply_to_device:
            return "dry_run"
        return "active"

    def device_attr(self, attr: str) -> Any:
        state = self.target_state
        return None if state is None else state.attributes.get(attr)

    def diagnostic_value(self, key: str) -> Any:
        room = self.room_temperature
        mode = self.device_mode
        mapping = {
            "controller_state": self.controller_state(),
            "last_correction_reason": self.last_correction_reason,
            "device_current_setpoint": self.device_setpoint,
            "device_current_temperature": self.device_attr("current_temperature"),
            "device_hvac_mode": mode,
            "device_hvac_action": self.device_attr("hvac_action"),
            "device_fan_mode": self.device_attr("fan_mode"),
            "device_swing_mode": self.device_attr("swing_mode"),
            "device_preset_mode": self.device_attr("preset_mode"),
            "room_temperature_error": None if room is None else round(room - self.target_temperature, 2),
            "room_lower_limit": self.lower_limit,
            "room_upper_limit": self.upper_limit,
            "learning_bucket": self.learning_bucket(self.target_temperature),
            "learned_setpoint_for_target": self.learned_setpoint_for_current_target(mode),
            "manual_override_active": self.manual_override_active,
            "fallback_active": self.fallback_active,
            "sensor_status": "available" if room is not None else "unavailable",
        }
        return mapping.get(key)

    def diagnostics(self) -> dict[str, Any]:
        return {
            "proxy_entry_id": self.entry.entry_id,
            "proxy_target_climate": self.target_climate,
            "proxy_temperature_sensor": self.temperature_sensor,
            "quiet_switch_entity": self.quiet_switch,
            "controller_state": self.controller_state(),
            "sensor_status": self.diagnostic_value("sensor_status"),
            "last_valid_room_temperature": self.last_valid_room_temperature,
            "last_valid_room_temperature_time": self.last_valid_room_temperature_time.isoformat() if self.last_valid_room_temperature_time else None,
            "room_target_temperature": self.target_temperature,
            "room_lower_limit": self.lower_limit,
            "room_upper_limit": self.upper_limit,
            "device_current_setpoint": self.device_setpoint,
            "expected_device_setpoint": self.expected_device_setpoint,
            "expected_device_setpoint_until": self.expected_device_setpoint_until.isoformat() if self.expected_device_setpoint_until else None,
            "learning_table_heat": self.learning.get("heat", {}),
            "learning_table_cool": self.learning.get("cool", {}),
            "last_learning_update": self.last_learning_update,
            "manual_override_until": self.manual_override_until.isoformat() if self.manual_override_until else None,
            "fallback_reason": self.fallback_reason,
            "last_correction_time": self.last_correction_time.isoformat() if self.last_correction_time else None,
            "next_correction_allowed": (self.last_correction_time + timedelta(minutes=int(self.option(CONF_CORRECTION_INTERVAL_MINUTES)))).isoformat() if self.last_correction_time else None,
            "mode_stable_since": self.mode_since.isoformat(),
            "device_setpoint_stable_since": self.device_setpoint_since.isoformat(),
            "target_stable_since": self.target_since.isoformat(),
            "in_range_since": self.in_range_since.isoformat() if self.in_range_since else None,
            "outside_range_since": self.outside_range_since.isoformat() if self.outside_range_since else None,
            "last_evaluation_reason": self.last_evaluation_reason,
            "last_evaluation_time": self.last_evaluation_time.isoformat() if self.last_evaluation_time else None,
        }
