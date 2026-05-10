"""
GPIO buttons on Pimoroni Inky Impression (A–D): map from plugin instances'
``hardware_button`` field; pins from ``device.json`` → hardware_buttons.gpios.

BCM defaults 5, 6, 16, 24 (top to bottom), active low with pull-up —
see Pimoroni inky examples/7color/buttons.py.
"""

import logging
import threading
import time

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
        self._gpiod_thread = None
        self._gpiod_stop = None
        self._gpiod_request = None

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

        hb = self.device_config.get_config("hardware_buttons") or {}
        pin_by_label = gpios_from_config(hb)
        assignment_by_label = {lbl: (pname, pid, inst) for lbl, pname, pid, inst in assignments}

        if self._try_start_gpiod(assignment_by_label, pin_by_label):
            return

        try:
            from gpiozero import Button
        except ImportError:
            logger.warning("gpiozero not available; hardware buttons disabled.")
            return

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

    def _stop_gpiod(self):
        thread = self._gpiod_thread
        request = self._gpiod_request
        stop_evt = self._gpiod_stop
        self._gpiod_thread = None
        self._gpiod_request = None
        self._gpiod_stop = None
        if stop_evt is not None:
            stop_evt.set()
        if request is not None:
            for meth in ("release", "close"):
                if hasattr(request, meth):
                    try:
                        getattr(request, meth)()
                    except Exception:
                        logger.exception("Error tearing down gpiod request (%s).", meth)
                    break
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)

    def _try_start_gpiod(self, assignment_by_label, pin_by_label):
        """Pi 5 (and newer gpiochip ABI): Pimoroni use gpiod + gpiodevice; gpiozero often fails."""
        try:
            import gpiod
            from gpiod.line import Bias, Direction, Edge
            import gpiodevice
        except ImportError:
            logger.info("gpiod/gpiodevice not installed; using gpiozero for hardware buttons.")
            return False

        try:
            chip = gpiodevice.find_chip_by_platform()
        except Exception:
            logger.exception("gpiodevice.find_chip_by_platform failed; using gpiozero for hardware buttons.")
            return False

        input_settings = gpiod.LineSettings(
            direction=Direction.INPUT,
            bias=Bias.PULL_UP,
            edge_detection=Edge.FALLING,
        )

        line_config = {}
        offset_handlers = {}

        for label in HARDWARE_BUTTON_LABELS:
            if label not in assignment_by_label:
                continue
            playlist_name, plugin_id, plugin_instance_name = assignment_by_label[label]
            gpio = pin_by_label[label]
            try:
                offset = chip.line_offset_from_id(gpio)
            except Exception:
                logger.exception(
                    "Failed to resolve gpiod line for button %s (GPIO id %s).",
                    label,
                    gpio,
                )
                continue
            if offset in line_config:
                logger.warning("Duplicate gpiod offset %s (label %s); skipping duplicate.", offset, label)
                continue
            line_config[offset] = input_settings
            offset_handlers[offset] = self._make_handler(
                label, playlist_name, plugin_id, plugin_instance_name
            )
            logger.info(
                "Hardware button %s (GPIO %s, line offset %s) [gpiod] -> playlist=%r plugin_id=%r instance=%r",
                label,
                gpio,
                offset,
                playlist_name,
                plugin_id,
                plugin_instance_name,
            )

        if not line_config:
            return False

        try:
            request = chip.request_lines(consumer="inkypi-hw-buttons", config=line_config)
        except Exception:
            logger.exception("gpiod chip.request_lines failed; using gpiozero for hardware buttons.")
            return False

        self._gpiod_stop = threading.Event()
        self._gpiod_request = request
        debounce_last = {}

        def _poll():
            debounce_s = 0.35
            while not self._gpiod_stop.is_set():
                try:
                    for event in request.read_edge_events():
                        if self._gpiod_stop.is_set():
                            break
                        off = event.line_offset
                        now = time.monotonic()
                        if now - debounce_last.get(off, 0.0) < debounce_s:
                            continue
                        debounce_last[off] = now
                        cb = offset_handlers.get(off)
                        if cb:
                            cb()
                        else:
                            logger.debug("gpiod edge for unmapped line offset %s", off)
                except Exception:
                    if self._gpiod_stop.is_set():
                        break
                    logger.exception("Hardware button gpiod poll error; retrying after short delay.")
                    time.sleep(0.5)

        self._gpiod_thread = threading.Thread(
            target=_poll,
            daemon=True,
            name="inkypi-gpiod-buttons",
        )
        self._gpiod_thread.start()
        logger.info("Hardware buttons: gpiod + gpiodevice listener started.")
        return True

    def _make_handler(self, label, playlist_name, plugin_id, plugin_instance_name):
        def _on_press():
            self._handle_press(label, playlist_name, plugin_id, plugin_instance_name)

        return _on_press

    def _handle_press(self, label, playlist_name, plugin_id, plugin_instance_name):
        """Apply playlist override under lock; run refresh on a worker so gpiod can keep reading edges.

        Calling ``manual_update`` from the gpiod poll thread blocks that thread for the full E-Ink update;
        no further button events are processed until then (kernel buffer can overflow; logs look idle).
        """
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
            except Exception:
                logger.exception("Hardware button %s: failed to apply playlist state.", label)
                return

        pl, inst = playlist, plugin_instance

        def _run_refresh():
            try:
                self.refresh_task.manual_update(PlaylistRefresh(pl, inst, force=True))
            except Exception:
                logger.exception("Hardware button %s: refresh failed.", label)

        logger.info("Hardware button %s: refresh started (async).", label)
        threading.Thread(
            target=_run_refresh,
            daemon=True,
            name=f"inky-hw-btn-{label}",
        ).start()

    def stop(self):
        self._stop_gpiod()

        for btn in self._buttons:
            try:
                btn.close()
            except Exception:
                logger.exception("Error closing GPIO button.")
        self._buttons.clear()
