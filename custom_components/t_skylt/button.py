"""Button platform for T-Skylt."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        # Display Group
        TSkyltButton(coordinator, "rotate", "rotate", "Display: Rotate", "mdi:rotate-3d-variant"),
        
        # Timer Group
        TSkyltButton(coordinator, "cleartimer", "?cleartimer=true", "Timer: Clear All", "mdi:timer-off-outline", EntityCategory.CONFIG),
        
        # System Group
        TSkyltButton(coordinator, "update", "update", "System: Update", "mdi:update", EntityCategory.CONFIG),
        TSkyltButton(coordinator, "ver", "ver", "System: Downgrade (v1.0)", "mdi:history", EntityCategory.CONFIG),
        TSkyltButton(coordinator, "ping", "ping", "System: Ping Test", "mdi:lan-check", EntityCategory.DIAGNOSTIC),
        TSkyltButton(coordinator, "dns", "dns", "System: DNS Info", "mdi:dns", EntityCategory.DIAGNOSTIC),
    ])

class TSkyltButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, key, command, name, icon, category=None):
        super().__init__(coordinator)
        self._key = key
        self._command = command
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
    def icon(self): return self._icon

    async def async_press(self) -> None:
        await self.coordinator.send_command(self._command)