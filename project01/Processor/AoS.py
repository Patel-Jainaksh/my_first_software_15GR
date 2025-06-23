import cv2 as cv
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    from cv2 import bgsegm
except ImportError:
    logger.error("cv2.bgsegm module not found. Install opencv-contrib-python.")
    exit(1)

class BackgroundSubtractor:
    def __init__(self, video_source=None, max_retries=5, retry_delay=10):
        """
        Initialize the background subtractor. If video_source is given, also initialize capture.
        """
        self.video_source = video_source
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cap = None
        self.fgbg = bgsegm.createBackgroundSubtractorMOG()
        self.kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (3, 3))

        if self.video_source is not None:
            self._initialize()

    def _initialize(self):
        """
        Attempt to initialize video capture with retries.
        """
        retries = 0
        while retries < self.max_retries:
            try:
                self.cap = cv.VideoCapture(self.video_source)
                if not self.cap.isOpened():
                    raise ValueError(f"Cannot open Video Source: {self.video_source}")

                logger.info(f"Successfully initialized video source: {self.video_source}")
                return

            except Exception as e:
                retries += 1
                logger.error(f"Initialization attempt {retries}/{self.max_retries} failed: {e}")
                if retries == self.max_retries:
                    raise ValueError(f"Failed to initialize video source after {self.max_retries} attempts: {e}")
                time.sleep(self.retry_delay)

    def process_frame(self):
        """
        Read and process a single frame from internal capture.
        """
        try:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.warning("No frame received. Video connection lost.")
                return None

            return self._process(frame)

        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            return None

    def process_external_frame(self, frame):
        """
        Process an external frame passed manually (e.g., from RTSP feed).
        """
        try:
            if frame is None:
                logger.warning("Empty frame received for external processing.")
                return None

            return self._process(frame)

        except Exception as e:
            logger.error(f"Error processing external frame: {str(e)}")
            return None

    def _process(self, frame):
        """
        Common processing logic used by both internal and external frame processing.
        """
        fgmask = self.fgbg.apply(frame)
        if fgmask is None:
            logger.error("Background subtraction failed.")
            return None

        fgmask = cv.morphologyEx(fgmask, cv.MORPH_CLOSE, self.kernel)
        return fgmask

    def release(self):
        """
        Release internal video capture resources.
        """
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
                logger.info("Video capture resources released.")
        except Exception as e:
            logger.error(f"Error releasing resources: {str(e)}")
