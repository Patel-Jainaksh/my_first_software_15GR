import csv
import subprocess
import threading
import logging
from datetime import datetime
import numpy as np
from collections import deque
from Processor.AoS import BackgroundSubtractor
from Processor.depth import DepthEstimator
from models.recording import Recording
from service.frames_optimiser_service import FrameEnhancer
from models.camera import Camera
import os
import pickle
import time
import cv2
from service.log_notifier_service import emit_recording_event, emit_camera_status

from service.log_notifier_service import emit_log_event,emit_frame

from service.rtdetr_manager_service import get_next_processor

recording_states = {}  # Per camera recording state
detection_streaks = {}
no_detection_counts = {}
recording_buffers = {}
processed_frames = {}
camera_feed_status = {}  # Stores the status of each camera
frame_lock = threading.Lock()  # Prevent race conditions
camera_threads = {}  # Tracks running threads
stop_flags = {}  # Flags to control thread execution
model_selected='none'
depth_processor=DepthEstimator()
AOS_Processor=BackgroundSubtractor()
processed_frame_queue = deque(maxlen=5)
frame_optimiser=FrameEnhancer()
frame_optimiser_status=False
csv_path = "C:/AI_VIGILNET/detections/detections.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("video_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
prev_frame = None

def get_app_and_socketio():
    from app import app
    from models import db
    return app,db

