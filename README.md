# InkyPi 

<img src="./docs/images/inky_clock.jpg" />

This repository is a **fork** of [fatihak/InkyPi](https://github.com/fatihak/InkyPi). It stays compatible with upstream while adding **Pimoroni Inky Impression hardware buttons** (A–D): assign them per playlist plugin instance, optional GPIO overrides, and three schedule modes (**Settings** ↔ `playlist_schedule_mode` in `playlist_config`). Details: [installation.md](./docs/installation.md) § *Inky Impression hardware buttons*.

---

## About InkyPi 
InkyPi is an open-source, customizable E-Ink display powered by a Raspberry Pi. Designed for simplicity and flexibility, it allows you to effortlessly display the content you care about, with a simple web interface that makes setup and configuration effortless.

**Features**:
- Natural paper-like aesthetic: crisp, minimalist visuals that are easy on the eyes, with no glare or backlight
- Web Interface allows you to update and configure the display from any device on your network
- Minimize distractions: no LEDs, noise, or notifications, just the content you care about
- Easy installation and configuration, perfect for beginners and makers alike
- Open source project allowing you to modify, customize, and create your own plugins
- Set up scheduled playlists to display different plugins at designated times

**Plugins**:

- Image Upload: Upload and display an image from your browser
- Daily Newspaper/Comic: Show daily comics and front pages of major newspapers from around the world
- Clock: Customizable clock faces for displaying time
- AI Image/Text: Generate images and dynamic text from prompts using OpenAI's models
- Weather: Display current weather conditions and multi-day forecasts with a customizable layout
- Calendar: Visualize your calendar from Google, Outlook, or Apple Calendar with customizable layouts

For documentation on building custom plugins, see [Building InkyPi Plugins](./docs/building_plugins.md).

Community-maintained third-party plugins are still listed on [the upstream wiki](https://github.com/fatihak/InkyPi/wiki).

## Hardware 
- Raspberry Pi (4 | 3 | Zero 2 W)
    - Recommended to get 40 pin Pre Soldered Header
- MicroSD Card (min 8 GB) like [this one](https://amzn.to/3G3Tq9W)
- E-Ink Display:
    - Inky Impression by Pimoroni
        - **[13.3 Inch Display](https://collabs.shop/q2jmza)**
        - **[7.3 Inch Display](https://collabs.shop/q2jmza)**
        - **[5.7 Inch Display](https://collabs.shop/ns6m6m)**
        - **[4 Inch Display](https://collabs.shop/cpwtbh)**
    - Inky wHAT by Pimoroni
        - **[4.2 Inch Display](https://collabs.shop/jrzqmf)**
    - Waveshare e-Paper Displays
        - Spectra 6 (E6) Full Color **[4 inch](https://www.waveshare.com/4inch-e-paper-hat-plus-e.htm?&aff_id=111126)** **[7.3 inch](https://www.waveshare.com/7.3inch-e-paper-hat-e.htm?&aff_id=111126)** **[13.3 inch](https://www.waveshare.com/13.3inch-e-paper-hat-plus-e.htm?&aff_id=111126)**
        - Black and White **[7.5 inch](https://www.waveshare.com/7.5inch-e-paper-hat.htm?&aff_id=111126)** **[13.3 inch](https://www.waveshare.com/13.3inch-e-paper-hat-k.htm?&aff_id=111126)**
        - See [Waveshare e-paper displays](https://www.waveshare.com/product/raspberry-pi/displays/e-paper.htm?&aff_id=111126) or visit their [Amazon store](https://amzn.to/3HPRTEZ) for additional models. Note that some models like the IT8951 based displays are not supported. See later section on [Waveshare e-Paper](#waveshare-display-support) compatibility for more information.
- Picture Frame or 3D Stand
    - See [community.md](./docs/community.md) for 3D models, custom builds, and other submissions from the community

**Disclosure:** The product links above are affiliate links from the original project readme. Purchases may support the linked maintainers; you pay no extra.

## Installation
To install InkyPi from **this fork**, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/Deumus74/InkyPi.git
    ```
    Or with SSH:
    ```bash
    git clone git@github.com:Deumus74/InkyPi.git
    ```
2. Navigate to the project directory:
    ```bash
    cd InkyPi
    ```
3. Run the installation script with sudo:
    ```bash
    sudo bash install/install.sh [-W <waveshare device model>]
    ``` 
     Option: 
    
    * -W \<waveshare device model\> - specify this parameter **ONLY** if installing for a Waveshare display.  After the -W option specify the Waveshare device model e.g. epd7in3f.

    e.g. for Inky displays use:
    ```bash
    sudo bash install/install.sh
    ```

    and for [Waveshare displays](#waveshare-display-support) use:
    ```bash
    sudo bash install/install.sh -W epd7in3f
    ```


After the installation is complete, the script will prompt you to reboot your Raspberry Pi. Once rebooted, the display will update to show the InkyPi splash screen.

Notes: 
- The installation script requires sudo privileges to install and run the service. We recommend starting with a fresh installation of Raspberry Pi OS to avoid potential conflicts with existing software or configurations.
- The installation process will automatically enable the required SPI and I2C interfaces on your Raspberry Pi.
- **Inky Impression rear buttons**: configure assignments on the Playlists page and the schedule mode under **Settings**; optional `hardware_buttons.gpios` in `src/config/device.json`. See [installation.md](./docs/installation.md).

For more details (imaging the microSD with Raspberry Pi OS, GPIO, migration from legacy `bindings`), refer to [installation.md](./docs/installation.md). You can also watch [this YouTube tutorial](https://youtu.be/L5PvQj1vfC4) based on upstream InkyPi.

## Update
To update your InkyPi install with the latest changes from **this fork**:

1. Navigate to the project directory:
    ```bash
    cd InkyPi
    ```
2. Fetch the latest changes:
    ```bash
    git pull
    ```
3. Run the update script with sudo:
    ```bash
    sudo bash install/update.sh
    ```

This installs updated dependencies, frontend vendor assets where applicable, and restarts the `inkypi` service. Pure code-only changes often take effect via the symlink under `/usr/local/inkypi/src`, but running `install/update.sh` after `git pull` is the safest routine (see upstream discussion in issues).

Optional: track upstream fixes with a second remote, e.g. `git remote add upstream https://github.com/fatihak/InkyPi.git`, then merge or cherry-pick selectively.

## Uninstall
To remove InkyPi, run:

```bash
sudo bash install/uninstall.sh
```

## Roadmap
This fork evolves together with upstream InkyPi:

- More plugins and modular layouts (see [upstream Trello](https://trello.com/b/SWJYWqe4/inkypi))
- **Inky Impression hardware buttons** — assign A–D per instance, schedule modes in **Settings** (this fork)
- Improved Web UI on mobile devices

## Waveshare Display Support

Waveshare offers a range of e-Paper displays, similar to the Inky screens from Pimoroni, but with slightly different requirements. While Inky displays auto-configure via the inky Python library, Waveshare displays require model-specific drivers from their [Python EPD library](https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd).

This project has been tested with several Waveshare models. **Displays based on the IT8951 controller are not supported**, and **screens smaller than 4 inches are not recommended** due to limited resolution.

If your display model has a corresponding driver in the link above, it’s likely to be compatible. When running the installation script, use the -W option to specify your display model (without the .py extension). The script will automatically fetch and install the correct driver.

## License

Distributed under the GPL 3.0 License, see [LICENSE](./LICENSE) for more information.

This project includes fonts and icons with separate licensing and attribution requirements. See [Attribution](./docs/attribution.md) for details.

## Issues & upstream

Bug reports and feature requests for **this fork**: [Issues – Deumus74/InkyPi](https://github.com/Deumus74/InkyPi/issues).

For upstream InkyPi: [Issues – fatihak/InkyPi](https://github.com/fatihak/InkyPi/issues).

See [./docs/troubleshooting.md](./docs/troubleshooting.md). If you're using a Pi Zero W, see [Known Issues during Pi Zero W Installation](./docs/troubleshooting.md#known-issues-during-pi-zero-w-installation).

## Credits & sponsoring

Upstream InkyPi is maintained by **[fatihak](https://github.com/fatihak)** — consider supporting the original author if this project helped you:

<p align="center">
<a href="https://github.com/sponsors/fatihak" target="_blank"><img src="https://user-images.githubusercontent.com/345274/133218454-014a4101-b36a-48c6-a1f6-342881974938.png" alt="GitHub Sponsors" height="35" width="auto"></a>
<a href="https://www.patreon.com/akzdev" target="_blank"><img src="https://c5.patreon.com/external/logo/become_a_patron_button.png" alt="Become a Patron on Patreon" height="35" width="auto"></a>
<a href="https://www.buymeacoffee.com/akzdev" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="35" width="auto"></a>
</p>


## Acknowledgements

Check out these similar projects:

- [PaperPi](https://github.com/txoof/PaperPi) - awesome project that supports waveshare devices
    - shoutout to @txoof for assisting with upstream InkyPi's installation process
- [InkyCal](https://github.com/aceinnolab/Inkycal) - has modular plugins for building custom dashboards
- [PiInk](https://github.com/tlstommy/PiInk) - inspiration behind InkyPi's flask web ui
- [rpi_weather_display](https://github.com/sjnims/rpi_weather_display) - alternative eink weather dashboard with advanced power efficiency
