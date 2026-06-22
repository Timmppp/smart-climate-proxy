"""Switch platform for Smart Climate Proxy."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_APPLY_TO_DEVICE,
    CONF_FORWARD_FAN_MODE,
    CONF_FORWARD_HVAC_MODE,
    CONF_FORWARD_PRESET_MODE,
    CONF_FORWARD_SWING_MODE,
    CONF_LEARNING_ENABLED,
    CONF_MANUAL_OVERRIDE_ENABLED,
    CONF_USE_CUSTOM_LIMITS,
    CONF_USE_QUIET_SWITCH,
    DOMAIN,
)
from .entity import SmartClimateProxyBaseEntity


@dataclass(frozen=True)
class ProxySwitchDescription(SwitchEntityDescription):
    option_key: str = ""


SWITCHES: tuple[ProxySwitchDescription, ...] = (
    ProxySwitchDescription(key="apply_to_device", option_key=CONF_APPLY_TO_DEVICE, name="Apply to device", icon="mdi:send"),
    ProxySwitchDescription(key="learning_enabled", option_key=CONF_LEARNING_ENABLED, name="Learning enabled", icon="mdi:school"),
    ProxySwitchDescription(key="manual_override_enabled", option_key=CONF_MANUAL_OVERRIDE_ENABLED, name="Manual override detection", icon="mdi:hand-back-right"),
    ProxySwitchDescription(key="use_custom_limits", option_key=CONF_USE_CUSTOM_LIMITS, name="Use custom limits", icon="mdi:ray-start-end"),
    ProxySwitchDescription(key="forward_hvac_mode", option_key=CONF_FORWARD_HVAC_MODE, name="Forward HVAC mode", icon="mdi:hvac"),
    ProxySwitchDescription(key="forward_fan_mode", option_key=CONF_FORWARD_FAN_MODE, name="Forward fan mode", icon="mdi:fan"),
    ProxySwitchDescription(key="forward_swing_mode", option_key=CONF_FORWARD_SWING_MODE, name="Forward swing mode", icon="mdi:swap-vertical"),
    ProxySwitchDescription(key="forward_preset_mode", option_key=CONF_FORWARD_PRESET_MODE, name="Forward preset mode", icon="mdi:tune-variant"),
    ProxySwitchDescription(key="use_quiet_switch", option_key=CONF_USE_QUIET_SWITCH, name="Use quiet switch", icon="mdi:volume-low"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartClimateProxySwitch(manager, description) for description in SWITCHES])


class SmartClimateProxySwitch(SmartClimateProxyBaseEntity, SwitchEntity):
    """Configurable switch entity."""

    entity_description: ProxySwitchDescription

    def __init__(self, manager, description: ProxySwitchDescription) -> None:
        super().__init__(manager, description.key, description.name)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return bool(self.manager.option(self.entity_description.option_key))

    async def async_turn_on(self, **kwargs) -> None:
        await self.manager.async_set_option(self.entity_description.option_key, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.manager.async_set_option(self.entity_description.option_key, False)
