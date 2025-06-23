from flask import jsonify

from models import db
from models.nvr import NVR
from models.camera import Camera

def fetch_cameras_for_nvr(nvr_id):
    try:
        # Query all cameras belonging to the given NVR ID

        cameras = Camera.query.filter_by(nvr_id=nvr_id).all()

        if not cameras:
            return

        # Convert camera data to JSON
        camera_list = [
            {
                "id": cam.id,
                "channel": cam.channel,
                "url": cam.url,
                "description": cam.description,
                "nvr_id": cam.nvr_id
            }
            for cam in cameras
        ]

        return jsonify(camera_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500