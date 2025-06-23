import os

from flask import Blueprint, render_template, jsonify, request

verify_data_set_bp = Blueprint('verify_data_set_bp', __name__)

@verify_data_set_bp.route('/verifyDataSet', methods=['GET'])
def home():
    return render_template('verifyDataSet.html')


@verify_data_set_bp.route('/api/list_annotated_images')
def list_annotated_images():
    frame_dir = 'annotator02/static/annotated_frames/frames'
    annotation_dir = 'annotator02/static/annotated_frames/annotation'

    image_files = [
        f for f in os.listdir(frame_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png')) and
           os.path.exists(os.path.join(annotation_dir, os.path.splitext(f)[0] + '.txt'))
    ]
    return jsonify(image_files)


@verify_data_set_bp.route('/api/delete_images', methods=['POST'])
def delete_images():
    import os
    data = request.get_json()
    files = data.get('files', [])

    frame_dir = 'annotator02/static/annotated_frames/frames'
    ann_dir = 'annotator02/static/annotated_frames/annotation'

    for filename in files:
        try:
            img_path = os.path.join(frame_dir, filename)
            txt_path = os.path.join(ann_dir, os.path.splitext(filename)[0] + '.txt')
            if os.path.exists(img_path):
                os.remove(img_path)
            if os.path.exists(txt_path):
                os.remove(txt_path)
        except Exception as e:
            print(f"Failed to delete {filename}: {e}")
    return jsonify({"status": "done"})

