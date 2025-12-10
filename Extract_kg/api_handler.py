# api_handler.py - DeepSeek API Version with improved error handling
import os
import time
from typing import Tuple, Optional
import json
import re
from openai import OpenAI
import config

# API Configuration - lấy từ config hoặc environment
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = getattr(config, 'DEEPSEEK_MODEL', 'deepseek-chat')

API_REQUEST_COUNT = 0
API_ERROR_COUNT = 0
API_EMPTY_RESPONSE_COUNT = 0

# Initialize DeepSeek client
def get_deepseek_client():
    """Get DeepSeek API client."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY environment variable is not set")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )


def fix_json_string(json_str: str) -> str:
    """
    Attempt to fix common JSON formatting issues.
    
    Args:
        json_str: Potentially malformed JSON string
        
    Returns:
        Fixed JSON string
    """
    # Remove trailing commas before } or ]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # Remove newlines within strings that might break parsing
    json_str = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*$)', ' ', json_str)
    
    # Fix unescaped quotes within strings (heuristic)
    # This is tricky - only do basic fixes
    
    # Remove any control characters
    json_str = re.sub(r'[\x00-\x1f]+', ' ', json_str)
    
    # Fix missing commas between objects in array
    json_str = re.sub(r'\}\s*\{', '},{', json_str)
    
    return json_str


def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Extract JSON from text, with multiple fallback strategies.
    
    Args:
        text: Response text that may contain JSON
        
    Returns:
        Parsed JSON dict or None
    """
    # Strategy 1: Find complete JSON object with "relationships" key (highest priority)
    json_match = re.search(r'\{[\s\S]*"relationships"[\s\S]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            # Try to fix and parse
            fixed = fix_json_string(json_match.group())
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
    
    # Strategy 2: Find JSON array and wrap in relationships (before finding individual objects)
    # This handles cases like: [{"subject_id": ...}, {...}]
    json_array_match = re.search(r'\[[\s\S]*\]', text, re.DOTALL)
    if json_array_match:
        try:
            arr = json.loads(json_array_match.group())
            if isinstance(arr, list):
                return {"relationships": arr}
        except json.JSONDecodeError:
            fixed = fix_json_string(json_array_match.group())
            try:
                arr = json.loads(fixed)
                if isinstance(arr, list):
                    return {"relationships": arr}
            except json.JSONDecodeError:
                pass
    
    # Strategy 3: Find any JSON object (fallback)
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group())
            # If it's an object with relationships, return it
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            fixed = fix_json_string(json_match.group())
            try:
                result = json.loads(fixed)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
    
    # Strategy 4: Try to extract individual relationship objects
    rel_pattern = r'\{[^{}]*"subject_id"[^{}]*"predicate"[^{}]*"object_id"[^{}]*\}'
    matches = re.findall(rel_pattern, text, re.DOTALL)
    if matches:
        relationships = []
        for match in matches:
            try:
                rel = json.loads(fix_json_string(match))
                relationships.append(rel)
            except:
                pass
        if relationships:
            return {"relationships": relationships}
    
    return None


def call_deepseek_api(prompt: str, max_retries: int = 3, model: str = None) -> Optional[dict]:
    """
    Call DeepSeek API with improved error handling and retry logic.
    
    Args:
        prompt: The prompt to send
        max_retries: Number of retry attempts
        model: Model to use (deepseek-chat or deepseek-reasoner)
    
    Returns:
        Parsed JSON response or None
    """
    global API_REQUEST_COUNT, API_ERROR_COUNT, API_EMPTY_RESPONSE_COUNT
    
    # Sử dụng model từ config nếu không được chỉ định
    if model is None:
        model = DEEPSEEK_MODEL
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            time.sleep(1)  # Rate limiting
            
            client = get_deepseek_client()
            
            API_REQUEST_COUNT += 1
            print(f"[DeepSeek #{API_REQUEST_COUNT}] model={model}", end=" ")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý trích xuất quan hệ từ văn bản lịch sử Việt Nam. Luôn trả về kết quả dưới dạng JSON hợp lệ với format: {\"relationships\": [...]}. Nếu không tìm thấy quan hệ nào, trả về {\"relationships\": []}."},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                temperature=0.3,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content
            
            # Try to extract JSON from response
            result = extract_json_from_text(response_text)
            
            if result is not None:
                relationships = result.get('relationships', [])
                if len(relationships) == 0:
                    print("OK (no relationships found)")
                    API_EMPTY_RESPONSE_COUNT += 1
                else:
                    print(f"OK ({len(relationships)} relationships)")
                return result
            else:
                print("No valid JSON found in response")
                if attempt < max_retries - 1:
                    print(f"   Retrying... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(2)
                continue
                
        except json.JSONDecodeError as e:
            API_ERROR_COUNT += 1
            last_error = f"JSON parse error: {e}"
            print(last_error)
            if attempt < max_retries - 1:
                print(f"   Retrying with JSON fix... (attempt {attempt + 2}/{max_retries})")
                time.sleep(2)
                
        except Exception as e:
            API_ERROR_COUNT += 1
            last_error = str(e)
            print(f"API Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                print(f"   [!] Failed after {max_retries} attempts: {last_error}")
    
    return {"relationships": []}  # Return empty instead of None to continue processing


# Backward compatibility - alias for old function name
def call_gemini_api(prompt: str, max_retries: int = 3) -> Optional[dict]:
    """Backward compatibility wrapper - calls DeepSeek instead of Gemini."""
    return call_deepseek_api(prompt, max_retries)


def get_api_request_count() -> int:
    """Get total API request count."""
    return API_REQUEST_COUNT


def get_api_error_count() -> int:
    """Get total API error count."""
    return API_ERROR_COUNT


def get_api_empty_response_count() -> int:
    """Get count of responses with no relationships."""
    return API_EMPTY_RESPONSE_COUNT


def reset_api_request_count():
    """Reset API request counter."""
    global API_REQUEST_COUNT, API_ERROR_COUNT, API_EMPTY_RESPONSE_COUNT
    API_REQUEST_COUNT = 0
    API_ERROR_COUNT = 0
    API_EMPTY_RESPONSE_COUNT = 0


def get_api_statistics() -> dict:
    """Get API call statistics."""
    return {
        "total_requests": API_REQUEST_COUNT,
        "errors": API_ERROR_COUNT,
        "empty_responses": API_EMPTY_RESPONSE_COUNT,
        "success_rate": (API_REQUEST_COUNT - API_ERROR_COUNT) / max(1, API_REQUEST_COUNT) * 100
    }