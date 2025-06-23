import torch
import cv2
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

class DepthEstimator:
    def __init__(self, model_name="modelRepository/depth-model/default", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_name).to(self.device)

    def process_frame(self, frame):
        # Convert BGR to RGB and to PIL
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        depth = self.processor.post_process_depth_estimation(
            outputs,
            target_sizes=[(image.height, image.width)],
        )[0]["predicted_depth"]

        depth = (depth - depth.min()) / (depth.max() - depth.min())
        depth = depth.squeeze().detach().cpu().numpy() * 255
        depth_image = depth.astype("uint8")
        # depth_colored = cv2.applyColorMap(depth_image, cv2.COLORMAP_MAGMA)
        depth_colored = cv2.applyColorMap(depth_image, cv2.COLORMAP_JET)

        return depth_colored
