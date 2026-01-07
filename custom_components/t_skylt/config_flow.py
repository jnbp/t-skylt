"""Config flow for T-Skylt integration."""
import logging
import voluptuous as vol
import aiohttp
import async_timeout

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class TSkyltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for T-Skylt."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            
            # Simple validation: Check if we can reach the device
            try:
                # Resolve host logic logic is in coordinator, but simple check here:
                url = f"http://{host}/"
                async with aiohttp.ClientSession() as session:
                    with async_timeout.timeout(10):
                        async with session.get(url) as response:
                            if response.status != 200:
                                errors["base"] = "cannot_connect"
                            else:
                                # Connection successful
                                await self.async_set_unique_id(host)
                                self._abort_if_unique_id_configured()
                                return self.async_create_entry(title=host, data=user_input)
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                # HIER ist die Änderung: default value gesetzt
                vol.Required(CONF_HOST, default="esp32-s3-zero.local"): str,
            }),
            errors=errors,
        )