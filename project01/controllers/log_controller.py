import time
from flask import Blueprint, render_template, request, jsonify,Response,current_app,redirect,url_for
import csv
from models.nvr import NVR
from service.video_processor_service import processed_frames, restart_processing
from models import db
from models.camera import Camera
import traceback 
    
log_bp=Blueprint('log', __name__)

@log_bp.route('/admin/log', methods=['GET'])
def camera():
    return render_template('/admin/logs.html')

from flask import Blueprint, request, jsonify, redirect, url_for
import os
import csv
from datetime import datetime
import traceback

CSV_PATH = r"C:/AI_VIGILNET/detections/detections.csv"

@log_bp.route('/admin/fetchLogs', methods=['GET'])
def get_logs():
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 50))
        camera_id_filter = request.args.get('camera_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Ensure the file exists
        if not os.path.exists(CSV_PATH):
            # Create the file and add header row
            os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
            with open(CSV_PATH, "w", newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["date", "time", "camera_id", "frame_id", "class", "confidence", "xmin", "ymin", "xmax", "ymax"])
                print('📁 Empty CSV created with headers.')
            return jsonify([])

        logs = []
        with open(CSV_PATH, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers is None:
                return jsonify([])

            all_rows = [row for row in reader if len(row) == 10]

        all_rows.reverse()

        def row_matches(row):
            if camera_id_filter and str(row[2]) != str(camera_id_filter):
                return False
            if start_date or end_date:
                try:
                    date_obj = datetime.strptime(row[0], "%d-%m-%y")
                except Exception:
                    return False
                if start_date and date_obj < datetime.strptime(start_date, "%d-%m-%Y"):
                    return False
                if end_date and date_obj > datetime.strptime(end_date, "%d-%m-%Y"):
                    return False
            return True

        filtered_rows = [row for row in all_rows if row_matches(row)]
        selected_rows = filtered_rows[offset:offset + limit]

        for row in selected_rows:
            logs.append({
                "date": row[0],
                "time": row[1],
                "camera_id": row[2],
                "frame_id": row[3],
                "class": row[4],
                "confidence": row[5],
                "bbox": {
                    "xmin": row[6],
                    "ymin": row[7],
                    "xmax": row[8],
                    "ymax": row[9],
                }
            })

        return jsonify(logs)
    except Exception as e:
        traceback.print_exc()
        return jsonify([])



@log_bp.route('/admin/getCamerasByNVR', methods=['GET'])
def get_cameras_by_nvr():
    nvr_id = request.args.get('nvr_id')
    cameras = Camera.query.filter_by(nvr_id=nvr_id).all()
    return jsonify([{"id": cam.id, "desc": cam.description} for cam in cameras])

@log_bp.route('/admin/getNVRs', methods=['GET'])
def get_nvrs():
    nvrs = NVR.query.all()
    return jsonify([{"id": n.id, "area_name": n.area_name} for n in nvrs])


@log_bp.route('/admin/deleteLogsByDate', methods=['DELETE'])
def delete_logs_by_date():
    date_to_delete = request.args.get('date')
    if not date_to_delete:
        return jsonify({'message': 'Missing date parameter'}), 400

    try:
        with open(CSV_PATH, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = [row for row in reader if len(row) == 10]

        remaining_rows = [row for row in rows if row[0] != date_to_delete]

        with open(CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(remaining_rows)

        return jsonify({'message': f'Logs for {date_to_delete} deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Error deleting logs: {str(e)}'}), 500
