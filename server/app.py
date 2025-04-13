from flask import Flask, request, jsonify, render_template
from io import BytesIO
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO
import google.generativeai as genai
from dotenv import load_dotenv
from twilio.rest import Client
from datetime import datetime
import os
import threading
import requests

# === Load environment variables ===
load_dotenv()

# === Configure Gemini and Twilio ===
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model_gemini = genai.GenerativeModel('gemini-2.0-flash-lite')

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
RECIPIENT_PHONE = os.getenv("TWILIO_RECIPIENT_PHONE")
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# === Flask App Setup ===
app = Flask(__name__, template_folder='templates')
model = YOLO("model_- 4 april 2025 18_39.pt")

lock = threading.Lock()

# === Store detection history ===
detection_history = []
detected_people = []
# === SMS sending ===
def send_sms(people_count, latitude, longitude):
    message = f"Distress Alert: {people_count} people detected in need. Location: {latitude}, {longitude}"
    # client.messages.create(to=RECIPIENT_PHONE, from_=TWILIO_PHONE, body=message)
    print("SMS Sent:", message)

# === Upload Route ===
@app.route('/upload', methods=['POST'])
def upload_file():
    with lock:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json'
        }

        response = requests.get(url, params=params, headers={'User-Agent': 'MyApp'})
        data = response.json()

        # Extract address
        address = data.get('display_name')

        print(f"The address is: {address}")

        file = request.files['image']
        in_memory_file = BytesIO()
        file.save(in_memory_file)
        data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
        image_cv2 = cv2.imdecode(data, cv2.IMREAD_COLOR)

        results = model(image_cv2, verbose=False)
        people_count = sum(1 for obj in results[0].boxes.cls if int(obj) == 0)

        message = "No people detected"
        gemini_response_text = None
        print("no people detected")
        if people_count > 0:
            message = f"✅ Detected {people_count} people"
            if latitude and longitude:
                message += f" at location ({latitude}, {longitude})"

            for box in results[0].boxes:
                if int(box.cls) == 0:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(image_cv2, (x1, y1), (x2, y2), (0, 255, 0), 2)

            image_pil = Image.fromarray(cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB))
            image_pil.thumbnail((640, 640))

            prompt = (
                "This image contains detected people. "
                "Do any of them appear to be stranded or in need of help? "
                "Answer only 'Yes' or 'No' and mention the number of people that appear in distress."
            )

            try:
                response = model_gemini.generate_content([prompt, image_pil])
                gemini_response_text = response.text.strip()
                print(message)
                print(f"Gemini Response: {gemini_response_text}")

                if gemini_response_text and gemini_response_text.lower().startswith("yes"):
                    send_sms(people_count, latitude, longitude)

            except Exception as e:
                print(f"Gemini Error: {e}")
                gemini_response_text = "Error analyzing image with Gemini."

        detection_entry = {
            'message': message,
            'gemini_analysis': gemini_response_text or "No response",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'address': address
        }

        if gemini_response_text and gemini_response_text.lower().startswith("yes"):
            people_det = {
                'message': message,
                'gemini_analysis': gemini_response_text or "No response",
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'address': address
            }
            detected_people.append(people_det)

        detection_history.append(detection_entry)

        return jsonify({
            'message': message,
            'gemini_analysis': gemini_response_text,
            'timestamp': detection_entry['timestamp']
        })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detection_history')
def get_detection_history():
    return jsonify(detected_people[::-1])  # Return last 10 entries (newest first)

@app.route('/live_feed')
def get_detection_historys():
    return jsonify(detection_history[-10:][::-1])  # Return last 10 entries (newest first)

@app.route('/print_detection_history')
def print_detection_history():
    print(detection_history)
    return "Detection history printed to console"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
