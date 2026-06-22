"""Climate platform for Smart Climate Proxy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_FORWARD_FAN_MODE,
    CONF_FORWARD_HVAC_MODE,
    CONF_FORWARD_PRESET_MODE,
    CONF_FORWARD_SWING_MODE,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    manager = hass.data[DOMAIN][entry.entry_id]
    entity = SmartClimateProxyClimate(manager)
    manager.climate_entity = entity
    manager.entities.append(entity)
    async_add_entities([entity])
    await manager.async_start()


class SmartClimateProxyClimate(ClimateEntity):
    """Virtual climate entity using an external room sensor and setpoint correction."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_should_poll = False
    _attr_icon = "mdi:thermostat-auto"

    def __init__(self, manager) -> None:
        self.manager = manager
        self._attr_unique_id = f"{manager.entry.entry_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, manager.entry.entry_id)},
            "name": manager.name,
            "manufacturer": "Smart Climate Proxy",
            "model": "Generic Climate Proxy",
        }

    @property
    def available(self) -> bool:
        target = self.manager.target_state
        return target is not None and target.state not in ("unknown", "unavailable")

    @property
    def current_temperature(self) -> float | None:
        return self.manager.room_temperature

    @property
    def target_temperature(self) -> float | None:
        return self.manager.target_temperature

    @property
    def min_temp(self) -> float:
        state = self.manager.target_state
        if state is None:
            return 8
        return state.attributes.get("min_temp", 8)

    @property
    def max_temp(self) -> float:
        state = self.manager.target_state
        if state is None:
            return 30
        return state.attributes.get("max_temp", 30)

    @property
    def hvac_mode(self):
        mode = self.manager.device_mode
        if mode is None:
            return HVACMode.OFF
        try:
            return HVACMode(mode)
        except ValueError:
            return HVACMode.OFF

    @property
    def hvac_modes(self):
        state = self.manager.target_state
        if state is None:
            return [HVACMode.OFF]
        modes = []
        for mode in state.attributes.get("hvac_modes", [HVACMode.OFF]):
            try:
                modes.append(HVACMode(mode))
            except ValueError:
                pass
        return modes or [HVACMode.OFF]

    @property
    def hvac_action(self):
        return self.manager.device_attr("hvac_action")

    @property
    def current_humidity(self):
        return self.manager.device_attr("current_humidity")

    @property
    def fan_mode(self):
        return self.manager.device_attr("fan_mode")

    @property
    def fan_modes(self):
        state = self.manager.target_state
        if state is None:
            return []
        return state.attributes.get("fan_modes", [])

    @property
    def swing_mode(self):
        return self.manager.device_attr("swing_mode")

    @property
    def swing_modes(self):
        state = self.manager.target_state
        if state is None:
            return []
        return state.attributes.get("swing_modes", [])

    @property
    def preset_mode(self):
        return self.manager.device_attr("preset_mode")

    @property
    def preset_modes(self):
        state = self.manager.target_state
        if state is None:
            return []
        return state.attributes.get("preset_modes", [])

    @property
    def supported_features(self):
        features = ClimateEntityFeature.TARGET_TEMPERATURE
        state = self.manager.target_state
        if state is None:
            return features
        try:
            target_features = ClimateEntityFeature(state.attributes.get("supported_features", 0))
        except (TypeError, ValueError):
            target_features = ClimateEntityFeature(0)

        if self.manager.option(CONF_FORWARD_FAN_MODE) and target_features & ClimateEntityFeature.FAN_MODE:
            features |= ClimateEntityFeature.FAN_MODE
        if self.manager.option(CONF_FORWARD_SWING_MODE) and target_features & ClimateEntityFeature.SWING_MODE:
            features |= ClimateEntityFeature.SWING_MODE
        if self.manager.option(CONF_FORWARD_PRESET_MODE) and target_features & ClimateEntityFeature.PRESET_MODE:
            features |= ClimateEntityFeature.PRESET_MODE
        return features

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.manager.diagnostics()

    async def async_set_temperature(self, **kwargs) -> None:
        if ATTR_TEMPERATURE in kwargs:
            await self.manager.async_set_target_temperature(float(kwargs[ATTR_TEMPERATURE]))

    async def async_set_hvac_mode(self, hvac_mode) -> None:
        if not self.manager.option(CONF_FORWARD_HVAC_MODE):
            return
        await self.manager.async_call_climate_service("set_hvac_mode", {"hvac_mode": hvac_mode})

    async def async_set_fan_mode(self, fan_mode) -> None:
        if not self.manager.option(CONF_FORWARD_FAN_MODE):
            return
        await self.manager.async_call_climate_service("set_fan_mode", {"fan_mode": fan_mode})

    async def async_set_swing_mode(self, swing_mode) -> None:
        if not self.manager.option(CONF_FORWARD_SWING_MODE):
            return
        await self.manager.async_call_climate_service("set_swing_mode", {"swing_mode": swing_mode})

    async def async_set_preset_mode(self, preset_mode) -> None:
        if not self.manager.option(CONF_FORWARD_PRESET_MODE):
            return
        await self.manager.async_call_climate_service("set_preset_mode", {"preset_mode": preset_mode})

    async def async_turn_on(self) -> None:
        await self.manager.async_call_climate_service("turn_on", {})

    async def async_turn_off(self) -> None:
        await self.manager.async_call_climate_service("turn_off", {})
