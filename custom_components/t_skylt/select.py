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
        TSkyltSelect(coordinator, "brightness", "View: Brightness", "mdi:brightness-6", ["0", "1", "2"]),
        TSkyltSelect(coordinator, "scroll", "View: Scroll Speed", "mdi:speedometer", ["0", "1"]),
        
        # Display Hardware Settings
        # Width ist jetzt CONFIG category
        TSkyltSelect(coordinator, "width", "Display: Width", "mdi:arrow-expand-horizontal", ["XS", "X", "XL"], EntityCategory.CONFIG),
        TSkyltSelect(coordinator, "offset", "Display: Offset / Hide Within", "mdi:clock-start", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "20", "30"], EntityCategory.CONFIG),
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
        self._options = options
        if category:
            self._attr_entity_category = category

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.host)},
            name="T-Skylt Board",
            manufacturer="T-Skylt Sweden AB",
            model="Departure Board",
            sw_version=self.coordinator.sw_version,
        )

    @property
    def name(self):
        return f"T-Skylt {self._name_suffix}"

    @property
    def unique_id(self):
        return f"{self.coordinator.host}_select_{self._key}"

    @property
    def icon(self):
        return self._icon

    @property
    def options(self):
        return self._options

    @property
    def current_option(self):
        """Return the current selected option."""
        # Hol den Wert aus dem Coordinator Data
        val = self.coordinator.data.get(self._key, self._options[0])
        
        # Mapping für interne Werte, falls nötig (hier meistens direkt String)
        if val in self._options:
            return val
        return self._options[0]

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        encoded_val = urllib.parse.quote(option)
        await self.coordinator.send_command(f"?{self._key}={encoded_val}")
        # Optimistic update
        self.coordinator.data[self._key] = option
        self.async_write_ha_state()