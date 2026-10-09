# Departures Plus

Since 0.3.0 the integration also supports boards running **Departures Plus**, an alternative departures app for the MatrixBOX firmware with station rotation, line colors and a ticker.

When you add a board, the integration detects which app is running. You can also choose it yourself under **App on the board**:

| Choice | Meaning |
| --- | --- |
| **Detect automatically** | Recommended. Departures Plus is recognized by its API. |
| **Legacy (stock Departures app)** | Everything described in the [README](README.md). Boards added before 0.3.0 keep working as legacy boards without any change. |
| **Departures Plus** | The smaller entity set below. The app must be running on the board while you add it. |

To switch an existing board from legacy to Departures Plus, remove it under *Settings -> Devices & Services* and add it again.

## Entities

Departures Plus is configured on its own settings page on the board, so Home Assistant only gets what automations need:

| Entity | Description |
| --- | --- |
| **Display: Power** (switch) | Turn the display on or off. |
| **Display: Brightness** (number) | 1 to 3. |
| **Station: Shown** (select) | Rotate through all stations, or hold one of them. |
| **Station: Next** (button) | Jump to the next station. |
| **Station: Current** (sensor) | The station on the display, with mode and ticker messages as attributes. |
| **Next Departure: (station)** (sensor) | Minutes until the next departure at each station. Line, destination, data source and the following departures are attributes. |
| **Ticker** (notify) | Sends a text to the ticker. |
| **Ticker: Message Duration** (number) | Seconds a notify message stays in the ticker. Default 60, 0 keeps it until cleared. |
| **Ticker: Wake Display** (switch) | On by default: a ticker message turns a switched-off display on for as long as the message runs. Needs Departures Plus 0.5.0 or newer. |
| **Ticker: Permanent Text** (text) | The text that is always in the ticker. Saved on the board. |
| **System: Temperature / Uptime / Wi-Fi Signal** (sensors) | Diagnostics reported by the board. Need Departures Plus 0.5.0 or newer. |

Stations are read when the integration starts. After adding or removing stations on the board, reload the integration.

## Ticker messages

The simple way is the standard notify action. The message disappears after the time set in **Ticker: Message Duration**:

```yaml
action: notify.send_message
target:
  entity_id: notify.t_skylt_ticker
data:
  message: "Door opened"
```

For full control use `t_skylt.ticker_message`. `duration` is in seconds (0 keeps the message until it is cleared), a `message_id` lets you replace or clear exactly this message later, and `wake: true` or `wake: false` overrides the **Ticker: Wake Display** switch for this one message:

```yaml
action: t_skylt.ticker_message
data:
  message: "Window open"
  duration: 0
  message_id: window
```

```yaml
action: t_skylt.clear_ticker
data:
  message_id: window
```

Without `message_id`, `t_skylt.clear_ticker` removes all messages. The permanent ticker text stays.
