"""Select platform for T-Skylt."""
import urllib.parse
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the T-Skylt selects."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        # View Settings
        # Scroll Speed with label mapping (Caption -> Value)
        TSkyltSelect(coordinator, "scroll", "View: Scroll Speed", "mdi:speedometer", 
                     {"Normal (0)": "0", "Low (1)": "1"}),
        
        # Max Departures (previously a slider, now a dropdown)
        TSkyltSelect(coordinator, "maxdest", "Station: Max Departures", "mdi:format-list-numbered", 
                     [str(i) for i in range(1, 9)]), # 1 to 8

        # Offset (previously duplicate or slider, now dropdown)
        TSkyltSelect(coordinator, "offset", "Station: Offset / Hide Within", "mdi:clock-start", 
                     ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "20", "30"]),
        
        # Display Hardware Settings
        # Width moved to CONFIG category
        TSkyltSelect(coordinator, "width", "Display: Width", "mdi:arrow-expand-horizontal", 
                     ["XS", "X", "XL"], EntityCategory.CONFIG),
    ]

    async_add_entities(entities)


class TSkyltSelect(CoordinatorEntity, SelectEntity):
    """Representation of a T-Skylt Select."""

    def __init__(self, coordinator, key, name, icon, options, category=None):
        """Initialize the select."""
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._icon = icon
        
        # Handle options: can be list or dict {label: value}
        if isinstance(options, dict):
            self._options_map = options
            self._attr_options = list(options.keys())
        else:
            self._options_map = {opt: opt for opt in options}
            self._attr_options = options
            
        if category:
            self._attr_entity_category = category

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)

    @property
    def name(self): return f"T-Skylt {self._name_suffix}"
    @property
    def unique_id(self): return f"{self.coordinator.host}_select_{self._key}"
    @property
    def icon(self): return self._icon

    @property
    def current_option(self):
        """Return the current selected option key."""
        # Value from device (e.g., "0")
        device_val = self.coordinator.data.get(self._key, "")
        
        # Find matching label key for this value
        for label, val in self._options_map.items():
            if val == str(device_val):
                return label
        
        # Fallback
        return self._attr_options[0]

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find value for the label
        value_to_send = self._options_map[option]
        
        encoded_val = urllib.parse.quote(value_to_send)
        await self.coordinator.send_command(f"?{self._key}={encoded_val}")
        
        # Optimistic update
        self.coordinator.data[self._key] = value_to_send
        self.async_write_ha_state()