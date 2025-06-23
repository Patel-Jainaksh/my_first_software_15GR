import threading
import time
import cv2
from flask import Blueprint, render_template, request, jsonify,Response,current_app
from models.manual_recording import ManualRecording
from models.recording import Recording
from service.video_processor_service import processed_frames, restart_processing, stop_processing
from models import db
from models.camera import Camera

camera_bp = Blueprint('camera', __name__)

@camera_bp.route('/admin/cameras', methods=['GET'])
def camera():
    return render_template('/admin/cameras.html')

@camera_bp.route("/admin/camera/list/<int:nvr_id>", methods=["GET"])
def get_cameras_by_nvr(nvr_id):
    try:
        # Query all cameras belonging to the given NVR ID
        cameras = Camera.query.filter_by(nvr_id=nvr_id).all()

        if not cameras:
            return jsonify({"message": "No cameras found for this NVR"}), 200

        # Convert camera data to JSON
        camera_list = [
            {
                "id": cam.id,
                "channel": cam.channel,
                "url": cam.url,
                "channel_url": cam.channel_url,
                "description": cam.description,
                "nvr_id": cam.nvr_id
            }
            for cam in cameras
        ]

        return jsonify(camera_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@camera_bp.route("/admin/camera/<int:id>", methods=["GET"])
def get_camera_by_id(id):
    try:
        # Query all cameras belonging to the given NVR ID
        cameras = Camera.query.filter_by(id=id).all()

        if not cameras:
            return jsonify({"message": "No cameras found for this id"}), 200

        # Convert camera data to JSON
        camera_list = [
            {
                "id": cam.id,
                "channel": cam.channel,
                "url": cam.url,
                "channel_url": cam.channel_url,
                "description": cam.description,
                "nvr_id": cam.nvr_id
            }
            for cam in cameras
        ]

        return jsonify(camera_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@camera_bp.route("/admin/camera/list", methods=["GET"])
def get_all_cameras():
    try:
        # Query all cameras belonging to the given NVR ID
        cameras = Camera.query.all()

        if not cameras:
            return jsonify([]), 200

        # Convert camera data to JSON
        camera_list = [
            {
                "id": cam.id,
                "channel": cam.channel,
                "url": cam.url,
                "description": cam.description,
                "nvr_id": cam.nvr_id
            }
            for cam in cameras
        ]

        return jsonify(camera_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

import cv2

@camera_bp.route("/admin/camera/addCamera", methods=["POST"])
def add_camera():
    # try:
        socketio = current_app.extensions["socketio"]
        data = request.json

        # Extract fields
        channel = data.get("channel")
        url = data.get("url")
        description = data.get("description")
        nvr_id = data.get("nvr_id")
        channel_url = data.get("channel_url")

        # Validation
        if not all([channel, url, description, nvr_id, channel_url]):
            return jsonify({"error": "All fields are required!"}), 400


        print("Checking started")
        result = {"success": False}


        def check_rtsp_stream(url, result_dict):
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            success, frame = cap.read()
            cap.release()
            result_dict["success"] = success and frame is not None


        # Threaded check to avoid OpenCV blocking main request
        thread = threading.Thread(target=check_rtsp_stream, args=(url, result))
        thread.start()
        thread.join(timeout=10)

        if thread.is_alive() or not result["success"]:
            return jsonify({"error": "Camera feed not available or timed out."}), 400

        print("Stream check complete")

# ✅ Add to DB if feed is valid
        new_camera = Camera(
            channel=channel,
            url=url,
            description=description,
            nvr_id=nvr_id,
            channel_url=channel_url
        )

        db.session.add(new_camera)
        db.session.commit()


        print("Database insert complete")
        restart_processing(new_camera.id, new_camera.url)


        print("Request complete")

        return jsonify({"status": True, "id": new_camera.id}), 201

    # except Exception as e:
    #     db.session.rollback()
    #     return jsonify({"error": str(e)}), 500


@camera_bp.route('/admin/camera/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    socketio = current_app.extensions["socketio"]
    data = request.get_json()

    camera = Camera.query.get(camera_id)
    if not camera:
        return jsonify({'error': 'Camera not found'}), 404

    # Extract new values from request (fallback to old ones)
    new_channel = data.get('channel', camera.channel)
    new_url = data.get('url', camera.url)
    new_channel_url = data.get('channel_url', camera.channel_url)
    new_description = data.get('description', camera.description)
    new_nvr_id = data.get('nvr_id', camera.nvr_id)

    # 🔍 Validate RTSP feed using OpenCV before updating
    cap = cv2.VideoCapture(new_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    success, frame = False, None
    start_time = time.time()

    # Retry reading for up to 3 seconds
    while time.time() - start_time < 3:
        success, frame = cap.read()
        if success:
            break
        time.sleep(0.2)

    cap.release()


    if not success or frame is None:
        return jsonify({'error': 'Camera feed not available or invalid RTSP URL.'}), 400

    # ✅ Proceed to update
    camera.channel = new_channel
    camera.url = new_url
    camera.channel_url = new_channel_url
    camera.description = new_description
    camera.nvr_id = new_nvr_id

    try:
        db.session.commit()
        restart_processing(camera.id, camera.url)
        return jsonify({'message': 'Camera updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@camera_bp.route('/stream/<int:camera_id>')
def stream(camera_id):
    """ Stream processed frames for a given camera. """
    def generate():
        while True:

            if camera_id in processed_frames:
                frame = processed_frames[camera_id]
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                time.sleep(0.3)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')



@camera_bp.route('/admin/camera/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    camera = Camera.query.get(camera_id)
    if not camera:
        return jsonify({'error': 'Camera not found'}), 404

    try:
        # Unlink camera_id references
        Recording.query.filter_by(camera_id=camera.id).update({Recording.camera_id: None})
        ManualRecording.query.filter_by(camera_id=camera.id).update({ManualRecording.camera_id: None})

        db.session.delete(camera)
        db.session.commit()

        stop_processing(camera.id)

        return jsonify({'message': 'Camera deleted, related records unlinked'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
