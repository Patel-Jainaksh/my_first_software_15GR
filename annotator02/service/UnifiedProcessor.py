import threading

from service.animal_image_procesor import AnimalDetectionProcessor
from service.human_processor_service import RTDETRProcessor


class UnifiedProcessor:
    def __init__(self):
        """Simple constructor to initialize both processors"""
        self.animal_processor = AnimalDetectionProcessor()
        self.rtdetr_processor = RTDETRProcessor()
        self.lock = threading.Lock()

    def process_frame(self, frame,confidecnce):
        """Process the frame using both models in parallel and return combined detections"""
        combined_detections = []

        def append_detections(results):
            with self.lock:
                combined_detections.extend(results)

        def run_animal():
            results = self.animal_processor.process_frame(frame,confidecnce)
            append_detections(results)

        def run_rtdetr():
            results = self.rtdetr_processor.get_detections(frame,confidecnce)
            append_detections(results)

        t1 = threading.Thread(target=run_animal)
        t2 = threading.Thread(target=run_rtdetr)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        return combined_detections
