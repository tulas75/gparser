from groq import Groq
import base64
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def describe_image(file_path):
    # Path to your image
    image_path = file_path 

    # Getting the base64 string
    base64_image = encode_image(image_path)

    client = Groq(api_key=os.environ['GROQ_API_KEY'])

    chat_completion = client.chat.completions.create(
        messages=[
           {
               "role": "user",
               "content": [
                   {"type": "text", "text": "What's in this image?"},
                   {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                   },
               ],
           }
        ],
         model="llama-3.2-11b-vision-preview",
    )
    return chat_completion.choices[0].message.content
