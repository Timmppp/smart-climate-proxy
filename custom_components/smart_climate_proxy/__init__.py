"""Smart Climate Proxy integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.storage import Store

from .const import DOMAIN, PLATFORMS, STORE_KEY, STORE_VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Smart Climate Proxy and register services."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("managers", {})

    async def _handle_reset_learning(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        managers = hass.data[DOMAIN].get("managers", {})
        if entry_id:
            manager = managers.get(entry_id)
            if manager is None:
                _LOGGER.warning("No Smart Climate Proxy manager found for entry_id %s", entry_id)
                return
            await manager.async_reset_learning()
            return
        for manager in list(managers.values()):
            await manager.async_reset_learning()

    hass.services.async_register(DOMAIN, "reset_learning", _handle_reset_learning)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Climate Proxy from a config entry."""
    from .manager import SmartClimateProxyManager

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("managers", {})

    store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{STORE_KEY}_{entry.entry_id}")
    manager = SmartClimateProxyManager(hass, entry, store)
    await manager.async_load()

    hass.data[DOMAIN][entry.entry_id] = manager
    hass.data[DOMAIN]["managers"][entry.entry_id] = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        manager = hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN].get("managers", {}).pop(entry.entry_id, None)
        if manager:
            await manager.async_unload()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)
