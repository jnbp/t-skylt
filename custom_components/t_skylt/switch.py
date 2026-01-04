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
        # Display Group
        TSkyltSwitch(coordinator, "onoff", "?onoff=active", "Display: Power", "mdi:power"),
        TSkyltSwitch(coordinator, "listcolor", "?listcolor=switch", "Display: Color Highlight", "mdi:palette"),
        TSkyltSwitch(coordinator, "fontmini", "?fontmini=switch", "Display: Small Font", "mdi:format-size"),

        # Station Types Group
        TSkyltSwitch(coordinator, "type_metro", "?type=metro", "Station: Type Subway", "mdi:subway-variant"),
        TSkyltSwitch(coordinator, "type_bus", "?type=bus", "Station: Type Bus", "mdi:bus"),
        TSkyltSwitch(coordinator, "type_train", "?type=train", "Station: Type Train", "mdi:train"),
        TSkyltSwitch(coordinator, "type_tram", "?type=tram", "Station: Type Tram", "mdi:tram"),
        TSkyltSwitch(coordinator, "type_ship", "?type=ship", "Station: Type Ship", "mdi:ferry"),
        
        # View Group
        TSkyltSwitch(coordinator, "listmode", "?listmode=switch", "View: List Mode", "mdi:format-list-bulleted"),
        TSkyltSwitch(coordinator, "clocktime", "?clocktime=switch", "View: Clock/Countdown", "mdi:clock-digital"),
        TSkyltSwitch(coordinator, "sleep", "?sleep=1", "View: Sleep if no Depts", "mdi:sleep"),
        TSkyltSwitch(coordinator, "show_station", "?show_station=1", "View: Show Station Name", "mdi:sign-text"),
        TSkyltSwitch(coordinator, "multiple", "?multiple=1", "View: Multiple Stops", "mdi:bus-multiple"),
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
        return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)
    @property
    def name(self): return f"T-Skylt {self._name_suffix}"
    @property
    def unique_id(self): return f"{self.coordinator.host}_{self._key}"
    @property
    def is_on(self): return self.coordinator.data.get(self._key, False)
    @property
    def icon(self): return self._icon

    async def async_turn_on(self, **kwargs):
        if not self.is_on:
            await self.coordinator.send_command(self._command)
            self.coordinator.data[self._key] = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        if self.is_on:
            await self.coordinator.send_command(self._command)
            self.coordinator.data[self._key] = False
            self.async_write_ha_state()