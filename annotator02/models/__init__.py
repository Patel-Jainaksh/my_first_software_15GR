from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)


from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models in a specific order
from .nvr import NVR
from .camera import Camera
from .manual_recording import ManualRecording
from .recording import Recording

# Late-binding for circular relationships
Camera.recordings = db.relationship('Recording', backref='camera', lazy=True)


