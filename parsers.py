import magic
import os
import openparse
import json
import uuid
import base64
from coordinates import normalize_coordinates
import tempfile
from imgs import describe_image,describe_image_oai
from s3 import upload_file_to_s3
from pdf_helpers import handle_text_content, handle_image_content, process_mixed_variant
from moviepy.editor import VideoFileClip
from langchain_core.documents import Document
from vectemb import get_vector_store_pg
from whisper import whisper_parse

def get_pg_vector_store():
    """Helper function to get PostgreSQL vector store with environment variables"""
    return get_vector_store_pg(
        pgdb=os.environ['PGDB'],
        collection_name=os.environ['COLLECTION_NAME'],
        pghost=os.environ['PGHOST'],
        pgpwd=os.environ['PGPWD'],
        pguser=os.environ['PGUSER'],
        pgport=os.environ['PGPORT']
    )

def parse_pdf(file_path, s3_file_name):
    """Parse PDF file and extract text, images, and mixed content"""
    try:
        filename = os.path.basename(file_path)
        processed_chunks = []
        parser = openparse.DocumentParser(
            table_args={
                "parsing_algorithm": "pymupdf",
                "table_output_format": "markdown"
            }
        )
        parsed_basic_doc = parser.parse(file_path)
        print('Number of chunks:', len(parsed_basic_doc.nodes))
        
        chunks = json.loads(parsed_basic_doc.model_dump_json())
        documents = []
        uuids = []

        for i, node in enumerate(chunks['nodes'], start=0):
            variant = node['variant']
            url = s3_file_name
            bbox_list = node['bbox']
            page = bbox_list[0]['page'] if bbox_list else 0
            node_uuid = node['node_id']

            print(f"Processing node {i} with variant: {variant}")

            # Handle pure text or table+text variants
            if set(variant).issubset({'text', 'table'}):
                doc = handle_text_content(node, filename, url, page)
                documents.append(doc)
                uuids.append(node_uuid)
                
            # Handle pure image variant
            elif variant == ['image']:
                try:
                    image_description, s3_path = handle_image_content(node, filename, url, page)
                    if image_description and s3_path:
                        doc = Document(
                            page_content=image_description,
                            metadata={
                                "source": filename,
                                "page": page,
                                "url": url,
                                "mimetype": "image/",
                                "image_url": s3_path
                            }
                        )
                        documents.append(doc)
                        uuids.append(node_uuid)
                except Exception as e:
                    print(f"Failed to process image node {i}: {str(e)}")
                    
            # Handle mixed variants (text+image, image+text, etc)
            elif set(variant).intersection({'text', 'image'}):
                try:
                    mixed_docs = process_mixed_variant(node, filename, url, page)
                    for doc in mixed_docs:
                        documents.append(doc)
                        uuids.append(f"{node_uuid}_{len(uuids)}")
                except Exception as e:
                    print(f"Failed to process mixed variant node {i}: {str(e)}")
            
            print(f"Processed variant {variant} for node {node_uuid}")

        # Add error handling
        try:
            #vector_store = get_vector_store(namespace="testino",index_name="langchain-test-index")
            vector_store = get_pg_vector_store()
            vector_store.add_documents(documents=documents, ids=uuids)
            print("Documents successfully added to the vector store.")
            
            # Prepare chunks info for return
            for doc in documents:
                chunk_info = {
                    'token_count': len(doc.page_content.split()),  # Approximate token count
                    'mimetype': doc.metadata.get('mimetype', 'N/A'),
                    'source': doc.metadata.get('source', 'N/A'),
                    'page': doc.metadata.get('page', 'N/A'),
                    'url': doc.metadata.get('url', 'N/A'),
                    'image_url': doc.metadata.get('image_url', None),
                    'vectorized': True
                }
                processed_chunks.append(chunk_info)
                
        except Exception as e:
            print(f"An error occurred while adding documents: {str(e)}")
            
        return processed_chunks
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {str(e)}")
    
def parse_audio(file_path,s3_file_name):
    """Parse audio file and extract metadata"""
    try:
        url = s3_file_name
        filename = os.path.basename(file_path)
        processed_chunks = []
        
        # Process the transcription JSON
        transcription_data = whisper_parse(file_path)
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
                        "source": filename,
                        "start_time": group_timestamps['from'],
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
            vector_store = get_pg_vector_store()
            vector_store.add_documents(documents=documents, ids=uuids)
            print("Audio transcription chunks successfully added to the vector store.")
            # Prepare chunks info for return
            for doc in documents:
                chunk_info = {
                    'token_count': len(doc.page_content.split()),  # Approximate token count
                    'mimetype': doc.metadata.get('mimetype', 'N/A'),
                    'source': doc.metadata.get('source', 'N/A'),
                    'url': doc.metadata.get('url', 'N/A'),
                    'start_time': doc.metadata.get('start_time','N/A'),
                    'vectorized': True
                }
                processed_chunks.append(chunk_info)

        except Exception as e:
            print(f"An error occurred while adding audio chunks: {str(e)}")
            
        return processed_chunks
            
    except Exception as e:
        raise Exception(f"Failed to parse audio: {str(e)}")

