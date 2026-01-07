"""Number platform for T-Skylt."""
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the T-Skylt numbers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        # Brightness as Slider (0-2)
        TSkyltBrightnessNumber(coordinator),
    ]

    async_add_entities(entities)

class TSkyltBrightnessNumber(CoordinatorEntity, NumberEntity):
    """Representation of the Brightness Slider."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)

    @property
    def name(self): return "T-Skylt Display: Brightness"
    @property
    def unique_id(self): return f"{self.coordinator.host}_number_brightness"
    @property
    def icon(self): return "mdi:brightness-6"
    
    # Slider Configuration
    @property
    def native_min_value(self): return 0
    @property
    def native_max_value(self): return 2
    @property
    def native_step(self): return 1

    @property
    def native_value(self):
        try:
            return float(self.coordinator.data.get("brightness", 0))
        except ValueError:
            return 0

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        int_val = int(value)
        await self.coordinator.send_command(f"?brightness={int_val}")
        self.coordinator.data["brightness"] = str(int_val)
        self.async_write_ha_state()