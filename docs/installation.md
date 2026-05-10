# InkyPi Detailed Installation

## Flashing Raspberry Pi OS 

1. Install the Raspberry Pi Imager from the [official download page](https://www.raspberrypi.com/software/)
2. Insert the target SD Card into your computer and launch the Raspberry Pi Imager software
    - Raspberry Pi Device: Choose your Pi model
    - Operating System: Select the recommended system
    - Storage: Select the target SD Card

<img src="./images/raspberry_pi_imager.png" alt="Raspberry Pi Imager" width="500"/>

3. Click Next and choose Edit Settings on the Use OS customization? screen
    - General:
        - Set hostname: enter your desired hostname
            -  This will be used to ssh into the device & access the InkyPi UI on your network.
        - Set username & password
            - Do not use the default username and password on a Raspberry PI as this poses a security risk
        - Configure wireless LAN to your network
            - The InkyPi web server will only be accessible to devices on this network
        - Set local settings to your Time zone
    - Service:
        - Enable SSH:
            - Use password authentication
    - Options: leave default values

<p float="left">
  <img src="./images/raspberry_pi_imager_general.png" width="250" />
  <img src="./images/raspberry_pi_imager_options.png" width="250" /> 
  <img src="./images/raspberry_pi_imager_services.png" width="250" />
</p>

4. Click Yes to apply OS customization options and confirm

## Inky Impression hardware buttons (optional)

Pimoroni **Inky Impression** boards expose four rear buttons (A–D, top to bottom). Configure them in the **Playlists** page: each playlist plugin instance can have **HW Btn** **A**–**D** (or none). A press shows that instance immediately (like **Display** in the web UI) when a mode that uses buttons is active.

In **Settings**, choose how buttons interact with **time-based playlists** (`playlist_config.playlist_schedule_mode`):

| Mode | Value | Behaviour |
|------|--------|-----------|
| **C** | `schedule_only` | Timed playlist rotation only; physical buttons are ignored. |
| **B** | `schedule_with_button_override` | Timed rotation; a button temporarily switches to that instance’s playlist until the scheduled “winning” playlist changes. |
| **A** | `exclusive_schedule` | Timed **between-playlist** switching is disabled; only the playlist last chosen by a button is used for rotation (until you press another assigned button). Before the first press, the normal scheduled playlist applies. |

GPIO is only opened when **not** running with `--dev`, `display_type` is `inky`, at least one instance has a hardware button, and the schedule mode is **A** or **B**.

Optional **BCM pin overrides** in `src/config/device.json` (defaults **5, 6, 16, 24** for A–D, active low, internal pull-up — see [Pimoroni’s Inky example](https://github.com/pimoroni/inky/blob/main/examples/7color/buttons.py)):

```json
"hardware_buttons": {
    "gpios": { "A": 5, "B": 6, "C": 16, "D": 24 }
}
```

Omit keys for buttons that should keep the default pin.

**Legacy configs** that used `hardware_buttons.enabled` and `hardware_buttons.bindings` are migrated automatically on load: bindings are applied to the matching plugin instances as `hardware_button`, and an old `playlist_schedule_mode` stored under `hardware_buttons` is moved into `playlist_config`.

On **Raspberry Pi 5**, GPIO line numbering can differ; if buttons misbehave, check Pimoroni’s current documentation or set explicit values in `hardware_buttons.gpios`.
