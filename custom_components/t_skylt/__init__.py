"""The T-Skylt integration."""
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN, CONF_MODE, MODE_PLUS, SERVICE_TICKER_MESSAGE, SERVICE_CLEAR_TICKER, SERVICE_SET_ICON,
)
from .coordinator import TSkyltCoordinator
from .plus_coordinator import TSkyltPlusCoordinator

_LOGGER = logging.getLogger(__name__)

# Registered platforms
PLATFORMS = ["switch", "select", "number", "sensor", "binary_sensor", "text", "button"]
# The Departures Plus app is configured on the board itself, so it needs fewer entities.
PLUS_PLATFORMS = ["switch", "select", "number", "sensor", "text", "button", "notify"]

TICKER_MESSAGE_SCHEMA = vol.Schema({
    vol.Required("message"): cv.string,
    vol.Optional("duration"): vol.All(vol.Coerce(int), vol.Range(min=0, max=86400)),
    vol.Optional("message_id"): cv.string,
    vol.Optional("wake"): cv.boolean,
    vol.Optional("config_entry_id"): cv.string,
})
SET_ICON_SCHEMA = vol.Schema({
    vol.Required("place"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
    vol.Optional("icon", default=""): cv.string,
    vol.Optional("color", default=""): cv.string,
    vol.Optional("config_entry_id"): cv.string,
})
CLEAR_TICKER_SCHEMA = vol.Schema({
    vol.Optional("message_id"): cv.string,
    vol.Optional("config_entry_id"): cv.string,
})


def _platforms(entry: ConfigEntry):
    return PLUS_PLATFORMS if entry.data.get(CONF_MODE) == MODE_PLUS else PLATFORMS


def _plus_coordinators(hass: HomeAssistant, call: ServiceCall):
    """The Departures Plus boards a service call is aimed at: one by id, or all of them."""
    boards = {eid: c for eid, c in hass.data.get(DOMAIN, {}).items() if getattr(c, "is_plus", False)}
    wanted = call.data.get("config_entry_id")
    if wanted:
        if wanted not in boards:
            raise ServiceValidationError(f"No Departures Plus board with config entry id {wanted}")
        return [boards[wanted]]
    if not boards:
        raise ServiceValidationError("No Departures Plus board is set up")
    return list(boards.values())


def _register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_TICKER_MESSAGE):
        return

    async def ticker_message(call: ServiceCall) -> None:
        for coordinator in _plus_coordinators(hass, call):
            await coordinator.send_ticker(
                call.data["message"], call.data.get("duration"), call.data.get("message_id"), call.data.get("wake")
            )

    async def clear_ticker(call: ServiceCall) -> None:
        for coordinator in _plus_coordinators(hass, call):
            await coordinator.clear_ticker(call.data.get("message_id"))

    hass.services.async_register(DOMAIN, SERVICE_TICKER_MESSAGE, ticker_message, schema=TICKER_MESSAGE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_TICKER, clear_ticker, schema=CLEAR_TICKER_SCHEMA)

    async def set_icon(call: ServiceCall) -> None:
        for coordinator in _plus_coordinators(hass, call):
            await coordinator.set_icon(call.data["place"], call.data.get("icon", ""), call.data.get("color", ""))

    hass.services.async_register(DOMAIN, SERVICE_SET_ICON, set_icon, schema=SET_ICON_SCHEMA)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up T-Skylt from a config entry."""
    if entry.data.get(CONF_MODE) == MODE_PLUS:
        coordinator = TSkyltPlusCoordinator(hass, entry.data["host"])
    else:
        coordinator = TSkyltCoordinator(hass, entry.data["host"])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, _platforms(entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _platforms(entry))
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_TICKER_MESSAGE)
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_TICKER)
            hass.services.async_remove(DOMAIN, SERVICE_SET_ICON)
    return unload_ok
