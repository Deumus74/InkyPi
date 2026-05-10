from flask import Blueprint, request, jsonify, current_app, render_template
from utils.time_utils import calculate_seconds
from utils.device_config_normalize import hardware_button_claims_first_win
from model import HARDWARE_BUTTON_LABELS
from hardware.inky_impression_buttons import schedule_hardware_buttons_restart
import json
from datetime import datetime, timedelta
import os
import logging
from utils.app_utils import resolve_path, handle_request_files, parse_form


logger = logging.getLogger(__name__)
playlist_bp = Blueprint("playlist", __name__)

@playlist_bp.route('/add_plugin', methods=['POST'])
def add_plugin():
    device_config = current_app.config['DEVICE_CONFIG']
    refresh_task = current_app.config['REFRESH_TASK']
    playlist_manager = device_config.get_playlist_manager()

    try:
        plugin_settings = parse_form(request.form)
        refresh_settings = json.loads(plugin_settings.pop("refresh_settings"))
        plugin_id = plugin_settings.pop("plugin_id")

        playlist = refresh_settings.get('playlist')
        instance_name = refresh_settings.get('instance_name')
        if not playlist:
            return jsonify({"error": "Playlist name is required"}), 400
        if not instance_name or not instance_name.strip():
            return jsonify({"error": "Instance name is required"}), 400
        if not all(char.isalpha() or char.isspace() or char.isnumeric() for char in instance_name):
            return jsonify({"error": "Instance name can only contain alphanumeric characters and spaces"}), 400
        refresh_type = refresh_settings.get('refreshType')
        if not refresh_type or refresh_type not in ["interval", "scheduled"]:
            return jsonify({"error": "Refresh type is required"}), 400

        existing = playlist_manager.find_plugin(plugin_id, instance_name)
        if existing:
            return jsonify({"error": f"Plugin instance '{instance_name}' already exists"}), 400

        if refresh_type == "interval":
            unit, interval = refresh_settings.get('unit'), refresh_settings.get("interval")
            if not unit or unit not in ["minute", "hour", "day"]:
                return jsonify({"error": "Refresh interval unit is required"}), 400
            if not interval:
                return jsonify({"error": "Refresh interval is required"}), 400
            refresh_interval_seconds = calculate_seconds(int(interval), unit)
            refresh_config = {"interval": refresh_interval_seconds}
        else:
            refresh_time = refresh_settings.get('refreshTime')
            if not refresh_settings.get('refreshTime'):
                return jsonify({"error": "Refresh time is required"}), 400
            refresh_config = {"scheduled": refresh_time}

        plugin_settings.update(handle_request_files(request.files))
        plugin_dict = {
            "plugin_id": plugin_id,
            "refresh": refresh_config,
            "plugin_settings": plugin_settings,
            "name": instance_name
        }
        result = playlist_manager.add_plugin_to_playlist(playlist, plugin_dict)
        if not result:
            return jsonify({"error": "Failed to add to playlist"}), 500

        device_config.write_config()
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    return jsonify({"success": True, "message": "Scheduled refresh configured."})

@playlist_bp.route('/playlist')
def playlists():
    device_config = current_app.config['DEVICE_CONFIG']
    playlist_manager = device_config.get_playlist_manager()
    refresh_info = device_config.get_refresh_info()
    plugins_list = device_config.get_plugins()
    hb_claims = hardware_button_claims_first_win(playlist_manager)
    seen = set()
    duplicate_hw_button = False
    for pl in playlist_manager.playlists:
        for inst in pl.plugins:
            lbl = inst.hardware_button
            if not lbl:
                continue
            if lbl in seen:
                duplicate_hw_button = True
                break
            seen.add(lbl)
        if duplicate_hw_button:
            break

    return render_template(
        'playlist.html',
        playlist_config=playlist_manager.to_dict(),
        refresh_info=refresh_info.to_dict(),
        plugins={p["id"]: p for p in plugins_list},
        hardware_button_claims=hb_claims,
        hardware_button_duplicate=duplicate_hw_button,
        hardware_button_labels=list(HARDWARE_BUTTON_LABELS),
    )


