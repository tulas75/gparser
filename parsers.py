from openai import OpenAI
import magic
import openparse
import os
import json
import uuid
import base64
from coordinates import normalize_coordinates
import tempfile
import base64
from imgs import describe_image,describe_image_di,describe_image_oai
from s3 import upload_file_to_s3
from moviepy.editor import VideoFileClip
from langchain_core.documents import Document
from vectemb import get_vector_store_pg

#FIREWORKS_API_KEY = os.environ['FIREWORKS_API_KEY']
DEEPINFRA_API_KEY= os.environ['DEEPINFRA_API_KEY']
def parse_pdf(file_path,s3_file_name):
    """Parse PDF file and extract text"""
    try:
        temp_file = file_path
        filename = os.path.basename(file_path)

        parser = openparse.DocumentParser(
             table_args={
             "parsing_algorithm": "pymupdf",
             "table_output_format": "markdown"
             }
        )
        parsed_basic_doc = parser.parse(temp_file)

        print('Number of chunks:', len(parsed_basic_doc.nodes))
        chunks = parsed_basic_doc.model_dump_json()
        chunks = json.loads(chunks)

        documents = []
        uuids = []

        # Iterate over the nodes and create Document objects and UUIDs
        for i, node in enumerate (chunks['nodes'], start=0):
            variant = node['variant']
            url = s3_file_name 
            document_name = f"document_{i}"
            bbox_list = node['bbox']
            for bbox in bbox_list:
                page = bbox['page']
                
            if variant == ['text'] or variant == ['table', 'text']:
                doc = Document(
                    page_content=node['text'],
                    metadata={
                        "source": filename,
                        "tokens": node['tokens'],
                        "page": page,
                        "url": url,
                        "mimetype": "application/pdf",
                    },
                )
                documents.append(doc)
                uuids.append(node['node_id'])
            elif 'image' in variant:
                # Extract and save the image temporarily
                temp_image_path = os.path.join("temp_uploads", f"{node['node_id']}.jpeg")
                try:
                    print(f"\nProcessing image node at index {i}")
                    print(f"Node variant: {variant}")
                    print(f"Node keys: {node.keys()}")
                    
                    if 'images' not in node or not node['images']:
                        print(f"No valid images in node at index {i}")
                        continue
                    
                    # Process each image in the node
                    for image_dict in node['images']:
                        if not isinstance(image_dict, dict):
                            print(f"Invalid image dictionary in node at index {i}")
                            continue
                            
                        raw_image = image_dict.get('image') or image_dict.get('data')
                        if not raw_image:
                            print(f"No image data found in dictionary")
                            continue

                        # Ensure temp_uploads directory exists
                        os.makedirs("temp_uploads", exist_ok=True)

                        try:
                            # Handle base64 data
                            if isinstance(raw_image, bytes):
                                image_data = raw_image
                            elif isinstance(raw_image, str):
                                if raw_image.startswith(('data:image/', 'iVBOR', '/9j/')):
                                    # Remove headers if present
                                    if ',' in raw_image:
                                        raw_image = raw_image.split(',', 1)[1]
                                # Try direct base64 decode
                                image_data = base64.b64decode(raw_image)
                            else:
                                print(f"Unsupported image data type: {type(raw_image)}")
                                continue

                            # Verify we have actual image data
                            if len(image_data) == 0:
                                print("Empty image data received")
                                continue

                            with open(temp_image_path, 'wb') as f:
                                f.write(image_data)
                                f.flush()
                                os.fsync(f.fileno())  # Ensure data is written to disk

                            # Verify the file was created and has content
                            if os.path.exists(temp_image_path):
                                file_size = os.path.getsize(temp_image_path)
                                if file_size > 0:
                                    print(f"Successfully saved image to {temp_image_path}")
                                    print(f"Image file size: {file_size} bytes")
                                else:
                                    print("Image file was created but is empty")
                                    continue
                            else:
                                print("Failed to create image file")
                                continue

                        except base64.binascii.Error as e:
                            print(f"Failed to decode base64 data: {str(e)}")
                            continue
                        except AttributeError as e:
                            print(f"Failed to save image from node: {str(e)}")
                            continue
                        except Exception as e:
                            print(f"Unexpected error saving image: {str(e)}")
                            continue
                        
                    # Get image description
                    try:
                        print(f"Attempting to describe image...")
                        image_description = describe_image_oai(temp_image_path)
                        print(f"Got description: {image_description[:100]}...")
                        
                        # Upload image to S3 if description was successful
                        s3_image_path = f"images/{node['node_id']}.jpeg"
                        with open(temp_image_path, 'rb') as img_file:
                            upload_file_to_s3(img_file, s3_image_path)
                        print(f"Successfully uploaded image to S3: {s3_image_path}")
                        
                        doc = Document(
                            page_content=image_description,
                            metadata={
                                "source": filename,
                                "page": page,
                                "url": url,
                                "mimetype": "image/",
                                "image_url": s3_image_path
                            },
                        )
                        documents.append(doc)
                        uuids.append(node['node_id'])
                    except Exception as e:
                        print(f"Failed to describe image in {filename} at index {i}: {str(e)}")
                        continue
                finally:
                    # Clean up temporary image file
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
            print(f"{variant} {node['node_id']} {document_name}")

        # Add error handling
        try:
            #vector_store = get_vector_store(namespace="testino",index_name="langchain-test-index")
            vector_store = get_vector_store_pg(db="langchain", collection_name="dino")
            vector_store.add_documents(documents=documents, ids=uuids)
            print("Documents successfully added to the vector store.")
        except Exception as e:
            print(f"An error occurred while adding documents: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {str(e)}")
    
