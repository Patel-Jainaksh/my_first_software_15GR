import re
from flask import Blueprint, request, jsonify, render_template, Response
from models import db
from models.camera import Camera
from models.nvr import NVR
from models.recording import Recording
from sqlalchemy import func, cast, DateTime
from datetime import datetime, timedelta

recording_bp = Blueprint('recording', __name__)

@recording_bp.route('/admin/recordings', methods=['GET'])
def recordings():
    return render_template('/admin/recordings.html')

import os
import subprocess
from flask import current_app


@recording_bp.route('/static/recordings/<filename>')
def get_video(filename):
    path = os.path.join(r"C:\AI_VIGILNET\auto_recordings", filename)

    if not os.path.exists(path):
        os.abort(404)

    range_header = request.headers.get('Range', None)
    if not range_header:
        return Response(open(path, 'rb'), mimetype='video/mp4')

    file_size = os.path.getsize(path)
    byte1, byte2 = 0, None
    match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    if match:
        byte1 = int(match.group(1))
        if match.group(2):
            byte2 = int(match.group(2))

    byte2 = byte2 if byte2 is not None else file_size - 1
    length = byte2 - byte1 + 1

    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    response = Response(data, 206, mimetype='video/mp4')
    response.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Content-Length', str(length))
    return response

@recording_bp.route('/api/recordings', methods=['GET'])
def get_recordings():
    # try:
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('limit', 5))

        # Filters
        nvr_filter = request.args.get('nvr')
        camera_filter = request.args.get('camera')
        start_date = request.args.get('start')
        end_date = request.args.get('end')

        # Build base query
        query = Recording.query

        # Join with Camera and NVR for filtering
        if nvr_filter and nvr_filter != "all":
            query = query.join(Camera).filter(Camera.nvr_id == int(nvr_filter))

        if camera_filter and camera_filter != "all":
            query = query.filter(Recording.camera_id == int(camera_filter))
            
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(cast(Recording.start_time, DateTime) >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(cast(Recording.start_time, DateTime) < end_dt)



        # Get all distinct dates from the filtered query
        date_query = query.with_entities(func.date(Recording.start_time).label("date")).distinct().order_by(func.date(Recording.start_time).desc())
        all_dates = [row.date for row in date_query.all()]
        paged_dates = all_dates[(page - 1) * per_page: page * per_page]

        result = []

        for date in paged_dates:
            daily_query = query.filter(func.date(Recording.start_time) == date).order_by(Recording.start_time.asc())
            recordings = daily_query.all()

            videos = []
            for rec in recordings:
                file_path = os.path.join("C:/AI_VIGILNET/auto_recordings/", rec.file_path)

                # Get duration
                try:
                    cmd = [
                        "ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", file_path
                    ]
                    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).strip()
                    duration_seconds = float(output)
                    duration_formatted = str(timedelta(seconds=int(duration_seconds)))
                except Exception:
                    duration_formatted = "00:00:00"

                # Get file size
                try:
                    size_bytes = os.path.getsize(file_path)
                    size_mb = round(size_bytes / (1024 * 1024), 2)
                    size_str = f"{size_mb} MB"
                except Exception:
                    size_str = "Unknown"

                # Camera & NVR info
                camera = Camera.query.get(rec.camera_id)
                nvr_info = camera.nvr if camera else None

                videos.append({
                    "id":rec.id,
                    "src": f"/static/recordings/{rec.file_path}",
                    "time": datetime.strptime(rec.start_time, "%Y-%m-%d %H:%M:%S").strftime("%H:%M"),
                    "duration": duration_formatted,
                    "size": size_str,
                    "fullDate": rec.start_time,
                    "cameraId": rec.camera_id,
                    "camera": {
                        "id": camera.id,
                        "channel": camera.channel,
                        "url": camera.url,
                        "channel_url": camera.channel_url,
                        "description": camera.description
                    } if camera else None,
                    "nvr": {
                        "id": nvr_info.id,
                        "area_name": nvr_info.area_name,
                        "url": nvr_info.url
                    } if nvr_info else None
                })

            formatted_date = date.strftime("%d/%m/%Y")
            result.append({
                "date": formatted_date,
                "dateFull": date.isoformat(),
                "videos": videos
            })

        return jsonify({
            "recordings": result,
            "hasMore": len(all_dates) > page * per_page
        })

    # except Exception as e:
    #     return jsonify({"error": str(e)}), 500


@recording_bp.route('/api/filters')
def get_filter_options():
    nvrs = NVR.query.all()
    cameras = Camera.query.all()

    return jsonify({
        "nvrs": [{"id": n.id, "area_name": n.area_name} for n in nvrs],
        "cameras": [{
            "id": c.id,
            "channel": c.channel,
            "description": c.description,
            "nvr_id": c.nvr_id
        } for c in cameras]
    })


@recording_bp.route('/api/recordings/<int:recording_id>', methods=['DELETE'])
def delete_recording(recording_id):
    recording = Recording.query.get(recording_id)
    if not recording:
        return jsonify({'message': 'Recording not found'}), 404

    try:
        if os.path.exists(f"C:/AI_VIGILNET/auto_recordings/{recording.file_path}"):
            os.remove(f"C:/AI_VIGILNET/auto_recordings/{recording.file_path}")

        db.session.delete(recording)
        db.session.commit()

        return jsonify({'message': 'Recording deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500