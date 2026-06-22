"""Sensor platform for Smart Climate Proxy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import SmartClimateProxyBaseEntity


SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="controller_state", name="Controller state", icon="mdi:state-machine"),
    SensorEntityDescription(key="last_correction_reason", name="Last correction reason", icon="mdi:information-outline"),
    SensorEntityDescription(key="sensor_status", name="External sensor status", icon="mdi:access-point-check"),
    SensorEntityDescription(key="device_current_setpoint", name="Device current setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE),
    SensorEntityDescription(key="device_current_temperature", name="Device current temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE),
    SensorEntityDescription(key="device_hvac_mode", name="Device HVAC mode", icon="mdi:hvac"),
    SensorEntityDescription(key="device_hvac_action", name="Device HVAC action", icon="mdi:heat-wave"),
    SensorEntityDescription(key="device_fan_mode", name="Device fan mode", icon="mdi:fan"),
    SensorEntityDescription(key="device_swing_mode", name="Device swing mode", icon="mdi:swap-vertical"),
    SensorEntityDescription(key="device_preset_mode", name="Device preset mode", icon="mdi:tune-variant"),
    SensorEntityDescription(key="room_temperature_error", name="Room temperature error", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE),
    SensorEntityDescription(key="room_lower_limit", name="Room lower limit", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE),
    SensorEntityDescription(key="room_upper_limit", name="Room upper limit", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE),
    SensorEntityDescription(key="learning_bucket", name="Learning bucket", icon="mdi:table"),
    SensorEntityDescription(key="learned_setpoint_for_target", name="Learned setpoint for target", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE),
    SensorEntityDescription(key="manual_override_active", name="Manual override active", icon="mdi:hand-back-right"),
    SensorEntityDescription(key="fallback_active", name="Fallback active", icon="mdi:backup-restore"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartClimateProxySensor(manager, description) for description in SENSORS])


class SmartClimateProxySensor(SmartClimateProxyBaseEntity, SensorEntity):
    """Diagnostic sensor."""

    entity_description: SensorEntityDescription

    def __init__(self, manager, description: SensorEntityDescription) -> None:
        super().__init__(manager, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        value = self.manager.diagnostic_value(self.entity_description.key)
        if isinstance(value, bool):
            return "on" if value else "off"
        return value
