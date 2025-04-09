# from flask import Flask, request, jsonify
# from io import BytesIO
# from PIL import Image
# import numpy as np
# import cv2
# from ultralytics import YOLO
# import google.generativeai as genai  # Make sure you have this installed: pip install google-generativeai
# from dotenv import load_dotenv
# from twilio.rest import Client  # noqa: F401
# import os

# # Load environment variables
# load_dotenv()

# # === Gemini Config ===
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))  # Get API key from .env
# model_gemini = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
# # Twilio credentials
# TWILIO_SID = "ACbc0e64016b0568ceda63525d447c85fa"
# TWILIO_AUTH_TOKEN = "37b74398668409f679e3aaebd68c721e"
# TWILIO_PHONE = "+17193599865"
# RECIPIENT_PHONE = "+917338887170"
# client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
# # === Flask App Setup ===
# app = Flask(__name__)

# # Load YOLOv8 model
# model = YOLO("model_- 4 april 2025 18_39.pt")

# def send_sms(people_count, latitude, longitude):
#     message = f"Distress Alert: {people_count} people detected in need. Location: {latitude}, {longitude}"
#     # client.messages.create(to=RECIPIENT_PHONE, from_=TWILIO_PHONE, body=message)
#     print("SMS Sent:", message)

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     # Check for image
#     if 'image' not in request.files:
#         print('❌ No image provided')
#         return jsonify({'error': 'No image provided'}), 400

#     # Get GPS
#     latitude = request.form.get('latitude')
#     longitude = request.form.get('longitude')

#     # Read image into OpenCV
#     file = request.files['image']
#     in_memory_file = BytesIO()
#     file.save(in_memory_file)
#     data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
#     image_cv2 = cv2.imdecode(data, cv2.IMREAD_COLOR)

#     # YOLO detection
#     results = model(image_cv2, verbose=False)
#     people_count = sum(1 for obj in results[0].boxes.cls if int(obj) == 0)

#     # Message default
#     message = "No people detected"
#     gemini_response_text = None

#     if people_count > 0:
#         message = f"✅ Detected {people_count} people"
#         if latitude and longitude:
#             message += f" at location ({latitude}, {longitude})"
#         print(message)

#         # Prepare image for Gemini
#         image_pil = Image.open(BytesIO(in_memory_file.getvalue()))
#         image_pil.thumbnail((640, 640))

#         # Ask Gemini if people look stranded or in need
#         prompt = (
#             "This image contains detected people. "
#             "Do any of them appear to be stranded or in need of help? "
#             "Answer only 'Yes' or 'No' and mention the number of people that appear in distress."
#         )

#         try:
#             response = model_gemini.generate_content(
#                 [prompt, image_pil]
#             )
#             gemini_response_text = response.text.strip()
#             print(f"Gemini Response: {gemini_response_text}")
#             if gemini_response_text and gemini_response_text.lower().startswith("yes"):
#                 send_sms(people_count, latitude, longitude)
#         except Exception as e:
#             print(f"Error from Gemini: {e}")
#             gemini_response_text = "Error analyzing image with Gemini."

#     # Return both YOLO and Gemini info
#     return jsonify({
#         'message': message,
#         'gemini_analysis': gemini_response_text
#     })

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0')


from flask import Flask, request, jsonify
from io import BytesIO
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO
import google.generativeai as genai
from dotenv import load_dotenv
from twilio.rest import Client
import os
import threading  # 🧠 For thread safety (sequential processing)

# === Load environment variables ===
load_dotenv()

# === Gemini Config ===
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model_gemini = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')

# === Twilio credentials ===
TWILIO_SID = "ACbc0e64016b0568ceda63525d447c85fa"
TWILIO_AUTH_TOKEN = "37b74398668409f679e3aaebd68c721e"
TWILIO_PHONE = "+17193599865"
RECIPIENT_PHONE = "+917338887170"
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# === Flask App Setup ===
app = Flask(__name__)
model = YOLO("model_- 4 april 2025 18_39.pt")

# === Lock for single image processing at a time ===
lock = threading.Lock()

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
            print('❌ No image provided')
            return jsonify({'error': 'No image provided'}), 400

        # GPS coordinates
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        # Read image into OpenCV
        file = request.files['image']
        in_memory_file = BytesIO()
        file.save(in_memory_file)
        data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
        image_cv2 = cv2.imdecode(data, cv2.IMREAD_COLOR)

        # Run YOLO detection
        results = model(image_cv2, verbose=False)
        people_count = sum(1 for obj in results[0].boxes.cls if int(obj) == 0)

        message = "No people detected"
        gemini_response_text = None

        if people_count > 0:
            message = f"✅ Detected {people_count} people"
            if latitude and longitude:
                message += f" at location ({latitude}, {longitude})"
            print(message)

            # Prepare image for Gemini
            image_pil = Image.open(BytesIO(in_memory_file.getvalue()))
            image_pil.thumbnail((640, 640))

            prompt = (
                "This image contains detected people. "
                "Do any of them appear to be stranded or in need of help? "
                "Answer only 'Yes' or 'No' and mention the number of people that appear in distress."
            )

            try:
                response = model_gemini.generate_content([prompt, image_pil])
                gemini_response_text = response.text.strip()
                print(f"Gemini Response: {gemini_response_text}")

                if gemini_response_text and gemini_response_text.lower().startswith("yes"):
                    send_sms(people_count, latitude, longitude)

            except Exception as e:
                print(f"Error from Gemini: {e}")
                gemini_response_text = "Error analyzing image with Gemini."

        return jsonify({
            'message': message,
            'gemini_analysis': gemini_response_text
        })

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
