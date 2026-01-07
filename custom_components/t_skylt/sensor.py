"""Sensor platform for T-Skylt."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the T-Skylt sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        TSkyltSensor(coordinator, "temperature", "System Temperature", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, "°C", EntityCategory.DIAGNOSTIC),
        TSkyltSensor(coordinator, "uptime", "Uptime", "mdi:clock-outline", SensorDeviceClass.DURATION, "min", EntityCategory.DIAGNOSTIC),
        
        # NEW: Active IP Address Sensor
        TSkyltIPSensor(coordinator),
    ]

    async_add_entities(entities)

class TSkyltSensor(CoordinatorEntity, SensorEntity):
    """Representation of a generic T-Skylt Sensor."""

    def __init__(self, coordinator, key, name, icon, device_class=None, unit=None, category=None):
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._icon = icon
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        if category:
            self._attr_entity_category = category

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)

    @property
    def name(self): return f"T-Skylt {self._name_suffix}"
    @property
    def unique_id(self): return f"{self.coordinator.host}_sensor_{self._key}"
    @property
    def icon(self): return self._icon
    @property
    def native_value(self): return self.coordinator.data.get(self._key)

class TSkyltIPSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the currently resolved IP address."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)

    @property
    def name(self): return "T-Skylt Network: Active IP"
    @property
    def unique_id(self): return f"{self.coordinator.host}_sensor_active_ip"
    @property
    def icon(self): return "mdi:ip-network"
    
    @property
    def native_value(self):
        # Retrieve the internal _cached_ip variable from the coordinator
        return getattr(self.coordinator, "_cached_ip", "Unknown")