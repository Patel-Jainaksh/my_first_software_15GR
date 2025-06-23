import os
import shutil
from service.training_service import convert_to_coco_format, IMAGE_DIR

def create_human_dataset_zip():
    from datetime import datetime

    OUTPUT_DIR = 'maintenance/dataset/human'
    TEMP_DATASET_DIR = os.path.join(OUTPUT_DIR, 'full_dataset')

    # Add timestamp to ZIP name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"human_dataset_{timestamp}"
    ZIP_PATH = os.path.join(OUTPUT_DIR, zip_filename)

    os.makedirs(TEMP_DATASET_DIR, exist_ok=True)

    all_images = [
        os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]

    # Filter and convert all with only 'person' class
    convert_to_coco_format(
        all_images,
        TEMP_DATASET_DIR,
        os.path.join(TEMP_DATASET_DIR, '_annotations.coco.json'),
        allowed_classes=['person']
    )

    # Create ZIP archive using efficient shutil.make_archive
    shutil.make_archive(ZIP_PATH, 'zip', TEMP_DATASET_DIR)

