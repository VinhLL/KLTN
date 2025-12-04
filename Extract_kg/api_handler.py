# api_handler.py
import os
import time
import google.generativeai as genai
from typing import Tuple, Optional
import json
import re

API_REQUEST_COUNT = 0

def get_next_api_key() -> Tuple[str, int]:
    """Get next available Google API key."""
    for i in range(5, 9):
        key_name = f"GOOGLE_API_KEY_{i}"
        key = os.environ.get(key_name)
        if key:
            return key, i
    default_key = os.environ.get('GOOGLE_API_KEY')
    if default_key:
        return default_key, 0
    return None, 0

def call_gemini_api(prompt: str, max_retries: int = 3) -> Optional[dict]:
    """Call Gemini API with error handling and retry logic."""
    global API_REQUEST_COUNT
    
    for attempt in range(max_retries):
        try:
            time.sleep(2)  # Rate limiting
            
            api_key, key_idx = get_next_api_key()
            if not api_key:
                print("No API key available")
                return None
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            API_REQUEST_COUNT += 1
            print(f"[API Request #{API_REQUEST_COUNT}]", end=" ")
            
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                print("No JSON found in response")
                return None
                
        except Exception as e:
            print(f"API Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                print(f"Failed after {max_retries} attempts")
                return None
    
    return None