def parse_audio(file_path,s3_file_name):
    """Parse audio file and extract metadata"""
    try:
        url = s3_file_name
        #client = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=FIREWORKS_API_KEY)
        client = OpenAI(base_url="http://192.168.1.8:8000/v1", api_key=FIREWORKS_API_KEY)
        audio_file = open(file_path, "rb")
        transcription = client.audio.transcriptions.create(
          model="whisper-v3", 
          file=audio_file, 
          response_format="verbose_json"
        )
        
        # Process the transcription JSON
        transcription_data = json.loads(transcription.json())
        segments = transcription_data['segments']
        grouped_segments = []
        group_text = []
        documents = []
        uuids = []
        
        if not segments:
            raise Exception("No segments found in transcription")
            
        group_timestamps = {
            'from': segments[0]['start'],
            'to': ''
        }

        # Process segments by approximate token count
        current_word_count = 0
        for i, entry in enumerate(segments):
            text = entry['text']
            word_count = len(text.split())
            group_text.append(text)
            group_timestamps['to'] = entry['end']
            current_word_count += word_count

            # Targeting ~250 tokens (approximately 180-200 words)
            # or if we've reached the end of segments
            if current_word_count >= 180 or i == len(segments) - 1:
                # Join the text chunks
                aggregated_text = ' '.join(group_text)
                
                # Create a Document object
                doc = Document(
                    page_content=aggregated_text,
                    metadata={
                        "source": s3_file_name,
                        "start_time": group_timestamps['from'],
                        "end_time": group_timestamps['to'],
                        "url": url,
                        "mimetype": "audio/",
                    }
                )
                
                # Generate UUID for the chunk
                chunk_uuid = str(uuid.uuid4())
                
                documents.append(doc)
                uuids.append(chunk_uuid)

                # Reset for next group
                group_text = []
                current_word_count = 0
                if i < len(segments) - 1:
                    group_timestamps['from'] = segments[i + 1]['start']

        # Add to vector store
        try:
            vector_store = get_vector_store(namespace="audio", index_name="langchain-test-index")
            vector_store.add_documents(documents=documents, ids=uuids)
            print("Audio transcription chunks successfully added to the vector store.")
        except Exception as e:
            print(f"An error occurred while adding audio chunks: {str(e)}")
            
    except Exception as e:
        raise Exception(f"Failed to parse audio: {str(e)}")

