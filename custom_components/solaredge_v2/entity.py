"""Base entities for the SolarEdge Monitoring API v2 integration."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Device
from .const import DOMAIN, MANUFACTURER
from .coordinator import SolarEdgeCoordinator


class SolarEdgeSiteEntity(CoordinatorEntity[SolarEdgeCoordinator]):
    """An entity that belongs to the site device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SolarEdgeCoordinator, description: EntityDescription
    ) -> None:
        """Attach the entity to the site device."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.site_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, str(coordinator.site_id))})


class SolarEdgeDeviceEntity(CoordinatorEntity[SolarEdgeCoordinator]):
    """An entity that belongs to an inverter, meter, or battery."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolarEdgeCoordinator,
        description: EntityDescription,
        device: Device,
    ) -> None:
        """Describe the device from the inventory entry."""
        super().__init__(coordinator)
        self.entity_description = description
        self.serial_number = device.serial_number
        self._attr_unique_id = f"{device.serial_number}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial_number)},
            manufacturer=device.manufacturer or MANUFACTURER,
            model=device.model,
            model_id=device.part_number,
            name=device.name or f"{device.type.title()} {device.serial_number}",
            serial_number=device.serial_number,
            sw_version=device.firmware_version,
            via_device_id=dr.async_get_device_id_by_identifier(
                coordinator.hass,
                (DOMAIN, str(coordinator.site_id)),
                config_entry_id=coordinator.config_entry.entry_id,
            ),
        )

    @property
    def available(self) -> bool:
        """Unavailable once the device leaves the inventory."""
        return super().available and any(
            d.serial_number == self.serial_number for d in self.coordinator.data.devices
        )
