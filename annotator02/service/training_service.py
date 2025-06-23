import os
import json
import shutil
import random
from datetime import datetime
from zipfile import ZipFile

from PIL import Image

ANNOTATION_DIR = 'annotator02/static/annotated_frames/annotation'
IMAGE_DIR = 'annotator02/static/annotated_frames/frames'
BASE_DIR = 'annotator02/Model_traning_Area'
HUMAN_MODEL_DIR = os.path.join(BASE_DIR, 'human_model_area')
ANIMAL_MODEL_DIR = os.path.join(BASE_DIR, 'animal_model_area')
MAINTENANCE_DATASET_DIR = 'maintenance/dataset/animal/full_dataset'

ANIMAL_CLASSES = [
    "antelope", "bear", "boar", "cat", "chimpanzee", "cow",
    "deer", "dog", "fox", "wild boar", "hare", "leopard",
    "goat", "owl", "ox", "pig", "reindeer", "sheep", "snake", "wolf"
]

# Master category list
CLASSES = [
    "antelope", "bear", "boar", "cat", "chimpanzee", "cow",
    "deer", "dog", "fox", "wild boar", "hare", "leopard",
    "goat", "owl", "ox", "pig", "reindeer", "sheep", "snake", "wolf", "person"
]
CATEGORY_MAP = {name: idx + 1 for idx, name in enumerate(CLASSES)}

