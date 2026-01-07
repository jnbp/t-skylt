"""Button platform for T-Skylt."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the T-Skylt buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        # System / Maintenance Buttons
        TSkyltButton(coordinator, "update?update=true", "System: Update Firmware", "mdi:update", EntityCategory.CONFIG),
        TSkyltButton(coordinator, "ver?ver=1", "System: Downgrade Firmware", "mdi:arrow-down-bold-box", EntityCategory.CONFIG),
        TSkyltButton(coordinator, "cleartimer", "System: Clear Timers", "mdi:timer-off", EntityCategory.CONFIG),
        TSkyltButton(coordinator, "stop", "System: Reboot", "mdi:restart", EntityCategory.CONFIG),

        # Network Tools (Links via Button-Press mimic)
        TSkyltButton(coordinator, "ping", "Network: Ping Test", "mdi:network-outline", EntityCategory.DIAGNOSTIC),
        TSkyltButton(coordinator, "dns", "Network: DNS Info", "mdi:dns-outline", EntityCategory.DIAGNOSTIC),

        # Display Actions
        TSkyltButton(coordinator, "rotate", "Display: Rotate", "mdi:rotate-3d-variant", EntityCategory.CONFIG),
    ]

    async_add_entities(entities)


class TSkyltButton(CoordinatorEntity, ButtonEntity):
    """Representation of a T-Skylt Button."""

    def __init__(self, coordinator, command, name, icon, category=None):
        """Initialize the button."""
        super().__init__(coordinator)
        self._command = command
        self._name_suffix = name
        self._icon = icon
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
        return f"{self.coordinator.host}_btn_{self._command}"

    @property
    def icon(self):
        return self._icon

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.send_command(self._command)
