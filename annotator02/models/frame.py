# models/frame_model.py
from extensions import db

class Frame(db.Model):
    __tablename__ = 'frame'  # optional, but keeps things consistent

    id = db.Column(db.Integer, primary_key=True)
    frame_path = db.Column(db.String(200), nullable=False)
    manual_recording_id = db.Column(db.Integer, db.ForeignKey('manual_recording.id'), nullable=True)  # ✅ match __tablename__
