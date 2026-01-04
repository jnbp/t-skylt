"""Text platform for T-Skylt."""
import urllib.parse
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        # Station Group
        TSkyltText(coordinator, "newstation", "Station: ID Input", "mdi:map-marker"),
        
        # View Group
        TSkyltText(coordinator, "no_more_departures", "View: No Departures Text", "mdi:message-text-outline"),
        TSkyltText(coordinator, "mins", "View: Minutes Suffix", "mdi:clock-end"),
        
        # System Group
        TSkyltText(coordinator, "user", "System: E-Mail", "mdi:email", EntityCategory.CONFIG),
    ]

    # Timer Group (Separate block)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days:
        entities.append(TSkyltTimerText(coordinator, day, "start", f"Timer: {day} Start"))
        entities.append(TSkyltTimerText(coordinator, day, "end", f"Timer: {day} End"))

    async_add_entities(entities)

class TSkyltText(CoordinatorEntity, TextEntity):
    def __init__(self, coordinator, key, name, icon, category=None):
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
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
    def native_value(self): return self.coordinator.data.get(self._key, "")
    @property
    def icon(self): return self._icon

    async def async_set_value(self, value: str) -> None:
        encoded_val = urllib.parse.quote(value)
        await self.coordinator.send_command(f"?{self._key}={encoded_val}")
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()

class TSkyltTimerText(CoordinatorEntity, TextEntity):
    def __init__(self, coordinator, day, type, name):
        super().__init__(coordinator)
        self._day = day
        self._type = type 
        self._name_suffix = name
        self._icon = "mdi:timer-settings"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def device_info(self) -> DeviceInfo: return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)
    @property
    def name(self): return f"T-Skylt {self._name_suffix}"
    @property
    def unique_id(self): return f"{self.coordinator.host}_timer_{self._day}_{self._type}"
    @property
    def native_value(self): 
        key = f"{self._day.lower()}_{self._type}"
        return self.coordinator.data.get(key, "00:00")
    @property
    def icon(self): return self._icon

    async def async_set_value(self, value: str) -> None:
        key_me = f"{self._day.lower()}_{self._type}"
        key_other = f"{self._day.lower()}_{'end' if self._type == 'start' else 'start'}"
        other_val = self.coordinator.data.get(key_other, "00:00")
        start = value if self._type == 'start' else other_val
        end = value if self._type == 'end' else other_val
        time_str = f"{start}to={end}"
        encoded_time = urllib.parse.quote(time_str)
        await self.coordinator.send_command(f"?set_timer={self._day}&start={encoded_time}")
        self.coordinator.data[key_me] = value
        self.async_write_ha_state()