from flask import Flask, request, jsonify
from io import BytesIO
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image
import google.generativeai as genai
from google.generativeai import Part


# Initialize Flask app
app = Flask(__name__)

# Load YOLOv8 model (make sure the .pt file is in the same directory or provide full path)
model = YOLO("model_- 4 april 2025 18_39.pt")

# Configure Gemini with your API key
genai.configure(api_key='YOUR_GEMINI_API_KEY') # Replace with your actual API key
gemini_client = genai.GenerativeModel('gemini-pro-vision')

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

        # Convert OpenCV image to PIL for thumbnailing
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        pil_image.thumbnail((640, 640), Image.Resampling.LANCZOS)

        # Convert PIL image to byte stream for potential later use (optional for Gemini)
        # buffer = BytesIO()
        # pil_image.save(buffer, format="JPEG")
        # buffer.seek(0)

        # Use Gemini for analysis
        prompt = "Are any of the people in the image appearing stranded or needing help? Answer yes or no only."
        try:
            # Reset the buffer to the beginning to read the image data again
            in_memory_file.seek(0)
            gemini_response = gemini_client.generate_content(
                [prompt, Part.from_data(data=in_memory_file.read(), mime_type=file.content_type)]
            )
            gemini_text = gemini_response.text.strip()
            print(f"🤖 Gemini response: {gemini_text}")
            message += f". Gemini analysis: {gemini_text}"
        except Exception as e:
            print(f"⚠️ Gemini error: {e}")
            message += ". Gemini analysis failed."

    return jsonify({'message': message})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')