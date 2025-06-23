from extensions import db


class NVR(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    area_name = db.Column(db.String(100), nullable=False, unique=True)
    url = db.Column(db.String(200), nullable=False)

    cameras = db.relationship('Camera', backref='nvr', lazy=True)
