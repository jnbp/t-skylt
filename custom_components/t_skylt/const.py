"""Constants for the T-Skylt integration."""
DOMAIN = "t_skylt"
CONF_HOST = "host"

# Which app runs on the board. Entries created before 0.3.0 have no mode and are legacy.
CONF_MODE = "mode"
MODE_AUTO = "auto"
MODE_LEGACY = "legacy"
MODE_PLUS = "plus"

PLUS_APP_ID = "departuresplus"
DEFAULT_TICKER_DURATION = 60  # seconds a notify message stays in the ticker

SERVICE_TICKER_MESSAGE = "ticker_message"
SERVICE_CLEAR_TICKER = "clear_ticker"
