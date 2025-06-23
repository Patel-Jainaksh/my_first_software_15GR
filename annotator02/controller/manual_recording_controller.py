import shutil
import os
import uuid
from flask import Blueprint, jsonify, current_app, request
from datetime import datetime
import threading

from extensions import db
from models import ManualRecording, Camera
from models.frame import Frame
from service.extraction_service import get_status
from service.extraction_service import extract_frames

manual_bp = Blueprint('manual_bp', __name__)


@manual_bp.route('/api/manual_recordings', methods=['GET'])
def get_manual_recordings():
    recordings = ManualRecording.query.all()
    result = []
    for idx, rec in enumerate(recordings, start=1):
        camera = Camera.query.get(rec.camera_id)

        # Attempt to parse start_time and end_time with two different formats
        try:
            start = datetime.strptime(rec.start_time, "%Y-%m-%d %H:%M:%S.%f")  # With microseconds
        except ValueError:
            start = datetime.strptime(rec.start_time, "%Y-%m-%d %H:%M:%S")  # Without microseconds

        try:
            end = datetime.strptime(rec.end_time, "%Y-%m-%d %H:%M:%S.%f")  # With microseconds
        except ValueError:
            end = datetime.strptime(rec.end_time, "%Y-%m-%d %H:%M:%S")  # Without microseconds

        # Calculate duration
        duration = str(end - start)

        result.append({
            'id': rec.id,  # ✅ Pass ID for JS button use
            'sr_no': idx,
            'file_path': rec.file_path,
            'duration': duration,
            'channel': camera.channel if camera else 'N/A',
            'extract_frame': rec.extract_frame,
            'extract_status': get_status(rec.id),  # ✅ Optional, use to disable button in JS
        })
    return jsonify(result)


@manual_bp.route('/api/manual_recordings/<int:id>', methods=['DELETE'])
def delete_manual_recording(id):
    rec = ManualRecording.query.get_or_404(id)

    # Delete all associated frames
    Frame.query.filter_by(manual_recording_id=id).delete()

    # Delete associated folder (optional)
    frame_dir = os.path.join('static', 'frames', str(id))
    if os.path.exists(frame_dir):
        shutil.rmtree(frame_dir)

    # Delete the recording entry
    db.session.delete(rec)
    db.session.commit()

    return jsonify({'message': 'Recording and associated frames deleted successfully.'})



@manual_bp.route('/api/manual_recordings/<int:id>/extract', methods=['POST'])
def start_extraction(id):
    from models.manual_recording import ManualRecording

    recording = ManualRecording.query.get_or_404(id)
    if get_status(id) in ['in_progress', 'completed']:
        return jsonify({'message': 'Extraction already in progress or done.'}), 400

    # ✅ Pass app to the thread explicitly
    thread = threading.Thread(target=extract_frames, args=(id, recording.file_path, current_app._get_current_object()))
    thread.start()

    return jsonify({'message': 'Extraction started'})


@manual_bp.route("/upload_video", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"message": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    allowed_ext = {"mp4", "avi", "mov", "webm", "mkv", "flv"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_ext:
        return jsonify({"message": "Invalid file format"}), 400

    # Save file
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Create DB entry without camera_id
    recording = ManualRecording(
        file_path=filepath,
        start_time=str(datetime.now()),
        end_time=str(datetime.now()),  # update this if needed
        extract_frame=False
    )
    db.session.add(recording)
    db.session.commit()

    return jsonify({"message": "Upload successful", "id": recording.id}), 200