def parse_video(file_path,s3_file_name):
    """Parse video file by extracting and transcribing its audio"""
    try:
        # Extract audio from video
        video = VideoFileClip(file_path)
        
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
            video.audio.write_audiofile(temp_audio_path)
        
        try:
            # Use the existing audio parsing logic
            url = s3_file_name
            client = OpenAI(base_url="http://192.168.1.8:8000/v1", api_key=FIREWORKS_API_KEY)
            
            audio_file = open(temp_audio_path, "rb")
            transcription = client.audio.transcriptions.create(
                model="whisper-v3",
                file=audio_file,
                response_format="verbose_json"
            )
            
            # Process the transcription JSON
            transcription_data = json.loads(transcription.json())
            segments = transcription_data['segments']
            grouped_segments = []
            group_text = []
            documents = []
            uuids = []
            
            if not segments:
                raise Exception("No segments found in transcription")
                
            group_timestamps = {
                'from': segments[0]['start'],
                'to': ''
            }

            # Process segments by approximate token count
            current_word_count = 0
            for i, entry in enumerate(segments):
                text = entry['text']
                word_count = len(text.split())
                group_text.append(text)
                group_timestamps['to'] = entry['end']
                current_word_count += word_count

                # Targeting ~250 tokens (approximately 180-200 words)
                # or if we've reached the end of segments
                if current_word_count >= 180 or i == len(segments) - 1:
                    # Join the text chunks
                    aggregated_text = ' '.join(group_text)
                    
                    # Create a Document object
                    doc = Document(
                        page_content=aggregated_text,
                        metadata={
                            "source": s3_file_name,
                            "start_time": group_timestamps['from'],
                            "end_time": group_timestamps['to'],
                            "url": url,
                            "mimetype": "video/",
                        }
                    )
                    
                    # Generate UUID for the chunk
                    chunk_uuid = str(uuid.uuid4())
                    
                    documents.append(doc)
                    uuids.append(chunk_uuid)

                    # Reset for next group
                    group_text = []
                    current_word_count = 0
                    if i < len(segments) - 1:
                        group_timestamps['from'] = segments[i + 1]['start']

            # Add to vector store
            try:
                #vector_store = get_vector_store(namespace="video", index_name="langchain-test-index")
                vector_store = get_vector_store_pg(db="langchain", collection_name="langchain-test-index")
                vector_store.add_documents(documents=documents, ids=uuids)
                print("Video transcription chunks successfully added to the vector store.")
            except Exception as e:
                print(f"An error occurred while adding video chunks: {str(e)}")
                
        finally:
            # Clean up
            audio_file.close()
            os.unlink(temp_audio_path)
            video.close()
            
    except Exception as e:
        raise Exception(f"Failed to parse video: {str(e)}")

def parse_image(file_path):
    """Parse image file and extract metadata"""
    try:
        print(file_path)
        # Here you could add image processing logic
        # For example: extract EXIF data, run OCR, etc.
    except Exception as e:
        raise Exception(f"Failed to parse image: {str(e)}")

def parse_file(file_path,s3_file_name):
    """Main parsing function that determines file type and calls appropriate parser"""
    mime_type = magic.from_file(file_path, mime=True)
    s3_file_name = s3_file_name    
    if mime_type == 'application/pdf':
        parse_pdf(file_path,s3_file_name)
    elif mime_type.startswith('audio/'):
        parse_audio(file_path,s3_file_name)
    elif mime_type.startswith('video/'):
        parse_video(file_path,s3_file_name)
    elif mime_type in ['image/jpeg', 'image/png', 'image/jpg']:
        parse_image(file_path)
    else:
        raise Exception(f"Unsupported file type: {mime_type}")
        
    return mime_type
