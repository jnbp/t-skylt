"""Select platform for T-Skylt."""
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TSkyltSelect(coordinator, "brightness", "Brightness", {"Low": "0", "Medium": "1", "High": "2"}, "mdi:brightness-6"),
        TSkyltSelect(coordinator, "color", "LED Color", {"Orange": "0", "Yellow": "1", "White": "2"}, "mdi:palette-swatch"),
    ])

class TSkyltSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, key, name, options_map, icon):
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._options_map = options_map
        self._inv_options_map = {v: k for k, v in self._options_map.items()}
        self._icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.host)},
            name="T-Skylt Board",
            manufacturer="T-Skylt Sweden AB",
            model="Departure Board",
            sw_version=self.coordinator.sw_version,
            configuration_url=f"http://{self.coordinator.host}/"
        )

    @property
    def name(self):
        return f"T-Skylt {self._name_suffix}"

    @property
    def unique_id(self):
        return f"{self.coordinator.host}_{self._key}"

    @property
    def options(self):
        return list(self._options_map.keys())

    @property
    def current_option(self):
        val = self.coordinator.data.get(self._key, "0")
        # Fallback if value is unknown
        return self._inv_options_map.get(str(val), list(self._options_map.keys())[0])

    @property
    def icon(self):
        return self._icon

    async def async_select_option(self, option: str):
        val = self._options_map[option]
        await self.coordinator.send_command(f"?{self._key}={val}")
        # Manually update local data for optimistic feeling before refresh
        self.coordinator.data[self._key] = val
        self.async_write_ha_state()