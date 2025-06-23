from flask import Blueprint, render_template,session,flash,redirect,url_for

operator_bp = Blueprint('operator', __name__)

@operator_bp.route('/operator', methods=['GET'])
def operatorDashboard():
    return render_template('/operator/index.html')


@operator_bp.route('/operator/logHistory', methods=['GET'])
def operatorLogHistory():
    return render_template('/operator/logHistory.html')


@operator_bp.route('/operator/recordings', methods=['GET'])
def operatorRecordings():
    return render_template('/operator/recordings.html')

@operator_bp.route('/operator/cameras', methods=['GET'])
def operatorManageCameraAndAreas():
    return render_template('/operator/cameras.html')

