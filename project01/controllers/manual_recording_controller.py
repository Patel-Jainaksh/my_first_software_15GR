from datetime import datetime
import os
import threading
from models.camera import Camera
from flask import Blueprint
from service.manual_recording_service import record_rtsp_stream
from flask import request, jsonify

manual_recording_bp = Blueprint('manual_recording', __name__)

recording_states = {}
manual_recording_threads = {}
manual_recording_flags = {}
manual_recording_states = {}

@manual_recording_bp.route('/api/manual_recordings', methods=['POST'])
def toggle_manual_recording():
    data = request.get_json()
    camera_id = data.get("camera_id")

    if not camera_id:
        return jsonify({"error": "camera_id is required"}), 400

    is_recording = manual_recording_states.get(camera_id, False)

    if is_recording:
        manual_recording_flags[camera_id].set()
        manual_recording_threads[camera_id].join()
        manual_recording_states[camera_id] = False
        return jsonify({"camera_id": camera_id, "recording": False})

    # Fetch RTSP URL from DB
    camera = Camera.query.filter_by(id=camera_id).first()
    if not camera:
        return jsonify({"error": "Camera not found"}), 404

    rtsp_url = camera.url
    start_time = datetime.now()
    save_dir = "C:\AI_VIGILNET\manual_recordings"
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{camera_id}_{start_time.strftime('%Y%m%d_%H%M%S')}.mp4"
    file_path = os.path.join(save_dir, filename)

    stop_event = threading.Event()
    thread = threading.Thread(
        target=record_rtsp_stream,
        args=(camera_id, rtsp_url, file_path, start_time, stop_event),
        daemon=True
    )
    thread.start()

    manual_recording_threads[camera_id] = thread
    manual_recording_flags[camera_id] = stop_event
    manual_recording_states[camera_id] = True

    return jsonify({"camera_id": camera_id, "recording": True})




@manual_recording_bp.route('/api/manual_recordings', methods=['GET'])
def get_manual_recording_status():
    return jsonify({
        cam_id: True for cam_id, state in manual_recording_states.items() if state
    }), 200
