import os
import torch
import json
from PIL import Image
from torch.utils.data import DataLoader
from torch.optim import AdamW
from transformers import AutoModelForImageClassification, AutoImageProcessor, AutoConfig
from torchvision import datasets, transforms
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from tqdm import tqdm
from service.model_maintenance import move_corrupted_checkpoints_and_update_path, notify_main_server_to_reload

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

def start_animal_training(socketio=None, num_epochs=5):
    base_dir = "annotator02/Model_traning_Area/animal_model_area"
    train_dir = os.path.join(base_dir, "train")
    test_dir = os.path.join(base_dir, "test")

    # Step 1: Filter valid class names BEFORE loading model
    valid_class_names = []
    for class_name in os.listdir(train_dir):
        class_path = os.path.join(train_dir, class_name)
        if os.path.isdir(class_path):
            has_images = any(
                file.lower().endswith((".jpg", ".jpeg", ".png")) for file in os.listdir(class_path)
            )
            if has_images:
                valid_class_names.append(class_name)

    try:
        with open("modelRepository/modelUsageStatus.json", "r") as f:
            data = json.load(f)
            model_path = data.get("animalModelPath", "")
    except Exception as e:
        raise RuntimeError(f"Failed to load model paths: {e}")

    processor = AutoImageProcessor.from_pretrained(model_path)

    # Load config and set correct number of labels
    config = AutoConfig.from_pretrained(model_path)
    config.num_labels = len(valid_class_names)

    # Initialize new classification head with correct class count
    model = AutoModelForImageClassification.from_pretrained(model_path, config=config, ignore_mismatched_sizes=True)
    print(model.classifier)
    # Rebuild label mappings
    model.config.id2label = {i: c for i, c in enumerate(valid_class_names)}
    model.config.label2id = {c: i for i, c in enumerate(valid_class_names)}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor()
    ])

    # Remove empty folders from train_dir (already handled above)
    removed_classes_dir = os.path.join(base_dir, "removed_empty_classes")
    os.makedirs(removed_classes_dir, exist_ok=True)
    for class_name in os.listdir(train_dir):
        if class_name not in valid_class_names:
            os.rename(
                os.path.join(train_dir, class_name),
                os.path.join(removed_classes_dir, class_name)
            )

    # Load datasets
    train_dataset = datasets.ImageFolder(train_dir, transform=transform)

    # Align test_dir with train_dataset.classes
    valid_test_class_names = set(train_dataset.classes)
    for class_name in os.listdir(test_dir):
        class_path = os.path.join(test_dir, class_name)
        if os.path.isdir(class_path) and class_name not in valid_test_class_names:
            os.rename(class_path, os.path.join(removed_classes_dir, f"test_{class_name}"))

    test_dataset = datasets.ImageFolder(test_dir, transform=transform)

    # Verify test classes match
    assert test_dataset.classes == train_dataset.classes, \
        f"Mismatch between train and test classes! \nTrain: {train_dataset.classes} \nTest: {test_dataset.classes}"

    # Set loaders
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

    optimizer = AdamW(model.parameters(), lr=5e-5)
    criterion = torch.nn.CrossEntropyLoss()

    checkpoint_dir = "modelRepository/dino-animal-classifer"
    status_file = os.path.join(checkpoint_dir, "modelCheckPointStatus.json")
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_count = 0

    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            checkpoint_count = json.load(f).get("checkPointsCount", 0)

    # Manual sample check
    sample_img, sample_label = train_dataset[0]
    print("Sample Label:", sample_label, "Label name:", train_dataset.classes[sample_label])
    assert 0 <= sample_label < model.config.num_labels, "Invalid label index!"

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)

            # Extra label check
            if labels.min() < 0 or labels.max() >= model.config.num_labels:
                print(f"🚨 Invalid label in batch! Min: {labels.min().item()}, Max: {labels.max().item()}, Allowed: 0 to {model.config.num_labels - 1}")
                print("Labels:", labels.cpu().tolist())
                raise ValueError("Invalid label detected!")

            outputs = model(pixel_values=images)
            loss = criterion(outputs.logits, labels)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

            if socketio:
                percent = int(((batch_idx + 1) / len(train_loader)) * 100)
                socketio.emit("training_log", {"message": f"Epoch {epoch + 1} Progress: {percent}%"})

        avg_loss = total_loss / len(train_loader)

        model.eval()
        y_true, y_pred = [], []
        with torch.no_grad():
            for images, labels in test_loader:
                images = images.to(device)
                outputs = model(pixel_values=images)
                preds = torch.argmax(outputs.logits, dim=1).cpu().numpy()
                y_true.extend(labels.numpy())
                y_pred.extend(preds)

        acc = accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, average="macro", zero_division=0)
        rec = recall_score(y_true, y_pred, average="macro", zero_division=0)
        f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)

        msg = f"Epoch {epoch+1} | Loss: {avg_loss:.4f} | Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f}"
        print(msg)
        if socketio:
            socketio.emit("training_log", {"message": msg})

        checkpoint_count += 1
        ckpt_path = os.path.join(checkpoint_dir, f"checkPoint{checkpoint_count}")
        os.makedirs(ckpt_path, exist_ok=True)
        model.save_pretrained(ckpt_path)
        processor.save_pretrained(ckpt_path)
        with open(status_file, "w") as f:
            json.dump({"checkPointsCount": checkpoint_count}, f, indent=4)

        msg = f"Checkpoint saved: checkPoint{checkpoint_count}"
        print(msg)
        if socketio:
            socketio.emit("training_log", {"message": msg})

    final_model_dir = os.path.join(base_dir, "trained_model")
    os.makedirs(final_model_dir, exist_ok=True)
    model.save_pretrained(final_model_dir)
    processor.save_pretrained(final_model_dir)
    final_msg = f"Final model saved to: {final_model_dir}"
    print(final_msg)
    if socketio:
        socketio.emit("training_log", {"message": final_msg})

    move_corrupted_checkpoints_and_update_path(
        checkpoint_dir=checkpoint_dir,
        corrupt_dir=r"maintenance/animal/corruptedCheckPoints/animal",
        log_json_path=r"maintenance/animal/corruptedCheckPointInfo.json",
        usage_status_path="modelRepository/modelUsageStatus.json",
        train_for='animal',
        socketio=socketio
    )

    notify_main_server_to_reload(socketio=socketio)

    return {
        "loss": float(avg_loss),
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1)
    }
