"""Binary Sensor platform for T-Skylt."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TSkyltUpdateSensor(coordinator)
    ])

class TSkyltUpdateSensor(CoordinatorEntity, BinarySensorEntity):
    """Detects if an update is available."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "T-Skylt System: Update Available"
        self._attr_unique_id = f"{coordinator.host}_update_available"
        self._attr_device_class = BinarySensorDeviceClass.UPDATE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return self.coordinator.data.get("update_available", False)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)