"""Number platform for T-Skylt."""
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        # Station Group
        TSkyltNumber(coordinator, "maxdest", "Station: Max Departures", 1, 8, "mdi:counter"),
        TSkyltNumber(coordinator, "offset", "Station: Offset (Hide Within)", 0, 30, "mdi:timer-off"),
        
        # Display Group
        TSkyltNumber(coordinator, "line_length", "Display: Line ID Cutoff", 0, 6, "mdi:ruler"),

        # System Group
        TSkyltNumber(coordinator, "power", "System: TX Power", 7, 20, "mdi:wifi-strength-4", EntityCategory.CONFIG),
    ])

class TSkyltNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, key, name, min_val, max_val, icon, category=None):
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._icon = icon
        if category:
            self._attr_entity_category = category

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)
    @property
    def name(self): return f"T-Skylt {self._name_suffix}"
    @property
    def unique_id(self): return f"{self.coordinator.host}_{self._key}"
    @property
    def native_value(self):
        try: return float(self.coordinator.data.get(self._key, self._attr_native_min_value))
        except: return self._attr_native_min_value
    @property
    def icon(self): return self._icon

    async def async_set_native_value(self, value: float) -> None:
        val_int = int(value)
        await self.coordinator.send_command(f"?{self._key}={val_int}")
        self.coordinator.data[self._key] = str(val_int)
        self.async_write_ha_state()