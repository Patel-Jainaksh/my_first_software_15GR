import cv2
import numpy as np
import torch
import os
import pickle
import logging
from transformers import AutoImageProcessor, AutoModelForObjectDetection, AutoModelForImageClassification
from PIL import Image

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AnimalDetectionProcessor:
    def __init__(
        self,
        det_model_name="modelRepository/detr-resn/default",
        cls_checkpoint_dir=None,
        confidence_threshold=0.69
    ):
        self.det_model_name = det_model_name
        self.cls_checkpoint_dir = cls_checkpoint_dir
        self.confidence_threshold = confidence_threshold

        # Check CUDA availability
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        # Load detection processor and model
        try:
            if not os.path.exists(det_model_name):
                raise FileNotFoundError(f"Detection model directory {det_model_name} does not exist")
            self.det_processor = AutoImageProcessor.from_pretrained(det_model_name)
            self.det_model = AutoModelForObjectDetection.from_pretrained(det_model_name)
        except Exception as e:
            logger.error(f"Failed to load detection model {det_model_name}: {e}")
            raise RuntimeError(f"Cannot load detection model: {e}")

        # Move detection model to device
        if any(param.is_meta for param in self.det_model.parameters()):
            logger.info("Detection model has meta tensors, using to_empty to move to device")
            self.det_model.to_empty(device=self.device)
        else:
            self.det_model.to(self.device)
        self.det_model.eval()
        logger.info(f"Detection model loaded from: {det_model_name}")

        # Load classification processor and model
        try:
            if not os.path.exists(cls_checkpoint_dir):
                raise FileNotFoundError(f"Classification checkpoint directory {cls_checkpoint_dir} does not exist")
            if not os.path.exists(os.path.join(cls_checkpoint_dir, "preprocessor_config.json")):
                raise FileNotFoundError(f"Missing preprocessor_config.json in {cls_checkpoint_dir}")
            self.cls_processor = AutoImageProcessor.from_pretrained(cls_checkpoint_dir)
            self.cls_model = AutoModelForImageClassification.from_pretrained(cls_checkpoint_dir)
        except Exception as e:
            logger.error(f"Failed to load classification model from {cls_checkpoint_dir}: {e}")
            raise RuntimeError(f"Cannot load classification model: {e}")

        # Move classification model to device
        if any(param.is_meta for param in self.cls_model.parameters()):
            logger.info("Classification model has meta tensors, using to_empty to move to device")
            self.cls_model.to_empty(device=self.device)
        else:
            self.cls_model.to(self.device)
        self.cls_model.eval()
        logger.info(f"Classification model loaded from: {cls_checkpoint_dir}")

        # Initialize animal classes and mappings
        self.animal_classes = [
            "antelope", "bat", "bear", "boar", "cat", "chimpanzee", "cow", "coyote", "crow",
            "deer", "dog", "eagle", "elephant", "fox", "hare", "leopard", "goat",
            "mouse", "owl", "ox", "pig", "pigeon", "rat", "reindeer", "sheep",
            "snake", "sparrow", "squirrel", "wolf", "zebra"
        ]
        self.target_animals = [
            "bear", "boar", "chimpanzee", "cow", "deer", "dog", "leopard", "goat",
            "ox", "pig", "sheep", "snake", "langur", "monkey", "tiger"
        ]
        # Updated detr_to_animal to map COCO classes to specific animals
        self.detr_to_animal = {
            "cat": ["leopard"],  # Map COCO "cat" to leopard
            "dog": ["dog", "wolf"],  # Map COCO "dog" to dog and wolf
            "bear": ["bear"],
            "cow": ["cow", "ox"],  # Deer not in COCO; use cow as fallback
            "pig": ["pig", "boar"],
            "sheep": ["sheep", "antelope", "reindeer"],  # Deer fallback
            "monkey": ["chimpanzee", "langur", "monkey"],
            "snake": ["snake"],
            "rabbit": ["hare"],
            "goat": ["goat"],
            "tiger": ["tiger"],
            "elephant": []
        }

        # Restrict DETR model to classes that map to target_animals
        self.valid_detr_classes = [
            detr_cls for detr_cls, mapped_cls in self.detr_to_animal.items()
            if any(cls in self.target_animals for cls in mapped_cls) or detr_cls in self.target_animals
        ]
        # Add fallback for deer since it’s not in COCO
        if "cow" not in self.valid_detr_classes:
            self.valid_detr_classes.append("cow")
        if "sheep" not in self.valid_detr_classes:
            self.valid_detr_classes.append("sheep")
        
        # Update DETR model's id2label and label2id to include only valid animal classes
        original_id2label = self.det_model.config.id2label
        new_id2label = {
            k: v for k, v in original_id2label.items()
            if v.lower() in self.valid_detr_classes
        }
        new_label2id = {v: k for k, v in new_id2label.items()}
        
        if not new_id2label:
            logger.warning("No valid animal classes found in DETR model labels. Using fallback classes.")
            self.valid_detr_classes = list(self.detr_to_animal.keys())
            new_id2label = {k: v for k, v in original_id2label.items() if v.lower() in self.valid_detr_classes}
            new_label2id = {v: k for k, v in new_id2label.items()}

        self.det_model.config.id2label = new_id2label
        self.det_model.config.label2id = new_label2id
        logger.info(f"DETR model restricted to animal classes: {list(new_label2id.keys())}")

        # Update classification model config with animal classes
        if len(self.cls_model.config.id2label) != len(self.animal_classes):
            logger.warning(
                f"Model has {len(self.cls_model.config.id2label)} labels, but {len(self.animal_classes)} are expected. "
                "Updating id2label and label2id to match animal_classes."
            )
        self.cls_model.config.id2label = {i: cls for i, cls in enumerate(self.animal_classes)}
        self.cls_model.config.label2id = {cls: i for i, cls in enumerate(self.animal_classes)}
        self.cls_model.config.num_labels = len(self.animal_classes)

        # Define softened kernel to preserve animal features
        self.kernel = np.array([
            [0, -0.8, 0],
            [-0.6, 3.8, -0.8],
            [0, -1, 0]
        ], dtype=np.float32)

    def apply_kernel(self, frame):
        try:
            if frame is None or frame.size == 0:
                raise ValueError("Invalid frame")
            filtered_frame = cv2.filter2D(frame, -1, self.kernel)
            logger.debug("Kernel applied to frame")
            return filtered_frame
        except Exception as e:
            logger.error(f"Error applying kernel: {e}")
            return frame

    def process_frame_for_detection(self, frame):
        if frame is None or frame.size == 0:
            logger.warning("Invalid frame for detection")
            return []

        # Convert frame to RGB and process using the model
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = self.det_processor(images=rgb, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.det_model(**inputs)

        target_sizes = torch.tensor([rgb.shape[:2]]).to(self.device)
        detections = self.det_processor.post_process_object_detection(
            outputs, target_sizes=target_sizes, threshold=0.4  # Lowered threshold to capture more detections
        )[0]

        result = []
        for score, label, box in zip(detections["scores"], detections["labels"], detections["boxes"]):
            label_name = self.det_model.config.id2label.get(label.item(), "unknown").lower()

            # Only keep detections that match the valid classes
            if label_name in self.valid_detr_classes:
                xmin, ymin, xmax, ymax = [int(coord) for coord in box.tolist()]
                result.append({
                    "class": label_name,
                    "confidence": score.item(),
                    "xmin": xmin,
                    "ymin": ymin,
                    "xmax": xmax,
                    "ymax": ymax
                })

        return result

    def classify_region(self, image, box, det_label):
        x_min, y_min, x_max, y_max = box
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(image.width, x_max)
        y_max = min(image.height, y_max)

        if x_max <= x_min or y_max <= y_min:
            return None, 0.0

        cropped = image.crop((x_min, y_min, x_max, y_max))
        inputs = self.cls_processor(images=cropped, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.cls_model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)

        valid_indices = [idx for idx, label in self.cls_model.config.id2label.items() if label.lower() in self.animal_classes]
        if not valid_indices:
            return None, 0.0

        valid_probs = probs[0, valid_indices]
        if valid_probs.numel() == 0:
            return None, 0.0

        pred_idx = valid_indices[torch.argmax(valid_probs).item()]
        pred_label = self.cls_model.config.id2label[pred_idx].lower()
        confidence = valid_probs.max().item()

        return (pred_label, confidence) if pred_label in self.animal_classes else (None, 0.0)

    def process_frame(self, frame_id, frame, camera_id):
        if frame is None or frame.size == 0:
            return

        filtered_frame = self.apply_kernel(frame)
        image = Image.fromarray(cv2.cvtColor(filtered_frame, cv2.COLOR_BGR2RGB))
        detections = self.process_frame_for_detection(filtered_frame)
        results = []

        # Critical animals with stricter confidence
        critical_animals = ["deer", "wolf", "leopard"]
        strict_confidence = 0.65  # Stricter threshold for critical animals

        for det in detections:
            det_label, det_score, box = det["label"], det["score"], det["box"]
            if det_label == "person":
                continue

            pred_label, confidence = self.classify_region(image, box, det_label)

            final_label = None
            final_conf = 0.0

            # Validation for critical animals
            valid_mappings = self.detr_to_animal.get(det_label, [])
            if pred_label in critical_animals:
                # Ensure classification aligns with DETR mapping
                if pred_label not in valid_mappings and det_label not in critical_animals:
                    # Special handling for deer (no direct COCO class)
                    if pred_label == "deer" and det_label in ["cow", "sheep"]:
                        if confidence >= strict_confidence:
                            final_label = pred_label
                            final_conf = confidence
                            logger.info(f"High-confidence deer classification from {det_label}: {pred_label} ({confidence:.2f})")
                        else:
                            logger.warning(
                                f"Low confidence for deer with DETR {det_label}: {pred_label} ({confidence:.2f}). Discarding."
                            )
                            continue
                    else:
                        logger.warning(
                            f"Invalid classification for {pred_label} with DETR label {det_label}. Discarding."
                        )
                        continue
                elif confidence >= strict_confidence:
                    final_label = pred_label
                    final_conf = confidence
                    logger.info(f"High-confidence critical animal: {pred_label} ({confidence:.2f})")
                else:
                    logger.warning(
                        f"Low confidence for critical animal {pred_label} ({confidence:.2f}). Checking DETR fallback."
                    )

            # Standard classification logic
            if not final_label and pred_label in self.target_animals and confidence > 0.2:
                final_label = pred_label
                final_conf = confidence
                logger.info(f"High-confidence classification: {pred_label} ({confidence:.2f})")

            elif not final_label and det_label in self.target_animals and det_score > 0.2:
                final_label = det_label
                final_conf = det_score
                logger.info(f"Low-confidence classification, fallback to DETR: {det_label} ({det_score:.2f})")

            elif not final_label and (det_label in self.target_animals or (pred_label in self.target_animals if pred_label else False)):
                used_label = det_label if det_label in self.target_animals else pred_label
                used_conf = det_score if det_label in self.target_animals else (confidence if confidence is not None else 0.0)
                logger.warning(
                    f"Animal detected with low confidence: {det_label} / {pred_label} with confidence {used_conf:.2f}"
                )
                final_label = used_label
                final_conf = used_conf

            else:
                logger.debug(f"Filtered out detection: {det_label} / {pred_label}")
                continue

            if final_label:
                results.append({
                    "camera_id": camera_id,
                    "frame_id": frame_id,
                    "class": final_label,
                    "de_confidence": round(final_conf, 4),
                    "det_class": det_label,
                    "confidence": round(det_score, 4),
                    "xmin": box[0],
                    "ymin": box[1],
                    "xmax": box[2],
                    "ymax": box[3],
                    "is_target_animal": final_label in self.target_animals
                })
                # Detailed logging for critical animals
                if final_label in critical_animals:
                    logger.info(
                        f"Critical animal detected: {final_label} (DETR: {det_label}, "
                        f"Conf: {final_conf:.2f}, Box: {box})"
                    )

        pickle_dir = os.path.join("project02/detections/output_pickle")
        os.makedirs(pickle_dir, exist_ok=True)
        pickle_file = os.path.join(pickle_dir, f"{camera_id}_frame{frame_id}.pkl")
        try:
            with open(pickle_file, "wb") as f:
                pickle.dump(results, f)
            logger.info(f"[Frame-{frame_id}] Saved {len(results)} detections to {pickle_file}")
        except Exception as e:
            logger.error(f"Failed to save detections for frame {frame_id}: {e}")

    def enqueue_frame(self, frame_id, frame, camera_id):
        try:
            self.process_frame(frame_id, frame, camera_id)
            return True
        except Exception as e:
            logger.error(f"Failed to process frame {frame_id}: {e}")
            return False