from datetime import datetime
import logging
import time
import cv2
from models.manual_recording import ManualRecording
from service.video_processor_service import get_app_and_socketio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("video_processing.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def record_rtsp_stream(camera_id, rtsp_url, output_path, start_time, stop_event):
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        logger.error(f"[ManualRecording-{camera_id}] Failed to open RTSP stream")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    stream_fps = cap.get(cv2.CAP_PROP_FPS)
    fps = stream_fps if stream_fps and stream_fps > 1 else 15  # fallback if RTSP doesn't provide

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    logger.info(f"[ManualRecording-{camera_id}] Recording started -> {output_path} at {fps} FPS")

    frame_count = 0
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            logger.warning(f"[ManualRecording-{camera_id}] Failed to read frame, retrying...")
            time.sleep(0.05)
            continue
        writer.write(frame)
        frame_count += 1

    # Optional: write a few more frames (flush)
    flush_start = time.time()
    while (time.time() - flush_start) < 1.0:
        ret, frame = cap.read()
        if not ret:
            break
        writer.write(frame)
        frame_count += 1

    logger.info(f"[ManualRecording-{camera_id}] Total frames written: {frame_count}")
    cap.release()
    writer.release()

    end_time = datetime.now()

    logger.info(f"[ManualRecording-{camera_id}] Recording stopped")

    app, db = get_app_and_socketio()
    with app.app_context():
        recording = ManualRecording(
            file_path=output_path,
            start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            camera_id=camera_id,
            extract_frame=False
        )
        db.session.add(recording)
        db.session.commit()
        logger.info(f"[ManualRecording-{camera_id}] Saved to DB")
