import os
import torch
import json
import pandas as pd
import numpy as np
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torch.optim import AdamW
from transformers import AutoModelForObjectDetection, AutoImageProcessor
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from torchvision.ops import box_iou
from pycocotools.coco import COCO
from tqdm import tqdm

from service.model_maintenance import move_corrupted_checkpoints_and_update_path, notify_main_server_to_reload


class CocoDataFrameDataset(Dataset):
    def __init__(self, df, image_dir):
        self.df = df
        self.image_dir = image_dir
        self.grouped = df.groupby("image_id")
        self.samples = list(self.grouped.groups.keys())

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        image_id = self.samples[idx]
        group = self.grouped.get_group(image_id)
        image_path = os.path.join(self.image_dir, group.iloc[0]["file_name"])

        annotations = []
        for _, row in group.iterrows():
            bbox = eval(row["bbox"]) if isinstance(row["bbox"], str) else row["bbox"]
            annotations.append({
                "bbox": bbox,
                "category_id": int(row["category_id"]),
                "area": float(row["area"]),
                "iscrowd": 0
            })

        if len(annotations) == 0:
            return self.__getitem__((idx + 1) % len(self))

        return {
            "image_path": image_path,
            "annotations": annotations,
            "image_id": int(image_id)
        }

def get_collate_fn(processor):
    def collate_fn(batch):
        images, targets = [], []
        for sample in batch:
            if not sample["annotations"]:
                continue
            images.append(Image.open(sample["image_path"]).convert("RGB"))
            targets.append({
                "image_id": sample["image_id"],
                "annotations": sample["annotations"]
            })

        if not images or not targets:
            raise ValueError("All samples in batch were invalid. Skipping.")

        encoding = processor(images=images, annotations=targets, return_tensors="pt")
        return {
            "pixel_values": encoding["pixel_values"],
            "labels": encoding["labels"]
        }
    return collate_fn

def start_human_training(socketio=None, num_epochs=5):
    base_dir = "annotator02/Model_traning_Area/human_model_area"
    train_json = os.path.join(base_dir, "train/_annotations.coco.json")
    test_json = os.path.join(base_dir, "test/_annotations.coco.json")
    image_dir_train = os.path.join(base_dir, "train")
    image_dir_test = os.path.join(base_dir, "test")

    df_train = coco_to_df(COCO(train_json))
    df_test = coco_to_df(COCO(test_json))

    train_dataset = CocoDataFrameDataset(df_train, image_dir_train)
    test_dataset = CocoDataFrameDataset(df_test, image_dir_test)
    try:
        with open("modelRepository/modelUsageStatus.json", "r") as f:
            data = json.load(f)
            model_path=data.get("humanModelPath", "")
    except Exception as e:
        raise RuntimeError(f"Failed to load model paths: {e}")
    processor = AutoImageProcessor.from_pretrained(model_path)
    model = AutoModelForObjectDetection.from_pretrained(model_path)

    collate_fn = get_collate_fn(processor)
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, collate_fn=collate_fn)
    test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False, collate_fn=collate_fn)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = AdamW(model.parameters(), lr=5e-5)

    # Setup checkpoint management
    checkpoint_dir = "modelRepository/rtdetr-v2-r18d-person-detection"
    status_file = os.path.join(checkpoint_dir, "modelCheckPointStatus.json")
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_count = 0

    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            checkpoint_count = json.load(f).get("checkPointsCount", 0)

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        num_batches = len(train_loader)

        for batch_idx, batch in enumerate(train_loader):
            pixel_values = batch["pixel_values"].to(device)
            labels = [{k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in t.items()} for t in batch["labels"]]

            outputs = model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

            if socketio:
                percent = int(((batch_idx + 1) / num_batches) * 100)
                socketio.emit("training_log", {
                    "message": f"Epoch {epoch + 1} Progress: {percent}%"
                })

        avg_loss = total_loss / num_batches
        model.eval()
        y_true, y_pred = [], []

        with torch.no_grad():
            for batch in test_loader:
                pixel_values = batch["pixel_values"].to(device)
                labels_batch = batch["labels"]
                outputs = model(pixel_values=pixel_values)

                target_sizes = [(img.shape[1], img.shape[2]) for img in pixel_values]
                processed_outputs = processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)

                for i, output in enumerate(processed_outputs):
                    pred_boxes = output["boxes"].cpu()
                    pred_labels = output["labels"].cpu()
                    gt = labels_batch[i]
                    gt_boxes = gt["boxes"].cpu()
                    gt_labels = gt["class_labels"].cpu()

                    if len(gt_boxes) == 0:
                        continue

                    ious = box_iou(pred_boxes, gt_boxes)
                    matched_preds, matched_gts = [], []

                    for pred_idx, iou_row in enumerate(ious):
                        max_iou, gt_idx = iou_row.max(0)
                        if max_iou > 0.5 and gt_idx.item() not in matched_gts:
                            y_pred.append(pred_labels[pred_idx].item())
                            y_true.append(gt_labels[gt_idx].item())
                            matched_preds.append(pred_idx)
                            matched_gts.append(gt_idx.item())

                    for idx in range(len(gt_labels)):
                        if idx not in matched_gts:
                            y_true.append(gt_labels[idx].item())
                            y_pred.append(-1)
                    for idx in range(len(pred_labels)):
                        if idx not in matched_preds:
                            y_true.append(-1)
                            y_pred.append(pred_labels[idx].item())

        acc = accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, average="macro", zero_division=0)
        rec = recall_score(y_true, y_pred, average="macro", zero_division=0)
        f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)

        log_msg = f"Epoch {epoch + 1} | Avg Loss: {avg_loss:.4f} | Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f}"
        print(log_msg)
        if socketio:
            socketio.emit("training_log", {"message": log_msg})

        # 🔥 Save epoch checkpoint
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

    # ✅ Save final model to dedicated directory
    final_model_dir = os.path.join(base_dir, "trained_model")
    os.makedirs(final_model_dir, exist_ok=True)
    final_msg = f"Final model saved to: {final_model_dir}"
    print(final_msg)
    model.save_pretrained(final_model_dir)
    processor.save_pretrained(final_model_dir)
    # After final model save
    move_corrupted_checkpoints_and_update_path(
        checkpoint_dir="modelRepository/rtdetr-v2-r18d-person-detection",
        corrupt_dir=r"maintenance/human/corruptedCheckPoints\human",
        log_json_path=r"maintenance/human/corruptedCheckPointInfo.json",
        usage_status_path="modelRepository/modelUsageStatus.json",
        train_for='human',
        socketio=socketio
    )
    notify_main_server_to_reload(socketio=socketio)
    if socketio:
        socketio.emit("training_log", {"message": final_msg})

    return {
        "loss": float(avg_loss),
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1)
    }

def coco_to_df(coco):
    ann_ids = coco.getAnnIds()
    anns = coco.loadAnns(ann_ids)
    data = []
    for ann in anns:
        image_info = coco.loadImgs(ann['image_id'])[0]
        data.append({
            "image_id": ann['image_id'],
            "category_id": ann['category_id'],
            "category_name": coco.loadCats(ann['category_id'])[0]['name'],
            "bbox": ann['bbox'],
            "area": ann['area'],
            "width": image_info['width'],
            "height": image_info['height'],
            "file_name": image_info['file_name']
        })
    return pd.DataFrame(data)



