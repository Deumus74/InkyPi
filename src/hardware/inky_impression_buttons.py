"""
GPIO buttons on Pimoroni Inky Impression (A–D): map from plugin instances'
``hardware_button`` field; pins from ``device.json`` → hardware_buttons.gpios.

BCM defaults 5, 6, 16, 24 (top to bottom), active low with pull-up —
see Pimoroni inky examples/7color/buttons.py.
"""

import logging
import threading

from refresh_task import PlaylistRefresh
from model import (
    HARDWARE_BUTTON_LABELS,
    PLAYLIST_SCHEDULE_MODE_SCHEDULE_ONLY,
)
from utils.device_config_normalize import gpios_from_config, hardware_button_assignments

logger = logging.getLogger(__name__)

_active_controller = None


def set_active_button_controller(controller):
    """Called from inkypi main so saves can hot-replug GPIO handlers."""
    global _active_controller
    _active_controller = controller


def restart_hardware_buttons_if_active():
    ctrl = _active_controller
    if ctrl:
        ctrl.restart_handlers()


def schedule_hardware_buttons_restart():
    """Run GPIO teardown/setup off the HTTP worker — avoids blocking Flask/Waitress."""

    def _run():
        try:
            restart_hardware_buttons_if_active()
        except Exception:
            logger.exception("Hardware button GPIO restart failed.")

    threading.Thread(target=_run, daemon=True, name="inky-hw-btn-restart").start()


class InkyImpressionButtons:
    """Attach gpiozero handlers when schedule mode allows and instances are bound."""

    def __init__(self, device_config, refresh_task, dev_mode=False):
        self.device_config = device_config
        self.refresh_task = refresh_task
        self.dev_mode = dev_mode
        self._buttons = []
        self._press_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()

    def restart_handlers(self):
        with self._lifecycle_lock:
            self.stop()
            self.start()

    def start(self):
        if self.dev_mode:
            logger.debug("Hardware buttons skipped (development mode).")
            return

        if self.device_config.get_config("display_type", default="inky") != "inky":
            logger.debug("Hardware buttons skipped (display_type is not inky).")
            return

        pm = self.device_config.get_playlist_manager()
        if pm.playlist_schedule_mode == PLAYLIST_SCHEDULE_MODE_SCHEDULE_ONLY:
            logger.debug("Hardware buttons skipped (playlist_schedule_mode is schedule_only).")
            return

        assignments = hardware_button_assignments(pm)
        if not assignments:
            logger.debug("No hardware_button assignments on plugin instances; skipping GPIO.")
            return

        try:
            from gpiozero import Button
        except ImportError:
            logger.warning("gpiozero not available; hardware buttons disabled.")
            return

        hb = self.device_config.get_config("hardware_buttons") or {}
        pin_by_label = gpios_from_config(hb)

        assignment_by_label = {lbl: (pname, pid, inst) for lbl, pname, pid, inst in assignments}

        for label in HARDWARE_BUTTON_LABELS:
            if label not in assignment_by_label:
                continue
            playlist_name, plugin_id, plugin_instance_name = assignment_by_label[label]
            gpio = pin_by_label[label]

            try:
                btn = Button(gpio, pull_up=True, bounce_time=0.3)
            except Exception:
                logger.exception("Failed to open GPIO %s for button %s.", gpio, label)
                continue

            btn.when_pressed = self._make_handler(label, playlist_name, plugin_id, plugin_instance_name)
            self._buttons.append(btn)
            logger.info(
                "Hardware button %s (GPIO %s) -> playlist=%r plugin_id=%r instance=%r",
                label,
                gpio,
                playlist_name,
                plugin_id,
                plugin_instance_name,
            )

        if not self._buttons:
            logger.warning("No hardware buttons registered.")

    def _make_handler(self, label, playlist_name, plugin_id, plugin_instance_name):
        def _on_press():
            self._handle_press(label, playlist_name, plugin_id, plugin_instance_name)

        return _on_press

    def _handle_press(self, label, playlist_name, plugin_id, plugin_instance_name):
        with self._press_lock:
            try:
                pm = self.device_config.get_playlist_manager()
                playlist = pm.get_playlist(playlist_name)
                if not playlist:
                    logger.error("Hardware button %s: playlist %r not found.", label, playlist_name)
                    return
                plugin_instance = playlist.find_plugin(plugin_id, plugin_instance_name)
                if not plugin_instance:
                    logger.error(
                        "Hardware button %s: plugin %r instance %r not found in playlist %r.",
                        label,
                        plugin_id,
                        plugin_instance_name,
                        playlist_name,
                    )
                    return

                self.refresh_task.apply_hardware_button_press(playlist, plugin_instance)
                self.refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
            except Exception:
                logger.exception("Hardware button %s: refresh failed.", label)

    def stop(self):
        for btn in self._buttons:
            try:
                btn.close()
            except Exception:
                logger.exception("Error closing GPIO button.")
        self._buttons.clear()
