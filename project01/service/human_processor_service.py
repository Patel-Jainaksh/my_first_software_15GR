import os
import time
import cv2
from transformers import AutoImageProcessor, AutoModelForObjectDetection
import torch

class RTDETRProcessor:
    def __init__(self,
                 model_name=None,
                 confidence_threshold=0.45):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold

        # ✅ Initialize once
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoImageProcessor.from_pretrained(self.model_name)
        self.model = AutoModelForObjectDetection.from_pretrained(self.model_name)

        if any(param.is_meta for param in self.model.parameters()):
            self.model.to_empty(device=self.device)
        else:
            self.model.to(self.device)

        self.model.eval()

    def get_detections(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = self.processor(images=rgb, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        height, width = frame.shape[:2]
        target_sizes = torch.tensor([[height, width]], device=self.device)

        results = self.processor.post_process_object_detection(
            outputs, target_sizes=target_sizes, threshold=self.confidence_threshold
        )[0]

        detections = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            class_name = self.model.config.id2label[label.item()]

            # Only detect "person"
            if class_name.lower() != "person":
                continue

            # ✅ NaN-safe conversion
            box_list = box.tolist()
            if any(coord != coord for coord in box_list):  # NaN check
                print(f"⚠️ Skipping invalid box: {box_list}")
                continue

            xmin, ymin, xmax, ymax = [int(coord) for coord in box_list]
            detections.append({
                "class": class_name,
                "confidence": round(score.item(), 2),
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax
            })

        return detections
