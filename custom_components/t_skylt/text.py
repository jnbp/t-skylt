"""Text platform for T-Skylt."""
import urllib.parse
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TSkyltText(coordinator, "no_more_departures", "Text: No Departures", "mdi:message-text-outline"),
        TSkyltText(coordinator, "mins", "Text: Minutes Suffix", "mdi:clock-end"),
    ])

class TSkyltText(CoordinatorEntity, TextEntity):
    def __init__(self, coordinator, key, name, icon):
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
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
    def native_value(self):
        return self.coordinator.data.get(self._key, "")

    @property
    def icon(self):
        return self._icon

    async def async_set_value(self, value: str) -> None:
        """Update the text value."""
        # Ensure special characters like spaces are encoded to %20
        encoded_val = urllib.parse.quote(value)
        await self.coordinator.send_command(f"?{self._key}={encoded_val}")
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()