from flask import Flask, request, jsonify
from io import BytesIO
import cv2
import numpy as np
from ultralytics import YOLO

app = Flask(__name__)
model = YOLO("yolov8n.pt")  # Load the YOLOv8 model

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        print('Error: No image provided')
        return 'No image provided', 400

    file = request.files['image']
    # Convert the image file to an OpenCV format
    in_memory_file = BytesIO()
    file.save(in_memory_file)
    data = np.fromstring(in_memory_file.getvalue(), dtype=np.uint8)
    color_image_flag = 1
    image = cv2.imdecode(data, color_image_flag)

    # Process image with YOLO model with verbose=False
    results = model(image, verbose=False)
    people_count = sum(1 for obj in results[0].boxes.cls if int(obj) == 0)  # Class 0 is 'person'
    
    # Print the detection results
    message = f'Detected {people_count} people' if people_count > 0 else 'No people detected'
    print(message)
    
    return message

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
