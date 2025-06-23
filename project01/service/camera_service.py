from models import db
from models.camera import Camera
from flask import jsonify,current_app
from service.video_processor_service import restart_processing

def change_camera_url(nvr_id, nvr_url):
    try:
        cameras = Camera.query.filter_by(nvr_id=nvr_id).all()
        if not cameras:
            return jsonify({"message": "No cameras found for the given NVR ID"}), 404

        for camera in cameras:
            camera.url = 'rtsp://'+nvr_url + camera.channel_url  # Update the URL
            print("New camera url update !!",camera.url)
            db.session.add(camera)
        # Commit changes to the database

        # Restart processing for all affected cameras
        print("looping through cameras ")
        for camera in cameras:
            print("Camera restart process restarted !!")
            restart_processing(camera.id, camera.url)

        db.session.commit()
        return jsonify({"message": "Camera URLs updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
