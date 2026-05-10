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

Pimoroni **Inky Impression** boards expose four rear buttons (A–D, top to bottom). InkyPi can map each button to a **playlist plugin instance** so a press shows that plugin immediately (same behaviour as **Display** in the web UI).

1. Edit `src/config/device.json` on the device.
2. Set `hardware_buttons.enabled` to `true`.
3. Set `hardware_buttons.bindings` to up to four objects in order **A, B, C, D**. Each object needs:
   - `playlist`: exact playlist name (e.g. `Default`)
   - `plugin_id`: plugin id (e.g. `clock`)
   - `plugin_instance`: exact instance name as shown in the playlist
4. Optional per button: `gpio` (BCM number). If omitted, defaults are **5, 6, 16, 24** (active low, internal pull-up), matching [Pimoroni’s Inky example](https://github.com/pimoroni/inky/blob/main/examples/7color/buttons.py).

Example (replace names with your playlist and instances):

```json
"hardware_buttons": {
    "enabled": true,
    "bindings": [
        { "playlist": "Default", "plugin_id": "clock", "plugin_instance": "Kitchen clock" },
        { "playlist": "Default", "plugin_id": "weather", "plugin_instance": "Home" },
        {},
        {}
    ]
}
```

Empty objects skip that physical button. GPIO is only opened when **not** running with `--dev`, `display_type` is `inky`, and `enabled` is true. On **Raspberry Pi 5**, GPIO line numbering can differ; if buttons misbehave, check Pimoroni’s current `gpiod` examples or set explicit `gpio` values for your board revision.
