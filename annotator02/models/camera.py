from extensions import db


class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(100), nullable=False)
    channel_url = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    nvr_id = db.Column(db.Integer, db.ForeignKey('nvr.id'), nullable=False)

    # Manual recording relationship is safe to define here
    manual_recordings = db.relationship('ManualRecording', backref='camera', lazy=True)

    # Recording relationship is added later in models/__init__.py
