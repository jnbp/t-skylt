"""Config flow for T-Skylt."""
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_HOST

class TSkyltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=f"T-Skylt ({user_input[CONF_HOST]})", 
                data=user_input
            )

        # Schema with explicit Label "IP Address"
        data_schema = vol.Schema({
            vol.Required(CONF_HOST, description="IP Address (e.g., 192.168.1.50)"): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"device_name": "T-Skylt Board"},
        )