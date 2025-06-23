import threading
import json
import os
from service.animal_image_procesor import AnimalDetectionProcessor
from service.human_processor_service import RTDETRProcessor

class UnifiedProcessor:
    _instance = None

    def __new__(cls, animal_model_path=None, human_model_path=None, confidence_threshold=0.45):
        # if cls._instance is None:
        cls._instance = super(UnifiedProcessor, cls).__new__(cls)
        cls._instance.initialize(animal_model_path, human_model_path, confidence_threshold)
        return cls._instance

    def initialize(self, animal_model_path, human_model_path, confidence_threshold=0.45):
        self.animal_processor = AnimalDetectionProcessor(
            cls_checkpoint_dir=animal_model_path,
            confidence_threshold=confidence_threshold
        )
        self.rtdetr_processor = RTDETRProcessor(
            model_name=human_model_path,
            confidence_threshold=confidence_threshold
        )

    def process_frame(self, frame_id, frame, camera_id):
        combined_detections = []
        lock = threading.Lock()

        def append_detections(results):
            with lock:
                combined_detections.extend(results)

        def animal_processing():
            animal_results = self.animal_processor.process_frame_for_detection(frame)
            append_detections(animal_results)

        def rtdetr_processing():
            rtdetr_results = self.rtdetr_processor.get_detections(frame)
            append_detections(rtdetr_results)

        animal_thread = threading.Thread(target=animal_processing)
        rtdetr_thread = threading.Thread(target=rtdetr_processing)
        animal_thread.start()
        rtdetr_thread.start()
        animal_thread.join()
        rtdetr_thread.join()

        return combined_detections
