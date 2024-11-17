import os
import base64
from langchain_core.documents import Document
from s3 import upload_file_to_s3
from imgs import describe_image_oai

def handle_text_content(node, filename, url, page):
    """Process text content from a node"""
    return Document(
        page_content=node['text'],
        metadata={
            "source": filename,
            "tokens": node['tokens'],
            "page": page,
            "url": url,
            "mimetype": "application/pdf",
        }
    )

def handle_image_content(node, filename, url, page, temp_dir="temp_uploads"):
    """Process image content from a node"""
    temp_image_path = os.path.join(temp_dir, f"{node['node_id']}.jpeg")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Process image data
        for image_dict in node['images']:
            raw_image = image_dict.get('image') or image_dict.get('data')
            if not raw_image:
                continue

            # Handle base64 data
            if isinstance(raw_image, bytes):
                image_data = raw_image
            elif isinstance(raw_image, str):
                if raw_image.startswith(('data:image/', 'iVBOR', '/9j/')):
                    if ',' in raw_image:
                        raw_image = raw_image.split(',', 1)[1]
                image_data = base64.b64decode(raw_image)
            else:
                continue

            # Save image temporarily
            with open(temp_image_path, 'wb') as f:
                f.write(image_data)

            # Get image description and upload to S3
            image_description = describe_image_oai(temp_image_path)
            s3_image_path = f"images/{node['node_id']}.jpeg"
            
            with open(temp_image_path, 'rb') as img_file:
                upload_file_to_s3(img_file, s3_image_path)
                
            return image_description, s3_image_path
                
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        raise
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
    
    return None, None

def process_mixed_variant(node, filename, url, page):
    """Process nodes containing both text and image content"""
    documents = []
    
    # Handle text content if present
    if 'text' in node['variant']:
        text_doc = handle_text_content(node, filename, url, page)
        documents.append(text_doc)
    
    # Handle image content if present
    if 'image' in node['variant']:
        try:
            image_description, s3_path = handle_image_content(node, filename, url, page)
            if image_description and s3_path:
                image_doc = Document(
                    page_content=image_description,
                    metadata={
                        "source": filename,
                        "page": page,
                        "url": url,
                        "mimetype": "image/",
                        "image_url": s3_path,
                        "original_text": node.get('text', '')
                    }
                )
                documents.append(image_doc)
        except Exception as e:
            print(f"Error processing image in mixed variant: {str(e)}")
    
    return documents
