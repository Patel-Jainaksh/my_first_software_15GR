import json
from service.UnifiedProcessor import UnifiedProcessor

processors = []
NUM_PROCESSORS = 4
current_index = 0

def load_model_paths(json_path="modelRepository/modelUsageStatus.json"):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            return data.get("animalModelPath", ""), data.get("humanModelPath", "")
    except Exception as e:
        raise RuntimeError(f"Failed to load model paths: {e}")

def get_processors():
    global processors
    processors.clear()

    animal_path, human_path = load_model_paths()
    print("Creating unified instance with animal model path : ",animal_path)
    print("Creating unified instance with human model path : ",human_path)

    for _ in range(NUM_PROCESSORS):
        processor = UnifiedProcessor(
            animal_model_path=animal_path,
            human_model_path=human_path
        )
        processors.append(processor)

def get_next_processor():
    global current_index
    if not processors:
        raise RuntimeError("Processors not initialized. Call get_processors() first.")

    proc = processors[current_index]
    current_index = (current_index + 1) % NUM_PROCESSORS
    return proc
