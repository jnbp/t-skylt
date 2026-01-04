"""Select platform for T-Skylt."""
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Operator Mapping
    ops = {
        "sl": "SL (Stockholm)", "vt": "VT (Västtrafik)", "otraf": "Östgötatrafiken",
        "vastmanland": "VL (Västmanlands län)", "dt": "DT (Dalatrafik)", "jlt": "JLT (Jönköpings län)",
        "krono": "KRONO (Kronobergs länstrafik)", "ul": "UL (Uppsala län)", "klt": "KLT (Kalmar länstrafik)",
        "orebro": "Länstrafiken Örebro", "xt": "X-Trafik (Gävleborg)", "varm": "Värmlandstrafik",
        "skane": "Skånetrafiken", "norrbotten": "Norrbotten", "fe": "Trafikverkets färjor", "sj": "SJ (Trafikverket)",
        "hsl": "HSL (Helsinki)", "kb": "Alle operatører (DK)", "no": "Entur (Norway)",
        "sncb": "SNCB (Belgium)", "ns": "Nederlandse Spoorwegen", "ch": "Switzerland",
        "za": "ZET (Zagreb)", "db": "DB (Deutsche Bahn)", "vbb": "VBB (Berlin-Brandenburg)", "vrr": "VRR (Rhein-Ruhr)"
    }

    async_add_entities([
        # Station Group
        TSkyltScreenSelect(coordinator),
        TSkyltCountrySelect(coordinator),
        TSkyltOperatorSelect(coordinator, ops),
        
        # View Group
        TSkyltSelect(coordinator, "scroll", "View: Scroll Speed", {"Normal": "0", "Low": "1"}, "mdi:speedometer-slow"),
        
        # Display Group
        TSkyltSelect(coordinator, "brightness", "Display: Brightness", {"Low": "0", "Medium": "1", "High": "2"}, "mdi:brightness-6"),
        TSkyltSelect(coordinator, "width", "Display: Width", {"XS": "xs", "X": "x", "XL": "xl"}, "mdi:monitor-screenshot"),
        TSkyltSelect(coordinator, "color", "Display: LED Tone", {"Orange": "0", "Yellow": "1", "White": "2"}, "mdi:palette"),
        
        # System Group (using Config Category)
        TSkyltSelect(coordinator, "language", "System: Language", {"English": "en", "Svenska": "se"}, "mdi:translate", EntityCategory.CONFIG),
    ])

class TSkyltSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, key, name, options_map, icon, category=None):
        super().__init__(coordinator)
        self._key = key
        self._name_suffix = name
        self._options_map = options_map
        self._inv_options_map = {v: k for k, v in self._options_map.items()}
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
    def options(self): return list(self._options_map.keys())
    @property
    def current_option(self):
        val = self.coordinator.data.get(self._key, "0")
        return self._inv_options_map.get(str(val), list(self._options_map.keys())[0])
    @property
    def icon(self): return self._icon

    async def async_select_option(self, option: str):
        val = self._options_map[option]
        await self.coordinator.send_command(f"?{self._key}={val}")
        self.coordinator.data[self._key] = val
        self.async_write_ha_state()

class TSkyltScreenSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "T-Skylt Station: Active Config"
        self._attr_unique_id = f"{coordinator.host}_screen_select"
        self._attr_options = ["Station 1", "Station 2"]
        self._attr_icon = "mdi:monitor-dashboard"
        self._current = "Station 1"

    @property
    def current_option(self): return self._current
    @property
    def device_info(self) -> DeviceInfo: return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)

    async def async_select_option(self, option: str):
        val = "1" if option == "Station 1" else "2"
        await self.coordinator.send_command(f"?screen={val}")
        self._current = option
        self.async_write_ha_state()

class TSkyltCountrySelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "T-Skylt Station: Country"
        self._attr_unique_id = f"{coordinator.host}_country"
        self._map = {
            "Sweden 🇸🇪": "se", "Germany 🇩🇪": "de", "Finland 🇫🇮": "fi", 
            "Denmark 🇩🇰": "dk", "Norway 🇳🇴": "no", "Belgium 🇧🇪": "be", 
            "Netherlands 🇳🇱": "nl", "Switzerland 🇨🇭": "ch", "Croatia 🇭🇷": "cr"
        }
        self._attr_options = list(self._map.keys())
        self._attr_icon = "mdi:flag"

    @property
    def current_option(self): return None
    @property
    def device_info(self) -> DeviceInfo: return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)

    async def async_select_option(self, option: str):
        val = self._map[option]
        await self.coordinator.send_command(f"?country={val}")

class TSkyltOperatorSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, options_map):
        super().__init__(coordinator)
        self._attr_name = "T-Skylt Station: Operator"
        self._attr_unique_id = f"{coordinator.host}_operator"
        self._options_map = options_map
        self._inv_map = {v: k for k, v in options_map.items()}
        self._attr_options = sorted(list(options_map.values()))
        self._attr_icon = "mdi:train-car"

    @property
    def current_option(self):
        detected = self.coordinator.data.get('operator_display', '').lower()
        if not detected: return None
        if detected in self._options_map: return self._options_map[detected]
        for name in self._attr_options:
            if detected.upper() in name.upper(): return name
        return None

    @property
    def device_info(self) -> DeviceInfo: return DeviceInfo(identifiers={(DOMAIN, self.coordinator.host)}, name="T-Skylt Board", manufacturer="T-Skylt Sweden AB", model="Departure Board", sw_version=self.coordinator.sw_version)

    async def async_select_option(self, option: str):
        val = self._inv_map.get(option)
        if val:
            await self.coordinator.send_command(f"?operator={val}")
            self.coordinator.data['operator_display'] = val
            self.async_write_ha_state()