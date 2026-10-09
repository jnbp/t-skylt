"""Coordinator for boards running the Departures Plus app.

Departures Plus has a JSON API, so nothing is scraped here. The connection
handling (retries, IP history, DNS fallback) is inherited from the legacy
coordinator unchanged.
"""
import asyncio
import json
import logging
import urllib.parse
from datetime import timedelta

import aiohttp

from homeassistant.core import HomeAssistant

from .const import DEFAULT_TICKER_DURATION, PLUS_APP_ID
from .coordinator import TSkyltCoordinator

_LOGGER = logging.getLogger(__name__)

PLUS_POLLING_INTERVAL = 30  # seconds


class TSkyltPlusCoordinator(TSkyltCoordinator):
    """Polls /api/state and sends /api/set and /api/message commands."""

    is_plus = True

    def __init__(self, hass: HomeAssistant, host: str):
        super().__init__(hass, host)
        self.update_interval = timedelta(seconds=PLUS_POLLING_INTERVAL)
        self.ticker_duration = DEFAULT_TICKER_DURATION
        self.ticker_wake = True

    async def _perform_request(self, target_ip, timeout=20, param=None):
        url = f"http://{target_ip}/{param or 'api/state'}"
        async with aiohttp.ClientSession() as session:
            async with asyncio.timeout(timeout):
                async with session.get(url, headers={"Connection": "close", "Host": self.host}) as response:
                    if response.status >= 400:
                        raise Exception(f"HTTP Error {response.status}")
                    text = await response.text()
                    if param is not None:
                        return True
                    try:
                        data = json.loads(text)
                    except ValueError as err:
                        raise Exception("Departures Plus is not running on the board") from err
                    if data.get("app") != PLUS_APP_ID:
                        raise Exception("Departures Plus is not running on the board")
                    self.sw_version = str(data.get("version", "Unknown"))
                    return data

    async def set_value(self, **values):
        """Change runtime settings, e.g. set_value(power=0). Not written to the board's flash."""
        await self.send_command("api/set?" + urllib.parse.urlencode(values))
        await self.async_refresh()

    async def save_value(self, **values):
        """Change settings and store them on the board."""
        values["save"] = 1
        await self.set_value(**values)

    async def send_ticker(self, message: str, duration=None, message_id=None, wake=None):
        """Show a ticker message. duration in seconds, 0 keeps it until cleared.

        wake turns a switched-off display on for as long as the message runs.
        """
        ttl = self.ticker_duration if duration is None else int(duration)
        query = {"text": message, "ttl": int(ttl)}
        if message_id:
            query["id"] = message_id
        if self.ticker_wake if wake is None else wake:
            query["wake"] = 1
        await self.send_command("api/message?" + urllib.parse.urlencode(query, quote_via=urllib.parse.quote))
        await self.async_refresh()

    async def clear_ticker(self, message_id=None):
        query = {"clear": 1}
        if message_id:
            query["id"] = message_id
        await self.send_command("api/message?" + urllib.parse.urlencode(query, quote_via=urllib.parse.quote))
        await self.async_refresh()
