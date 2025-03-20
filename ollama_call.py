import requests
import json

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def query_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    payload = json.dumps({
        "model": "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF",
        "prompt": prompt
    })
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(url, headers=headers, data=payload, timeout=60)
    response.raise_for_status()  # Raise an exception for bad status codes
    
    # The response might contain multiple JSON objects, so we'll parse them line by line
    json_responses = [json.loads(line) for line in response.text.strip().split('\n') if line.strip()]
    
    # Combine all responses
    full_response = ''.join(resp.get('response', '') for resp in json_responses if 'response' in resp)
    return full_response