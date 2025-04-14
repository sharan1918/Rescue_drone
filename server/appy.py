
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
import base64
import re

# === Load environment variables ===
load_dotenv()

# === Configure Gemini and Twilio ===
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model_gemini = genai.GenerativeModel('gemini-2.0-flash-lite')

TWILIO_SID = "ACbc0e64016b0568ceda63525d447c85fa"
TWILIO_AUTH_TOKEN = "358116af9b81d6ca6fd44fa652ff47bf"
TWILIO_PHONE = "+17193599865"
RECIPIENT_PHONE = "+917338887170"
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# === Flask App Setup ===
app = Flask(__name__, template_folder='templates')
model = YOLO("model_- 4 april 2025 18_39.pt")

lock = threading.Lock()

# === Store detection history ===
detection_history = []
detected_people = []

# === SMS sending ===
def send_sms(people_count, latitude, longitude,address):
    message = f"Distress Alert: {people_count} people detected in need. Location: {latitude}, {longitude}, Full address: {address}"
    # client.messages.create(to=RECIPIENT_PHONE, from_=TWILIO_PHONE, body=message)
    print("SMS Sent:", message)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {'lat': latitude, 'lon': longitude, 'format': 'json'}
    response = requests.get(url, params=params, headers={'User-Agent': 'MyApp'})
    address = response.json().get('display_name')
    print(f"The address is: {address}")

    file = request.files['image']
    in_memory_file = BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    image_cv2 = cv2.imdecode(data, cv2.IMREAD_COLOR)

    # Run YOLO detection
    results = model(image_cv2, verbose=False)
    for box in results[0].boxes:
        if int(box.cls) == 0:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(image_cv2, (x1, y1), (x2, y2), (0, 255, 0), 2)

    image_pil = Image.fromarray(cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB))
    image_pil.thumbnail((640, 640))

    # Gemini prompt
    prompt = (
        "Look at this image and answer the following:\n"
        "(1) How many people can you see?\n"
        "(2) Do any of them look like they might need help — even just possibly? \n"
        "This could be someone in an awkward position, looking unsure, alone in a risky spot, in water, or in a situation that just seems off.\n"
        "Use your judgment — it's okay to count people if you're not totally sure but they seem like they *could* need assistance.\n"
        "Respond only in this format: People: <number>, Distressed: <number>"
    )

    try:
        response = model_gemini.generate_content([prompt, image_pil])
        gemini_response_text = response.text.strip()
        print(f"Gemini Response: {gemini_response_text}")

        match = re.search(r"People:\s*(\d+),\s*Distressed:\s*(\d+)", gemini_response_text)
        if match:
            people_count = int(match.group(1))
            distress_count = int(match.group(2))
        else:
            people_count = 0
            distress_count = 0

    except Exception as e:
        print(f"Gemini Error: {e}")
        gemini_response_text = "Error analyzing image with Gemini."
        people_count = 0
        distress_count = 0

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if people_count == 0:
        message = "❌ No people detected"
    else:
        message = f"✅ Detected people: {people_count}"
        if latitude and longitude:
            message += f" at location ({latitude}, {longitude})"

    # Prepare detection entries
    detection_entry = {
        'message': message,
        'gemini_analysis': gemini_response_text,
        'timestamp': timestamp,
        'address': address
    }

    if distress_count > 0:
        send_sms(distress_count, latitude, longitude, address)
        img_encoded = cv2.imencode('.jpg', image_cv2)[1]
        img_base64 = base64.b64encode(img_encoded).decode('utf-8')
        people_det = {
            'message': message,
            'gemini_analysis': gemini_response_text,
            'timestamp': timestamp,
            'address': address,
            'image': img_base64
        }

    # Only lock this part — thread-safe update
    with lock:
        detection_history.append(detection_entry)
        if distress_count > 0:
            detected_people.append(people_det)

    return jsonify({
        'message': message,
        'gemini_analysis': gemini_response_text,
        'timestamp': timestamp
    })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detection_history')
def get_detection_history():
    return jsonify(detected_people[::-1])

@app.route('/live_feed')
def get_detection_historys():
    return jsonify(detection_history[-10:][::-1])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
