# controller/annotate_controller.py
import os
from datetime import datetime
from shutil import copyfile
import cv2

from models.frame import Frame
from flask import Blueprint, jsonify, render_template, request

from service.rtdetr_manager_service import get_processor

annotate_bp = Blueprint('annotate_bp', __name__)

@annotate_bp.route('/annotate/<int:recording_id>')
def annotate_page(recording_id):
    return render_template('annotate.html', recording_id=recording_id)

@annotate_bp.route('/api/frames/<int:recording_id>')
def get_frames_for_recording(recording_id):
    from models.frame import Frame
    frames = Frame.query.filter_by(manual_recording_id=recording_id).all()
    return jsonify([
        {'id': f.id, 'frame_path': f.frame_path}
        for f in frames
    ])

@annotate_bp.route('/api/save_annotations', methods=['POST'])
def save_annotations():
    data = request.get_json()
    print("Received annotation payload:", data)

    if not isinstance(data, list):
        return jsonify({"error": "Expected a list of frame annotations"}), 400

    frame_ids = [int(item["frame_id"]) for item in data]
    frames = Frame.query.filter(Frame.id.in_(frame_ids)).all()
    frame_lookup = {f.id: f.frame_path for f in frames}
    print("Found frame IDs in DB:", list(frame_lookup.keys()))

    annotation_dir = os.path.join('annotator02', 'static', 'annotated_frames', 'annotation')
    frame_dir = os.path.join('annotator02', 'static', 'annotated_frames', 'frames')
    log_dir = os.path.join('maintenance')
    os.makedirs(annotation_dir, exist_ok=True)
    os.makedirs(frame_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, "annotations_log.txt")

    for item in data:
        frame_id = int(item["frame_id"])
        boxes = item["boxes"]

        if frame_id not in frame_lookup:
            print(f"Frame ID {frame_id} not found in DB.")
            continue

        frame_path = frame_lookup[frame_id]
        filename = os.path.basename(frame_path)
        base_name, _ = os.path.splitext(filename)
        annotation_path = os.path.join(annotation_dir, base_name + ".txt")
        dst_path = os.path.join(frame_dir, filename)

        if boxes:
            with open(annotation_path, 'w') as f, open(log_file_path, 'a') as log_f:
                for box in boxes:
                    x, y, w, h = int(box['x']), int(box['y']), int(box['w']), int(box['h'])
                    label = box['label']
                    f.write(f"{label} {x} {y} {w} {h}\n")

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_entry = f"{timestamp} | Frame: {filename} | Label: {label} | Coords: ({x}, {y}, {w}, {h})\n"
                    log_f.write(log_entry)
            print(f"Annotation saved and log written for frame {frame_id}")
        else:
            # ❌ No boxes —> delete annotation + frame + logs
            if os.path.exists(annotation_path):
                os.remove(annotation_path)
                print(f"Deleted annotation file: {annotation_path}")
            if os.path.exists(dst_path):
                os.remove(dst_path)
                print(f"Deleted frame file: {dst_path}")

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            removal_log = f"{timestamp} | Frame: {filename} | Annotations removed.\n"
            with open(log_file_path, 'a') as log_f:
                log_f.write(removal_log)
            print(f"Added removal log for frame: {filename}")

        # Always copy frame if exists and not already copied
        src_path='annotator02'+frame_path
        if boxes and os.path.exists(src_path):
            copyfile(src_path, dst_path)
            print("Copied (or overwritten) successfully.")
        elif not boxes:
            print("Empty box list, skipping frame copy.")

    return jsonify({"message": "Annotations saved successfully!"})


@annotate_bp.route('/api/annotation/<int:frame_id>')
def get_annotation_for_frame(frame_id):
    frame = Frame.query.get(frame_id)
    if not frame:
        return jsonify([])

    filename = os.path.basename(frame.frame_path)
    base_name, _ = os.path.splitext(filename)
    annotation_path = os.path.join('annotator02','static', 'annotated_frames', 'annotation', base_name + '.txt')

    if not os.path.exists(annotation_path):
        return jsonify([])

    boxes = []
    with open(annotation_path, 'r') as f:
        for line in f:
            try:
                parts = line.strip().split()
                label = parts[0]
                x, y, w, h = map(int, parts[1:5])
                boxes.append({'label': label, 'x': x, 'y': y, 'w': w, 'h': h})
            except Exception as e:
                continue

    return jsonify(boxes)


@annotate_bp.route('/api/auto_annotate', methods=['POST'])
def auto_annotate_frame():
    data = request.get_json()
    frame_id = data.get("frame_id")
    confidence = float(data.get("confidence", 0.5))

    if not frame_id:
        return jsonify({"error": "Missing frame ID"}), 400

    frame = Frame.query.get(frame_id)
    if not frame:
        return jsonify({"error": "Frame not found"}), 404

    full_path = os.path.join('annotator02', frame.frame_path.lstrip('/'))

    if not os.path.exists(full_path):
        return jsonify({"error": "Image file not found"}), 404

    frame_data = cv2.imread(full_path)
    if frame_data is None:
        return jsonify({"error": "Unable to load the image"}), 404

    detections = get_processor().process_frame(frame_data, confidence)
    return jsonify({"frame_id": frame_id, "detections": detections})

