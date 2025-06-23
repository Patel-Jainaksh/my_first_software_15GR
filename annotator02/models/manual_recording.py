from extensions import db

class ManualRecording(db.Model):
    __tablename__ = 'manual_recording'  # ✅ Add this line

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.String(100), nullable=False)
    end_time = db.Column(db.String(100), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=True)
    extract_frame = db.Column(db.Boolean, default=False, nullable=False)
