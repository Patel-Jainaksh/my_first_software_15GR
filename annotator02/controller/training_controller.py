import json
import os
import threading
from flask import request  # Make sure this is imported
from flask import Blueprint, render_template, request, jsonify
from extensions import socketio
from service.start_human_training import start_human_training
from service.training_service import prepare_filtered_dataset
from service.start_animal_training import start_animal_training  # optional lazy import
import traceback

from service.training_service import prepare_animal_dataset

training_bp = Blueprint('training_bp', __name__)
STATUS_FILE = "training_status.json"

@training_bp.route('/training', methods=['GET'])
def home():
    return render_template('training.html')

@training_bp.route('/api/training_status', methods=['GET'])
def check_training_status():
    if not os.path.exists(STATUS_FILE):
        return jsonify({"status": "idle"})
    with open(STATUS_FILE, "r") as f:
        return jsonify(json.load(f))


@training_bp.route('/api/train', methods=['POST'])
def start_training():
    training_type = request.args.get("type")
    if training_type not in ["human", "animal"]:
        return jsonify({"error": "Invalid training type"}), 400

    def update_status(type_, status):
        with open(STATUS_FILE, "w") as f:
            json.dump({"type": type_, "status": status}, f)

    # def run_training():
    #     # try:
    #         update_status(training_type, "in_progress")
    #         if training_type == "human":
    #             from service.data_export_service import create_human_dataset_zip
    #             create_human_dataset_zip()  # ⬅️ Create ZIP before anything else
    #
    #             prepare_filtered_dataset(
    #                 base_dir='annotator02/Model_traning_Area/human_model_area',
    #                 class_filter=['person']
    #             )
    #             socketio.emit("training_log", {"message": "Dataset prepared. Starting human model training..."})
    #             result = start_human_training(socketio=socketio, num_epochs=5)
    #             socketio.emit("training_log", {"message": "Human model training completed!"})
    #
    #         elif training_type == "animal":
    #             prepare_animal_dataset()
    #             socketio.emit("training_log", {"message": "Dataset prepared. Starting animal model training..."})
    #             result = start_animal_training(socketio=socketio, num_epochs=5)
    #             socketio.emit("training_log", {"message": "Animal model training completed!"})
    #
    #         update_status(training_type, "completed")
    #     # except Exception as e:
    #     #     print("🚨 Error in training thread:", e)
    #     #     socketio.emit("training_log", {"message": f"Training failed: {str(e)}"})
    #
    # # Start training in background thread
    #
    #

    def run_training():
        try:
            update_status(training_type, "in_progress")
            socketio.emit("training_log", {"message": "🚀 Training initialized..."})

            if training_type == "human":
                from service.data_export_service import create_human_dataset_zip
                create_human_dataset_zip()

                prepare_filtered_dataset(
                    base_dir='annotator02/Model_traning_Area/human_model_area',
                    class_filter=['person']
                )
                socketio.emit("training_log", {"message": "📦 Human dataset ready."})

                result = start_human_training(socketio=socketio, num_epochs=5)
                socketio.emit("training_log", {"message": "✅ Human model training complete."})

            elif training_type == "animal":
                prepare_animal_dataset()
                socketio.emit("training_log", {"message": "📦 Animal dataset ready."})

                result = start_animal_training(socketio=socketio, num_epochs=5)
                socketio.emit("training_log", {"message": "✅ Animal model training complete."})

            update_status(training_type, "completed")

        except Exception as e:
            error_msg = f"🚨 Training crashed: {str(e)}"
            socketio.emit("training_log", {"message": error_msg})
            print(error_msg)
            traceback.print_exc()
            update_status(training_type, "error")

    threading.Thread(target=run_training).start()

    return jsonify({"message": f"{training_type.capitalize()} training Initialized!"})
