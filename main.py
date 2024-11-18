from flask import Flask, request, jsonify
import uuid
import os
import shutil
from s3 import upload_file_to_s3
from parsers import parse_file

app = Flask(__name__)

# Create a temporary directory if it doesn't exist
TEMP_DIR = "temp_uploads"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Generate a UUID for S3 storage
    file_uuid = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    s3_file_name = f"files/{file_uuid}{file_extension}"

    # Save the file temporarily with original name
    temp_path = os.path.join(TEMP_DIR, file.filename)
    try:
        file.save(temp_path)
        
        # Check and parse the file based on its type
        parse_result = parse_file(temp_path,s3_file_name)
        mime_type = parse_result['mime_type']
        chunks = parse_result['chunks']
        
        message = "File parsed but not uploaded (unsupported type for storage)"
        # Only upload if it's a supported file type
        if mime_type in ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'] or mime_type.startswith(('audio/', 'video/')):
            with open(temp_path, 'rb') as f:
                upload_file_to_s3(f, s3_file_name)
            message = "File parsed,vectorialized and uploaded successfully"
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return jsonify({
        "message": message,
        "s3_file_name": s3_file_name if mime_type in ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'] or mime_type.startswith(('audio/', 'video/')) else None,
        "chunks": chunks
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
