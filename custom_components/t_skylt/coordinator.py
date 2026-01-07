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
TIMEOUT_PROBE = 4       # Seconds for fast connectivity checks (history probing)
RETRY_ATTEMPTS = 3      # Phase 1: How often to retry the current IP
RETRY_DELAY = 2         # Phase 1: Seconds to wait between retries

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
            _LOGGER.debug(f"Setup: Resolving hostname '{self.host}' for the first time...")
            initial_ip = await self._resolve_host()
            self._cached_ip = initial_ip
            self._add_to_history(initial_ip)
            _LOGGER.info(f"Setup: Initialized with IP {self._cached_ip}")
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self):
        """Fetch data from the device."""
        async with self._lock:
            return await self._execute_robust_request(param=None)

    async def send_command(self, parameter):
        """Send command using the same robust logic."""
        async with self._lock:
            # We ignore the return value for commands
            await self._execute_robust_request(param=parameter)

    async def _execute_robust_request(self, param=None):
        """
        Executes a request using the 'Defense in Depth' strategy.
        Phase 1: Gentle Retry (3x on current IP)
        Phase 2: History Check
        Phase 3: DNS Resolution
        Phase 4: Final Attempt
        """
        request_type = "Command" if param else "Status Update"
        target_url_suffix = f"/{param}" if param else "/"
        
        # --- PHASE 1: Gentle Retry on Current IP ---
        # We try the current cached IP multiple times with a cooldown.
        # This handles short WiFi dropouts or device busy states.
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                # Log only on retries to reduce noise on happy path
                if attempt > 1:
                    _LOGGER.info(f"[{request_type}] Phase 1: Retry attempt {attempt}/{RETRY_ATTEMPTS} on {self._cached_ip}...")
                
                result = await self._perform_request(self._cached_ip, timeout=TIMEOUT_FULL, param=param)
                
                # If we succeeded after a retry, log it
                if attempt > 1:
                    _LOGGER.info(f"[{request_type}] Recovered in Phase 1 (Attempt {attempt})!")
                return result

            except Exception as err:
                _LOGGER.warning(f"[{request_type}] Phase 1: Attempt {attempt}/{RETRY_ATTEMPTS} failed on {self._cached_ip}. Error: {err}")
                
                # If this was the last attempt, we move to Phase 2
                if attempt < RETRY_ATTEMPTS:
                    _LOGGER.debug(f"[{request_type}] Waiting {RETRY_DELAY}s before retry...")
                    await asyncio.sleep(RETRY_DELAY)

        # If we are here, Phase 1 failed completely.
        if self._is_static_ip:
             raise UpdateFailed(f"Static IP {self._cached_ip} is unreachable after {RETRY_ATTEMPTS} attempts.")

        # --- PHASE 2: History Fallback ---
        _LOGGER.info(f"[{request_type}] Entering Phase 2: Checking IP History...")
        
        # Iterate over a copy of known IPs
        for fallback_ip in list(self._known_ips):
            if fallback_ip == self._cached_ip:
                continue # Skip the one we just tried 3 times
            
            _LOGGER.debug(f"[{request_type}] Phase 2: Probing history IP {fallback_ip}...")
            try:
                # Use short timeout for probing
                result = await self._perform_request(fallback_ip, timeout=TIMEOUT_PROBE, param=param)
                
                _LOGGER.info(f"[{request_type}] Phase 2 Success! Device found at known IP {fallback_ip}. Updating Cache.")
                self._cached_ip = fallback_ip
                self._add_to_history(fallback_ip)
                return result
            except Exception:
                pass # Silent fail in probe loop

        # --- PHASE 3: DNS Resolution ---
        _LOGGER.info(f"[{request_type}] Entering Phase 3: History exhausted. Resolving Hostname '{self.host}'...")
        try:
            new_ip = await self._resolve_host()
            _LOGGER.info(f"[{request_type}] Phase 3: DNS resolved to {new_ip}.")
        except Exception as dns_err:
            _LOGGER.error(f"[{request_type}] Phase 3: DNS failed: {dns_err}")
            raise UpdateFailed(f"All connection phases failed. DNS Error: {dns_err}")

        # --- PHASE 4: Final Attempt ---
        _LOGGER.info(f"[{request_type}] Entering Phase 4: Final attempt with resolved IP {new_ip}...")
        
        try:
            result = await self._perform_request(new_ip, timeout=TIMEOUT_FULL, param=param)
            
            _LOGGER.info(f"[{request_type}] Phase 4 Success! Connection established on {new_ip}.")
            self._cached_ip = new_ip
            self._add_to_history(new_ip)
            return result
        except Exception as final_err:
            _LOGGER.error(f"[{request_type}] Phase 4 Failed. Device is truly unavailable. Last Error: {final_err}")
            raise UpdateFailed(f"Device unavailable after Phase 4. Last IP tried: {new_ip}")


    async def _perform_request(self, target_ip, timeout=20, param=None):
        """Helper to execute the HTTP request."""
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
                    # For commands, we just ensure the request was sent (status check could be added)
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
