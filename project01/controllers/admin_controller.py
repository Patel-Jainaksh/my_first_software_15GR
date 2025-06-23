from threading import Thread

from service.user_service import UserService
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from service.video_processor_service import model_changed, get_selected_model_from_service, change_frame_enhancer

from service.rtdetr_manager_service import get_processors

from service.log_notifier_service import emit_recording_event

from service.video_processor_service import start_processing

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin', methods=['GET'])
def index():
    return render_template('/admin/index.html')

@admin_bp.route('/admin/index', methods=['GET'])
def index_new():
    return render_template('/admin/alertView.html')

@admin_bp.route('/admin/create', methods=['GET'])
def create_user():
    data={
        "username":"admin",
        "password":"admin123"
    }
    response, status_code = UserService.create_user(data)
    return redirect(url_for('auth.login'))

@admin_bp.route('/admin/changeAiModel/<string:model_name>', methods=['GET'])
def change_ai_model(model_name):
    model_changed(model_name)
    return jsonify({"message": "Model changed !!"}), 200

@admin_bp.route('/admin/get_selected_model', methods=['GET'])
def get_selected_model():
    selected_model=get_selected_model_from_service()
    return jsonify({"model_selected": selected_model}), 200

@admin_bp.route('/admin/changeFrameEnhancer/<status>', methods=['GET'])
def change_frame_enhancer_route(status):
    status = status.lower() == "true"
    change_frame_enhancer(status)
    if status:
        return jsonify({"message": "Frame Enhancer Enabled."}), 200
    return jsonify({"message": "Frame Enhancer Disabled."}), 200


@admin_bp.route('/admin/getFrameEnhancerStatus', methods=['GET'])
def get_frame_enhancer_status():
    selected_model=get_selected_model_from_service()
    return jsonify({"model_selected": selected_model}), 200

@admin_bp.route("/recreate-processors", methods=["POST"])
def recreate_processors():
    try:
        emit_recording_event("PLease Wait....", "ModelChanging")
        selected_model = get_selected_model_from_service()
        if selected_model == 'human':
            model_changed('none')
        get_processors()       # ✅ Create processors with updated model path
        if selected_model == 'human':
            model_changed('human')
        emit_recording_event("Model Changed Successfully ", "ModelChanged")
        return jsonify({"message": "✅ Processors reloaded and detection restarted."}), 200
    except Exception as e:
        emit_recording_event(f"❌ Failed to reload processors: {str(e)}", "System")
        return jsonify({"error": str(e)}), 500
