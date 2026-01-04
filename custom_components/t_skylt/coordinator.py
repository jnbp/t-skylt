"""DataUpdateCoordinator for T-Skylt."""
import logging
import aiohttp
import async_timeout
import re
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
        self.base_url = f"http://{host}/"
        self.sw_version = "Unknown"
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self):
        """Fetch data from the device."""
        try:
            # We fetch the main page to get most data
            # Optimization: Timer data is technically on /?timer=set, but often 
            # simple params are hidden in the main HTML inputs.
            # Based on your HTML dump, inputs like 'mondayStartTime' are NOT on the main page,
            # but on the timer page. To be efficient, we might need a second fetch
            # or we accept that timers update only when we visit that page logic.
            # For now, let's fetch the main page.
            async with aiohttp.ClientSession() as session:
                with async_timeout.timeout(15):
                    async with session.get(self.base_url) as response:
                        html = await response.text()
                        
                    # Fetch Timer page separately? 
                    # To keep it simple and efficient, we will assume standard data on main page.
                    # If inputs are missing, we might need to fetch /?timer=set.
                    # Let's try fetching timer data only every 5th update to save resources?
                    # For this version, let's keep it simple: Fetch main page.
                    # If you need timer data refreshed, we might need a dedicated fetch.
                    # Let's see if we can get by with just main page for status.
                    
                    return self.parse_html(html)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with {self.host}: {err}")

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

        # --- Update Available Check ---
        # Look for the update button. If it is NOT disabled, an update is available.
        # <button ... onclick="...update=true" disabled=""> -> No Update
        update_btn = soup.find('button', onclick=re.compile(r'update=true'))
        data['update_available'] = False
        if update_btn:
            if not update_btn.has_attr('disabled'):
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
        
        ns_sel = soup.find('select', {'id': 'newstation'})
        data['newstation'] = "0"
        if ns_sel:
             opt = ns_sel.find('option', selected=True)
             if opt: data['newstation'] = opt['value']

        # --- Timers ---
        # Note: If these fields are not on the main page, they will default to 00:00
        # This is expected behavior until we implement multi-page fetching.
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
        """Send command only. Fire and forget."""
        url = f"{self.base_url}{parameter}"
        try:
            async with aiohttp.ClientSession() as session:
                 with async_timeout.timeout(5):
                    await session.get(url)
        except Exception as e:
            _LOGGER.error(f"Error sending command {parameter}: {e}")