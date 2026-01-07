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
        # Wir speichern hier nur noch das Schema, die IP holen wir dynamisch
        self.sw_version = "Unknown"
        
        # Locking to prevent race conditions
        self._lock = asyncio.Lock()
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    async def _resolve_host(self) -> str:
        """Resolve the hostname to an IP address explicitly."""
        # Wenn es schon eine IP ist, einfach zurückgeben
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", self.host):
            return self.host
            
        try:
            # Wir zwingen Python, den Namen jetzt frisch aufzulösen
            # Das läuft im Executor, um den Event-Loop nicht zu blockieren
            return await self.hass.async_add_executor_job(socket.gethostbyname, self.host)
        except Exception as err:
            _LOGGER.warning(f"Could not resolve host {self.host}: {err}")
            # Fallback: Wir geben den Hostnamen zurück und hoffen, dass aiohttp es schafft
            return self.host

    async def _async_update_data(self):
        """Fetch data from the device with locking and retry logic."""
        async with self._lock:
            return await self._fetch_data_internal()

    async def _fetch_data_internal(self):
        """Internal helper to perform the actual fetch with retries."""
        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                # SCHRITT 1: Hostnamen frisch in IP auflösen
                current_ip = await self._resolve_host()
                
                # Wenn wir im Debug-Modus wären, könnte man das loggen:
                # _LOGGER.debug(f"Connecting to {self.host} resolved as {current_ip}")
                
                # URL dynamisch mit der aktuellen IP bauen
                dynamic_url = f"http://{current_ip}/"

                # SCHRITT 2: Anfrage an diese IP senden
                # Wir setzen den 'Host'-Header, falls der Webserver das prüft (meistens egal bei ESP)
                async with aiohttp.ClientSession() as session:
                    with async_timeout.timeout(40):
                        async with session.get(dynamic_url, headers={"Connection": "close", "Host": self.host}) as response:
                            html = await response.text()
                            return self.parse_html(html)

            except Exception as err:
                _LOGGER.warning(f"Attempt {attempt}/{attempts} failed fetching data from {self.host} (IP: {current_ip if 'current_ip' in locals() else 'unknown'}): {err}")
                if attempt == attempts:
                    raise UpdateFailed(f"Error communicating with {self.host}: {err}")
                await asyncio.sleep(2)

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
        """Send command with locking and explicit DNS resolution."""
        
        async with self._lock:
            try:
                # Auch hier: Erst IP auflösen!
                current_ip = await self._resolve_host()
                dynamic_url = f"http://{current_ip}/{parameter}"
                
                async with aiohttp.ClientSession() as session:
                     with async_timeout.timeout(20):
                        await session.get(dynamic_url, headers={"Connection": "close", "Host": self.host})
            except Exception as e:
                _LOGGER.error(f"Error sending command {parameter} to {self.host}: {e}")
