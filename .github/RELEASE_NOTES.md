# 0.3.0 - Departures Plus

**New** ✨

* ➕ **Departures Plus:** Boards running the Departures Plus app (station rotation, line colors, ticker) are now supported. Setup detects the app automatically, or you choose it under *App on the board*.
* 📣 **Ticker:** Send messages to the board's ticker with the standard `notify.send_message` action (`notify.t_skylt_ticker`). The default duration is 60 seconds and can be changed with the *Ticker: Message Duration* entity.
* 🛠️ **Services:** `t_skylt.ticker_message` (custom duration, replaceable by `message_id`) and `t_skylt.clear_ticker`.
* 🚉 **Entities:** Power, brightness, shown station, next station, current station and one *Next Departure* sensor per station with line, destination and following departures as attributes.

**Unchanged** 🔒

* Boards added before 0.3.0 keep working as legacy boards (stock Departures app) with all their entities.

**Switching a board to Departures Plus**

Start Departures Plus on the board, then remove the board under *Settings -> Devices & Services* and add it again.

Details: [DEPARTURES_PLUS.md](https://github.com/jnbp/t-skylt/blob/main/DEPARTURES_PLUS.md)
