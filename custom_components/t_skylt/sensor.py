"""Sensor platform for T-Skylt."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TSkyltSensor(coordinator, "temperature", "System: Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, "mdi:thermometer"),
        TSkyltSensor(coordinator, "uptime", "System: Uptime", UnitOfTime.MINUTES, SensorDeviceClass.DURATION, "mdi:timer-outline"),
    ])

class TSkyltSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit, device_class, icon):
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._icon = icon
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)
    @property
    def name(self): return f"T-Skylt {self._name_suffix}"
    @property
    def unique_id(self): return f"{self.coordinator.host}_{self._key}"
    @property
    def native_value(self): return self.coordinator.data.get(self._key)
    @property
    def icon(self): return self._icon