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
        # --- STATION CATEGORY ---
        # 1. Active Config (Station 1 / 2)
        TSkyltSelect(coordinator, "screen", "Station: Active Config", "mdi:monitor-dashboard",
                     {"Station 1": "1", "Station 2": "2"}),

        # 2. Country (Data Provider)
        TSkyltSelect(coordinator, "country", "Station: Country", "mdi:flag",
                     {"Sweden (SE)": "se", "Germany (DE)": "de", "Netherlands (NL)": "nl", 
                      "Belgium (BE)": "be", "Switzerland (CH)": "ch", "Norway (NO)": "no",
                      "Denmark (DK)": "dk", "Finland (FI)": "fi", "Croatia (CR)": "cr"}),

        # 3. Operator
        TSkyltSelect(coordinator, "operator", "Station: Operator", "mdi:train-car",
                     {"Berlin-Brandenburg (VBB)": "be", "Deutsche Bahn (DB)": "db", "Rhein-Ruhr (VRR)": "vrr"}),

        # Existing
        TSkyltSelect(coordinator, "maxdest", "Station: Max Departures", "mdi:format-list-numbered", 
                     [str(i) for i in range(1, 9)]),
        TSkyltSelect(coordinator, "offset", "Station: Offset / Hide Within", "mdi:clock-start", 
                     [str(i) for i in range(31)]),

        # --- DISPLAY CATEGORY ---
        # 4. LED Tone (Color)
        TSkyltSelect(coordinator, "color", "Display: LED Tone", "mdi:palette",
                     {"Orange (0)": "0", "Yellow (1)": "1", "White (2)": "2"}),

        # --- VIEW CATEGORY ---
        TSkyltSelect(coordinator, "scroll", "View: Scroll Speed", "mdi:speedometer", 
                     {"Normal": "0", "Low": "1"}),

        # --- SYSTEM / CONFIG ---
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
        # Value from device (e.g., "1" or "be")
        device_val = self.coordinator.data.get(self._key, "")
        
        # Find matching label key for this value
        for label, val in self._options_map.items():
            if str(val) == str(device_val):
                return label
        
        # Fallback if unknown or initial load (default to first option)
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