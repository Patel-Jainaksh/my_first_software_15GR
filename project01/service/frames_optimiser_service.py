import numpy as np
import cv2
from scipy.signal import convolve2d

class FrameEnhancer:
    def __init__(self):
        # Base sharpening kernel
        self.base_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        # PID controller parameters
        self.kp = 0.5  # Proportional gain
        self.ki = 0.1  # Integral gain
        self.kd = 0.2  # Derivative gain
        self.integral = 0
        self.prev_error = 0
        # Target metrics for optimal frame
        self.target_contrast = 1.0
        self.target_brightness = 128
        self.max_noise_level = 10.0

    def calculate_frame_metrics(self, frame):
        """Calculate frame characteristics: noise, contrast, brightness."""
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Noise estimation (standard deviation of Laplacian)
        laplacian = cv2.Laplacian(frame, cv2.CV_64F)
        noise_level = np.std(laplacian)

        # Contrast (standard deviation of pixel intensities)
        contrast = np.std(frame) / (np.mean(frame) + 1e-6)

        # Brightness (mean pixel intensity)
        brightness = np.mean(frame)

        return noise_level, contrast, brightness

    def pid_control(self, noise_level, contrast, brightness):
        """Apply PID control to adjust kernel strength."""
        # Calculate error based on deviation from target metrics
        contrast_error = self.target_contrast - contrast
        brightness_error = self.target_brightness - brightness
        noise_error = max(0, noise_level - self.max_noise_level)

        # Combined error (weighted)
        error = 0.5 * contrast_error + 0.3 * brightness_error + 0.2 * noise_error

        # Proportional term
        proportional = self.kp * error

        # Integral term
        self.integral += error
        integral = self.ki * self.integral

        # Derivative term
        derivative = self.kd * (error - self.prev_error)
        self.prev_error = error

        # PID output (kernel strength adjustment)
        pid_output = proportional + integral + derivative

        # Limit the adjustment to avoid extreme changes
        adjustment = np.clip(pid_output, -0.5, 0.5)

        return adjustment

    def adjust_kernel(self, adjustment):
        """Dynamically adjust the kernel based on PID output."""
        # Scale the kernel's sharpening effect
        center = 5 + adjustment * 2  # Adjust central value
        sides = -0.5 - adjustment * 0.5  # Adjust surrounding values
        adjusted_kernel = np.array([[-0.5, sides, 0.5],
                                    [sides, center, sides],
                                    [0.5, sides, -0.5]], dtype=np.float32)
        return adjusted_kernel

    def enhance_frame(self, frame):
        """Enhance the input frame for object detection."""
        if len(frame.shape) == 3:
            channels = cv2.split(frame)
            enhanced_channels = []
            for channel in channels:
                # Calculate frame metrics
                noise_level, contrast, brightness = self.calculate_frame_metrics(channel)

                # Get kernel adjustment via PID control
                adjustment = self.pid_control(noise_level, contrast, brightness)

                # Adjust kernel
                kernel = self.adjust_kernel(adjustment)

                # Apply kernel to enhance frame
                enhanced = convolve2d(channel, kernel, mode='same', boundary='symm')
                enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
                enhanced_channels.append(enhanced)

            # Merge channels back
            enhanced_frame = cv2.merge(enhanced_channels)
        else:
            # Grayscale frame
            noise_level, contrast, brightness = self.calculate_frame_metrics(frame)
            adjustment = self.pid_control(noise_level, contrast, brightness)
            kernel = self.adjust_kernel(adjustment)
            enhanced_frame = convolve2d(frame, kernel, mode='same', boundary='symm')
            enhanced_frame = np.clip(enhanced_frame, 0, 255).astype(np.uint8)

        return enhanced_frame

    def preprocess_for_detection(self, frame):
        """Preprocess enhanced frame for object detection model."""
        # Enhance frame
        enhanced_frame = self.enhance_frame(frame)

        # Additional preprocessing steps for object detection
        # Resize to standard input size (e.g., 416x416 for YOLO)
        input_size = (416, 416)
        resized_frame = cv2.resize(enhanced_frame, input_size, interpolation=cv2.INTER_LINEAR)

        # Normalize pixel values to [0, 1]
        normalized_frame = resized_frame / 255.0

        # Convert to model input format (e.g., add batch dimension)
        model_input = np.expand_dims(normalized_frame, axis=0)

        return model_input


# Example usage
if __name__ == "__main__":
    # Load a sample frame (replace with actual video frame input)
    frame = cv2.imread(r"/home/agx/Desktop/jammu-vigilmet-model-human/dark_img.jpeg")
    if frame is None:
        raise ValueError("Failed to load sample frame")

    enhancer = FrameEnhancer()

    # Enhance and preprocess frame
    model_input = enhancer.preprocess_for_detection(frame)

    # Output shape for verification
    print(f"Preprocessed frame shape: {model_input.shape}")

    # Save enhanced frame for visualization (optional)
    enhanced_frame = enhancer.enhance_frame(frame)
    cv2.imwrite("enhanced_frame.jpg", enhanced_frame)