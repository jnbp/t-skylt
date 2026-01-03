"""DataUpdateCoordinator for T-Skylt."""
import logging
import aiohttp
import async_timeout
import re
import urllib.parse
from bs4 import BeautifulSoup
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class TSkyltCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str):
        """Initialize the coordinator."""
        self.host = host
        self.base_url = f"http://{host}/"
        self.sw_version = "Unknown"
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # WICHTIG: Nur noch alle 60 Sekunden abfragen, um CPU zu schonen
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self):
        """Fetch data from the device."""
        try:
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.get(self.base_url) as response:
                        html = await response.text()
                        return self.parse_html(html)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with {self.host}: {err}")

    def parse_html(self, html):
        """Parse HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        data = {}

        def get_value(elem_id, default):
            el = soup.find('input', {'id': elem_id})
            if not el: return default
            val = el.get('value', '').strip()
            if val: return val
            val = el.get('placeholder', '').strip()
            return val if val else default

        # Version
        if self.sw_version == "Unknown":
            version_match = soup.find(string=re.compile(r"v\.\s*\d+\.\d+"))
            if version_match: self.sw_version = version_match.strip()

        # Switches (Checkboxen)
        def is_checked(elem_id):
            el = soup.find('input', {'id': elem_id})
            return el.has_attr('checked') if el else False

        data['onoff'] = is_checked('onoff')
        data['listmode'] = is_checked('abc')
        data['multiple'] = is_checked('multiple')
        data['show_station'] = is_checked('show_my_station')
        data['clocktime'] = is_checked('clocktime')
        data['listcolor'] = is_checked('LISTCOLOR')
        data['fontmini'] = is_checked('FONTMINI')

        # Selects & Inputs
        br_sel = soup.find('select', {'id': 'brightness'})
        data['brightness'] = "0"
        if br_sel:
            opt = br_sel.find('option', selected=True)
            if opt: data['brightness'] = opt['value']

        data['color'] = data.get('color', '0')
        data['power'] = get_value('power', '20')
        data['line_length'] = get_value('line_length', '3')
        data['no_more_departures'] = get_value('no_more_departures', '')
        data['mins'] = get_value('mins', '')

        # Sensors
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
        """Send command ONLY. Do NOT refresh immediately."""
        url = f"{self.base_url}{parameter}"
        _LOGGER.debug(f"Sending command: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                 # Kurzes Timeout, damit HA nicht hängt
                 with async_timeout.timeout(5):
                    await session.get(url)
            # Wir machen hier KEIN refresh mehr!
            # Das verhindert Flackern und CPU Last.
        except Exception as e:
            _LOGGER.error(f"Error sending command {parameter}: {e}")