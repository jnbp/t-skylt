"""Entities for boards running the Departures Plus app.

Departures Plus is configured on its own settings page, so Home Assistant only
gets what automations need: power, brightness, which station is shown, the
next departures and the ticker.
"""
import re

from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberMode, RestoreNumber, NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.text import TextEntity
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_TICKER_DURATION

ROTATE_ALL = "Rotate all stations"


class PlusEntity(CoordinatorEntity):
    """Shared device info and naming."""

    def __init__(self, coordinator, key, name, icon=None, category=None):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_plus_{key}"
        self._attr_name = f"T-Skylt {name}"
        if icon:
            self._attr_icon = icon
        if category:
            self._attr_entity_category = category

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.host)},
            name="T-Skylt Board",
            manufacturer="T-Skylt Sweden AB",
            model="Departure Board (Departures Plus)",
            sw_version=self.coordinator.sw_version,
            configuration_url=f"http://{self.coordinator.host}/",
        )

    @property
    def state_data(self) -> dict:
        return self.coordinator.data or {}


class PlusPowerSwitch(PlusEntity, SwitchEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "power", "Display: Power", "mdi:power")

    @property
    def is_on(self):
        return bool(self.state_data.get("power"))

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_value(power=1)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_value(power=0)


class PlusTickerWakeSwitch(PlusEntity, SwitchEntity, RestoreEntity):
    """Whether a ticker message turns a switched-off display on while it runs. Kept in Home Assistant."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ticker_wake", "Ticker: Wake Display", "mdi:monitor-eye", EntityCategory.CONFIG)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self.coordinator.ticker_wake = last.state == "on"

    @property
    def is_on(self):
        return self.coordinator.ticker_wake

    async def async_turn_on(self, **kwargs):
        self.coordinator.ticker_wake = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self.coordinator.ticker_wake = False
        self.async_write_ha_state()


class PlusBrightnessNumber(PlusEntity, NumberEntity):
    _attr_native_min_value = 1
    _attr_native_max_value = 3
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator):
        super().__init__(coordinator, "brightness", "Display: Brightness", "mdi:brightness-6")

    @property
    def native_value(self):
        return self.state_data.get("brightness")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.set_value(brightness=int(value))


class PlusTickerDurationNumber(PlusEntity, RestoreNumber):
    """How long a message sent through the notify entity stays in the ticker. Kept in Home Assistant."""

    _attr_native_min_value = 0
    _attr_native_max_value = 86400
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "s"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator):
        super().__init__(coordinator, "ticker_duration", "Ticker: Message Duration", "mdi:timer-outline", EntityCategory.CONFIG)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self.coordinator.ticker_duration = int(last.native_value)

    @property
    def native_value(self):
        return self.coordinator.ticker_duration

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.ticker_duration = int(value)
        self.async_write_ha_state()


class PlusStationSelect(PlusEntity, SelectEntity):
    """Rotate through all stations, or hold one of them."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "station", "Station: Shown", "mdi:map-marker")

    def _names(self):
        return [s.get("name", "") for s in self.state_data.get("stations", [])]

    @property
    def options(self):
        return [ROTATE_ALL] + self._names()

    @property
    def current_option(self):
        names = self._names()
        pinned = self.state_data.get("pinned", -1)
        return names[pinned] if 0 <= pinned < len(names) else ROTATE_ALL

    async def async_select_option(self, option: str) -> None:
        names = self._names()
        await self.coordinator.set_value(pin=names.index(option) if option in names else -1)


class PlusNextStationButton(PlusEntity, ButtonEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "next_station", "Station: Next", "mdi:skip-next")

    async def async_press(self) -> None:
        await self.coordinator.set_value(next=1)


class PlusCurrentStationSensor(PlusEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "current_station", "Station: Current", "mdi:train")

    @property
    def native_value(self):
        return self.state_data.get("station") or None

    @property
    def extra_state_attributes(self):
        d = self.state_data
        return {"mode": d.get("mode"), "phase": d.get("phase"), "display_on": bool(d.get("shown")),
                "asleep": bool(d.get("asleep")), "woken_by_ticker": bool(d.get("woken")),
                "ticker_messages": d.get("messages", [])}


class PlusDepartureSensor(PlusEntity, SensorEntity):
    """Minutes until the next departure at one station."""

    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, station_name):
        slug = re.sub(r"[^a-z0-9]+", "_", station_name.lower()).strip("_")
        super().__init__(coordinator, f"next_{slug}", f"Next Departure: {station_name}", "mdi:timetable")
        self._station = station_name

    def _entry(self):
        for s in self.state_data.get("stations", []):
            if s.get("name") == self._station:
                return s
        return None

    @property
    def available(self):
        return super().available and self._entry() is not None

    @property
    def native_value(self):
        s = self._entry()
        return s["next"][0]["mins"] if s and s.get("next") else None

    @property
    def extra_state_attributes(self):
        s = self._entry() or {}
        nxt = s.get("next") or []
        first = nxt[0] if nxt else {}
        return {"line": first.get("line"), "destination": first.get("dest"), "source": s.get("source"),
                "operator": s.get("operator"), "status": s.get("status"), "departures": nxt}


class PlusSystemSensor(PlusEntity, SensorEntity):
    """A diagnostic value the board reports: temperature, uptime, Wi-Fi signal."""

    def __init__(self, coordinator, key, name, icon, unit, device_class):
        super().__init__(coordinator, key, f"System: {name}", icon, EntityCategory.DIAGNOSTIC)
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def native_value(self):
        return self.state_data.get(self._key)


class PlusIPSensor(PlusEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator, "active_ip", "System: Active IP", "mdi:ip-network", EntityCategory.DIAGNOSTIC)

    @property
    def native_value(self):
        return self.coordinator._cached_ip


class PlusTickerText(PlusEntity, TextEntity):
    """The ticker text that is always shown. Saved on the board."""

    _attr_native_max = 160

    def __init__(self, coordinator):
        super().__init__(coordinator, "ticker_text", "Ticker: Permanent Text", "mdi:message-text-outline", EntityCategory.CONFIG)

    @property
    def native_value(self):
        return self.state_data.get("ticker_text")

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.save_value(ticker_text=value)


def switches(coordinator):
    return [PlusPowerSwitch(coordinator), PlusTickerWakeSwitch(coordinator)]


def numbers(coordinator):
    return [PlusBrightnessNumber(coordinator), PlusTickerDurationNumber(coordinator)]


def selects(coordinator):
    return [PlusStationSelect(coordinator)]


def buttons(coordinator):
    return [PlusNextStationButton(coordinator)]


def sensors(coordinator):
    stations = (coordinator.data or {}).get("stations", [])
    seen = []
    out = [
        PlusCurrentStationSensor(coordinator),
        PlusIPSensor(coordinator),
        PlusSystemSensor(coordinator, "temperature", "Temperature", "mdi:thermometer", "°C", SensorDeviceClass.TEMPERATURE),
        PlusSystemSensor(coordinator, "uptime", "Uptime", "mdi:clock-outline", "min", SensorDeviceClass.DURATION),
        PlusSystemSensor(coordinator, "rssi", "Wi-Fi Signal", "mdi:wifi", "dBm", SensorDeviceClass.SIGNAL_STRENGTH),
    ]
    for s in stations:
        name = s.get("name", "")
        if name and name not in seen:
            seen.append(name)
            out.append(PlusDepartureSensor(coordinator, name))
    return out


def texts(coordinator):
    return [PlusTickerText(coordinator)]