def analyze_frame_conditions(frame):
    """Analyze frame conditions to determine required enhancements."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    brightness = np.mean(gray)
    
    contrast = np.std(gray)
    
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    return {
        'brightness': brightness,
        'contrast': contrast,
        'blur': laplacian_var,
        'is_low_light': brightness < 70,
        'is_low_contrast': contrast < 30,
        'is_blurry': laplacian_var < 100
    }
    

def model_changed(model_name):
    global model_selected
    model_selected = model_name
    # Chaning mode without restaring the thread !
    # app,db = get_app_and_socketio()
    # start_processing(app)

def get_selected_model_from_service():
    global model_selected
    return model_selected

def change_frame_enhancer(status):
    global frame_optimiser_status
    frame_optimiser_status = status
    # Chaning mode without restaring the thread !
    # app,db = get_app_and_socketio()
    # start_processing(app)

def get_frame_enhancer_status():
    global frame_optimiser_status
    return frame_optimiser_status


def start_processing(app):
    """ Start processing video streams for all cameras in separate threads. """
    with app.app_context():
        cameras = Camera.query.all()

    for camera in cameras:
        restart_processing(camera.id, camera.url)


def stop_processing(camera_id):
    """Stop processing frames and recording for a specific camera."""
    logger.info(f"[Camera-{camera_id}] Stopping processing...")
    # Signal the fetch-and-process thread to stop
    if camera_id in stop_flags:
        stop_flags[camera_id] = True

    # Wait for the fetch-and-process thread to end
    if camera_id in camera_threads:
        camera_threads[camera_id].join()
        del camera_threads[camera_id]

    # Stop any active recording thread in the background
    def stop_recording_thread():
        try:
            if camera_id in recording_states and recording_states[camera_id]["is_recording"]:
                logger.info(f"[Camera-{camera_id}] Stopping active recording thread...")
                recording_states[camera_id]["stop_event"].set()
                recording_states[camera_id]["thread"].join()
                recording_states[camera_id]["is_recording"] = False
                logger.info(f"[Camera-{camera_id}] Recording thread stopped.")
        except Exception as e:
            logger.error(f"[Camera-{camera_id}] Error stopping recording: {e}")

    threading.Thread(target=stop_recording_thread, daemon=True).start()

    # Cleanup all camera-related state
    recording_states.pop(camera_id, None)
    detection_streaks.pop(camera_id, None)
    no_detection_counts.pop(camera_id, None)
    recording_buffers.pop(camera_id, None)
    processed_frames.pop(camera_id, None)
    camera_feed_status.pop(camera_id, None)

    logger.info(f"[Camera-{camera_id}] Processing fully stopped and cleaned up.")



def restart_processing(camera_id, new_rtsp_url):
    """ Restart processing for a camera with a new RTSP URL. """
    stop_processing(camera_id)  # Stop existing processing
    stop_flags[camera_id] = False  # Reset stop flag

    thread = threading.Thread(target=fetch_and_process, args=(camera_id, new_rtsp_url ), daemon=True)
    camera_threads[camera_id] = thread
    thread.start()
    logger.info(f"Processing restarted for Camera ID {camera_id}")



def fetch_and_process(camera_id, rtsp_url, target_fps=1):
    frame_id = 0
    interval = 1.0 / target_fps
    last_processed_time = 0

    while not stop_flags.get(camera_id, False):
        logger.info(f"Connecting to RTSP stream for Camera ID {camera_id}...")
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            logger.error(f"Could not open RTSP stream for Camera ID {camera_id}. Retrying in 1 second...")
            with frame_lock:
                camera_feed_status[camera_id] = "Disconnected"
            emit_camera_status(camera_id, "Disconnected")
            emit_camera_status(camera_id, "Reconnecting")
            time.sleep(1)
            continue

        no_frame_count = 0

        while not stop_flags.get(camera_id, False):
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"No frame received from Camera ID {camera_id}")
                no_frame_count += 1
                time.sleep(1)
                if no_frame_count >= 5:
                    logger.error(f"No frames received for 1 second. Reconnecting Camera ID {camera_id}...")
                    with frame_lock:
                        camera_feed_status[camera_id] = "Disconnected"
                    emit_camera_status(camera_id, "Reconnecting")
                    break
                continue

            no_frame_count = 0
            current_time = time.time()
            if current_time - last_processed_time < interval:
                cap.grab()
                continue

            last_processed_time = current_time

            with frame_lock:
                camera_feed_status[camera_id] = "Receiving Frames"
            emit_camera_status(camera_id, "Receiving Frames")

            # Process frame without locking
            if frame_optimiser_status:
                frame = frame_optimiser.enhance_frame(frame)

            processed_frame = process_frame_with_ai(frame, camera_id, frame_id)
            frame_id += 1

            # Add frame to processed_frames
            with frame_lock:
            #   processed_frames[camera_id] = processed_frame
                emit_frame(camera_id, processed_frame)


            _, buffer = cv2.imencode(".jpg", processed_frame)
            frame_base64 = buffer.tobytes()

        cap.release()
    logger.info(f"Processing stopped for Camera ID {camera_id}")





def process_frame_with_ai(frame, camera_id, frame_id):
    # If we switched away from "human", stop any active recording without blocking
    if model_selected != "human":
        state = recording_states.get(camera_id)
        if state and state.get("is_recording", False) and not state.get("stop_in_progress", False):
            logger.info(f"[Camera-{camera_id}] Model switched away from 'human'. Stopping recording.")

            # ✅ Mark as stopping to avoid spawning multiple threads
            state["stop_in_progress"] = True

            def stop_rec_thread():
                try:
                    state["stop_event"].set()
                    state["thread"].join()
                    state["is_recording"] = False
                    state["stop_in_progress"] = False  # ✅ Reset after done
                    logger.info(f"[Camera-{camera_id}] Recording stopped cleanly after model switch.")
                    emit_recording_event(camera_id, "stopped")
                except Exception as e:
                    logger.error(f"[Camera-{camera_id}] Error stopping recording: {e}")
                    state["stop_in_progress"] = False  # Reset anyway

            threading.Thread(target=stop_rec_thread, daemon=True).start()


    # Dispatch based on selected model
    match model_selected:
        case "none":
            return frame
        case "human":
            return process_human_detection_with_recording(frame, camera_id, frame_id)
        case "depth":
            return depth_processor.process_frame(frame)
        case "AOS":
            return AOS_Processor.process_external_frame(frame)
        case _:
            return frame
from datetime import datetime, timedelta

# Tracks last seen timestamp per camera
camera_presence_state = {}

# Define how long absence must be to count as "new presence"
absence_threshold_seconds = 30

def should_emit_log(camera_id):
    now = datetime.now()
    last_seen = camera_presence_state.get(camera_id)

    if last_seen is None:
        # First time detection
        camera_presence_state[camera_id] = now
        return True

    time_diff = (now - last_seen).total_seconds()

    if time_diff > absence_threshold_seconds:
        # Person was absent for long enough – treat as new presence
        camera_presence_state[camera_id] = now
        return True

    # Still within active presence window – skip
    camera_presence_state[camera_id] = now  # Update even if skipping, to reset absence window
    return False

def record_and_notify_logs(detections, camera_id, frame_id):
    if not any(det["class"] == "person" for det in detections):
        # No person, don't update presence
        return

    if not should_emit_log(camera_id):
        # Person recently detected, skip redundant log
        return

    # Proceed to log
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                "date", "time", "camera_id", "frame_id",
                "class", "confidence", "xmin", "ymin", "xmax", "ymax"
            ])

        now = datetime.now()
        date_str = now.strftime("%d-%m-%y")
        time_str = now.strftime("%H:%M:%S")

        for det in detections:
            if det["class"] != "person":
                continue  # You only want to control logging for persons

            log_entry = [
                date_str, time_str,
                camera_id, frame_id,
                det["class"], det["confidence"],
                det["xmin"], det["ymin"], det["xmax"], det["ymax"]
            ]
            writer.writerow(log_entry)

            emit_log_event({
                "date": date_str,
                "time": time_str,
                "camera_id": camera_id,
                "frame_id": frame_id,
                "class": det["class"],
                "confidence": det["confidence"],
                "bbox": {
                    "xmin": det["xmin"],
                    "ymin": det["ymin"],
                    "xmax": det["xmax"],
                    "ymax": det["ymax"]
                }
            })


def process_human_detection_with_recording(frame, camera_id, frame_id, fps=1, detection_dir='detections'):
    processor = get_next_processor()  # Round-robin selection
    detections = processor.process_frame(frame_id, frame, camera_id)

    # Initialize per-camera state
    if camera_id not in recording_states:
        recording_states[camera_id] = {
            "is_recording": False,
            "thread": None,
            "stop_event": threading.Event()
        }
        detection_streaks[camera_id] = 0
        no_detection_counts[camera_id] = 0
        recording_buffers[camera_id] = deque(maxlen=30 * fps)  # 30 seconds buffer

    marked_frame = frame.copy()
    has_detection = detections is not None and len(detections) > 0

    # Update streak counters
    if has_detection:
        detection_streaks[camera_id] += 1
        no_detection_counts[camera_id] = 0
    else:
        detection_streaks[camera_id] = 0
        no_detection_counts[camera_id] += 1

    # Add frame to rolling buffer
    recording_buffers[camera_id].append(marked_frame)

    # Start recording if streak passes threshold
    if detection_streaks[camera_id] >= 5 and not recording_states[camera_id]["is_recording"]:
        if camera_id not in recording_buffers or len(recording_buffers[camera_id]) == 0:
            logger.warning(f"[Camera-{camera_id}] Buffer not ready. Skipping recording trigger.")
            return marked_frame

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("C:/AI_VIGILNET/auto_recordings/", f"{camera_id}_{timestamp}.mp4")

        stop_event = threading.Event()
        thread = threading.Thread(
            target=recorder,
            args=(camera_id, output_path, list(recording_buffers[camera_id]), stop_event, fps),
            daemon=True
        )
        thread.start()

        recording_states[camera_id] = {
            "is_recording": True,
            "thread": thread,
            "stop_event": stop_event
        }
        logger.info(f"[Camera-{camera_id}] Started recording.")
        emit_recording_event(camera_id, "started")

    # Stop recording if inactivity detected
    if recording_states[camera_id]["is_recording"] and no_detection_counts[camera_id] >= 5:
        def stop_rec_due_to_inactivity():
            try:
                recording_states[camera_id]["stop_event"].set()
                recording_states[camera_id]["thread"].join()
                recording_states[camera_id]["is_recording"] = False
                logger.info(f"[Camera-{camera_id}] Stopped recording due to inactivity.")
            except Exception as e:
                logger.error(f"[Camera-{camera_id}] Error stopping recording: {e}")

        threading.Thread(target=stop_rec_due_to_inactivity, daemon=True).start()


    # Draw bounding boxes
    if detections:
        marked_frame = draw_bounding_boxes(marked_frame, detections)
    return marked_frame

def draw_bounding_boxes(frame, detections):
    for det in detections:
        x1 = int(det["xmin"])
        y1 = int(det["ymin"])
        x2 = int(det["xmax"])
        y2 = int(det["ymax"])
        label = det["class"]
        score = det["confidence"]

        # Draw the bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Add label and confidence
        label_text = f"{label} ({score:.2f})"
        cv2.putText(frame, label_text, (x1, max(0, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return frame

def recorder(camera_id, output_path, buffer, stop_event, fps=1):
    app, db = get_app_and_socketio()
    logger.info(f"[Recorder-{camera_id}] Starting recording to {output_path}")

    height, width = buffer[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    start_time = datetime.now()

    for frame in buffer:
        writer.write(frame)

    while not stop_event.is_set() or (datetime.now() - start_time).total_seconds() < 30:
        if camera_id in recording_buffers and len(recording_buffers[camera_id]) > 0:
            writer.write(recording_buffers[camera_id][-1])
        time.sleep(1 / fps)

    writer.release()
    end_time = datetime.now()
    logger.info(f"[Recorder-{camera_id}] Stopped recording.")

    # ✅ Offload FFmpeg + DB save to separate thread
    post_thread = threading.Thread(
        target=post_process_recording,
        args=(camera_id, output_path, start_time, end_time),
        daemon=True
    )
    post_thread.start()

def stop_all_processing():
    """Stop processing for all currently active cameras."""
    camera_ids = list(camera_threads.keys())  # Get all active camera IDs
    logger.info("🛑 Stopping processing for all cameras...")

    for cam_id in camera_ids:
        try:
            stop_processing(cam_id)
        except Exception as e:
            logger.error(f"❌ Failed to stop Camera-{cam_id}: {e}")


def post_process_recording(camera_id, input_path, start_time, end_time):
    app, db = get_app_and_socketio()
    final_path = input_path
    try:
        browser_friendly_path = input_path.replace(".mp4", "_web.mp4")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-movflags", "+faststart",
            browser_friendly_path
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        os.remove(input_path)
        final_path = browser_friendly_path
        logger.info(f"[PostProcess-{camera_id}] FFmpeg post-processing complete.")
    except Exception as e:
        logger.error(f"[PostProcess-{camera_id}] FFmpeg conversion failed: {e}")

    try:
        with app.app_context():
            filename = os.path.basename(final_path)
            new_recording = Recording(
                file_path=filename,
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                camera_id=camera_id
            )
            db.session.add(new_recording)
            db.session.commit()
            logger.info(f"[PostProcess-{camera_id}] Recording saved to DB.")
    except Exception as e:
        logger.error(f"[PostProcess-{camera_id}] Failed to save to DB: {e}")