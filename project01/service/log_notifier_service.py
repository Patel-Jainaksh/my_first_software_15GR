# service/log_notifier.py
import cv2

socketio_instance = None

def init_notifier(socketio):
    global socketio_instance
    socketio_instance = socketio

def emit_from_queue(emit_queue):
    while True:
        log = emit_queue.get()
        if socketio_instance:
            socketio_instance.emit('new_log', log, namespace='/logs')

# ✅ New helper for recording events
def emit_recording_event(camera_id, status):
    if socketio_instance:
        socketio_instance.emit('recording_event', {
            "camera_id": camera_id,
            "status": status  # "started" or "stopped"
        }, namespace='/recordings')

def emit_camera_status(camera_id, status):
    if socketio_instance:
        socketio_instance.emit('camera_status', {
            "camera_id": camera_id,
            "status": status
        }, namespace='/cameras')

def emit_log_event(log):
    if socketio_instance:
        socketio_instance.emit('new_log', log, namespace='/logs')

from base64 import b64encode

def emit_frame(camera_id, frame):
    if socketio_instance:
        _, buffer = cv2.imencode(".jpg", frame)
        b64 = b64encode(buffer).decode("utf-8")
        socketio_instance.emit('frame', {
            'camera_id': camera_id,
            'image': b64
        }, namespace='/cameras')
