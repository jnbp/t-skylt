"""Notify platform for T-Skylt: the Departures Plus ticker."""
from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .plus import PlusEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the ticker notify entity (Departures Plus boards only)."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if getattr(coordinator, "is_plus", False):
        async_add_entities([TSkyltTickerNotify(coordinator)])


class TSkyltTickerNotify(PlusEntity, NotifyEntity):
    """notify.send_message puts a text into the ticker for the default duration."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "ticker", "Ticker", "mdi:message-flash-outline")

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        text = f"{title}: {message}" if title else message
        await self.coordinator.send_ticker(text)
