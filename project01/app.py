import os
import re
import threading
from flask import Flask, Response, abort, redirect, request, flash, send_file, session, url_for, send_from_directory
from models import db, init_db
from controllers import auth_controller, operator_controller, admin_controller, nvr_controller, camera_controller, \
    log_controller, recording_controller, manual_recording_controller
from service.video_processor_service import start_processing
import multiprocessing
from service.rtdetr_manager_service import get_processors
from flask_socketio import SocketIO
from service.socket_events_service import register_socket_handlers
from service.log_notifier_service import init_notifier, emit_from_queue
log_emit_queue = multiprocessing.Queue()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://agx:rootroot@localhost:5432/ai_sur'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'jhdbfhsbdhbfuygdfhb3egwjhb2mn22382882!@!@#!@#SDSFDF!@WEQWDSDCSEQe'
init_db(app)

# @app.before_request
# def check_auth():
#     allowed_routes = ['auth.login', 'static','admin.recreate_processors']
#
#     endpoint = request.endpoint
#     path = request.path
#
#     if endpoint and (endpoint in allowed_routes or endpoint.startswith('static')):
#         return None
#
#     # Enforce login
#     if 'username' not in session:
#         flash("Please log in first.", "danger")
#         return redirect(url_for('auth.login'))
#
#     user_role = session.get('role')
#
#     if path.startswith('/operator') and user_role != 'operator':
#         flash("Unauthorized access. Operator role required.", "danger")
#         return redirect(url_for('auth.login'))
#
#     if path.startswith('/admin') and user_role != 'admin':
#         flash("Unauthorized access. Admin role required.", "danger")
#         return redirect(url_for('auth.login'))
#
#     return None

app.register_blueprint(auth_controller.auth_bp)
app.register_blueprint(operator_controller.operator_bp)
app.register_blueprint(admin_controller.admin_bp)
app.register_blueprint(nvr_controller.nvr_bp)
app.register_blueprint(camera_controller.camera_bp)
app.register_blueprint(log_controller.log_bp)
app.register_blueprint(recording_controller.recording_bp)
app.register_blueprint(manual_recording_controller.manual_recording_bp)

def initialize_directories_and_files():
    folder_path = r"C:\AI_VIGILNET\detections"
    os.makedirs(folder_path, exist_ok=True)
    folder_path = r"C:\AI_VIGILNET\auto_recordings"
    os.makedirs(folder_path, exist_ok=True)
    folder_path = r"C:\AI_VIGILNET\manual_recordings"
    os.makedirs(folder_path, exist_ok=True)
    detection_csv_file = r"C:\AI_VIGILNET\detections\detections.csv"
    if not os.path.exists(detection_csv_file):
        open(detection_csv_file, "w").close()



if __name__ == "__main__":
    init_notifier(socketio)
    initialize_directories_and_files()
    processor = get_processors()
    register_socket_handlers(socketio)

    with app.app_context():
        db.create_all()
        threading.Thread(target=emit_from_queue, args=(log_emit_queue,), daemon=True).start()
        threading.Thread(target=start_processing, args=(app,), daemon=True).start()

    # ✅ Correct method to launch Flask-SocketIO app
    socketio.run(app, debug=False, port=8081, host="0.0.0.0")

