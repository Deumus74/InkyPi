"""One-time in-memory migration of device.json for hardware buttons and playlist schedule mode."""

from __future__ import annotations

import logging
from typing import Optional

from model import (
    HARDWARE_BUTTON_LABELS,
    PLAYLIST_SCHEDULE_MODES,
    PLAYLIST_SCHEDULE_MODE_SCHEDULE_ONLY,
)

logger = logging.getLogger(__name__)


def normalize_device_config(config: dict) -> None:
    """Mutate loaded device config: move legacy keys, migrate bindings to plugin instances."""
    pc = config.setdefault("playlist_config", {})
    if not isinstance(pc, dict):
        return

    hb = config.get("hardware_buttons")
    if hb is not None and not isinstance(hb, dict):
        config["hardware_buttons"] = {}
        hb = config["hardware_buttons"]

    if isinstance(hb, dict):
        legacy_mode = hb.pop("playlist_schedule_mode", None)
        if legacy_mode and legacy_mode in PLAYLIST_SCHEDULE_MODES:
            if not pc.get("playlist_schedule_mode"):
                pc["playlist_schedule_mode"] = legacy_mode
                logger.info("Moved playlist_schedule_mode from hardware_buttons to playlist_config.")

        bindings = hb.pop("bindings", None)
        hb.pop("enabled", None)

        if bindings and isinstance(bindings, list):
            _migrate_legacy_bindings(config, bindings)

    if not pc.get("playlist_schedule_mode"):
        pc["playlist_schedule_mode"] = PLAYLIST_SCHEDULE_MODE_SCHEDULE_ONLY


def _migrate_legacy_bindings(config: dict, bindings: list) -> None:
    playlists = (config.get("playlist_config") or {}).get("playlists") or []
    if not playlists:
        return
    for idx, letter in enumerate(HARDWARE_BUTTON_LABELS):
        if idx >= len(bindings):
            break
        b = bindings[idx]
        if not isinstance(b, dict):
            continue
        pname = (b.get("playlist") or "").strip()
        plugin_id = (b.get("plugin_id") or "").strip()
        instance = (b.get("plugin_instance") or "").strip()
        if not (pname and plugin_id and instance):
            continue
        for pl in playlists:
            if pl.get("name") != pname:
                continue
            for pinst in pl.get("plugins") or []:
                if (
                    pinst.get("plugin_id") == plugin_id
                    and pinst.get("name") == instance
                ):
                    pinst["hardware_button"] = letter
                    logger.info(
                        "Migrated legacy hardware button %s to %s / %s / %s",
                        letter,
                        pname,
                        plugin_id,
                        instance,
                    )
                    break
            break


def hardware_button_assignments(playlist_manager):
    """Return ordered list of (label, playlist_name, plugin_id, instance_name) — first occurrence wins per label."""
    seen = {}
    order = []
    for pl in playlist_manager.playlists:
        for inst in pl.plugins:
            lbl = inst.hardware_button
            if not lbl:
                continue
            if lbl not in HARDWARE_BUTTON_LABELS:
                continue
            if lbl in seen:
                prev = seen[lbl]
                logger.warning(
                    "Duplicate hardware_button %s: keeping %s/%s, ignoring %s/%s",
                    lbl,
                    prev[0],
                    prev[1],
                    pl.name,
                    inst.name,
                )
                continue
            seen[lbl] = (pl.name, inst.name)
            order.append((lbl, pl.name, inst.plugin_id, inst.name))
    return order


def hardware_button_claims_first_win(playlist_manager):
    """Which instance (row key) owns each label under first-scan-wins semantics."""
    claims = {}
    for pl in playlist_manager.playlists:
        for inst in pl.plugins:
            lbl = inst.hardware_button
            if lbl and lbl in HARDWARE_BUTTON_LABELS and lbl not in claims:
                claims[lbl] = f"{pl.name}|{inst.plugin_id}|{inst.name}"
    return claims


def gpios_from_config(hb: Optional[dict]):
    """Map label -> int BCM pin; missing labels use defaults (5,6,16,24)."""
    defaults = dict(zip(HARDWARE_BUTTON_LABELS, (5, 6, 16, 24)))
    out = dict(defaults)
    if not hb or not isinstance(hb.get("gpios"), dict):
        return out
    for k, v in hb["gpios"].items():
        key = str(k).strip().upper()
        if key not in HARDWARE_BUTTON_LABELS:
            continue
        try:
            out[key] = int(v)
        except (TypeError, ValueError):
            logger.warning("Invalid GPIO %r for button %s; using default.", v, key)
    return out
