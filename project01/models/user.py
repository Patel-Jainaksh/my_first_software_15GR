from models import  db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Boolean, default=True)
    enabled = db.Column(db.Integer, default=1)
