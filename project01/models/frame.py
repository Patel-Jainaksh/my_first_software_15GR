from models import db

class Frame(db.Model):
    __tablename__ = 'frame'
    id = db.Column(db.Integer, primary_key=True)
    frame_path = db.Column(db.String(200), nullable=False)
    manual_recording_id = db.Column(db.Integer, db.ForeignKey('manual_recording.id'), nullable=True)  # ✅ match __tablename__
