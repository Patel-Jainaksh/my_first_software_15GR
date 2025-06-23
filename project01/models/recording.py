from models import db

class Recording(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.String(100), nullable=False)
    end_time = db.Column(db.String(100), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=True)
