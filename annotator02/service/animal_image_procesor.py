import os
import cv2
import torch
import numpy as np
import logging
from transformers import AutoImageProcessor, AutoModelForObjectDetection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnimalDetectionProcessor:
    ANIMAL_CLASSES = {
        "antelope", "bear", "boar", "cat", "chimpanzee", "cow",
        "deer", "dog", "fox", "wild boar", "hare", "leopard",
        "goat", "owl", "ox", "pig", "reindeer", "sheep", "snake", "wolf"
    }

    def __init__(
            self,
            det_model_path=os.path.abspath("modelRepository/detr-resn/default"),
            confidence_threshold=0.4
    ):
        self.det_model_path = det_model_path
        self.confidence_threshold = confidence_threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            self.processor = AutoImageProcessor.from_pretrained(self.det_model_path, local_files_only=True)
            self.model = AutoModelForObjectDetection.from_pretrained(self.det_model_path, local_files_only=True)
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            logger.error(f"❌ Failed to load detection model: {e}")
            self.model = None
            self.processor = None

    def process_frame(self, frame, confidence_threshold=None):
        if self.model is None or self.processor is None:
            logger.error("❌ Model or processor is not loaded.")
            return []

        if frame is None or not isinstance(frame, np.ndarray):
            logger.error("❌ Invalid frame passed to process_frame.")
            return []

        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.error(f"❌ Failed to convert frame to RGB: {e}")
            return []

        try:
            inputs = self.processor(images=rgb, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)

            height, width = frame.shape[:2]
            target_sizes = torch.tensor([[height, width]], device=self.device)
            threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold

            results = self.processor.post_process_object_detection(
                outputs,
                target_sizes=target_sizes,
                threshold=threshold
            )[0]

            detections = []
            for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                class_name = self.model.config.id2label[label.item()].lower()

                # ✅ Only allow defined animal classes
                if class_name not in self.ANIMAL_CLASSES:
                    continue

                box_list = box.tolist()
                if any(coord != coord for coord in box_list):  # NaN check
                    continue

                xmin, ymin, xmax, ymax = map(int, box_list)
                detections.append({
                    "class": class_name,
                    "confidence": round(score.item(), 2),
                    "xmin": xmin,
                    "ymin": ymin,
                    "xmax": xmax,
                    "ymax": ymax
                })

            return detections

        except Exception as e:
            logger.error(f"❌ Error during inference: {e}")
            return []
