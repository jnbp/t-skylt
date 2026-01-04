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
4. [Credits](#-credits)

---

## 🎛 Features

This integration exposes almost every known function of the board. Below is a complete list of all controls, grouped by their category in Home Assistant. The **official API parameter** used by the board is listed in `code` format for reference. Purposely missing are DNS settings, save button and obviously WiFi settings.

### 🚉 Category: Station
*Configuration regarding *what* data is shown.*

* **Active Config** (`?screen`)
    * Switch between the "Station 1" and "Station 2" internal memory slots.
* **Country** (`?country`)
    * Select the data provider country (e.g., SE, DE, FI, NO, etc.).
* **Operator** (`?operator`)
    * Select the specific transport service (e.g., VBB, SL, DB, SJ).
* **Station ID Input** (`?newstation`)
    * Text field to input the raw Station ID (see "Infinite Stations" below).
* **Transport Types** (`?type`)
    * Toggle specific transport modes: **Subway**, **Bus**, **Train**, **Tram**, **Ship**.
* **Max Departures** (`?maxdest`)
    * Limit the list to 1-8 departures.
* **Offset / Hide Within** (`?offset`)
    * Hide departures leaving in less than X minutes (0-30 min).

### 👁 Category: View
*Configuration regarding *how* the data is presented.*

* **List Mode** (`?listmode`)
    * Toggle between list view and other layouts.
* **Clock/Countdown** (`?clocktime`)
    * Toggle between showing the absolute time (e.g., 14:00) or countdown (e.g., 5 min).
* **Multiple Stops** (`?multiple`)
    * Enable grouping of multiple stops.
* **Show Station Name** (`?show_station`)
    * Toggle displaying the station name in the header.
* **Sleep Mode** (`?sleep`)
    * Turn off the display automatically if no departures are available.
* **Scroll Speed** (`?scroll`)
    * Set text scrolling to **Normal** (0) or **Low** (1).
* **No Departures Text** (`?no_more_departures`)
    * Custom text shown when the board is empty.
* **Minutes Suffix** (`?mins`)
    * Custom text for the minute abbreviation (e.g., "min").

### 📺 Category: Display
*Hardware settings for the LED matrix.*

* **Power** (`?onoff`)
    * Turn the display output On or Off.
* **Brightness** (`?brightness`)
    * Set brightness level: **Low**, **Medium**, **High**.
* **LED Tone** (`?color`)
    * Adjust the color temperature: **Orange**, **Yellow**, **White**.
* **Width** (`?width`)
    * Configure matrix width: **XS**, **X**, **XL**.
* **Color Highlight** (`?listcolor`)
    * Enable/Disable colored highlighting of line numbers.
* **Small Font** (`?fontmini`)
    * Force small font usage.
* **Line ID Cutoff** (`?line_length`)
    * Trim long line numbers after X characters.
* **Rotate** (`/rotate`)
    * Button to flip the display orientation by 180°.

### ⚙️ Category: System
*Maintenance and device configuration.*

* **Timers** (`?set_timer`)
    * Start/End time fields for every day of the week (Monday - Sunday).
* **Clear Timers** (`?cleartimer`)
    * Button to delete all active schedules.
* **TX Power** (`?power`)
    * Adjust the WiFi transmit power (dBm).
* **E-Mail** (`?user`)
    * Store user email address on the device.
* **Language** (`?language`)
    * Set system language (English/Swedish).
* **Update System** (`?update`)
    * Button to trigger an OTA firmware update (only active if update available).
* **Downgrade** (`?ver`)
    * Button to downgrade firmware to v1.0.
* **Network Tools**
    * **Ping Test** (`/ping`) and **DNS Info** (`/dns`).

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
6.  **Setup:** Enter the **IP Address** of your board.

---

## 💡 Automation Ideas & Recipes

Here are some ways to get the most out of your board.

### 1. Turn board on based on light and presence sensor

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

### 2. The "Infinite Stations" Workaround (Rotation)

By default, the board supports 2 active stations. In additions, this will always use the small font mode. However, you can use Home Assistant to **rotate through unlimited stations** by dynamically setting Station IDs via the integration.

#### ⚠️ Prerequisite: The "Warm-Up"

The board seems to cache station metadata locally. Before using a Station ID in Home Assistant, you **must** search for it **once manually** on the device's web interface (`http://<YOUR-IP>/`).

1. Open the board's IP in your browser.
2. Manually search and select the station you want to use.
3. Once the board has "seen" the station once, you can control it via Home Assistant.

#### How to find Station IDs

To use the automation, you need the raw Station IDs.
You can either track them in your developer mode directly on your browser or get them from somewhere else.For example for VBB (Berlin-Brandenburg) you can find a list of all stations here: [VBB Stations List](https://derhuerst.github.io/vbb-stations-html/).

In case you are using the VBB list, you need to be adjust the station id by **removing two zeros**.

* Change this: `9000**00*100003`
* to this: `9000100003`

I have not yet verified the ID formats for other operators (DB, SJ, etc.). If you figure out the logic, feel free to share your insights!

#### The Automation Code

Use an automation that changes the `text.t_skylt_station_id_input` every few seconds to cycle through your favorite stops.

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

---

## ❤️ Credits

A massive thank you to **T-Skylt Sweden AB**!
The collaboration with the manufacturer is quite cool fantastic, and their support allowed me to add some additional stuff to this integration possible.

* **Hardware Manufacturer:** [T-Skylt Sweden AB](http://t-skylt.se)
* **Integration Maintainer:** [@jnbp](https://github.com/jnbp)

```

```
