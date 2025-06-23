import os
import json
import zipfile
import shutil
import requests
from datetime import datetime
from transformers import AutoModelForObjectDetection, AutoModelForImageClassification, AutoImageProcessor


def move_corrupted_checkpoints_and_update_path(checkpoint_dir, corrupt_dir, log_json_path, usage_status_path,train_for,socketio=None):
    os.makedirs(corrupt_dir, exist_ok=True)

    # Load corruption log
    corruption_log = []
    if os.path.exists(log_json_path):
        with open(log_json_path, "r") as f:
            corruption_log = json.load(f)

    # Load model usage status JSON
    if os.path.exists(usage_status_path):
        with open(usage_status_path, "r") as f:
            model_status = json.load(f)
    else:
        model_status = {"humanModelPath": "", "animalModelPath": ""}

    def is_corrupted(ckpt_path):
       if train_for == 'human':
           try:
               AutoModelForObjectDetection.from_pretrained(ckpt_path)
               return False
           except Exception as e:
               print(f"❌ Failed to load checkpoint {ckpt_path}: {e}")
               return True
       else:
            try:
                AutoModelForImageClassification.from_pretrained(ckpt_path)
                return False
            except Exception as e:
                print(f"❌ Failed to load checkpoint {ckpt_path}: {e}")
                return True

    latest_valid_checkpoint = None
    socketio.emit("training_log", {"message": "Checking For Any Corrupted Checkpoints...."})
    for name in sorted(os.listdir(checkpoint_dir), key=lambda x: int(x.replace("checkPoint", "")) if x.startswith("checkPoint") else -1, reverse=True):
        ckpt_path = os.path.join(checkpoint_dir, name)
        print("Now checking .....  !!!!!!",ckpt_path)
        if not (os.path.isdir(ckpt_path) and name.startswith("checkPoint")):
            continue

        if is_corrupted(ckpt_path):
            socketio.emit("training_log", {"message": f"Found {name} corrupted !"})
            zip_name = f"{name}.zip"
            zip_path = os.path.join(corrupt_dir, zip_name)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(ckpt_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, ckpt_path)
                        zipf.write(file_path, arcname)

            shutil.rmtree(ckpt_path)

            corruption_log.append({
                "checkpoint": name,
                "timestamp": datetime.now().isoformat(),
                "zip_file": zip_name
            })

            # print(f"⚠️ Corrupted checkpoint {name} moved to maintenance.")
        else:
            if not latest_valid_checkpoint:
                latest_valid_checkpoint = os.path.relpath(ckpt_path).replace("\\", "/")

    with open(log_json_path, "w") as f:
        json.dump(corruption_log, f, indent=4)
    if train_for == 'human':
        if latest_valid_checkpoint:
            model_status["humanModelPath"] = latest_valid_checkpoint
            with open(usage_status_path, "w") as f:
                json.dump(model_status, f, indent=4)
            socketio.emit("training_log", {"message": f"Loading new checkPoint..."})

            print(f"Updated humanModelPath to: {latest_valid_checkpoint}")
    else:
        if latest_valid_checkpoint:
            model_status["animalModelPath"] = latest_valid_checkpoint
            with open(usage_status_path, "w") as f:
                json.dump(model_status, f, indent=4)
            socketio.emit("training_log", {"message": f"Loading new checkPoint..."})
            print(f"Updated animalModelPath to: {latest_valid_checkpoint}")


def notify_main_server_to_reload(socketio=None, base_url="http://localhost:8080"):
    try:
        response = requests.post(f"{base_url}/recreate-processors")
        if response.status_code == 200:
            msg = "Please wait new checkpoints are loading......"
            print(msg)
            if socketio:
                socketio.emit("training_log", {"message": msg})
        else:
            msg = f"Server responded with: {response.status_code} - {response.text}"
            print(msg)
            if socketio:
                socketio.emit("training_log", {"message": msg})
    except Exception as e:
        msg = f"Failed to notify main server: {e}"
        print(msg)
        if socketio:
            socketio.emit("training_log", {"message": msg})
