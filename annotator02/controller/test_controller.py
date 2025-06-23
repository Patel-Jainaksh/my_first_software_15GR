from flask import render_template, Blueprint


test_bp = Blueprint('test', __name__)

@test_bp.route('/index')
def home():
    return render_template('index.html')

@test_bp.route('/')
def index():
    return render_template('index.html')
