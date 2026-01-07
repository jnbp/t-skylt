"""DataUpdateCoordinator for T-Skylt."""
import logging
import asyncio
import aiohttp
import async_timeout
import re
import socket
from bs4 import BeautifulSoup
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class TSkyltCoordinator(DataUpdateCoordinator):
    """Class to manage fetching T-Skylt data."""

    def __init__(self, hass: HomeAssistant, host: str):
        """Initialize the coordinator."""
        self.host = host
        self.sw_version = "Unknown"
        self._lock = asyncio.Lock()

        # LOGIC: Check if input is a static IP or a hostname
        self._is_static_ip = self._is_valid_ip(host)
        
        # We store the IP we want to talk to here.
        # If static, it's the host. If hostname, it's the resolved IP.
        self._cached_ip = host 

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    def _is_valid_ip(self, host_str: str) -> bool:
        """Check if the string is a valid IP address."""
        return bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host_str))

    async def _resolve_host(self) -> str:
        """Resolve hostname to IP. Only called on init or error."""
        if self._is_static_ip:
            return self.host
        
        try:
            return await self.hass.async_add_executor_job(socket.gethostbyname, self.host)
        except Exception as err:
            _LOGGER.warning(f"DNS Resolution failed for {self.host}: {err}")
            return self.host # Fallback to hostname if DNS fails

    async def async_config_entry_first_refresh(self):
        """Custom first refresh to resolve IP initially."""
        if not self._is_static_ip:
            self._cached_ip = await self._resolve_host()
            _LOGGER.debug(f"Initial resolution: {self.host} -> {self._cached_ip}")
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self):
        """Fetch data from the device."""
        async with self._lock:
            return await self._fetch_data_internal()

    async def _fetch_data_internal(self):
        """Smart Fetch: Try cached IP -> Fail -> Re-resolve -> Retry."""
        
        # Versuch 1: Mit der bekannten IP (Cached)
        try:
            return await self._perform_request(self._cached_ip)
        except Exception as err:
            # Wenn wir eine statische IP haben, ist hier Ende.
            if self._is_static_ip:
                raise UpdateFailed(f"Connection failed to static IP {self._cached_ip}: {err}")

            # RETTUNGSSCHIRM (Smart Recovery)
            # Verbindung fehlgeschlagen & wir nutzen Hostname -> Neu auflösen!
            _LOGGER.warning(f"Connection to cached IP {self._cached_ip} failed. Re-resolving hostname '{self.host}'...")
            
            try:
                new_ip = await self._resolve_host()
                
                if new_ip == self._cached_ip:
                    # DNS hat immer noch die alte IP -> Echter Netzwerkfehler
                    raise UpdateFailed(f"Host {self.host} still resolves to {new_ip}, but is unreachable: {err}")
                
                # Wir haben eine neue IP! Cache updaten und nochmal versuchen.
                _LOGGER.info(f"Host moved! Updating IP cache: {self._cached_ip} -> {new_ip}")
                self._cached_ip = new_ip
                
                # Versuch 2: Mit neuer IP
                return await self._perform_request(self._cached_ip)
                
            except Exception as retry_err:
                raise UpdateFailed(f"Recovery failed for {self.host}: {retry_err}")

    async def _perform_request(self, target_ip):
        """Helper to execute the actual HTTP request."""
        url = f"http://{target_ip}/"
        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(20): # 20s Timeout
                async with session.get(url, headers={"Connection": "close", "Host": self.host}) as response:
                    html = await response.text()
                    return self.parse_html(html)

    def parse_html(self, html):
        """Parse HTML content to extract state."""
        soup = BeautifulSoup(html, 'html.parser')
        data = {}

        def get_value(elem_id, default):
            el = soup.find('input', {'id': elem_id})
            if not el: return default
            val = el.get('value', '').strip()
            if val: return val
            val = el.get('placeholder', '').strip()
            return val if val else default

        def is_checked(elem_id):
            el = soup.find('input', {'id': elem_id})
            return el.has_attr('checked') if el else False

        # --- General Info ---
        if self.sw_version == "Unknown":
            version_match = soup.find(string=re.compile(r"v\.\s*\d+\.\d+"))
            if version_match: self.sw_version = version_match.strip()

        # --- Update Available ---
        update_btn = soup.find('button', onclick=re.compile(r'update=true'))
        data['update_available'] = False
        if update_btn and not update_btn.has_attr('disabled'):
            data['update_available'] = True

        # --- Operator ---
        dropbtn = soup.find('button', class_='dropbtn')
        if dropbtn:
            raw_text = dropbtn.get_text().strip()
            clean_op = re.sub(r'^[^a-zA-Z0-9]+', '', raw_text).strip()
            data['operator_display'] = clean_op

        # --- Switches ---
        data['onoff'] = is_checked('onoff')
        data['listmode'] = is_checked('abc')
        data['multiple'] = is_checked('multiple')
        data['show_station'] = is_checked('show_my_station')
        data['clocktime'] = is_checked('clocktime')
        data['listcolor'] = is_checked('LISTCOLOR')
        data['fontmini'] = is_checked('FONTMINI')
        data['sleep'] = is_checked('sleep')
        
        # Types
        data['type_metro'] = is_checked('METRO')
        data['type_bus'] = is_checked('BUS')
        data['type_train'] = is_checked('TRAIN')
        data['type_tram'] = is_checked('TRAM')
        data['type_ship'] = is_checked('SHIP')

        # --- Selects & Inputs ---
        br_sel = soup.find('select', {'id': 'brightness'})
        data['brightness'] = "0"
        if br_sel:
            opt = br_sel.find('option', selected=True)
            if opt: data['brightness'] = opt['value']
            
        scroll_sel = soup.find('select', {'id': 'scroll'})
        data['scroll'] = "0"
        if scroll_sel:
            opt = scroll_sel.find('option', selected=True)
            if opt: data['scroll'] = opt['value']

        data['maxdest'] = get_value('maxdest', '5')
        
        data['offset'] = get_value('offset', '0') 
        off_sel = soup.find('select', {'id': 'offset'})
        if off_sel:
            opt = off_sel.find('option', selected=True)
            if opt: data['offset'] = opt['value']

        data['power'] = get_value('power', '20')
        data['line_length'] = get_value('line_length', '3')
        data['no_more_departures'] = get_value('no_more_departures', '')
        data['mins'] = get_value('mins', '')
        data['user'] = get_value('user', '')

        # --- Timers ---
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            data[f'{day}_start'] = get_value(f'{day}StartTime', '00:00')
            data[f'{day}_end'] = get_value(f'{day}EndTime', '00:00')

        # --- Sensors ---
        temp_label = soup.find('b', string=re.compile("System temperature"))
        if temp_label:
            temp_td = temp_label.find_next('td')
            if temp_td:
                match = re.search(r"(\d+)", temp_td.text)
                data['temperature'] = int(match.group(1)) if match else None

        uptime_label = soup.find('b', string=re.compile("Uptime"))
        if uptime_label:
            uptime_td = uptime_label.find_next('td')
            if uptime_td:
                match = re.search(r"(\d+)", uptime_td.text)
                data['uptime'] = int(match.group(1)) if match else None

        return data

    async def send_command(self, parameter):
        """Send command with locking and smart IP cache."""
        async with self._lock:
            try:
                # Nutze cached IP
                target_ip = self._cached_ip
                url = f"http://{target_ip}/{parameter}"
                
                async with aiohttp.ClientSession() as session:
                     with async_timeout.timeout(20):
                        await session.get(url, headers={"Connection": "close", "Host": self.host})
            
            except Exception as e:
                # Auch beim Senden: Wenn es fehlschlägt und wir Hostname nutzen -> Versuch neu aufzulösen
                if not self._is_static_ip:
                     _LOGGER.warning(f"Command failed on {self._cached_ip}, trying re-resolve...")
                     try:
                         new_ip = await self._resolve_host()
                         if new_ip != self._cached_ip:
                             self._cached_ip = new_ip
                             # Retry mit neuer IP
                             url = f"http://{new_ip}/{parameter}"
                             async with aiohttp.ClientSession() as session:
                                with async_timeout.timeout(20):
                                    await session.get(url, headers={"Connection": "close", "Host": self.host})
                             return # Success
                     except:
                         pass # Wenn Retry auch schiefgeht, loggen wir den originalen Fehler unten
                
                _LOGGER.error(f"Error sending command {parameter} to {self.host} (IP: {self._cached_ip}): {e}")