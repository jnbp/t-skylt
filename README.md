# T-Skylt Departure Board Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/v/release/jnbp/t-skylt)](https://github.com/jnbp/t-skylt/releases)
[![Maintainer](https://img.shields.io/badge/maintainer-%40jnbp-blue)](https://github.com/jnbp)

<br>
<p align="center">
  <img src="https://github.com/jnbp/t-skylt/blob/main/custom_components/t_skylt/icon.png" alt="T-Skylt Logo" width="100">
</p>
<p align="center">
  <b>Control your T-Skylt Sweden AB LED Departure Board directly from Home Assistant.</b>
</p>

---

## 🤖 Transparency Notice
**This integration was created with the assistance of AI.**
I developed this to solve my own need for better control over the board. While the code works well, I am not a professional Python developer. If you find bugs or see room for optimization, **I highly welcome your contributions!** Feel free to open a Pull Request or an Issue.

---

## 📋 Table of Contents
1. [Features](#-features)
2. [Installation](#-installation)
3. [Automation Ideas & Recipes](#-automation-ideas--recipes)
    - [Turn board on based on light and presence sensor](#1-turn-board-on-based-on-light-and-presence-sensor)
    - [The "Infinite Stations" Workaround](#2-the-infinite-stations-workaround-rotation)
4. [Technical Details](#-technical-details)
5. [Credits](#-credits)

---

## 🎛 Features

This integration exposes almost every known function of the board. Below is a complete list of all controls, grouped by their category in Home Assistant.

### 🚉 Category: Station
*Configuration regarding *what* data is shown.*

| Entity / Function | API Parameter | Description |
| :--- | :--- | :--- |
| **Active Config** | `?screen` | Switch between the "Station 1" and "Station 2" internal memory slots. |
| **Country** | `?country` | Select the data provider country (e.g., SE, DE, FI, NO, etc.). |
| **Operator** | `?operator` | Select the specific transport service (e.g., VBB, SL, DB, SJ). |
| **Station ID Input** | `?newstation` | Text field to input the raw Station ID (see "Infinite Stations" below). |
| **Transport Types** | `?type` | Toggle specific transport modes: **Subway**, **Bus**, **Train**, **Tram**, **Ship**. |
| **Max Departures** | `?maxdest` | Limit the list to 1-8 departures. |
| **Offset / Hide Within** | `?offset` | Hide departures leaving in less than X minutes (0-30 min). |

### 👁 Category: View
*Configuration regarding *how* the data is presented.*

| Entity / Function | API Parameter | Description |
| :--- | :--- | :--- |
| **List Mode** | `?listmode` | Toggle between list view and other layouts. |
| **Clock/Countdown** | `?clocktime` | Toggle between showing the absolute time (e.g., 14:00) or countdown (e.g., 5 min). |
| **Multiple Stops** | `?multiple` | Enable grouping of multiple stops. |
| **Show Station Name** | `?show_station` | Toggle displaying the station name in the header. |
| **Sleep Mode** | `?sleep` | Turn off the display automatically if no departures are available. |
| **Scroll Speed** | `?scroll` | Set text scrolling to **Normal** (0) or **Low** (1). |
| **No Departures Text** | `?no_more_departures` | Custom text shown when the board is empty. |
| **Minutes Suffix** | `?mins` | Custom text for the minute abbreviation (e.g., "min"). |

### 📺 Category: Display
*Hardware settings for the LED matrix.*

| Entity / Function | API Parameter | Description |
| :--- | :--- | :--- |
| **Power** | `?onoff` | Turn the display output On or Off. |
| **Brightness** | `?brightness` | Set brightness level: **Low**, **Medium**, **High**. |
| **LED Tone** | `?color` | Adjust the color temperature: **Orange**, **Yellow**, **White**. |
| **Width** | `?width` | Configure matrix width: **XS**, **X**, **XL**. |
| **Color Highlight** | `?listcolor` | Enable/Disable colored highlighting of line numbers. |
| **Small Font** | `?fontmini` | Force small font usage. |
| **Line ID Cutoff** | `?line_length` | Trim long line numbers after X characters. |
| **Rotate** | `/rotate` | Button to flip the display orientation by 180°. |

### ⚙️ Category: System
*Maintenance and device configuration.*

| Entity / Function | API Parameter | Description |
| :--- | :--- | :--- |
| **Timers** | `?set_timer` | Start/End time fields for every day of the week (Monday - Sunday). |
| **Clear Timers** | `?cleartimer` | Button to delete all active schedules. |
| **TX Power** | `?power` | Adjust the WiFi transmit power (dBm). |
| **E-Mail** | `?user` | Store user email address on the device. |
| **Language** | `?language` | Set system language (English/Swedish). |
| **Update System** | `?update` | Button to trigger an OTA firmware update (only active if update available). |
| **Downgrade** | `?ver` | Button to downgrade firmware to v1.0. |
| **Network Tools** | `/ping` / `/dns` | **Ping Test** and **DNS Info**. |

### 🔍 Sensors & Diagnostics
* **Update Available:** Binary sensor that checks if a new firmware version is detected.
* **System Temperature:** Internal temperature of the ESP/Controller.
* **Uptime:** Time since last reboot in minutes.

---

## 🚀 Installation

1.  **HACS:** Go to HACS -> Integrations -> 3 dots (top right) -> **Custom repositories**.
2.  **Add URL:** `https://github.com/jnbp/t-skylt` -> Category: **Integration**.
3.  **Install:** Click "Download" on the new card.
4.  **Restart:** Restart Home Assistant.
5.  **Add Device:** Go to Settings -> Devices & Services -> Add Integration -> Search **"T-Skylt"**.
6.  **Setup:** Enter the **IP Address** (e.g., `192.168.1.50`) or the **Hostname** (e.g., `esp32-s3-zero.local`) of your board.

> **💡 Tip:** For maximum stability, we recommend assigning a fixed **Static IP** to the board in your router and using that instead of a hostname.

---

## 💡 Automation Ideas & Recipes

Here are some ways to get the most out of your board.

### 1. Turn board on based on light and presence sensor

<details>
  <summary>Click to expand YAML code</summary>

```yaml
alias: "Automatisierung: T-Skylt On Off Light Radar"
description: ""
triggers:
  - trigger: state
    entity_id:
      - binary_sensor.kuche_radar_presence_sensor_1
    id: "off"
    to:
      - "off"
      - "on"
  - trigger: state
    entity_id:
      - light.galerie
conditions: []
actions:
  - if:
      - condition: state
        entity_id: light.galerie
        state:
          - "on"
      - condition: numeric_state
        entity_id: light.galerie
        attribute: brightness
        above: 10
      - condition: state
        entity_id: binary_sensor.kuche_radar_presence_sensor_1
        state:
          - "on"
    then:
      - if:
          - condition: state
            entity_id: switch.t_skylt_power
            state:
              - "off"
        then:
          - type: turn_on
            device_id: 834a99bc2f0d346ff6545ed9eaac306e
            entity_id: 399a5859d1908250cc4424e3be4feffe
            domain: switch
    else:
      - if:
          - condition: state
            entity_id: switch.t_skylt_power
            state:
              - "on"
        then: []
      - type: turn_off
        device_id: 834a99bc2f0d346ff6545ed9eaac306e
        entity_id: 399a5859d1908250cc4424e3be4feffe
        domain: switch
mode: single

```

</details>

### 2. The "Infinite Stations" Workaround (Rotation)

By default, the board supports 2 active stations. This will force you to switch to the small font mode. I was not satisfied by that. Wanted to have the normal font, and the possibility to even show more than two stations.
So I came to the solution to let home assistant **rotate through unlimited stations** by dynamically setting Station IDs via the integration.

#### ⚠️ Prerequisite: The "Warm-Up"

The board seems to cache station metadata locally. Before using a Station ID in Home Assistant, you **must** search for it **once manually** on the device's web interface (`http://<YOUR-IP>/`).

1. Open the board's IP in your browser.
2. Manually search and select the station you want to use.
3. Once the board has "seen" the station once, you can control it via Home Assistant.

#### How to find Station IDs

To use the automation, you need the raw Station IDs.
You can either track them in your developer mode directly on your browser or get them from somewhere else. For example for VBB (Berlin-Brandenburg) you can find a list of all stations here: [VBB Stations List](https://derhuerst.github.io/vbb-stations-html/).

In case you are using the VBB list, you need to be adjust the station id by **removing two zeros**.

* Change this: `900000100003`
* to this: `9000100003`

I have not yet verified the ID formats for other operators (DB, SJ, etc.). If you figure out the logic, feel free to share your insights!

#### The Automation Code

Use an automation that changes the `text.t_skylt_station_id_input` every few seconds to cycle through your favorite stops.

<details>
<summary>Click to expand YAML code</summary>

```yaml
alias: "Automatisierung: T-Skylt Station Switch"
description: ""
triggers:
  - trigger: state
    entity_id:
      - switch.t_skylt_power
    to:
      - "on"
    from:
      - "off"
conditions: []
actions:
  - device_id: 834a99bc2f0d346ff6545ed9eaac306e
    domain: select
    entity_id: aa57bd7c40f1d6e51823624569cf1368
    type: select_option
    option: Station 1
    enabled: false
  - repeat:
      while:
        - condition: state
          entity_id: switch.t_skylt_power
          state:
            - "on"
      sequence:
        - device_id: 834a99bc2f0d346ff6545ed9eaac306e
          domain: text
          entity_id: 952269e600452676018d385b25e2810a
          type: set_value
          value: "9000100003"
        - delay:
            hours: 0
            minutes: 0
            seconds: 10
            milliseconds: 0
        - device_id: 834a99bc2f0d346ff6545ed9eaac306e
          domain: text
          entity_id: 952269e600452676018d385b25e2810a
          type: set_value
          value: "9000003201"
        - delay:
            hours: 0
            minutes: 0
            seconds: 10
            milliseconds: 0
        - device_id: 834a99bc2f0d346ff6545ed9eaac306e
          domain: text
          entity_id: 952269e600452676018d385b25e2810a
          type: set_value
          value: "9000100020"
        - delay:
            hours: 0
            minutes: 0
            seconds: 10
            milliseconds: 0
mode: single

```

</details>

---

## 🧠 Technical Details

This integration is designed to be extremely robust against network latency and the hardware limitations of the T-Skylt board. Below is an overview of how it works under the hood.

### ⚙️ How it works: Web Scraping & Polling

The T-Skylt board does not provide a formal JSON API. Instead, this integration acts like a web browser:

1. **Fetching:** It performs an HTTP GET request to the device's root URL (`/`) to retrieve the raw HTML.
2. **Parsing:** It uses `BeautifulSoup` to parse the HTML structure. The state of the device (e.g., is the light on? what is the brightness?) is determined by inspecting HTML attributes like `checked` on checkboxes or `value` in input fields.
3. **Controlling:** To change settings, the integration sends HTTP requests with specific query parameters (e.g., `/?brightness=2`), mimicking the behavior of clicking buttons on the actual web interface.

### 🛡️ Concurrency Control (The "Queue")

The device is based on a microcontroller (likely ESP-based) with a single-threaded web server. It cannot handle multiple HTTP requests simultaneously. If Home Assistant tries to fetch the status (polling) at the exact same moment an automation sends a command, the device often drops the connection or freezes.

* **Implementation:** An `asyncio.Lock` is used within the DataUpdateCoordinator.
* **Effect:** Commands and Status Updates are strictly queued. If a status update is running, any button press waits until the update is finished (and vice versa). This ensures sequential processing and prevents overloading the chip.

### 📡 WiFi Weakness & Latency Handling

**My Setup & The Repeater Logic:**
The WiFi antenna on the board is relatively weak. To ensure a stable connection, I placed a WiFi repeater directly next to the unit to bridge the signal to my main router. While this solves the signal strength issue, the repeater introduces additional network latency.

To accommodate this setup and prevent the device from flickering to "Unavailable" in Home Assistant, the timeouts have been adjusted significantly:

* **Fetch Timeout:** **40 seconds**. If the device takes 39 seconds to answer (e.g., due to repeater latency or busy processing), the integration waits patiently.
* **Command Timeout:** **20 seconds**. When a button is pressed, the UI updates immediately (Optimistic Mode), but the backend keeps the connection open for up to 20 seconds to confirm the command was received.

### 🔄 Smart Retry Logic

Transient network errors are common with IoT devices. To avoid false alarms in the dashboard:

* **Logic:** If a status update fails, the integration pauses for **2 seconds** and tries a **second time**.
* **Result:** The device is only marked "Unavailable" if it genuinely fails to respond twice in a row.

### 💓 Heartbeat & Socket Management

* **Polling Interval:** Data is refreshed every **60 seconds** to minimize load.
* **Cleanup:** Every request sends `Connection: close` headers to force the device to free up memory sockets immediately after a transaction, preventing memory leaks on the hardware.

---

## ❤️ Credits

A massive thank you to **T-Skylt Sweden AB**!
The collaboration with the manufacturer is quite cool, and their support allowed me to add some additional stuff to this integration.

* **Hardware Manufacturer:** [T-Skylt Sweden AB](http://t-skylt.se)
* **Integration Maintainer:** [@jnbp](https://github.com/jnbp)

```

```
