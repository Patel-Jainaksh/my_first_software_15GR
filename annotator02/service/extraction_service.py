import os
import cv2

from extensions import db, socketio
from models import ManualRecording
from models.frame import Frame

extraction_status = {}

def set_status(recording_id, status):
    extraction_status[recording_id] = status

def get_status(recording_id):
    return extraction_status.get(recording_id, 'not_started')

def extract_frames(recording_id, file_path, app):
    from time import sleep
    from service.extraction_service import set_status

    set_status(recording_id, 'in_progress')

    with app.app_context():
        recording = ManualRecording.query.get(recording_id)
        if not recording:
            set_status(recording_id, 'failed')
            return

        video_path = recording.file_path
        save_dir = os.path.join('annotator02','static', 'frames', str(recording_id))
        os.makedirs(save_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames // fps

        for sec in range(duration_sec):
            cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
            sec_frames = []

            for i in range(fps):
                ret, frame = cap.read()
                if not ret:
                    break

                # Compute current timestamp in milliseconds
                millis = int(cap.get(cv2.CAP_PROP_POS_MSEC))

                # Score by resolution
                height, width = frame.shape[:2]
                resolution_score = height * width
                sec_frames.append((resolution_score, frame.copy(), millis))

            # Sort by resolution, keep top 5
            sec_frames.sort(key=lambda x: x[0], reverse=True)
            top_frames = sec_frames[:5]

            for _, frame, millis in top_frames:
                filename = f"{recording_id}_{millis}.jpg"
                frame_path = os.path.join(save_dir, filename)
                cv2.imwrite(frame_path, frame)
                frame_data_path="/static/frames/"+str(recording_id)+'/'+filename
                print(frame_data_path)
                # Save to DB
                db_frame = Frame(
                    frame_path=frame_data_path,
                    manual_recording_id=recording_id
                )
                db.session.add(db_frame)

        db.session.commit()

        # Mark extraction complete
        recording.extract_frame = True
        db.session.commit()
        set_status(recording_id, 'completed')

        socketio.emit('extraction_complete', {
            'recording_id': recording_id,
            'message': 'Frame extraction completed. Start annotation.'
        })

        cap.release()