def parse_video(file_path,s3_file_name):
    """Parse video file by extracting and transcribing its audio"""
    try:
        processed_chunks = []
        # Extract audio from video
        video = VideoFileClip(file_path)
        
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
            video.audio.write_audiofile(temp_audio_path)
        
        try:
            # Use whisper_parse for video audio just like we do for audio files
            url = s3_file_name
            transcription_data = whisper_parse(temp_audio_path)
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
                vector_store = get_pg_vector_store()
                vector_store.add_documents(documents=documents, ids=uuids)
                print("Video transcription chunks successfully added to the vector store.")
                # Prepare chunks info for return
                for doc in documents:
                    chunk_info = {
                        'token_count': len(doc.page_content.split()),  # Approximate token count
                        'mimetype': doc.metadata.get('mimetype', 'N/A'),
                        'source': doc.metadata.get('source', 'N/A'),
                        'url': doc.metadata.get('url', 'N/A'),
                        'start_time': doc.metadata.get('start_time','N/A'),
                        'vectorized': True
                    }
                processed_chunks.append(chunk_info)

            except Exception as e:
                print(f"An error occurred while adding video chunks: {str(e)}")
                
        finally:
            # Clean up
            os.unlink(temp_audio_path)
            video.close()
            
        return processed_chunks
            
    except Exception as e:
        raise Exception(f"Failed to parse video: {str(e)}")

def parse_image(file_path,s3_file_name):
    """Parse image file and extract metadata"""
    try:
        url = s3_file_name
        filename = os.path.basename(file_path)
        
        # Get image description
        try:
            print(f"Attempting to describe image...")
            image_description = describe_image_oai(file_path)
            print(f"Got description: {image_description[:100]}...")
            
            # Create Document object
            doc = Document(
                page_content=image_description,
                metadata={
                    "source": filename,
                    "url": url,
                    "mimetype": "image/",
                    "image_url": s3_file_name
                },
            )
            
            # Generate UUID for the document
            doc_uuid = str(uuid.uuid4())
            
            # Add to vector store
            try:
                vector_store = get_vector_store_pg(
                    pgdb=os.environ['PGDB'], 
                    collection_name=os.environ['COLLECTION_NAME'],
                    pghost=os.environ['PGHOST'],
                    pgpwd=os.environ['PGPWD'],
                    pguser=os.environ['PGUSER'],
                    pgport=os.environ['PGPORT']
                )
                vector_store.add_documents(documents=[doc], ids=[doc_uuid])
                print("Image description successfully added to the vector store.")
            except Exception as e:
                print(f"An error occurred while adding image description: {str(e)}")
                
            # Create chunks info for return
            processed_chunks = [{
                'token_count': len(doc.page_content.split()),
                'mimetype': doc.metadata.get('mimetype', 'N/A'),
                'source': doc.metadata.get('source', 'N/A'),
                'url': doc.metadata.get('url', 'N/A'),
                'image_url': doc.metadata.get('image_url', 'N/A'),
                'vectorized': True
            }]
            return processed_chunks
                
        except Exception as e:
            print(f"Failed to process image {filename}: {str(e)}")
            raise
            
    except Exception as e:
        raise Exception(f"Failed to parse image: {str(e)}")

def parse_file(file_path,s3_file_name):
    """Main parsing function that determines file type and calls appropriate parser"""
    chunks = []
    try:
        mime_type = str(magic.from_file(file_path, mime=True))
        s3_file_name = s3_file_name
        
        if mime_type == 'application/pdf':
            chunks = parse_pdf(file_path, s3_file_name)
        elif isinstance(mime_type, str) and mime_type.startswith('audio/'):
            chunks = parse_audio(file_path, s3_file_name)
        elif isinstance(mime_type, str) and mime_type.startswith('video/'):
            chunks = parse_video(file_path, s3_file_name)
        elif mime_type in ['image/jpeg', 'image/png', 'image/jpg']:
            chunks = parse_image(file_path, s3_file_name)
        else:
            raise Exception(f"Unsupported file type: {mime_type}")
            
    except Exception as e:
        print(f"Error parsing file: {str(e)}")
        mime_type = "unknown"
        
    # Ensure chunks is a list, even if empty
    if chunks is None:
        chunks = []
    
    return {"mime_type": mime_type, "chunks": chunks}
