import os
import uuid

from flask import Flask
from flask import request, jsonify

# Import controllers (but not individual blueprints!)
from controller import manual_recording_controller, test_controller, annotate_controller, training_controller,verify_dataset_controller
from extensions import db, socketio
from service.rtdetr_manager_service import get_processor

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://agx:rootroot@localhost:5432/ai_sur'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init extensions
db.init_app(app)
socketio.init_app(app)

with app.app_context():
    db.create_all()

# File upload config
app.config['UPLOAD_FOLDER'] = 'annotator02/static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register Blueprints AFTER they are fully defined
app.register_blueprint(test_controller.test_bp)
app.register_blueprint(manual_recording_controller.manual_bp)
app.register_blueprint(annotate_controller.annotate_bp)
app.register_blueprint(training_controller.training_bp)
app.register_blueprint(verify_dataset_controller.verify_data_set_bp)


@app.route("/upload_video", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"message": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    if file and file.filename.lower().endswith((".mp4", ".avi", ".mov")):
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        # Optionally: Save to DB or update your video list here
        return jsonify({"message": "Upload successful", "path": filepath}), 200

    return jsonify({"message": "Invalid file format"}), 400

@app.route("/api/videos", methods=["GET"])
def list_uploaded_videos():
    folder = app.config["UPLOAD_FOLDER"]
    videos = []

    for idx, filename in enumerate(os.listdir(folder), start=1):
        if allowed_file(filename):
            filepath = os.path.join(folder, filename)
            duration = "00:00"  # Optional: use OpenCV to extract duration
            channel = "Unknown"
            videos.append({
                "id": idx,
                "file_path": filename,
                "duration": duration,
                "channel": channel
            })

    return jsonify(videos)



if __name__ == '__main__':
    get_processor()
    socketio.run(app, debug=False, port=8082, host="0.0.0.0")
