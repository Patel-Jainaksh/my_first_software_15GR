from flask import request, jsonify, Blueprint
from models import db
from models.camera import Camera
from models.nvr import NVR
from models.recording import Recording
from service.camera_service import change_camera_url
from service.video_processor_service import stop_processing

nvr_bp = Blueprint('nvr', __name__)

@nvr_bp.route('/admin/nvr/addNVR', methods=['POST'])
def add_nvr():
    try:
        data = request.get_json()
        area_name = data.get("area_name")
        url = data.get("url")

        if not area_name or not url:
            return jsonify({"message": "Missing required fields","status":False}), 400

        # Check if NVR with the same area_name already exists (unique constraint)
        existing_nvr = NVR.query.filter_by(area_name=area_name).first()
        if existing_nvr:
            return jsonify({"message":"with this area_name already exists","status":False}), 409

        # Create new NVR object
        new_nvr = NVR(area_name=area_name, url=url)

        # Save to database
        db.session.add(new_nvr)
        db.session.commit()

        return jsonify({"message": "NVR added successfully!", "id": new_nvr.id,"status":True}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@nvr_bp.route("/admin/nvr/list", methods=["GET"])
def get_nvr_list():
    try:
        nvrs = NVR.query.all()
        nvr_list = [{"id": nvr.id, "area_name": nvr.area_name} for nvr in nvrs]

        return jsonify(nvr_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@nvr_bp.route("/admin/nvr/<int:nvr_id>", methods=["GET"])
def get_nvr_by_id(nvr_id):
    try:
        nvr = NVR.query.get(nvr_id)

        if not nvr:
            return jsonify({"error": "NVR not found"}), 404

        nvr_data = {
            "id": nvr.id,
            "area_name": nvr.area_name,
            "url": nvr.url
        }

        return jsonify(nvr_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@nvr_bp.route("/admin/nvr/<int:nvr_id>", methods=["DELETE"])
def delete_nvr(nvr_id):
    try:
        nvr = NVR.query.get(nvr_id)

        if not nvr:
            return jsonify({"error": "NVR not found"}), 404

        related_cameras = Camera.query.filter_by(nvr_id=nvr_id).all()
        for camera in related_cameras:
            # Stop processing if needed
            stop_processing(camera.id)

            # Delete related recordings
            recordings = Recording.query.filter_by(camera_id=camera.id).all()
            for recording in recordings:
                db.session.delete(recording)

            # Delete the camera
            db.session.delete(camera)

        # Delete the NVR after all cameras & recordings are deleted
        db.session.delete(nvr)
        db.session.commit()

        return jsonify({"message": "NVR, related cameras, and recordings deleted successfully", "status": True}), 200

    except Exception as e:
        return jsonify({"error": str(e), "status": False}), 500

@nvr_bp.route("/admin/nvr/<int:nvr_id>", methods=["PUT"])
def update_nvr(nvr_id):
    try:
        data = request.get_json()
        nvr = NVR.query.get(nvr_id)

        if not nvr:
            return jsonify({"error": "NVR not found"}), 404

        # Update fields if provided in request
        print(data)
        if "area_name" in data:
            nvr.area_name = data["area_name"]
        if "url" in data:
            nvr.url = data["url"]

        db.session.commit()

        updated_nvr_data = {
            "id": nvr.id,
            "area_name": nvr.area_name,
            "url": nvr.url
        }
        change_camera_url(nvr.id,nvr.url)

        return jsonify({"message": "NVR added successfully!", "id": nvr.id,"status":True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500