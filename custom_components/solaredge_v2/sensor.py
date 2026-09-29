"""Sensors for the SolarEdge Monitoring API v2 integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfRatio,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SolarEdgeConfigEntry
from .api import Device, DeviceType, Series, SiteData
from .coordinator import SolarEdgeCoordinator
from .entity import SolarEdgeDeviceEntity, SolarEdgeSiteEntity

PARALLEL_UPDATES = 0

type Metrics = dict[str, Series]


@dataclass(frozen=True, kw_only=True)
class SiteSensorDescription(SensorEntityDescription):
    """A sensor computed from the site-level data."""

    value_fn: Callable[[SiteData], float | int | datetime | None]


@dataclass(frozen=True, kw_only=True)
class DeviceSensorDescription(SensorEntityDescription):
    """A sensor computed from one device's telemetry metrics."""

    value_fn: Callable[[Metrics], float | None]


def _latest_w(metric: str) -> Callable[[Metrics], float | None]:
    return lambda m: m[metric].latest_watts if metric in m else None


def _today_wh(metric: str) -> Callable[[Metrics], float | None]:
    return lambda m: m[metric].total_watt_hours if metric in m else None


def _latest(metric: str) -> Callable[[Metrics], float | None]:
    return lambda m: m[metric].latest if metric in m else None


def _power(key: str, metric: str, *, enabled: bool = True) -> DeviceSensorDescription:
    return DeviceSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=enabled,
        value_fn=_latest_w(metric),
    )


def _energy(key: str, metric: str, *, enabled: bool = True) -> DeviceSensorDescription:
    return DeviceSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=enabled,
        value_fn=_today_wh(metric),
    )


def _site_energy(
    key: str, fn: Callable[[SiteData], float | None], *, enabled: bool = True
) -> SiteSensorDescription:
    return SiteSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=enabled,
        value_fn=fn,
    )


SITE_SENSORS: tuple[SiteSensorDescription, ...] = (
    SiteSensorDescription(
        key="current_power",
        translation_key="current_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.power.latest_watts if d.power else None,
    ),
    _site_energy("production_today", lambda d: d.overview.production if d.overview else None),
    _site_energy("consumption_today", lambda d: d.overview.consumption if d.overview else None),
    _site_energy(
        "export_today", lambda d: d.overview.production_to_grid if d.overview else None
    ),
    _site_energy(
        "import_today", lambda d: d.overview.consumption_from_grid if d.overview else None
    ),
    _site_energy(
        "self_consumption_today",
        lambda d: d.overview.production_to_self_consumption if d.overview else None,
        enabled=False,
    ),
    _site_energy(
        "to_storage_today",
        lambda d: d.overview.production_to_storage if d.overview else None,
        enabled=False,
    ),
    _site_energy(
        "from_storage_today",
        lambda d: d.overview.consumption_from_storage if d.overview else None,
        enabled=False,
    ),
    _site_energy("lifetime_energy", lambda d: d.lifetime_energy),
    SiteSensorDescription(
        key="peak_power",
        translation_key="peak_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.metadata.peak_power_kw,
    ),
    SiteSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.metadata.last_update_time,
    ),
    SiteSensorDescription(
        key="open_alerts",
        translation_key="open_alerts",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: len(d.open_alerts) if d.open_alerts is not None else None,
    ),
)

INVERTER_SENSORS: tuple[DeviceSensorDescription, ...] = (
    _power("inverter_power", "power"),
    _energy("inverter_energy_today", "energy"),
    DeviceSensorDescription(
        key="inverter_voltage",
        translation_key="inverter_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_latest("voltage"),
    ),
    DeviceSensorDescription(
        key="inverter_current",
        translation_key="inverter_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_latest("current"),
    ),
    DeviceSensorDescription(
        key="inverter_frequency",
        translation_key="inverter_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_latest("frequency"),
    ),
)

METER_SENSORS: tuple[DeviceSensorDescription, ...] = (
    _power("meter_production_power", "productionPower"),
    _power("meter_consumption_power", "consumptionPower"),
    _power("meter_import_power", "importPower"),
    _power("meter_export_power", "exportPower"),
    _energy("meter_production_energy_today", "productionEnergy", enabled=False),
    _energy("meter_consumption_energy_today", "consumptionEnergy", enabled=False),
    _energy("meter_import_energy_today", "importEnergy", enabled=False),
    _energy("meter_export_energy_today", "exportEnergy", enabled=False),
)

BATTERY_SENSORS: tuple[DeviceSensorDescription, ...] = (
    _power("battery_charge_power", "chargePower"),
    _power("battery_discharge_power", "dischargePower"),
    DeviceSensorDescription(
        key="battery_state_of_energy",
        translation_key="battery_state_of_energy",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_latest("stateOfEnergy"),
    ),
    DeviceSensorDescription(
        key="battery_remaining_energy",
        translation_key="battery_remaining_energy",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda m: (
            m["remainingEnergy"].latest_watt_hours if "remainingEnergy" in m else None
        ),
    ),
    _energy("battery_charge_energy_today", "chargeEnergy", enabled=False),
    _energy("battery_discharge_energy_today", "dischargeEnergy", enabled=False),
)

DEVICE_SENSORS: dict[str, tuple[tuple[DeviceSensorDescription, ...], str]] = {
    DeviceType.INVERTER: (INVERTER_SENSORS, "inverters"),
    DeviceType.METER: (METER_SENSORS, "meters"),
    DeviceType.BATTERY: (BATTERY_SENSORS, "storage"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarEdgeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add site sensors now and device sensors whenever the inventory grows."""
    coordinator = entry.runtime_data
    async_add_entities(SolarEdgeSiteSensor(coordinator, d) for d in SITE_SENSORS)
    if not coordinator.device_telemetry:
        return

    known: set[str] = set()

    @callback
    def _add_new_devices() -> None:
        new = [
            d
            for d in coordinator.data.devices
            if d.type in DEVICE_SENSORS and d.serial_number not in known
        ]
        if not new:
            return
        known.update(d.serial_number for d in new)
        async_add_entities(
            SolarEdgeDeviceSensor(coordinator, description, device)
            for device in new
            for description in DEVICE_SENSORS[device.type][0]
        )

    _add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_devices))


class SolarEdgeSiteSensor(SolarEdgeSiteEntity, SensorEntity):
    """A site-level sensor."""

    entity_description: SiteSensorDescription

    @property
    def native_value(self) -> float | int | datetime | None:
        """Compute the value from the latest site data."""
        return self.entity_description.value_fn(self.coordinator.data)


class SolarEdgeDeviceSensor(SolarEdgeDeviceEntity, SensorEntity):
    """A telemetry sensor on an inverter, meter, or battery."""

    entity_description: DeviceSensorDescription

    def __init__(
        self,
        coordinator: SolarEdgeCoordinator,
        description: DeviceSensorDescription,
        device: Device,
    ) -> None:
        """Remember which telemetry map holds this device."""
        super().__init__(coordinator, description, device)
        self._telemetry_attr = DEVICE_SENSORS[device.type][1]

    @property
    def native_value(self) -> float | None:
        """Compute the value from this device's metrics."""
        telemetry = getattr(self.coordinator.data, self._telemetry_attr)
        metrics = telemetry.get(self.serial_number)
        return self.entity_description.value_fn(metrics) if metrics else None
