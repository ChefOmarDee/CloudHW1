import uuid
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from io import BytesIO
from PIL import Image
from google.cloud import storage, datastore
from google.auth import credentials

app = Flask(__name__)

# Initialize Google Cloud Storage client
storage_client = storage.Client.create_anonymous_client()

bucket_name = "chefbuckets"

@app.get("/")
def index():
    """Render an HTML page that asks for an image."""
    return render_template("upload_image.html")

@app.post("/upload-image")
def upload_image():
    """
    Endpoint to receive an image from the frontend.
    The image is processed and uploaded to GCS in memory.
    """
    # Check if the request contains a file part
    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400
    
    # Get the file from the request
    file = request.files['image']

    # Ensure the file has a valid filename
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        # Generate a unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        
        # Read image into memory buffer
        image_data = file.read()
        image_buffer = BytesIO(image_data)
        
        # Upload directly to Google Cloud Storage
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(unique_filename)
        
        # Upload from the in-memory buffer
        blob.upload_from_file(
            BytesIO(image_data), 
            content_type=file.content_type
        )
        
        # Rewind buffer to read image metadata
        image_buffer.seek(0)
        
        # Open image to get metadata (if needed)
        image = Image.open(image_buffer)
        width, height = image.size

        return jsonify({
            "filename": unique_filename,
            "original_filename": file.filename,
            "format": image.format,
            "size": {"width": width, "height": height},
            "upload_status": "Success"
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="localhost", port=8000, debug=True)