@playlist_bp.route("/set_instance_hardware_button", methods=["POST", "PUT"])
def set_instance_hardware_button():
    device_config = current_app.config["DEVICE_CONFIG"]
    playlist_manager = device_config.get_playlist_manager()
    data = request.get_json() or {}
    playlist_name = data.get("playlist_name")
    plugin_id = data.get("plugin_id")
    instance_name = data.get("plugin_instance")
    raw = data.get("hardware_button")
    if raw is None or str(raw).strip() == "":
        label = None
    else:
        label = str(raw).strip().upper()
        if label not in HARDWARE_BUTTON_LABELS:
            return jsonify({"error": "hardware_button must be A, B, C, or D, or empty."}), 400

    playlist = playlist_manager.get_playlist(playlist_name)
    if not playlist:
        return jsonify({"error": "Playlist not found"}), 400
    pi = playlist.find_plugin(plugin_id, instance_name)
    if not pi:
        return jsonify({"error": "Plugin instance not found"}), 400

    if label:
        for pl in playlist_manager.playlists:
            for inst in pl.plugins:
                if pl.name == playlist_name and inst.plugin_id == plugin_id and inst.name == instance_name:
                    continue
                if inst.hardware_button == label:
                    return jsonify(
                        {"error": f'Button "{label}" is already assigned elsewhere. Clear it first.'}
                    ), 400

    pi.hardware_button = label
    device_config.write_config()

    refresh_task = current_app.config["REFRESH_TASK"]
    refresh_task.signal_config_change()
    schedule_hardware_buttons_restart()

    return jsonify({"success": True, "message": "Hardware button updated."})

@playlist_bp.route('/create_playlist', methods=['POST'])
def create_playlist():
    device_config = current_app.config['DEVICE_CONFIG']
    playlist_manager = device_config.get_playlist_manager()

    data = request.json
    playlist_name = data.get("playlist_name")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not playlist_name or not playlist_name.strip():
        return jsonify({"error": "Playlist name is required"}), 400
    if not start_time or not end_time:
        return jsonify({"error": "Start time and End time are required"}), 400

    try:
        playlist = playlist_manager.get_playlist(playlist_name)
        if playlist:
            return jsonify({"error": f"Playlist with name '{playlist_name}' already exists"}), 400

        result = playlist_manager.add_playlist(playlist_name, start_time, end_time)
        if not result:
            return jsonify({"error": "Failed to create playlist"}), 500

        # save changes to device config file
        device_config.write_config()

    except Exception as e:
        logger.exception("EXCEPTION CAUGHT: " + str(e))
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    return jsonify({"success": True, "message": "Created new Playlist!"})


@playlist_bp.route('/update_playlist/<string:playlist_name>', methods=['PUT'])
def update_playlist(playlist_name):
    device_config = current_app.config['DEVICE_CONFIG']
    playlist_manager = device_config.get_playlist_manager()

    data = request.get_json()

    new_name = data.get("new_name")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    if not new_name or not start_time or not end_time:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    playlist = playlist_manager.get_playlist(playlist_name)
    if not playlist:
        return jsonify({"error": f"Playlist '{playlist_name}' does not exist"}), 400

    result = playlist_manager.update_playlist(playlist_name, new_name, start_time, end_time)
    if not result:
        return jsonify({"error": "Failed to delete playlist"}), 500
    device_config.write_config()

    return jsonify({"success": True, "message": f"Updated playlist '{playlist_name}'!"})

@playlist_bp.route('/delete_playlist/<string:playlist_name>', methods=['DELETE'])
def delete_playlist(playlist_name):
    device_config = current_app.config['DEVICE_CONFIG']
    playlist_manager = device_config.get_playlist_manager()

    if not playlist_name:
        return jsonify({"error": f"Playlist name is required"}), 400

    playlist = playlist_manager.get_playlist(playlist_name)
    if not playlist:
        return jsonify({"error": f"Playlist '{playlist_name}' does not exist"}), 400

    # Delete all images associated with plugin instances in this playlist
    from blueprints.plugin import _delete_plugin_instance_images
    for plugin_instance in playlist.plugins:
        _delete_plugin_instance_images(device_config, plugin_instance)

    playlist_manager.delete_playlist(playlist_name)
    device_config.write_config()

    return jsonify({"success": True, "message": f"Deleted playlist '{playlist_name}'!"})

@playlist_bp.app_template_filter('format_relative_time')
def format_relative_time(iso_date_string):
    # Parse the input ISO date string
    dt = datetime.fromisoformat(iso_date_string)

    # Get the timezone from the parsed datetime
    if dt.tzinfo is None:
        raise ValueError("Input datetime doesn't have a timezone.")

    # Get the current time in the same timezone as the input datetime
    now = datetime.now(dt.tzinfo)
    delta = now - dt

    # Compute time difference
    diff_seconds = delta.total_seconds()
    diff_minutes = diff_seconds / 60

    # Define formatting
    time_format = "%I:%M %p"  # Example: 04:30 PM
    month_day_format = "%b %d at " + time_format  # Example: Feb 12 at 04:30 PM

    # Determine relative time string
    if diff_seconds < 120:
        return "just now"
    elif diff_minutes < 60:
        return f"{int(diff_minutes)} minutes ago"
    elif dt.date() == now.date():
        return "today at " + dt.strftime(time_format).lstrip("0")
    elif dt.date() == (now.date() - timedelta(days=1)):
        return "yesterday at " + dt.strftime(time_format).lstrip("0")
    else:
        return dt.strftime(month_day_format).replace(" 0", " ")  # Removes leading zero in day
