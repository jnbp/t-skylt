"""Switch platform for T-Skylt."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        TSkyltSwitch(coordinator, "onoff", "?onoff=active", "Power", "mdi:power"),
        TSkyltSwitch(coordinator, "listmode", "?listmode=switch", "List Mode", "mdi:format-list-bulleted"),
        TSkyltSwitch(coordinator, "multiple", "?multiple=1", "Multiple Stops", "mdi:bus-multiple"),
        TSkyltSwitch(coordinator, "show_station", "?show_station=1", "Show Station", "mdi:sign-text"),
        TSkyltSwitch(coordinator, "clocktime", "?clocktime=switch", "Clock/Countdown", "mdi:clock-digital"),
        TSkyltSwitch(coordinator, "listcolor", "?listcolor=switch", "Color Highlight", "mdi:palette"),
        TSkyltSwitch(coordinator, "fontmini", "?fontmini=switch", "Small Font", "mdi:format-size"),
    ]
    async_add_entities(entities)

class TSkyltSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, key, command, name, icon):
        super().__init__(coordinator)
        self._key = key
        self._command = command
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
    def is_on(self):
        # Zeigt den Status aus den Coordinator-Daten
        return self.coordinator.data.get(self._key, False)

    @property
    def icon(self):
        return self._icon

    async def async_turn_on(self, **kwargs):
        """Turn on."""
        if not self.is_on:
            # 1. Befehl senden
            await self.coordinator.send_command(self._command)
            # 2. SOFORT optimistisch auf True setzen (Fake it till you make it)
            self.coordinator.data[self._key] = True
            # 3. UI benachrichtigen
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off."""
        if self.is_on:
            await self.coordinator.send_command(self._command)
            # Optimistisch auf False setzen
            self.coordinator.data[self._key] = False
            self.async_write_ha_state()