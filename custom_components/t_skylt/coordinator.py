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

# --- Configuration Constants ---
MAX_HISTORY_IPS = 5     # Maximum number of IPs to remember
TIMEOUT_FULL = 20       # Seconds for standard data fetching
TIMEOUT_PROBE = 4       # Seconds for fast connectivity checks
RETRY_ATTEMPTS = 3      # Attempts on current IP before fallback
RETRY_DELAY = 2         # Seconds between retries

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
        
        # HISTORY: Store successful IPs
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
        return bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host_str))

    async def _resolve_host(self) -> str:
        if self._is_static_ip:
            return self.host
        try:
            return await self.hass.async_add_executor_job(socket.gethostbyname, self.host)
        except Exception as err:
            _LOGGER.warning(f"DNS Resolution failed for {self.host}: {err}")
            return self.host

    def _add_to_history(self, ip):
        if ip in self._known_ips:
            self._known_ips.remove(ip)
        self._known_ips.appendleft(ip)

    async def async_config_entry_first_refresh(self):
        if not self._is_static_ip:
            _LOGGER.info(f"Setup: Resolving hostname '{self.host}'...")
            initial_ip = await self._resolve_host()
            self._cached_ip = initial_ip
            self._add_to_history(initial_ip)
            _LOGGER.info(f"Setup: Initialized with IP {self._cached_ip}")
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self):
        async with self._lock:
            return await self._execute_robust_request(param=None)

    async def send_command(self, parameter):
        async with self._lock:
            await self._execute_robust_request(param=parameter)

    async def _execute_robust_request(self, param=None):
        request_type = "Command" if param else "Status Update"
        
        # --- PHASE 1: Gentle Retry ---
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                # Log detailed error context
                result = await self._perform_request(self._cached_ip, timeout=TIMEOUT_FULL, param=param)
                if attempt > 1: 
                     _LOGGER.info(f"[{request_type}] RECOVERED in Phase 1 (Attempt {attempt}) on {self._cached_ip}!")
                return result
            except Exception as err:
                err_msg = str(err) or "Timeout/Unreachable"
                _LOGGER.warning(f"[{request_type}] Phase 1: Attempt {attempt}/{RETRY_ATTEMPTS} failed on {self._cached_ip}. Error: {err_msg}")
                
                if attempt < RETRY_ATTEMPTS:
                    await asyncio.sleep(RETRY_DELAY)

        if self._is_static_ip:
             raise UpdateFailed(f"Static IP {self._cached_ip} is unreachable.")

        # --- PHASE 2: History Fallback ---
        history_list = list(self._known_ips)
        _LOGGER.warning(f"[{request_type}] Entering Phase 2. Checking History: {history_list}")
        
        for fallback_ip in history_list:
            if fallback_ip == self._cached_ip: 
                continue # Skip the one we just tried
            
            _LOGGER.warning(f"[{request_type}] Phase 2: Probing history IP {fallback_ip}...")
            try:
                result = await self._perform_request(fallback_ip, timeout=TIMEOUT_PROBE, param=param)
                _LOGGER.warning(f"[{request_type}] Phase 2 SUCCESS! Device found at {fallback_ip}. Switching IP.")
                self._cached_ip = fallback_ip
                self._add_to_history(fallback_ip)
                return result
            except Exception as hist_err: 
                _LOGGER.warning(f"[{request_type}] Phase 2: Probe failed on {fallback_ip}.")

        # --- PHASE 3: DNS Resolution ---
        _LOGGER.warning(f"[{request_type}] Entering Phase 3: History exhausted. Resolving DNS for '{self.host}'...")
        try:
            new_ip = await self._resolve_host()
            _LOGGER.warning(f"[{request_type}] Phase 3 Result: DNS returned {new_ip}")
        except Exception as dns_err:
            raise UpdateFailed(f"DNS failed: {dns_err}")

        # --- PHASE 4: Final Attempt ---
        _LOGGER.warning(f"[{request_type}] Entering Phase 4: Final try on {new_ip} with full timeout...")
        try:
            result = await self._perform_request(new_ip, timeout=TIMEOUT_FULL, param=param)
            _LOGGER.info(f"[{request_type}] Phase 4 SUCCESS! Connection established on {new_ip}")
            self._cached_ip = new_ip
            self._add_to_history(new_ip)
            return result
        except Exception as final_err:
            raise UpdateFailed(f"Device unavailable after Phase 4. Last IP tried: {new_ip}. Error: {final_err}")

    async def _perform_request(self, target_ip, timeout=20, param=None):
        url = f"http://{target_ip}/"
        if param: url = f"http://{target_ip}/{param}"

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(timeout):
                async with session.get(url, headers={"Connection": "close", "Host": self.host}) as response:
                    if param is None:
                        html = await response.text()
                        return self.parse_html(html)
                    if response.status >= 400:
                        raise Exception(f"HTTP Error {response.status}")
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

        # --- Operator Parsing ---
        # Look for label for="operator" and find the button inside
        op_label = soup.find('label', {'for': 'operator'})
        data['operator'] = "be" # Default
        if op_label:
            btn = op_label.find_next('button', class_='dropbtn')
            if btn:
                # Text is like "▼ BE"
                raw_text = btn.get_text().strip()
                clean_op = re.sub(r'[^a-zA-Z]+', '', raw_text).lower()
                data['operator'] = clean_op

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

        # Parsing Max Departures: Try SELECT first (correct per HTML), fallback to INPUT
        data['maxdest'] = '5'
        max_sel = soup.find('select', {'id': 'maxdest'})
        if max_sel:
             opt = max_sel.find('option', selected=True)
             if opt: data['maxdest'] = opt['value']
        else:
             data['maxdest'] = get_value('maxdest', '5')
        
        # Parsing Offset: Try SELECT first
        data['offset'] = '0'
        off_sel = soup.find('select', {'id': 'offset'})
        if off_sel:
            opt = off_sel.find('option', selected=True)
            if opt: data['offset'] = opt['value']
        else:
            data['offset'] = get_value('offset', '0')

        # Parsing hidden values or text inputs
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