import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

WHISPER_MODEL = "openai/whisper-large-v3"
DEEPINFRA_API_KEY = os.environ['DEEPINFRA_API_KEY']
def whisper_parse(file_path):
    audio = file_path 
    # Prepare the request
    url = f'https://api.deepinfra.com/v1/inference/{WHISPER_MODEL}'
    headers = {
        "Authorization": f"bearer {DEEPINFRA_API_KEY}"
    }
    files = {
        'audio': open(audio, 'rb'),
        'response_format': (None, 'verbose_json')
    }

    # Send the request
    response = requests.post(url, headers=headers, files=files)
    
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
