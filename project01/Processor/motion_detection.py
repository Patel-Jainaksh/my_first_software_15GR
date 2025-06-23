import cv2
import numpy as np

def detect_motion(frame):
    """Detects significant motion while ignoring lighting changes and wind-based movements."""
    # Initialize background subtractor
    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=30, detectShadows=True) # change to 30 instead of 25
    MOTION_THRESHOLD = 27  # Ignore small movements
    NOISE_FILTER_RATIO = 0.15  # Ignore minor environmental noise
    FRAME_SKIP = 5  # Process every 5th frame for efficiency

    global prev_frame

    if frame is None:
        return False  # Ensure frame is valid

    motion_detected = False

    try:
        # Preprocess frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Apply background subtraction
        fgmask = fgbg.apply(blurred)

        # Morphological filtering to reduce noise
        kernel = np.ones((3, 3), np.uint8)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)

        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        fgmask = cv2.bitwise_and(fgmask, edges)

        # Contour detection
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > MOTION_THRESHOLD]

        # Optical Flow Filtering - Only if we have contours and a previous frame
        if filtered_contours and prev_frame is not None:
            try:
                prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                # Ensure both frames have the same dimensions
                if prev_gray.shape == gray.shape:
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_gray, gray, None, 
                        0.5, 3, 15, 3, 5, 1.2, 0
                    )
                    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    movement_magnitude = np.mean(mag)

                    if movement_magnitude > NOISE_FILTER_RATIO * 2:
                        motion_detected = True
            except Exception as flow_error:
                print(f"Optical flow error: {flow_error}")
                motion_detected = False

        # Update previous frame
        prev_frame = frame.copy()

    except Exception as e:
        print(f"Error in motion detection: {e}")
        motion_detected = False

    return motion_detected