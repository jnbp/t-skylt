# T-Skylt Departure Board Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/v/release/jnbp/t-skylt)](https://github.com/jnbp/t-skylt/releases)

Connect your **T-Skylt Sweden AB** LED Departure Board to Home Assistant via local polling. Control brightness, toggle display modes, and monitor system stats directly from your dashboard.

<img src="custom_components/t_skylt/icon.png" alt="T-Skylt Icon" width="100">

## ✨ Features

* **Switch Control:** Turn the board On/Off.
* **Mode Toggles:**
    * Show/Hide Clock & Countdown (`?clocktime`).
    * List Mode vs. Single Line (`?listmode`).
    * Multiple Stops (`?multiple`).
    * Highlight Colors (`?listcolor`).
    * Small Font (`?fontmini`).
* **Settings:**
    * Set Brightness (Low, Medium, High).
    * Set LED Color Scheme (Orange, Yellow, White).
    * Adjust TX Power and Line ID Cutoff.
    * Set custom text for "No more departures".
* **Sensors:** Monitor Board Temperature and Uptime.

## 🚀 Installation via HACS

1.  Go to HACS -> Integrations.
2.  Click the three dots in the top right corner -> **Custom repositories**.
3.  Add the URL of this repository: `https://github.com/jnbp/t-skylt`
4.  Category: **Integration**.
5.  Click **Add** and then install "T-Skylt Departure Boards".
6.  Restart Home Assistant.
7.  Go to Settings -> Devices & Services -> Add Integration -> Search for "T-Skylt".
8.  Enter the **IP Address** of your board.

## 🤖 Disclaimer & Contribution

**This integration was created with the assistance of AI.**

I built this to solve my own need to control the T-Skylt board, but I am not a professional Python developer. The code works well, but there is definitely room for optimization.

**I welcome any contributions!**
If you know how to improve the code, handle the API more efficiently, or add new features, please feel free to open a Pull Request or an Issue. Let's make this better together.

## Credits

* Hardware by [T-Skylt Sweden AB](http://t-skylt.se)
* Maintained by [@jnbp](https://github.com/jnbp)
