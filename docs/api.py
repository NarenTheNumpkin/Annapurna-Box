import os
import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template
from PIL import Image 
from flask_cors import CORS
from google import genai

client = genai.Client(api_key=os.environ.get('GEMINI_API')) 

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        print("No file in request.files:", request.files)
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    print("Received file:", file.filename)

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    print(f"Saved file to {file_path}")

    try:
        img = Image.open(file_path)
        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        print(f"Image dimensions: {width}x{height}, mode: {img.mode}")
        
        prompt = "Analyze this food image and return a JSON object with the following structure: {\"dish\": \"name of the dish\", \"freshness\": number (0-100), \"quality\": \"Unhealthy/Bad/Can't Determine/Good/Very Good\", \"quantity\": \"description\", \"nutrition_value\": number (0-100)}. Identify the dish in the image and rate the quality based on freshness, edibility, quantity, and nutrition value. Return ONLY valid JSON without any markdown formatting or code blocks."
        
        ai_response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=[prompt, img]
        )
        
        print(f"Raw Gemini response: {ai_response.text}")
        
        try:
            import json
            import re
            
            ai_text = ai_response.text.strip()
            
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', ai_text, re.DOTALL)
            if json_match:
                ai_text = json_match.group(1).strip()
            
            # Extract JSON object from text
            json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
            if json_match:
                ai_text = json_match.group(0)
            
            ai_data = json.loads(ai_text)
            
            # Ensure all required fields are present
            if "dish" not in ai_data:
                ai_data["dish"] = "Unknown Food Item"
            if "freshness" not in ai_data:
                ai_data["freshness"] = 75
            if "quality" not in ai_data:
                ai_data["quality"] = "Good"
            if "quantity" not in ai_data:
                ai_data["quantity"] = "Medium"
            if "nutrition_value" not in ai_data and "nutrition value" not in ai_data:
                ai_data["nutrition_value"] = 70
            elif "nutrition value" in ai_data:
                ai_data["nutrition_value"] = ai_data.pop("nutrition value")
            
            print("AI analysis result:", ai_data)
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            print(f"Raw AI response: {ai_response.text}")
            ai_data = {
                "dish": "Unknown Food Item",
                "freshness": "75",
                "quality": "Good",
                "quantity": "Medium",
                "nutrition_value": "70"
            }
        
        image_url = f"http://127.0.0.1:5002/uploads/{file.filename}"
            
        response_data = {
            "image_url": image_url,
            "width": width,
            "height": height,
            "ai_analysis": ai_data
        }
        
        print("Returning combined response:", response_data)
        return jsonify(response_data)
    
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({
            "error": f"Error processing image: {str(e)}",
            "image_url": f"http://127.0.0.1:5002/uploads/{file.filename}"
        }), 500

@app.route('/user/<username>')
def profile(username):
    return f'{username}\'s profile'

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5002)
