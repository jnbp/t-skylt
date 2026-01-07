"""DataUpdateCoordinator for T-Skylt."""
import logging
import asyncio
import aiohttp
import async_timeout
import re
import socket
from collections import deque
from bs4 import BeautifulSoup
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Configuration constants
MAX_HISTORY_IPS = 5     # Maximum number of IPs to remember
TIMEOUT_FULL = 20       # Seconds for standard data fetching
TIMEOUT_PROBE = 4       # Seconds for fast connectivity checks (history probing)

class TSkyltCoordinator(DataUpdateCoordinator):
    """Class to manage fetching T-Skylt data."""

    def __init__(self, hass: HomeAssistant, host: str):
        """Initialize the coordinator."""
        self.host = host
        self.sw_version = "Unknown"
        self._lock = asyncio.Lock()

        # LOGIC: Check if input is a static IP or a hostname
        self._is_static_ip = self._is_valid_ip(host)
        
        # Current active IP used for communication
        self._cached_ip = host
        
        # HISTORY: Store successful IPs to bypass stale DNS records.
        # Using deque with maxlen ensures the list never grows infinitely.
        if self._is_static_ip:
            self._known_ips = deque([host], maxlen=MAX_HISTORY_IPS)
        else:
            self._known_ips = deque(maxlen=MAX_HISTORY_IPS)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    def _is_valid_ip(self, host_str: str) -> bool:
        """Check if the string is a valid IPv4 address."""
        return bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host_str))

    async def _resolve_host(self) -> str:
        """Resolve hostname to IP address."""
        if self._is_static_ip:
            return self.host
        try:
            return await self.hass.async_add_executor_job(socket.gethostbyname, self.host)
        except Exception as err:
            _LOGGER.warning(f"DNS Resolution failed for {self.host}: {err}")
            return self.host

    def _add_to_history(self, ip):
        """Add IP to history, moving it to the front (most recent)."""
        if ip in self._known_ips:
            self._known_ips.remove(ip) # Remove to re-add at front
        self._known_ips.appendleft(ip) # Add to front (newest)

    async def async_config_entry_first_refresh(self):
        """Custom first refresh to resolve IP initially."""
        if not self._is_static_ip:
            initial_ip = await self._resolve_host()
            self._cached_ip = initial_ip
            self._add_to_history(initial_ip)
            _LOGGER.debug(f"Initial resolution: {self.host} -> {self._cached_ip}")
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self):
        """Fetch data from the device."""
        async with self._lock:
            return await self._fetch_data_internal()

    async def _fetch_data_internal(self):
        """Fetch data using History-Fallback Logic."""
        
        # 1. Try current cached IP (Full Timeout)
        try:
            return await self._perform_request(self._cached_ip, timeout=TIMEOUT_FULL)
        except Exception:
            # If a static IP fails, there is no fallback
            if self._is_static_ip:
                raise UpdateFailed(f"Connection failed to static IP {self._cached_ip}")

            _LOGGER.warning(f"Connection to cached IP {self._cached_ip} failed. Probing history...")

            # 2. HISTORY FALLBACK: Try other known IPs (Fast Timeout)
            # Iterate over a list copy to avoid modification issues
            for fallback_ip in list(self._known_ips):
                if fallback_ip == self._cached_ip:
                    continue # Skip the one we just tried
                
                _LOGGER.debug(f"Probing fallback IP: {fallback_ip}...")
                try:
                    # Short timeout for probing!
                    data = await self._perform_request(fallback_ip, timeout=TIMEOUT_PROBE)
                    
                    # Success! Update current cache & history order
                    _LOGGER.info(f"Fallback successful! Switching active IP to {fallback_ip}")
                    self._cached_ip = fallback_ip
                    self._add_to_history(fallback_ip)
                    return data
                except Exception:
                    continue # This IP is also dead, try next

            # 3. DNS RESOLUTION (Last Resort)
            _LOGGER.info(f"History failed. Re-resolving hostname '{self.host}'...")
            try:
                new_ip = await self._resolve_host()
                
                # Prevent trying the same broken IP again if DNS is stale and we just probed it
                if new_ip == self._cached_ip:
                     raise UpdateFailed(f"DNS returned same stale IP {new_ip} which is unreachable.")
                
                _LOGGER.info(f"DNS resolved new IP: {new_ip}. Trying...")
                data = await self._perform_request(new_ip, timeout=TIMEOUT_FULL)
                
                # Success!
                self._cached_ip = new_ip
                self._add_to_history(new_ip)
                return data

            except Exception as final_err:
                raise UpdateFailed(f"All connection attempts failed. Last error: {final_err}")

    async def _perform_request(self, target_ip, timeout=20, param=None):
        """Helper to execute the request with variable timeout."""
        url = f"http://{target_ip}/"
        if param:
             url = f"http://{target_ip}/{param}"

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(timeout):
                async with session.get(url, headers={"Connection": "close", "Host": self.host}) as response:
                    # Only parse HTML if we are fetching data (param is None)
                    if param is None:
                        html = await response.text()
                        return self.parse_html(html)
                    return None

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
        """Send command with smart fallback."""
        async with self._lock:
            try:
                # 1. Try Cached IP (Full Timeout)
                await self._perform_request(self._cached_ip, timeout=TIMEOUT_FULL, param=parameter)
            
            except Exception:
                # If fail, try known IPs (History) - Fast Timeout
                if not self._is_static_ip:
                     for fallback_ip in list(self._known_ips):
                         if fallback_ip == self._cached_ip: continue
                         try:
                             # Probe with command
                             await self._perform_request(fallback_ip, timeout=TIMEOUT_PROBE, param=parameter)
                             
                             # Success! Switch cache
                             _LOGGER.info(f"Command fallback successful! Active IP is now {fallback_ip}")
                             self._cached_ip = fallback_ip
                             self._add_to_history(fallback_ip)
                             return
                         except:
                             pass
                _LOGGER.error(f"Failed to send command {parameter}")