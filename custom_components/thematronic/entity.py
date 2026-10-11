"""Base entity for Thematronic."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN, LANGUAGE, MANUFACTURER, MODEL
from .coordinator import ThematronicCoordinator
from .parser import configured_sections, schema_code


class ThematronicEntity(CoordinatorEntity[ThematronicCoordinator]):
    """Common device info and unique id handling."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ThematronicCoordinator,
        description: EntityDescription,
        section: str | None = None,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(coordinator.device_id))},
            name=f"Thematronic {MODEL}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            serial_number=str(coordinator.device_id),
            configuration_url=f"{BASE_URL}/{LANGUAGE}/",
        )
        if section is not None and coordinator.data is not None:
            # Parts of the dashboard the controller's hydraulic schema doesn't
            # use start disabled; the user can enable them any time.
            in_use = configured_sections(schema_code(coordinator.data))
            if section not in in_use:
                self._attr_entity_registry_enabled_default = False
