from flask import Flask, request, jsonify
from io import BytesIO
import cv2
import numpy as np
from ultralytics import YOLO



# Initialize Flask app
app = Flask(__name__)

# Load YOLOv8 model (make sure the .pt file is in the same directory or provide full path)
model = YOLO("model_- 4 april 2025 18_39.pt")

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check for image
    if 'image' not in request.files:
        print('❌ No image provided')
        return jsonify({'error': 'No image provided'}), 400

    # Get GPS
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')

    # Read image into OpenCV
    file = request.files['image']
    in_memory_file = BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)

    # Run YOLOv8 detection
    results = model(image, verbose=False)
    people_count = sum(1 for obj in results[0].boxes.cls if int(obj) == 0)

    message = "No people detected"

    if people_count > 0:
        message = f"✅ Detected {people_count} people"
        if latitude and longitude:
            message += f" at location ({latitude}, {longitude})"
        print(message)

    return jsonify({'message': message})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')