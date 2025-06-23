from models import db

class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(100), nullable=False)
    channel_url = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    nvr_id = db.Column(db.Integer, db.ForeignKey('nvr.id'), nullable=True)
    recordings = db.relationship('Recording', backref='camera', lazy=True)
