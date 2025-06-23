def handle_connect():
    print()

def handle_disconnect():
    print()

def handle_recording_connect():
    print()

def handle_recording_disconnect():
    print()

def handle_camera_connect():
    print()

def handle_camera_disconnect():
    print()

def register_socket_handlers(socketio):
    # Logs namespace
    socketio.on_event("connect", handle_connect, namespace="/logs")
    socketio.on_event("disconnect", handle_disconnect, namespace="/logs")

    # ✅ Recordings namespace
    socketio.on_event("connect", handle_recording_connect, namespace="/recordings")
    socketio.on_event("disconnect", handle_recording_disconnect, namespace="/recordings")
    socketio.on_event("connect", handle_camera_connect, namespace="/cameras")
    socketio.on_event("disconnect", handle_camera_disconnect, namespace="/cameras")