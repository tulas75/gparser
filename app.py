import streamlit as st
import requests
import os
from pathlib import Path

st.set_page_config(page_title="Document Parser Upload", page_icon="📄")

st.title("Document Parser Upload")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a file (PDF, Audio, Video, or Image)", 
    type=['pdf', 'mp3', 'wav', 'mp4', 'jpg', 'jpeg', 'png']
)

if uploaded_file is not None:
    # Show file details
    file_details = {
        "Filename": uploaded_file.name,
        "File size": f"{uploaded_file.size / 1024:.2f} KB",
        "File type": uploaded_file.type
    }
    st.write("File Details:")
    for key, value in file_details.items():
        st.write(f"- {key}: {value}")
    
    # Upload button
    if st.button("Upload and Process"):
        with st.spinner('Uploading and processing file...'):
            try:
                # Create temporary file
                temp_dir = Path("temp_uploads")
                temp_dir.mkdir(exist_ok=True)
                temp_path = temp_dir / uploaded_file.name
                
                # Save uploaded file temporarily
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                # Send to Flask API
                files = {'file': open(temp_path, 'rb')}
                response = requests.post('http://localhost:5000/upload', files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(result['message'])
                    if result.get('s3_file_name'):
                        st.info(f"File stored as: {result['s3_file_name']}")
                else:
                    st.error(f"Upload failed: {response.json().get('error', 'Unknown error')}")
                
                # Cleanup
                os.remove(temp_path)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                
            finally:
                # Ensure temp file is removed
                if temp_path.exists():
                    os.remove(temp_path)

st.divider()
st.markdown("""
### Supported File Types:
- PDF documents
- Audio files (MP3, WAV)
- Video files (MP4)
- Images (JPG, JPEG, PNG)
""")
