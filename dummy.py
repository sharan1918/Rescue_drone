from flask import Flask, request, jsonify
from io import BytesIO
import cv2
import numpy as np
from ultralytics import YOLO
# from PIL import Image
# import google.generativeai as genai


app = Flask(__name__)
model = YOLO("model_- 4 april 2025 18_39.pt")  # Load the YOLOv8 model

# # Configure Gemini
# genai.configure(api_key='AIzaSyAu-mvfNBqPwCFltYXfv9a6fan33yXXPuI')  # Replace with your actual API key
# model_name = 'gemini-pro-vision'
# client = genai.GenerativeModel(model_name)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        print('Error: No image provided')
        return 'No image provided', 400

    # Get location data
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')

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
    
    # Initialize message with default value
    message = f'No people detected'
    
    # Update message if people are detected
    if people_count > 0:
        message = f'Detected {people_count} people'
        if latitude and longitude:
            message += f' at location ({latitude}, {longitude})'
        print(message)
        
        # # Convert OpenCV image to PIL Image for Gemini
        # image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # pil_image = Image.fromarray(image_rgb)
        # pil_image.thumbnail([640, 640], Image.Resampling.LANCZOS)
        # # Convert to byte stream
        # buffer = BytesIO()
        # pil_image.save(buffer, format="JPEG")
        # buffer.seek(0)
        # image_bytes = buffer.read()
        
        # image_part = genai.types.ImagePart(
        #     mime_type='image/jpeg',
        #     data=image_bytes,
        # )

        # # Gemini analysis
        # prompt = "Are any of the people in the image appearing stranded or needing help? Answer yes or no only."
        # response = client.generate_content([prompt, image_part])
        
        # # Add Gemini's analysis to the message
        # message += f". Gemini analysis: {response.text}"
        # print(f"Gemini analysis: {response.text}")
    
    return message

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

# //////////////

# from ultralytics import YOLO
# from PIL import Image
# import cv2
# import os

# # === Step 1: Load YOLO model ===
# model = YOLO("model_- 4 april 2025 18_39.pt")  # your trained VisDrone YOLOv8 model

# # === Step 2: Detect humans ===
# img_path = "/content/download.jfif"
# results = model(img_path)

# # Get boxes only for 'person' or 'pedestrian' class (class_id depends on your training dataset)
# boxes = []
# for box in results[0].boxes.data:
#     cls_id = int(box[5].item())  # class id
#     if cls_id in [0]:  # replace [0] with actual human/pedestrian class ID
#         boxes.append(box[:4].cpu().numpy())  # xyxy format

# print(f"Detected {len(boxes)} people.")

# # === Step 3: If humans are detected, send to Gemini LLM ===
# if len(boxes) > 0:
#     # Load image and resize
#     im = Image.open(img_path)
#     im.thumbnail([640, 640], Image.Resampling.LANCZOS)

#     # Gemini Prompt
#     prompt = "Show me humans if they need help or not or look like stranded. Give the answer as yes or no?  where N is the number of people in distress."

#     # Gemini call (pseudo-code below; replace with your client logic)
#     response = client.models.generate_content(
#         model=model_name,
#         contents=[prompt, im],
#         config=types.GenerateContentConfig(
#             system_instruction=bounding_box_system_instructions,
#             temperature=0.5,
#             safety_settings=safety_settings,
#         )
#     )

#     # === Step 4: Print output ===
#     print(response.text)

# else:
#     print("No humans detected.")