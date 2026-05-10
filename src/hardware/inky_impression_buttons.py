"""
GPIO buttons on Pimoroni Inky Impression (A–D): switch to a configured playlist plugin instance.

BCM pins default to 5, 6, 16, 24 (top to bottom), active low with pull-up — see Pimoroni inky examples/7color/buttons.py.
"""

import logging
import threading

from refresh_task import PlaylistRefresh

logger = logging.getLogger(__name__)

# Default BCM GPIO per button A, B, C, D (Inky Impression on 40-pin header)
DEFAULT_BUTTON_GPIOS = (5, 6, 16, 24)


class InkyImpressionButtons:
    """Attach gpiozero handlers when enabled; no-op if disabled, wrong display, or import fails."""

    def __init__(self, device_config, refresh_task, dev_mode=False):
        self.device_config = device_config
        self.refresh_task = refresh_task
        self.dev_mode = dev_mode
        self._buttons = []
        self._press_lock = threading.Lock()

    def start(self):
        if self.dev_mode:
            logger.debug("Hardware buttons skipped (development mode).")
            return

        if self.device_config.get_config("display_type", default="inky") != "inky":
            logger.debug("Hardware buttons skipped (display_type is not inky).")
            return

        hb = self.device_config.get_config("hardware_buttons", default=None)
        if not hb or not hb.get("enabled"):
            return

        try:
            from gpiozero import Button
        except ImportError:
            logger.warning("gpiozero not available; hardware buttons disabled.")
            return

        bindings = hb.get("bindings") or []
        if not bindings:
            logger.warning("hardware_buttons.enabled is true but bindings is empty; no buttons registered.")
            return

        for i, pin in enumerate(DEFAULT_BUTTON_GPIOS):
            if i >= len(bindings):
                break
            b = bindings[i]
            if not isinstance(b, dict):
                continue
            playlist = (b.get("playlist") or "").strip()
            plugin_id = (b.get("plugin_id") or "").strip()
            instance = (b.get("plugin_instance") or "").strip()
            if not (playlist and plugin_id and instance):
                logger.info("Hardware button %s: empty binding, skipping.", chr(ord("A") + i))
                continue

            gpio = b.get("gpio", pin)
            try:
                gpio = int(gpio)
            except (TypeError, ValueError):
                logger.warning("Hardware button %s: invalid gpio %r, using default %s.", chr(ord("A") + i), b.get("gpio"), pin)
                gpio = pin

            try:
                btn = Button(gpio, pull_up=True, bounce_time=0.3)
            except Exception:
                logger.exception("Failed to open GPIO %s for button %s.", gpio, chr(ord("A") + i))
                continue

            btn.when_pressed = self._make_handler(i, playlist, plugin_id, instance)
            self._buttons.append(btn)
            logger.info(
                "Hardware button %s (GPIO %s) -> playlist=%r plugin_id=%r instance=%r",
                chr(ord("A") + i),
                gpio,
                playlist,
                plugin_id,
                instance,
            )

        if not self._buttons:
            logger.warning("No hardware buttons were registered (check bindings and GPIO).")

    def _make_handler(self, index, playlist_name, plugin_id, plugin_instance_name):
        def _on_press():
            self._handle_press(index, playlist_name, plugin_id, plugin_instance_name)

        return _on_press

    def _handle_press(self, index, playlist_name, plugin_id, plugin_instance_name):
        with self._press_lock:
            try:
                pm = self.device_config.get_playlist_manager()
                playlist = pm.get_playlist(playlist_name)
                if not playlist:
                    logger.error("Hardware button %s: playlist %r not found.", chr(ord("A") + index), playlist_name)
                    return
                plugin_instance = playlist.find_plugin(plugin_id, plugin_instance_name)
                if not plugin_instance:
                    logger.error(
                        "Hardware button %s: plugin %r instance %r not found in playlist %r.",
                        chr(ord("A") + index),
                        plugin_id,
                        plugin_instance_name,
                        playlist_name,
                    )
                    return
                self.refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
            except Exception:
                logger.exception("Hardware button %s: refresh failed.", chr(ord("A") + index))

    def stop(self):
        for btn in self._buttons:
            try:
                btn.close()
            except Exception:
                logger.exception("Error closing GPIO button.")
        self._buttons.clear()
