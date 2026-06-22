"""Number platform for Smart Climate Proxy."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_COOL_MAX_SETPOINT,
    CONF_COOL_MIN_SETPOINT,
    CONF_CORRECTION_INTERVAL_MINUTES,
    CONF_HEAT_MAX_SETPOINT,
    CONF_HEAT_MIN_SETPOINT,
    CONF_LEARNING_RESOLUTION,
    CONF_LEARNING_STABLE_HOURS,
    CONF_LOWER_TOLERANCE,
    CONF_MANUAL_OVERRIDE_MINUTES,
    CONF_SETPOINT_STEP,
    CONF_TARGET_TEMPERATURE,
    CONF_UPPER_TOLERANCE,
    DOMAIN,
)
from .entity import SmartClimateProxyBaseEntity


@dataclass(frozen=True)
class ProxyNumberDescription(NumberEntityDescription):
    option_key: str = ""


NUMBERS: tuple[ProxyNumberDescription, ...] = (
    ProxyNumberDescription(key="target_temperature", option_key=CONF_TARGET_TEMPERATURE, name="Target temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=5, native_max_value=35, native_step=0.5, mode="box"),
    ProxyNumberDescription(key="lower_tolerance", option_key=CONF_LOWER_TOLERANCE, name="Lower tolerance", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0, native_max_value=10, native_step=0.1, mode="box"),
    ProxyNumberDescription(key="upper_tolerance", option_key=CONF_UPPER_TOLERANCE, name="Upper tolerance", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0, native_max_value=10, native_step=0.1, mode="box"),
    ProxyNumberDescription(key="correction_interval_minutes", option_key=CONF_CORRECTION_INTERVAL_MINUTES, name="Correction interval", native_min_value=1, native_max_value=240, native_step=1, mode="box"),
    ProxyNumberDescription(key="setpoint_step", option_key=CONF_SETPOINT_STEP, name="Setpoint step", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0.5, native_max_value=5, native_step=0.5, mode="box"),
    ProxyNumberDescription(key="learning_stable_hours", option_key=CONF_LEARNING_STABLE_HOURS, name="Learning stable hours", native_min_value=0.1, native_max_value=24, native_step=0.1, mode="box"),
    ProxyNumberDescription(key="manual_override_minutes", option_key=CONF_MANUAL_OVERRIDE_MINUTES, name="Manual override minutes", native_min_value=1, native_max_value=480, native_step=1, mode="box"),
    ProxyNumberDescription(key="learning_resolution", option_key=CONF_LEARNING_RESOLUTION, name="Learning resolution", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0.5, native_max_value=5, native_step=0.5, mode="box"),
    ProxyNumberDescription(key="heat_min_setpoint", option_key=CONF_HEAT_MIN_SETPOINT, name="Heat min setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0, native_max_value=40, native_step=0.5, mode="box"),
    ProxyNumberDescription(key="heat_max_setpoint", option_key=CONF_HEAT_MAX_SETPOINT, name="Heat max setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0, native_max_value=40, native_step=0.5, mode="box"),
    ProxyNumberDescription(key="cool_min_setpoint", option_key=CONF_COOL_MIN_SETPOINT, name="Cool min setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0, native_max_value=40, native_step=0.5, mode="box"),
    ProxyNumberDescription(key="cool_max_setpoint", option_key=CONF_COOL_MAX_SETPOINT, name="Cool max setpoint", native_unit_of_measurement=UnitOfTemperature.CELSIUS, native_min_value=0, native_max_value=40, native_step=0.5, mode="box"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartClimateProxyNumber(manager, description) for description in NUMBERS])


class SmartClimateProxyNumber(SmartClimateProxyBaseEntity, NumberEntity):
    """Configurable number entity."""

    entity_description: ProxyNumberDescription

    def __init__(self, manager, description: ProxyNumberDescription) -> None:
        super().__init__(manager, description.key, description.name)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        if self.entity_description.option_key == CONF_TARGET_TEMPERATURE:
            return self.manager.target_temperature
        return self.manager.option(self.entity_description.option_key)

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_set_option(self.entity_description.option_key, value)
