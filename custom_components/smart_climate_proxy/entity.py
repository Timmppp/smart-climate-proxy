"""Base entity for Smart Climate Proxy."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class SmartClimateProxyBaseEntity(Entity):
    """Base entity linked to one proxy manager."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager, key: str, name: str | None = None) -> None:
        super().__init__()

        self.manager = manager
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{manager.entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, manager.entry.entry_id)},
            "name": manager.name,
            "manufacturer": "Smart Climate Proxy",
            "model": "Generic Climate Proxy",
        }

        manager.entities.append(self)

    @property
    def available(self) -> bool:
        return self.manager.target_state is not None
