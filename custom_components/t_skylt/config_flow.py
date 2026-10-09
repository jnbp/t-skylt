"""Config flow for T-Skylt integration."""
import asyncio
import json
import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import DOMAIN, CONF_MODE, MODE_AUTO, MODE_LEGACY, MODE_PLUS, PLUS_APP_ID

_LOGGER = logging.getLogger(__name__)


async def _probe(host: str):
    """Returns (reachable, runs_departures_plus)."""
    async with aiohttp.ClientSession() as session:
        try:
            async with asyncio.timeout(10):
                async with session.get(f"http://{host}/api/state", headers={"Connection": "close"}) as response:
                    if response.status == 200:
                        try:
                            if json.loads(await response.text()).get("app") == PLUS_APP_ID:
                                return True, True
                        except ValueError:
                            pass
        except Exception:  # noqa: BLE001 - any failure just means "not Departures Plus"
            pass
        try:
            async with asyncio.timeout(10):
                async with session.get(f"http://{host}/", headers={"Connection": "close"}) as response:
                    return response.status == 200, False
        except Exception:  # noqa: BLE001
            return False, False


class TSkyltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for T-Skylt."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            mode = user_input.get(CONF_MODE, MODE_AUTO)
            reachable, is_plus = await _probe(host)
            if not reachable:
                errors["base"] = "cannot_connect"
            elif mode == MODE_PLUS and not is_plus:
                errors["base"] = "plus_not_running"
            else:
                if mode == MODE_AUTO:
                    mode = MODE_PLUS if is_plus else MODE_LEGACY
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=host, data={CONF_HOST: host, CONF_MODE: mode})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default="esp32-s3-zero.local"): str,
                vol.Required(CONF_MODE, default=MODE_AUTO): SelectSelector(SelectSelectorConfig(
                    options=[MODE_AUTO, MODE_LEGACY, MODE_PLUS],
                    translation_key="mode",
                    mode=SelectSelectorMode.DROPDOWN,
                )),
            }),
            errors=errors,
        )
