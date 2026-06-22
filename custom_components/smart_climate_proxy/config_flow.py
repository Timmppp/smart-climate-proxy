"""Config flow for Smart Climate Proxy."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import *


def _entity_selector(domain: str) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))


def _base_schema(defaults: dict) -> vol.Schema:
    target_key = (
        vol.Required(CONF_TARGET_CLIMATE, default=defaults.get(CONF_TARGET_CLIMATE))
        if defaults.get(CONF_TARGET_CLIMATE)
        else vol.Required(CONF_TARGET_CLIMATE)
    )
    sensor_key = (
        vol.Required(CONF_TEMPERATURE_SENSOR, default=defaults.get(CONF_TEMPERATURE_SENSOR))
        if defaults.get(CONF_TEMPERATURE_SENSOR)
        else vol.Required(CONF_TEMPERATURE_SENSOR)
    )
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Keuken proxy")): str,
            target_key: _entity_selector("climate"),
            sensor_key: _entity_selector("sensor"),
            vol.Required(CONF_TARGET_TEMPERATURE, default=defaults.get(CONF_TARGET_TEMPERATURE, DEFAULTS[CONF_TARGET_TEMPERATURE])): vol.Coerce(float),
            vol.Required(CONF_LOWER_TOLERANCE, default=defaults.get(CONF_LOWER_TOLERANCE, DEFAULTS[CONF_LOWER_TOLERANCE])): vol.Coerce(float),
            vol.Required(CONF_UPPER_TOLERANCE, default=defaults.get(CONF_UPPER_TOLERANCE, DEFAULTS[CONF_UPPER_TOLERANCE])): vol.Coerce(float),
            vol.Required(CONF_CORRECTION_INTERVAL_MINUTES, default=defaults.get(CONF_CORRECTION_INTERVAL_MINUTES, DEFAULTS[CONF_CORRECTION_INTERVAL_MINUTES])): vol.Coerce(int),
            vol.Required(CONF_SETPOINT_STEP, default=defaults.get(CONF_SETPOINT_STEP, DEFAULTS[CONF_SETPOINT_STEP])): vol.Coerce(float),
            vol.Required(CONF_LEARNING_STABLE_HOURS, default=defaults.get(CONF_LEARNING_STABLE_HOURS, DEFAULTS[CONF_LEARNING_STABLE_HOURS])): vol.Coerce(float),
            vol.Required(CONF_APPLY_TO_DEVICE, default=defaults.get(CONF_APPLY_TO_DEVICE, DEFAULTS[CONF_APPLY_TO_DEVICE])): bool,
            vol.Required(CONF_LEARNING_ENABLED, default=defaults.get(CONF_LEARNING_ENABLED, DEFAULTS[CONF_LEARNING_ENABLED])): bool,
            vol.Required(CONF_MANUAL_OVERRIDE_ENABLED, default=defaults.get(CONF_MANUAL_OVERRIDE_ENABLED, DEFAULTS[CONF_MANUAL_OVERRIDE_ENABLED])): bool,
        }
    )


def _advanced_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MANUAL_OVERRIDE_MINUTES, default=defaults.get(CONF_MANUAL_OVERRIDE_MINUTES, DEFAULTS[CONF_MANUAL_OVERRIDE_MINUTES])): vol.Coerce(int),
            vol.Required(CONF_LEARNING_RESOLUTION, default=defaults.get(CONF_LEARNING_RESOLUTION, DEFAULTS[CONF_LEARNING_RESOLUTION])): vol.Coerce(float),
            vol.Required(CONF_FORWARD_HVAC_MODE, default=defaults.get(CONF_FORWARD_HVAC_MODE, DEFAULTS[CONF_FORWARD_HVAC_MODE])): bool,
            vol.Required(CONF_FORWARD_FAN_MODE, default=defaults.get(CONF_FORWARD_FAN_MODE, DEFAULTS[CONF_FORWARD_FAN_MODE])): bool,
            vol.Required(CONF_FORWARD_SWING_MODE, default=defaults.get(CONF_FORWARD_SWING_MODE, DEFAULTS[CONF_FORWARD_SWING_MODE])): bool,
            vol.Required(CONF_FORWARD_PRESET_MODE, default=defaults.get(CONF_FORWARD_PRESET_MODE, DEFAULTS[CONF_FORWARD_PRESET_MODE])): bool,
            vol.Required(CONF_USE_QUIET_SWITCH, default=defaults.get(CONF_USE_QUIET_SWITCH, DEFAULTS[CONF_USE_QUIET_SWITCH])): bool,
            vol.Optional(CONF_QUIET_SWITCH): _entity_selector("switch"),
            vol.Required(CONF_USE_CUSTOM_LIMITS, default=defaults.get(CONF_USE_CUSTOM_LIMITS, DEFAULTS[CONF_USE_CUSTOM_LIMITS])): bool,
            vol.Required(CONF_HEAT_MIN_SETPOINT, default=defaults.get(CONF_HEAT_MIN_SETPOINT, DEFAULTS[CONF_HEAT_MIN_SETPOINT])): vol.Coerce(float),
            vol.Required(CONF_HEAT_MAX_SETPOINT, default=defaults.get(CONF_HEAT_MAX_SETPOINT, DEFAULTS[CONF_HEAT_MAX_SETPOINT])): vol.Coerce(float),
            vol.Required(CONF_COOL_MIN_SETPOINT, default=defaults.get(CONF_COOL_MIN_SETPOINT, DEFAULTS[CONF_COOL_MIN_SETPOINT])): vol.Coerce(float),
            vol.Required(CONF_COOL_MAX_SETPOINT, default=defaults.get(CONF_COOL_MAX_SETPOINT, DEFAULTS[CONF_COOL_MAX_SETPOINT])): vol.Coerce(float),
        }
    )


class SmartClimateProxyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Climate Proxy."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            await self.async_set_unique_id(f"{self._data[CONF_TARGET_CLIMATE]}_{self._data[CONF_TEMPERATURE_SENSOR]}")
            self._abort_if_unique_id_configured()
            return await self.async_step_advanced()

        return self.async_show_form(step_id="user", data_schema=_base_schema({}), errors={})

    async def async_step_advanced(self, user_input=None):
        if user_input is not None:
            data = {**DEFAULTS, **self._data, **user_input}
            if not data.get(CONF_USE_QUIET_SWITCH):
                data[CONF_QUIET_SWITCH] = ""
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(step_id="advanced", data_schema=_advanced_schema(self._data), errors={})

    @staticmethod
    def async_get_options_flow(config_entry):
        return SmartClimateProxyOptionsFlow(config_entry)


class SmartClimateProxyOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Smart Climate Proxy."""

    def __init__(self, config_entry) -> None:
        self._data: dict = {**config_entry.data, **config_entry.options}

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_advanced()

        return self.async_show_form(step_id="init", data_schema=_base_schema(self._data), errors={})

    async def async_step_advanced(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            if not self._data.get(CONF_USE_QUIET_SWITCH):
                self._data[CONF_QUIET_SWITCH] = ""
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(step_id="advanced", data_schema=_advanced_schema(self._data), errors={})
