# gparser
Flask app for parsing documents,audio and videos, using openparse, embeddings and vector db
# Document Processing and Vectorization API

A Flask-based API for processing, parsing, and vectorizing various document types including PDFs, images, audio, and video files. The system extracts content, processes it, and stores both the files and their vector embeddings for later retrieval.

## Features

- Multi-format document processing (PDF, Audio, Video, Images)
- Automatic text extraction and processing
- Image description generation using AI
- Vector embeddings generation and storage
- S3-compatible storage integration
- Pinecone vector database integration

## System Requirements

- Python 3.8+
- Flask
- Various dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone git@github.com:tulas75/gparser.git
cd gparser
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env` file:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
S3_BUCKET=your_bucket_name
S3_ENDPOINT=your_endpoint
PINECONE_API_KEY=your_pinecone_key
FIREWORKS_API_KEY=your_fireworks_key
GROQ_API_KEY=your_groq_key
```

## API Endpoints

### POST /upload
Uploads and processes a file, storing both the file and its vector embeddings.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (file)

**Response:**
```json
{
    "message": "File parsed,vectorialized and uploaded successfully",
    "s3_file_name": "files/uuid.extension"
}
```

## Core Components

### 1. File Parsing (parsers.py)
- PDF parsing with coordinate normalization
- Audio transcription
- Video processing (extracts audio for transcription)
- Image processing and description

### 2. Vector Embeddings (vectemb.py)
- Generates embeddings using InfinityEmbeddings
- Stores vectors in Pinecone database
- Manages namespaces for different content types

### 3. S3 Storage (s3.py)
- Handles file uploads to S3-compatible storage
- Manages file paths and access

### 4. Image Processing (imgs.py)
- Generates image descriptions using AI
- Handles base64 encoding/decoding
- Integrates with Groq API for image analysis

### 5. Coordinate Processing (coordinates.py)
- Normalizes PDF coordinates
- Converts between different coordinate systems

## Usage

1. Start the Flask server:
```bash
python main.py
```

2. Send files for processing:
```bash
curl -X POST -F "file=@/path/to/your/file" http://localhost:5000/upload
```

## Error Handling

The API includes comprehensive error handling for:
- Invalid file types
- Processing failures
- Storage errors
- Vector embedding issues

## Development

### Project Structure
```
gparser/
├── main.py           # Flask application entry point
├── parsers.py        # File parsing logic
├── vectemb.py        # Vector embedding handling
├── s3.py            # S3 storage integration
├── imgs.py          # Image processing
├── coordinates.py    # Coordinate system handling
└── requirements.txt  # Project dependencies
```

### Adding New Features
1. Create new parser in parsers.py for new file types
2. Update main.py to handle new mime types
3. Add appropriate vector embedding logic in vectemb.py

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