def convert_to_coco_format(img_files, output_dir, output_ann_path, allowed_classes):
    os.makedirs(output_dir, exist_ok=True)

    # Filtered class map starting from ID 1
    filtered_categories = [c for c in CLASSES if c in allowed_classes]
    category_id_map = {name: idx + 1 for idx, name in enumerate(filtered_categories)}

    coco = {
        "images": [],
        "annotations": [],
        "categories": [{"id": idx + 1, "name": name} for idx, name in enumerate(filtered_categories)]
    }

    ann_id = 1
    img_id = 1
    for img_file in img_files:
        filename = os.path.basename(img_file)
        image_path = os.path.join(IMAGE_DIR, filename)
        ann_file = os.path.join(ANNOTATION_DIR, os.path.splitext(filename)[0] + '.txt')

        if not os.path.exists(image_path) or not os.path.exists(ann_file):
            continue

        valid_annotations = []

        with open(ann_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                label, x, y, w, h = parts
                if label not in allowed_classes:
                    continue
                try:
                    x, y, w, h = map(float, (x, y, w, h))
                except ValueError:
                    continue
                valid_annotations.append({
                    "category_id": category_id_map[label],
                    "bbox": [x, y, w, h],
                    "area": w * h,
                    "iscrowd": 0
                })

        if not valid_annotations:
            continue  # skip image with no valid annotations

        shutil.copy2(image_path, os.path.join(output_dir, filename))
        with Image.open(image_path) as img:
            width, height = img.size

        coco["images"].append({
            "id": img_id,
            "file_name": filename,
            "width": width,
            "height": height
        })

        for ann in valid_annotations:
            coco["annotations"].append({
                "id": ann_id,
                "image_id": img_id,
                **ann
            })
            ann_id += 1

        img_id += 1

    with open(output_ann_path, 'w') as f:
        json.dump(coco, f, indent=4)


def prepare_filtered_dataset(base_dir, class_filter):
    # Clean dataset folder only for human
    if class_filter == ['person'] and os.path.exists(base_dir):
        shutil.rmtree(base_dir)
        print(f"🧹 Cleaned human dataset folder: {base_dir}")

    all_images = [
        os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]
    random.shuffle(all_images)

    split_idx = int(len(all_images) * 0.8)
    train_imgs = all_images[:split_idx]
    test_imgs = all_images[split_idx:]

    train_dir = os.path.join(base_dir, 'train')
    test_dir = os.path.join(base_dir, 'test')

    for dir_path in [train_dir, test_dir]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        os.makedirs(dir_path, exist_ok=True)

    convert_to_coco_format(
        train_imgs, train_dir, os.path.join(train_dir, '_annotations.coco.json'), class_filter
    )
    convert_to_coco_format(
        test_imgs, test_dir, os.path.join(test_dir, '_annotations.coco.json'), class_filter
    )

from datetime import datetime
from zipfile import ZipFile

import tempfile

def prepare_animal_dataset(backup_dataset_dir='animals'):
    # Step 0: Validate backup directory
    if not os.path.isdir(backup_dataset_dir):
        print(f"❌ Backup folder not found: {backup_dataset_dir}")
        return
    print(f"📁 Using backup dataset folder: {backup_dataset_dir}")

    # Step 1: Clean existing train/test folders
    for subset in ['train', 'test']:
        path = os.path.join(ANIMAL_MODEL_DIR, subset)
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)

    # Step 2: Collect annotated classwise image paths
    classwise_images = {cls: [] for cls in ANIMAL_CLASSES}
    for ann_file in os.listdir(ANNOTATION_DIR):
        if not ann_file.endswith('.txt'):
            continue
        with open(os.path.join(ANNOTATION_DIR, ann_file), 'r') as f:
            labels = [line.split()[0] for line in f if len(line.split()) == 5]
            for label in set(labels):
                if label in ANIMAL_CLASSES:
                    img_path = os.path.join(IMAGE_DIR, os.path.splitext(ann_file)[0] + '.jpg')
                    if os.path.exists(img_path):
                        classwise_images[label].append(img_path)

    # Step 3: Fill shortages using backup
    for cls in ANIMAL_CLASSES:
        current_count = len(classwise_images[cls])
        if current_count >= 10:
            continue
        needed = 10 - current_count
        backup_cls_dir = os.path.join(backup_dataset_dir, cls)
        if os.path.exists(backup_cls_dir):
            available_images = [os.path.join(backup_cls_dir, f)
                                for f in os.listdir(backup_cls_dir)
                                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            random.shuffle(available_images)
            fill_images = available_images[:needed]
            classwise_images[cls].extend(fill_images)
            print(f"🧩 Filled {needed} images for class {cls} from backup")
        else:
            print(f"❌ No backup folder found for class {cls}, skipping fill.")

    # Step 4: Add 10 fallback images for fully missing classes
    for cls in ANIMAL_CLASSES:
        if not classwise_images[cls]:
            backup_cls_dir = os.path.join(backup_dataset_dir, cls)
            if os.path.exists(backup_cls_dir):
                all_backup_images = [os.path.join(backup_cls_dir, f)
                                     for f in os.listdir(backup_cls_dir)
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                random.shuffle(all_backup_images)
                classwise_images[cls] = all_backup_images[:10]
                print(f"📦 Injected 10 fallback images for missing class {cls}")
            else:
                print(f"⚠️ No backup images found for fully missing class: {cls}")

    # Step 5: Create train/test split and copy files
    for cls, images in classwise_images.items():
        if not images:
            continue
        random.shuffle(images)
        split_idx = int(len(images) * 0.8)
        train_imgs = images[:split_idx]
        test_imgs = images[split_idx:]

        for subset, subset_imgs in zip(['train', 'test'], [train_imgs, test_imgs]):
            out_dir = os.path.join(ANIMAL_MODEL_DIR, subset, cls)
            os.makedirs(out_dir, exist_ok=True)
            for img_path in subset_imgs:
                try:
                    shutil.copy2(img_path, out_dir)
                except Exception as e:
                    print(f"⚠️ Failed to copy {img_path}: {e}")

    # Optional: Debug info
    print("\n🧪 Final directory stats:")
    for cls in ANIMAL_CLASSES:
        train_dir = os.path.join(ANIMAL_MODEL_DIR, 'train', cls)
        test_dir = os.path.join(ANIMAL_MODEL_DIR, 'test', cls)
        train_count = len(os.listdir(train_dir)) if os.path.exists(train_dir) else 0
        test_count = len(os.listdir(test_dir)) if os.path.exists(test_dir) else 0
        print(f"{cls}: 🟢 Train = {train_count}, 🔵 Test = {test_count}")

    # Step 6: ZIP final dataset for archiving
    os.makedirs(MAINTENANCE_DATASET_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"animal_dataset_{timestamp}.zip"
    zip_path = os.path.join(MAINTENANCE_DATASET_DIR, zip_name)

    with ZipFile(zip_path, 'w') as zipf:
        for folder, _, files in os.walk(ANIMAL_MODEL_DIR):
            for file in files:
                full_path = os.path.join(folder, file)
                zipf.write(full_path, os.path.relpath(full_path, ANIMAL_MODEL_DIR))

    print(f"\n✅ Animal dataset preparation complete and zipped at: {zip_path}")

