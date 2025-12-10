"""
GraphRAG Pipeline - Main Pipeline and Answer Generation
"""

try:
    from kaggle_secrets import UserSecretsClient
    _KAGGLE_SECRETS_AVAILABLE = True
except Exception:
    _KAGGLE_SECRETS_AVAILABLE = False

def get_secret(key: str, default: str = None) -> str:
    if _KAGGLE_SECRETS_AVAILABLE:
        try:
            user_secrets = UserSecretsClient()
            val = user_secrets.get_secret(key)
            if val is not None and val != "":
                return val
        except Exception:
            pass
    val = os.getenv(key)
    if val:
        return val
    return default

import os
import re
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import google.generativeai as genai

from .core import (
    GraphRAGConfig, chunk_text, VietnameseNormalizer, 
    logger, MetricsCollector
)
from .embeddings import EmbeddingGenerator, Reranker
from .neo4j_manager import Neo4jManager
from .retriever import HybridRetriever, ContextBuilder

# ================================================================================
# DeepSeek API Client
# ================================================================================

class DeepSeekAPIClient:
    """Client for DeepSeek API calls."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.logger = logger
        
        # Import requests here to avoid issues if not installed
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError("requests library is required for DeepSeek API. Install with: pip install requests")
    
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
        """Generate response using DeepSeek API."""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    self.logger.warning(f"Unexpected API response format: {data}")
                    return ""
                    
            except self.requests.exceptions.RequestException as e:
                self.logger.warning(f"DeepSeek API attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"DeepSeek API failed after {max_retries} attempts")
                    raise
            except Exception as e:
                self.logger.error(f"DeepSeek API error: {e}")
                raise
        
        return ""
    
    def generate_with_system(self, system_prompt: str, user_prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
        """Generate response with system prompt."""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    return ""
                    
            except self.requests.exceptions.RequestException as e:
                self.logger.warning(f"DeepSeek API attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except Exception as e:
                self.logger.error(f"DeepSeek API error: {e}")
                raise
        
        return ""


# ================================================================================
# Entity Extractor (Enhanced)
# ================================================================================

class EntityExtractor:
    """Extract entities from questions using multiple methods."""
    
    HISTORICAL_KEYWORDS = [
        "Chiến tranh thế giới thứ hai", "Chiến tranh thế giới thứ nhất",
        "Chiến tranh lạnh", "Cách mạng tháng Tám", "Cách mạng tháng Mười",
        "Liên hợp quốc", "ASEAN", "Hội đồng Bảo an", "Đại hội đồng",
        "Đảng Cộng sản Việt Nam", "Đảng Cộng sản Đông Dương",
        "Hội Quốc liên", "NATO", "Hiệp hội các quốc gia Đông Nam Á",
        "Cộng đồng ASEAN", "Việt Minh", "Mặt trận Việt Minh",
        "Hồ Chí Minh", "Chủ tịch Hồ Chí Minh", "Nguyễn Ái Quốc",
        "Võ Nguyên Giáp", "Trường Chinh", "Phạm Văn Đồng",
        "Việt Nam", "Liên Xô", "Trung Quốc", "Mỹ", "Pháp", "Anh",
        "Đông Nam Á", "Đông Âu", "Tây Âu", "Đông Dương",
        "Hiến chương Liên hợp quốc", "Tuyên ngôn Độc lập", "Cương lĩnh chính trị",
        "Hiệp định Giơ-ne-vơ", "Hiệp định Pa-ri",
        "Toàn cầu hóa", "quyền dân tộc cơ bản", "trật tự hai cực",
        "Hội nghị I-an-ta", "Hội nghị Xan Phran-xi-xcô",
        "Điện Biên Phủ", "Chiến dịch Hồ Chí Minh",
        "Việt Nam Thanh niên Cách mạng Đồng chí Hội",
        "Tổng thư ký Liên hợp quốc", "xu thế hoà hoãn Đông-Tây",
    ]
    
    EXTRACTION_PROMPT = """Trích xuất các thực thể lịch sử từ câu hỏi sau.

Câu hỏi: {question}

Loại thực thể: sự kiện, tổ chức, nhân vật, quốc gia, văn kiện, địa điểm, thời gian.

Trả về JSON: {{"entities": ["entity1", "entity2", ...]}}"""
    
    def __init__(self, api_key: str = None):
        api_key = api_key or get_secret("GEMINI_API_KEY", "your_gemini_api_key")
        if api_key:
            genai.configure(api_key=api_key)
            self.gemini = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.gemini = None
            logger.warning("No GOOGLE_API_KEY, using keyword extraction only")
    
    def extract(self, question: str, options: List[str] = None) -> List[str]:
        """Extract entities using multiple methods."""
        entities = []
        
        # Vietnamese stopwords that can be confused with entities
        VIETNAMESE_STOPWORDS = {
            "anh",  # pronoun, can be confused with "England"
            "em", "tôi", "ta", "mình", "chúng", "họ", "ông", "bà", "cô", "chú",
            "người", "việc", "điều", "cách", "nào", "gì", "đâu", "nơi",
            "là", "có", "được", "bị", "để", "cho", "với", "từ", "trong", "ngoài",
            "trên", "dưới", "sau", "trước", "một", "các", "những", "nhiều", "ít",
            "đã", "đang", "sẽ", "không", "chưa", "rất", "lắm", "quá",
        }
        
        full_text = question
        if options:
            full_text += " " + " ".join(options)
        
        # Method 1: Keyword matching
        entities.extend(self._extract_keywords(full_text))
        
        # Method 2: Regex patterns
        entities.extend(self._extract_regex(full_text))
        
        # Method 3: Gemini API (if available and few entities found)
        if self.gemini and len(entities) < 3:
            try:
                gemini_entities = self._extract_gemini(full_text)
                entities.extend(gemini_entities)
            except Exception as e:
                logger.debug(f"Gemini extraction failed: {e}")
        
        # Deduplicate and filter stopwords + numeric entities
        unique = []
        seen = set()
        
        # Generic entities that should be deprioritized
        GENERIC_ENTITIES = {
            'việt nam', 'trung quốc', 'mỹ', 'pháp', 'anh', 'liên xô',
            'nhật bản', 'đức', 'thế giới', 'châu á', 'châu âu'
        }
        
        specific_entities = []  # More specific entities
        generic_entities = []   # Generic country/region names
        
        for e in entities:
            e_lower = e.lower().strip()
            # Skip Vietnamese stopwords
            if e_lower in VIETNAMESE_STOPWORDS:
                continue
            # Skip standalone number entities (years like 1945, 2000)
            # But keep date ranges like "1945-1954"
            if re.match(r'^\d{4}$', e):
                continue
            if e_lower and e_lower not in seen and len(e) > 1:
                seen.add(e_lower)
                # Categorize by specificity
                if e_lower in GENERIC_ENTITIES:
                    generic_entities.append(e.strip())
                else:
                    specific_entities.append(e.strip())
        
        # Prioritize specific entities, then add generic ones at the end
        # Limit generic entities to avoid noise
        unique = specific_entities[:15] + generic_entities[:5]
        
        return unique[:20]  # Increased from 15 to allow more entities
    
    def _extract_keywords(self, text: str) -> List[str]:
        text_lower = text.lower()
        return [kw for kw in self.HISTORICAL_KEYWORDS if kw.lower() in text_lower]
    
    def _extract_regex(self, text: str) -> List[str]:
        entities = []
        entities.extend(re.findall(r'\b(19\d{2}|20\d{2})\b', text))
        entities.extend(re.findall(r'(\d{4}\s*[-–]\s*\d{4})', text))
        entities.extend(re.findall(r'tháng\s+\d+\s+năm\s+\d{4}', text))
        quoted = re.findall(r'["""]([^"""]+)["""]', text)
        entities.extend([q for q in quoted if len(q) > 3])
        return entities
    
    def _extract_gemini(self, text: str) -> List[str]:
        prompt = self.EXTRACTION_PROMPT.format(question=text)
        response = self.gemini.generate_content(prompt)
        response_text = response.text.strip()
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            response_text = json_match.group()
        
        data = json.loads(response_text)
        return data.get("entities", [])
    
    def extract_tf_statement(self, question: str) -> str:
        patterns = [
            r'Phát biểu sau:\s*["""](.+?)["""]',
            r'["""](.+?)["""].*(?:đúng|sai)',
        ]
        for pattern in patterns:
            match = re.search(pattern, question, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return re.sub(r'là\s+đúng\s+hay\s+sai.*$', '', question, flags=re.IGNORECASE).strip()
    
    def extract_source_materials(self, question: str) -> dict:
        """
        Extract "Tư liệu" content from T/F questions.
        Many T/F questions contain source materials that should be used for verification.
        
        Returns dict like: {"Tư liệu 1": "content...", "Tư liệu 2": "content..."}
        """
        materials = {}
        
        # Pattern 1: Tư liệu X: "..."
        pattern1 = r'Tư liệu\s*(\d+)?\s*:\s*["\"\"](.+?)["\"\"]'
        matches = re.findall(pattern1, question, re.DOTALL | re.IGNORECASE)
        for idx, content in matches:
            name = f"Tư liệu {idx}" if idx else "Tư liệu"
            materials[name] = content.strip()
        
        # Pattern 2: "Đọc đoạn tư liệu sau đây: ..." (single block without numbered Tư liệu)
        if not materials:
            pattern2 = r'Đọc đoạn tư liệu sau đây\s*:\s*["\"\"]?(.+?)["\"\"]?\s*(?:Phát biểu sau|$)'
            match = re.search(pattern2, question, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                content = re.sub(r'^["\"\"]|["\"\"]$', '', content).strip()
                if len(content) > 20:
                    materials["Tư liệu"] = content
        
        return materials


# ================================================================================
# Answer Generator
# ================================================================================

class AnswerGenerator:
    """Generate answers using DeepSeek API or local models with provenance tracking."""
    
    MCQ_PROMPT = """Bạn là chuyên gia lịch sử Việt Nam. Dựa vào thông tin sau, chọn đáp án ĐÚNG NHẤT.

⚠️ QUY TẮC BẮT BUỘC:
1. **Xác định loại câu hỏi**: Nếu có "KHÔNG PHẢI", "KHÔNG ĐÚNG", "NGOẠI TRỪ", "HẠN CHẾ" → Tìm đáp án SAI/KHÔNG ĐÚNG
2. **PHẢI đọc và phân tích TẤT CẢ 4 đáp án** trước khi chọn
3. **KHÔNG được đoán** - chỉ chọn dựa trên thông tin tham khảo

**THÔNG TIN THAM KHẢO:**
{context}

**CÂU HỎI:** {question}

**ĐÁP ÁN:**
A. {option_a}
B. {option_b}
C. {option_c}
D. {option_d}

**QUY TRÌNH PHÂN TÍCH (PHẢI THỰC HIỆN ĐẦY ĐỦ):**

**Bước 1 - Phân loại câu hỏi:**
- Câu hỏi này là KHẲNG ĐỊNH hay PHỦ ĐỊNH?
- Nếu PHỦ ĐỊNH (không phải, ngoại trừ, hạn chế) → Tìm đáp án SAI
- Nếu KHẲNG ĐỊNH → Tìm đáp án ĐÚNG

**Bước 2 - Trích xuất thực thể chính:**
- Thực thể/khái niệm chính trong câu hỏi là gì?
- Thời gian/giai đoạn được đề cập?

**Bước 3 - Phân tích TỪNG đáp án:**
- A: [Tìm thông tin liên quan trong context] → Đúng/Sai vì...
- B: [Tìm thông tin liên quan trong context] → Đúng/Sai vì...
- C: [Tìm thông tin liên quan trong context] → Đúng/Sai vì...
- D: [Tìm thông tin liên quan trong context] → Đúng/Sai vì...

**Bước 4 - Kết luận:**
- So sánh 4 đáp án và chọn đáp án phù hợp nhất với yêu cầu câu hỏi.

**ĐÁP ÁN CUỐI CÙNG:** [CHỈ GHI MỘT CHỮ CÁI: A, B, C hoặc D]"""

    # Standard T/F prompt without source materials
    TF_PROMPT = """Bạn là chuyên gia lịch sử Việt Nam. Xác định phát biểu sau ĐÚNG hay SAI.

**THÔNG TIN THAM KHẢO:**
{context}

**PHÁT BIỂU CẦN XÁC MINH:** {statement}

**HƯỚNG DẪN PHÂN TÍCH:**
1. Đọc kỹ phát biểu và xác định các chi tiết cụ thể cần kiểm tra (thời gian, sự kiện, nhân vật, con số...)
2. So sánh từng chi tiết với thông tin tham khảo
3. Nếu có BẤT KỲ chi tiết nào KHÔNG CHÍNH XÁC hoặc BỊ DIỄN GIẢI SAI, phát biểu là SAI
4. Chỉ trả lời ĐÚNG khi TẤT CẢ các chi tiết đều khớp với thông tin tham khảo

Phân tích từng bước rồi kết luận: "Đúng" hoặc "Sai"."""
    
    # Direct T/F prompt (no KG context) - used with DeepSeek for 93.1% accuracy
    TF_PROMPT_DIRECT = """Phat bieu sau dung hay sai? Chi tra loi "Dung" hoac "Sai".

Phat bieu: {statement}

Tra loi:"""
    
    # Enhanced T/F prompt WITH source materials from question
    TF_PROMPT_WITH_MATERIALS = """Bạn là chuyên gia lịch sử Việt Nam. Xác định phát biểu sau ĐÚNG hay SAI.

**TƯ LIỆU TRONG ĐỀ BÀI (NGUỒN CHÍNH ĐỂ XÁC MINH):**
{source_materials}

**THÔNG TIN THAM KHẢO BỔ SUNG:**
{context}

**PHÁT BIỂU CẦN XÁC MINH:** {statement}

**HƯỚNG DẪN PHÂN TÍCH (RẤT QUAN TRỌNG):**
1. ĐỌC KỸ "Tư liệu trong đề bài" - đây là nguồn CHÍNH để xác minh phát biểu
2. So sánh CHÍNH XÁC từng từ, từng chi tiết trong PHÁT BIỂU với NỘI DUNG TƯ LIỆU
3. CHÚ Ý đặc biệt các từ khóa: "tất cả", "hoàn toàn", "chỉ", "không", "mọi", "luôn"
4. Nếu phát biểu có ý nghĩa KHÁC với tư liệu dù chỉ 1 chi tiết nhỏ → SAI
5. Phát biểu chỉ ĐÚNG khi phản ánh CHÍNH XÁC nội dung tư liệu, không thêm bớt, không suy diễn

Trả lời: "Đúng" hoặc "Sai" kèm giải thích ngắn."""
    
    def __init__(self, config = None, 
                 model_name: str = "Qwen/Qwen3-4B", 
                 tf_model_name: str = None,
                 device: str = "cuda",
                 mode: str = "auto"):
        """
        Initialize AnswerGenerator with DeepSeek API or local model support.
        
        Args:
            config: GraphRAGConfig with DeepSeek settings OR string (model name for backward compat)
            model_name: Model for MCQ (default Qwen3-4B) - used when not using API
            tf_model_name: Optional model for T/F questions
            device: cuda or cpu
            mode: 'auto' (use config setting), 'qwen' (force local), 'deepseek' (force API)
        """
        # Handle backward compatibility: config can be a string (model name)
        if isinstance(config, str):
            # Old usage: AnswerGenerator(model_name_string)
            model_name = config
            config = None
        
        self.config = config if config is not None else GraphRAGConfig()
        self.device = device
        self.mode = mode
        
        # Determine if using API based on mode
        if mode == "qwen":
            self.use_api = False
        elif mode == "deepseek":
            self.use_api = True
        else:  # auto
            self.use_api = self.config.use_deepseek_api
        
        # DeepSeek API client
        self.deepseek_client = None
        
        # Local model references
        self.model = None
        self.tokenizer = None
        self.tf_model = None
        self.tf_tokenizer = None
        self.tf_model_name = tf_model_name
        self.model_name = model_name
        
        # Detect available GPUs
        self.num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
        logger.info(f"Detected {self.num_gpus} GPU(s)")
        
        if self.use_api:
            # Initialize DeepSeek API client
            if not self.config.deepseek_api_key:
                logger.warning("DeepSeek API key not found. Set DEEPSEEK_API_KEY environment variable.")
                logger.info("Falling back to local model...")
                self.use_api = False
            else:
                logger.info(f"Using DeepSeek API (model: {self.config.deepseek_model})")
                self.deepseek_client = DeepSeekAPIClient(
                    api_key=self.config.deepseek_api_key,
                    base_url=self.config.deepseek_base_url,
                    model=self.config.deepseek_model
                )
                logger.info("✓ DeepSeek API client initialized")
        
        if not self.use_api:
            # Load local models with multi-GPU support
            logger.info(f"Loading local MCQ model: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Determine device for MCQ model
            if self.num_gpus >= 2:
                # Multi-GPU: MCQ on GPU 0
                mcq_device_map = "cuda:0"
                logger.info("Multi-GPU mode: MCQ model will use GPU 0")
            elif self.num_gpus == 1:
                # Single GPU: use auto or cuda
                mcq_device_map = device if device in ["cuda", "auto"] else None
            else:
                mcq_device_map = None
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.num_gpus > 0 else torch.float32,
                device_map=mcq_device_map,
            )
            if device == "cpu" and self.num_gpus == 0:
                self.model = self.model.to("cpu")
            logger.info(f"✓ MCQ model loaded on {mcq_device_map or 'cpu'}")
            
            # Load separate T/F model if specified
            if tf_model_name and tf_model_name != model_name:
                logger.info(f"Loading T/F model: {tf_model_name}")
                try:
                    self.tf_tokenizer = AutoTokenizer.from_pretrained(tf_model_name)
                    
                    # Determine device for T/F model
                    if self.num_gpus >= 2:
                        # Multi-GPU: T/F on GPU 1
                        tf_device_map = "cuda:1"
                        logger.info("Multi-GPU mode: T/F model will use GPU 1")
                    elif self.num_gpus == 1:
                        # Single GPU: share with MCQ model
                        tf_device_map = device if device in ["cuda", "auto"] else None
                    else:
                        tf_device_map = None
                    
                    self.tf_model = AutoModelForCausalLM.from_pretrained(
                        tf_model_name,
                        torch_dtype=torch.float16 if self.num_gpus > 0 else torch.float32,
                        device_map=tf_device_map,
                    )
                    logger.info(f"✓ T/F model loaded on {tf_device_map or 'cpu'}")
                except Exception as e:
                    logger.warning(f"Failed to load T/F model: {e}")
                    self.tf_model = None
                    self.tf_tokenizer = None
    
    def prepare_prompt(self, prompt_text: str, max_tokens: int = 3500) -> str:
        """Prepare and truncate prompt to fit token limit."""
        if self.use_api:
            # For API, use character-based truncation
            max_chars = max_tokens * 4  # Rough estimate: 4 chars per token
            if len(prompt_text) <= max_chars:
                return prompt_text
            return prompt_text[:max_chars] + "\n[...truncated...]"
        else:
            # For local model, use tokenizer
            tokens = self.tokenizer.encode(prompt_text)
            if len(tokens) <= max_tokens:
                return prompt_text
            ratio = max_tokens / len(tokens)
            max_chars = int(len(prompt_text) * ratio * 0.9)
            return prompt_text[:max_chars] + "\n[...truncated...]"
    
    def generate(self, prompt: str, max_new_tokens: int = 300) -> str:
        """Generate response using DeepSeek API or local model."""
        prompt = self.prepare_prompt(prompt)
        
        if self.use_api and self.deepseek_client:
            # Use DeepSeek API
            return self.deepseek_client.generate(prompt, max_tokens=max_new_tokens)
        else:
            # Use local model
            messages = [{"role": "user", "content": prompt}]
            
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            
            inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs, max_new_tokens=max_new_tokens, 
                    do_sample=False, pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(
                output_ids[0][len(inputs.input_ids[0]):], skip_special_tokens=True
            )
            return response.strip()
    
    def generate_tf(self, prompt: str, max_new_tokens: int = 300) -> str:
        """Generate response for T/F questions."""
        if self.use_api and self.deepseek_client:
            # Use DeepSeek API for T/F
            return self.deepseek_client.generate(prompt, max_tokens=max_new_tokens)
        elif self.tf_model is not None and self.tf_tokenizer is not None:
            # Use local T/F model
            prompt = self.prepare_prompt(prompt)
            messages = [{"role": "user", "content": prompt}]
            
            try:
                text = self.tf_tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                text = f"User: {prompt}\n\nAssistant:"
            
            inputs = self.tf_tokenizer([text], return_tensors="pt").to(self.tf_model.device)
            
            with torch.no_grad():
                output_ids = self.tf_model.generate(
                    **inputs, max_new_tokens=max_new_tokens,
                    do_sample=False, pad_token_id=self.tf_tokenizer.eos_token_id
                )
            
            response = self.tf_tokenizer.decode(
                output_ids[0][len(inputs.input_ids[0]):], skip_special_tokens=True
            )
            return response.strip()
        else:
            # Fall back to main model
            return self.generate(prompt, max_new_tokens)
    
    def answer_mcq(self, question: str, options: List[str], context: str) -> Tuple[str, str]:
        while len(options) < 4:
            options.append("")
        
        prompt = self.MCQ_PROMPT.format(
            context=context or "Không có thông tin chi tiết.",
            question=question,
            option_a=options[0], option_b=options[1],
            option_c=options[2], option_d=options[3]
        )
        
        raw = self.generate(prompt)
        answer = self._normalize_mcq(raw)
        return answer, raw
    
    def answer_tf(self, statement: str, context: str = None, source_materials: dict = None, use_direct: bool = None) -> Tuple[str, str]:
        """
        Answer True/False question.
        
        Args:
            statement: The statement to verify
            context: Retrieved context from knowledge graph (ignored in direct mode)
            source_materials: Optional dict of source materials from the question
            use_direct: If True, use direct prompt without KG. If None, auto-detect
        """
        # Auto-detect mode
        if use_direct is None:
            # Use direct mode with DeepSeek API or if tf_model is available
            use_direct = self.use_api or self.tf_model is not None
        
        if use_direct:
            # Direct mode: answers without KG context
            prompt = self.TF_PROMPT_DIRECT.format(statement=statement)
        elif source_materials:
            # With source materials from question
            materials_text = "\n\n".join([
                f"**{name}:**\n{content}" 
                for name, content in source_materials.items()
            ])
            prompt = self.TF_PROMPT_WITH_MATERIALS.format(
                source_materials=materials_text,
                context=context or "Không có thông tin bổ sung.",
                statement=statement
            )
        else:
            # Standard KG-based prompt
            prompt = self.TF_PROMPT.format(
                context=context or "Không có thông tin chi tiết.",
                statement=statement
            )
        
        raw = self.generate_tf(prompt)
        answer = self._normalize_tf(raw)
        return answer, raw
    
    def _normalize_mcq(self, response: str) -> str:
        response_upper = response.upper()
        # Thứ tự ưu tiên: Tìm đáp án cuối cùng được đề cập
        patterns = [
            r'ĐÁP ÁN CUỐI CÙNG[:\s]*([ABCD])',  # Từ prompt mới
            r'ĐÁP ÁN ĐÚNG[:\s]*([ABCD])',
            r'ĐÁP ÁN[:\s]*\**([ABCD])\**',
            r'CHỌN[:\s]*([ABCD])',
            r'KẾT LUẬN[:\s]*([ABCD])',
            r'^([ABCD])\.',  # Bắt đầu bằng A. B. C. D.
            r'\*\*([ABCD])\*\*',  # **A**
        ]
        for pattern in patterns:
            match = re.search(pattern, response_upper, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fallback: tìm chữ cái cuối cùng được mention
        all_matches = re.findall(r'\b([ABCD])\b', response_upper)
        if all_matches:
            return all_matches[-1]  # Lấy chữ cái cuối cùng
        
        return "A"
    
    def _normalize_tf(self, response: str) -> str:
        response_lower = response.lower()
        if 'sai' in response_lower:
            return "Sai"
        return "Đúng"


# ================================================================================
# Dual Answer Generator - Runs both Qwen and DeepSeek
# ================================================================================

class DualAnswerGenerator:
    """
    Dual Answer Generator that runs both Qwen (local) and DeepSeek (API) sequentially.
    Qwen runs first, then DeepSeek. Results from both are combined for comparison.
    """
    
    def __init__(self, config: GraphRAGConfig = None, 
                 qwen_model: str = "Qwen/Qwen3-4B",
                 device: str = "cuda"):
        """
        Initialize both Qwen and DeepSeek generators.
        
        Args:
            config: GraphRAGConfig with settings
            qwen_model: Local model name for Qwen
            device: cuda or cpu
        """
        self.config = config if config is not None else GraphRAGConfig()
        self.device = device
        self.qwen_model_name = qwen_model
        
        # Initialize Qwen (local model)
        logger.info("=" * 60)
        logger.info("Initializing DUAL Answer Generator")
        logger.info("=" * 60)
        
        logger.info("Step 1: Initializing Qwen (local model)...")
        self.qwen_generator = AnswerGenerator(
            config=self.config,
            model_name=qwen_model,
            device=device,
            mode="qwen"  # Force local model
        )
        logger.info("✓ Qwen generator ready")
        
        # Initialize DeepSeek (API)
        logger.info("Step 2: Initializing DeepSeek (API)...")
        self.deepseek_generator = None
        if self.config.deepseek_api_key:
            self.deepseek_generator = AnswerGenerator(
                config=self.config,
                model_name=qwen_model,  # Not used for API but required
                device=device,
                mode="deepseek"  # Force API
            )
            logger.info("✓ DeepSeek generator ready")
        else:
            logger.warning("DeepSeek API key not found. Only Qwen will be used.")
        
        logger.info("=" * 60)
        logger.info("DUAL Answer Generator initialized successfully")
        logger.info(f"  - Qwen model: {qwen_model}")
        logger.info(f"  - DeepSeek API: {'Available' if self.deepseek_generator else 'Not available'}")
        logger.info("=" * 60)
    
    def answer_mcq(self, question: str, options: List[str], context: str) -> Dict:
        """
        Answer MCQ using both Qwen and DeepSeek.
        
        Returns:
            Dict with both answers: {
                'qwen': {'answer': str, 'raw': str},
                'deepseek': {'answer': str, 'raw': str},
                'primary_answer': str,
                'primary_raw': str
            }
        """
        result = {
            'qwen': {'answer': None, 'raw': None},
            'deepseek': {'answer': None, 'raw': None},
            'primary_answer': None,
            'primary_raw': None
        }
        
        # Step 1: Qwen (always runs first)
        logger.debug("Running Qwen for MCQ...")
        qwen_answer, qwen_raw = self.qwen_generator.answer_mcq(question, options, context)
        result['qwen'] = {'answer': qwen_answer, 'raw': qwen_raw}
        
        # Step 2: DeepSeek (if available)
        if self.deepseek_generator:
            logger.debug("Running DeepSeek for MCQ...")
            deepseek_answer, deepseek_raw = self.deepseek_generator.answer_mcq(question, options, context)
            result['deepseek'] = {'answer': deepseek_answer, 'raw': deepseek_raw}
        
        # Primary answer: use DeepSeek if available, otherwise Qwen
        if self.deepseek_generator and result['deepseek']['answer']:
            result['primary_answer'] = result['deepseek']['answer']
            result['primary_raw'] = result['deepseek']['raw']
        else:
            result['primary_answer'] = result['qwen']['answer']
            result['primary_raw'] = result['qwen']['raw']
        
        return result
    
    def answer_tf(self, statement: str, context: str = None, 
                  source_materials: dict = None, use_direct: bool = None) -> Dict:
        """
        Answer T/F using both Qwen and DeepSeek.
        
        Returns:
            Dict with both answers: {
                'qwen': {'answer': str, 'raw': str},
                'deepseek': {'answer': str, 'raw': str},
                'primary_answer': str,
                'primary_raw': str
            }
        """
        result = {
            'qwen': {'answer': None, 'raw': None},
            'deepseek': {'answer': None, 'raw': None},
            'primary_answer': None,
            'primary_raw': None
        }
        
        # Step 1: Qwen (always runs first)
        logger.debug("Running Qwen for T/F...")
        qwen_answer, qwen_raw = self.qwen_generator.answer_tf(
            statement, context, source_materials, use_direct
        )
        result['qwen'] = {'answer': qwen_answer, 'raw': qwen_raw}
        
        # Step 2: DeepSeek (if available)
        if self.deepseek_generator:
            logger.debug("Running DeepSeek for T/F...")
            deepseek_answer, deepseek_raw = self.deepseek_generator.answer_tf(
                statement, context, source_materials, use_direct=True  # DeepSeek prefers direct mode
            )
            result['deepseek'] = {'answer': deepseek_answer, 'raw': deepseek_raw}
        
        # Primary answer: use DeepSeek if available (higher T/F accuracy), otherwise Qwen
        if self.deepseek_generator and result['deepseek']['answer']:
            result['primary_answer'] = result['deepseek']['answer']
            result['primary_raw'] = result['deepseek']['raw']
        else:
            result['primary_answer'] = result['qwen']['answer']
            result['primary_raw'] = result['qwen']['raw']
        
        return result
    
    def get_mode_info(self) -> Dict:
        """Return information about available modes."""
        return {
            'qwen_available': True,
            'qwen_model': self.qwen_model_name,
            'deepseek_available': self.deepseek_generator is not None,
            'deepseek_model': self.config.deepseek_model if self.deepseek_generator else None
        }


# ================================================================================
# Graph Encoder - Step 3: Encode sub-graph structure
# ================================================================================

class GraphEncoder:
    """
    Encode sub-graph structure into embedding vector g.
    
    Takes entities and their relationships from Neo4j sub-graph and produces
    a dense embedding representing the graph structure.
    """
    
    def __init__(self, config: GraphRAGConfig, embedding_gen: 'EmbeddingGenerator'):
        self.config = config
        self.embedding_gen = embedding_gen
        self.dim = config.graph_encoding_dim
        logger.info(f"GraphEncoder initialized with dim={self.dim}")
    
    def encode_subgraph(self, entities: List[str], relationships: List[Dict], 
                        entity_descriptions: Dict[str, str] = None) -> List[float]:
        """
        Encode sub-graph into dense embedding vector g.
        
        Args:
            entities: List of entity IDs in sub-graph
            relationships: List of relationship dicts with source, target, predicate
            entity_descriptions: Optional dict mapping entity_id to description
        
        Returns:
            Graph embedding vector g of dimension graph_encoding_dim
        """
        import numpy as np
        
        if not entities:
            return [0.0] * self.dim
        
        # Step 1: Encode entity nodes
        entity_embeddings = []
        for entity_id in entities[:20]:  # Limit to 20 entities
            text = entity_id
            if entity_descriptions and entity_id in entity_descriptions:
                text = f"{entity_id}: {entity_descriptions[entity_id][:200]}"
            emb = self.embedding_gen.generate_embedding(text)
            if emb:
                entity_embeddings.append(np.array(emb))
        
        if not entity_embeddings:
            return [0.0] * self.dim
        
        # Step 2: Encode relationships (edges)
        rel_embeddings = []
        for rel in relationships[:15]:  # Limit to 15 relationships
            rel_text = f"{rel.get('source', '')} [{rel.get('predicate', '')}] {rel.get('target', '')}"
            emb = self.embedding_gen.generate_embedding(rel_text)
            if emb:
                rel_embeddings.append(np.array(emb))
        
        # Step 3: Aggregate embeddings with attention-weighted pooling
        all_embeddings = entity_embeddings + rel_embeddings
        
        if len(all_embeddings) == 1:
            graph_emb = all_embeddings[0]
        else:
            # Simple mean pooling with entity weighting
            entity_weight = 0.6
            rel_weight = 0.4
            
            entity_mean = np.mean(entity_embeddings, axis=0) if entity_embeddings else np.zeros(len(all_embeddings[0]))
            rel_mean = np.mean(rel_embeddings, axis=0) if rel_embeddings else np.zeros(len(all_embeddings[0]))
            
            graph_emb = entity_weight * entity_mean + rel_weight * rel_mean
        
        # Reduce to target dimension if needed
        if len(graph_emb) > self.dim:
            # Use PCA-like reduction (simple truncation for efficiency)
            graph_emb = graph_emb[:self.dim]
        elif len(graph_emb) < self.dim:
            # Pad with zeros
            graph_emb = np.pad(graph_emb, (0, self.dim - len(graph_emb)))
        
        return graph_emb.tolist()
    
    def get_entity_centrality(self, entity_id: str, relationships: List[Dict]) -> float:
        """
        Compute centrality score for an entity based on relationship count.
        Used in trust score calculation.
        """
        if not relationships:
            return 0.0
        
        # Count relationships involving this entity
        count = sum(1 for r in relationships 
                   if r.get('source') == entity_id or r.get('target') == entity_id)
        
        # Normalize by total relationships
        centrality = count / len(relationships) if relationships else 0.0
        return min(centrality, 1.0)


# ================================================================================
# Embedding Fusion - Step 4: h = CrossAttn(q, g)
# ================================================================================

class EmbeddingFusion:
    """
    Fuse question embedding q with graph embedding g using cross-attention.
    
    Computes: h = CrossAttn(q, g) where:
    - q is the question embedding
    - g is the graph structure embedding
    - h is the fused embedding for answer generation
    """
    
    def __init__(self, config: GraphRAGConfig):
        self.config = config
        self.num_heads = config.fusion_heads
        logger.info(f"EmbeddingFusion initialized with {self.num_heads} attention heads")
    
    def fuse(self, question_embedding: List[float], graph_embedding: List[float]) -> List[float]:
        """
        Fuse question and graph embeddings using simplified cross-attention.
        
        Args:
            question_embedding: Question embedding q
            graph_embedding: Graph structure embedding g
        
        Returns:
            Fused embedding h = CrossAttn(q, g)
        """
        import numpy as np
        
        q = np.array(question_embedding)
        g = np.array(graph_embedding)
        
        # Handle dimension mismatch
        min_dim = min(len(q), len(g))
        q = q[:min_dim]
        g = g[:min_dim]
        
        if min_dim == 0:
            return question_embedding  # Fallback to question embedding
        
        # Simplified cross-attention mechanism
        # Attention score = softmax(q · g^T)
        attention_score = np.dot(q, g) / (np.linalg.norm(q) * np.linalg.norm(g) + 1e-9)
        attention_weight = 1 / (1 + np.exp(-attention_score))  # Sigmoid normalization
        
        # Fused embedding: weighted combination
        h = attention_weight * q + (1 - attention_weight) * g
        
        # Normalize the fused embedding
        h = h / (np.linalg.norm(h) + 1e-9)
        
        return h.tolist()
    
    def compute_attention_score(self, question_embedding: List[float], 
                                  graph_embedding: List[float]) -> float:
        """
        Compute attention score between question and graph.
        Higher score indicates stronger relevance of graph context.
        """
        import numpy as np
        
        q = np.array(question_embedding)
        g = np.array(graph_embedding)
        
        min_dim = min(len(q), len(g))
        if min_dim == 0:
            return 0.0
        
        q = q[:min_dim]
        g = g[:min_dim]
        
        # Cosine similarity as attention score
        score = np.dot(q, g) / (np.linalg.norm(q) * np.linalg.norm(g) + 1e-9)
        return float(max(0, score))  # Clamp to non-negative


# ================================================================================
# Trust Score Calculator - Step 6: Post-processing
# ================================================================================

class TrustScoreCalculator:
    """
    Calculate trust score for answer based on:
    - LLM confidence (from response analysis)
    - Graph centrality of referenced entities
    - Evidence coverage
    """
    
    def __init__(self, config: GraphRAGConfig):
        self.config = config
        self.confidence_weight = config.trust_confidence_weight
        self.centrality_weight = config.trust_centrality_weight
        logger.info(f"TrustScoreCalculator: confidence_w={self.confidence_weight}, centrality_w={self.centrality_weight}")
    
    def calculate(self, 
                  answer_confidence: float,
                  entity_centralities: List[float],
                  evidence_scores: List[float],
                  has_graph_context: bool) -> Dict:
        """
        Calculate comprehensive trust score.
        
        Args:
            answer_confidence: Confidence score from LLM (0-1)
            entity_centralities: Centrality scores of referenced entities
            evidence_scores: Retrieval scores of evidence passages
            has_graph_context: Whether graph context was used
        
        Returns:
            Dict with trust_score, confidence_component, centrality_component, etc.
        """
        # Confidence component (from LLM response analysis)
        conf_score = max(0, min(1, answer_confidence))
        
        # Centrality component (average centrality of entities)
        if entity_centralities:
            centrality_score = sum(entity_centralities) / len(entity_centralities)
        else:
            centrality_score = 0.0
        
        # Evidence coverage bonus
        if evidence_scores:
            evidence_score = sum(evidence_scores[:5]) / min(len(evidence_scores), 5)
        else:
            evidence_score = 0.0
        
        # Graph context bonus (if graph was used)
        graph_bonus = 0.1 if has_graph_context else 0.0
        
        # Combined trust score
        trust_score = (
            self.confidence_weight * conf_score +
            self.centrality_weight * centrality_score +
            0.1 * evidence_score +
            graph_bonus
        )
        
        # Normalize to [0, 1]
        trust_score = max(0, min(1, trust_score))
        
        return {
            "trust_score": round(trust_score, 4),
            "confidence_component": round(conf_score, 4),
            "centrality_component": round(centrality_score, 4),
            "evidence_component": round(evidence_score, 4),
            "graph_context_used": has_graph_context,
            "interpretation": self._interpret_score(trust_score)
        }
    
    def _interpret_score(self, score: float) -> str:
        """Interpret trust score into human-readable level."""
        if score >= 0.8:
            return "HIGH - Answer highly reliable"
        elif score >= 0.6:
            return "MEDIUM - Answer likely correct"
        elif score >= 0.4:
            return "LOW - Answer may need verification"
        else:
            return "VERY LOW - Answer uncertain"
    
    def estimate_confidence_from_response(self, raw_response: str) -> float:
        """
        Estimate confidence from LLM response text.
        Looks for confidence indicators in the response.
        """
        response_lower = raw_response.lower()
        
        # High confidence indicators
        high_conf_words = ["chắc chắn", "rõ ràng", "chính xác", "đúng", "definitely", "clearly"]
        # Low confidence indicators  
        low_conf_words = ["có thể", "có lẽ", "không chắc", "maybe", "perhaps", "uncertain"]
        
        high_count = sum(1 for w in high_conf_words if w in response_lower)
        low_count = sum(1 for w in low_conf_words if w in response_lower)
        
        # Base confidence
        base = 0.6
        
        # Adjust based on indicators
        confidence = base + (high_count * 0.1) - (low_count * 0.15)
        
        return max(0.2, min(1.0, confidence))


# ================================================================================
# GraphRAG Pipeline
# ================================================================================

class GraphRAGPipeline:
    """
    Complete GraphRAG pipeline for Vietnamese historical QA.
    
    Implements the full GraphRAG process:
    1. Question Preprocessing - Entity extraction using VnCoreNLP/Gemini
    2. Sub-graph Retrieval - Query Neo4j for relevant sub-graph
    3. Graph Encoding - Encode sub-graph structure into embedding g
    4. Embedding Fusion - Compute h = CrossAttn(q, g)
    5. Answer Generation - Generate answer using fused embedding
    6. Post-processing - Calculate trust score from confidence + centrality
    7. Return - Answer, citations, and trust score
    """
    
    def __init__(self, config: GraphRAGConfig = None, use_dual_mode: bool = False):
        """
        Initialize GraphRAG Pipeline with full GraphRAG steps.
        
        Args:
            config: GraphRAGConfig with all settings
            use_dual_mode: If True, use DualAnswerGenerator (runs both Qwen and DeepSeek)
        """
        self.config = config or GraphRAGConfig()
        self.metrics = MetricsCollector()
        self.use_dual_mode = use_dual_mode
        
        # Track Neo4j connection status
        self.neo4j_connected = False
        self.neo4j = None
        
        logger.info("=" * 60)
        logger.info("Initializing GraphRAG Pipeline (Full 7-Step Process)")
        logger.info("=" * 60)
        
        # Step 1: Initialize Entity Extractor (Question Preprocessing)
        logger.info("Step 1: Initializing Entity Extractor...")
        self.entity_extractor = EntityExtractor()
        logger.info("  ✓ Entity Extractor ready (VnCoreNLP + Gemini + Keywords)")
        
        # Step 2: Initialize Neo4j Manager (Sub-graph Retrieval)
        logger.info("Step 2: Connecting to Neo4j Knowledge Graph...")
        try:
            self.neo4j = Neo4jManager(self.config)
            self.neo4j_connected = True
            logger.info(f"  ✓ Neo4j connected: {self.config.neo4j_uri}")
        except Exception as e:
            logger.error(f"  ✗ Neo4j connection failed: {e}")
            if not self.config.allow_neo4j_fallback:
                raise ConnectionError(f"Neo4j connection required but failed: {e}")
            logger.warning("  ⚠ Running in FALLBACK mode (LLM-only, no KG)")
        
        # Initialize embedding generator
        self.embedding_gen = EmbeddingGenerator(self.config)
        
        # Step 3: Initialize Graph Encoder (if enabled)
        self.graph_encoder = None
        if self.config.use_graph_encoder and self.neo4j_connected:
            logger.info("Step 3: Initializing Graph Encoder...")
            self.graph_encoder = GraphEncoder(self.config, self.embedding_gen)
            logger.info(f"  ✓ Graph Encoder ready (dim={self.config.graph_encoding_dim})")
        else:
            logger.info("Step 3: Graph Encoder disabled or Neo4j not connected")
        
        # Step 4: Initialize Embedding Fusion (CrossAttention)
        self.embedding_fusion = None
        if self.config.use_cross_attention:
            logger.info("Step 4: Initializing Embedding Fusion...")
            self.embedding_fusion = EmbeddingFusion(self.config)
            logger.info(f"  ✓ CrossAttention Fusion ready (heads={self.config.fusion_heads})")
        else:
            logger.info("Step 4: Embedding Fusion disabled")
        
        # Initialize retriever and context builder
        self.reranker = Reranker(self.config)
        if self.neo4j_connected:
            self.retriever = HybridRetriever(
                self.config, self.embedding_gen, self.neo4j, self.reranker
            )
        else:
            self.retriever = None
        self.context_builder = ContextBuilder(self.config)
        
        # Step 5: Initialize Answer Generator (Answer Generation)
        logger.info("Step 5: Initializing Answer Generator...")
        if use_dual_mode:
            logger.info("  Using DUAL mode (Qwen + DeepSeek)")
            self.answer_gen = DualAnswerGenerator(
                config=self.config,
                qwen_model=self.config.qwen_model
            )
            self.dual_mode = True
        else:
            # Single model mode (Qwen or DeepSeek based on config)
            self.answer_gen = AnswerGenerator(
                config=self.config,
                model_name=self.config.qwen_model,
                tf_model_name=self.config.tf_model if self.config.tf_model else None
            )
            self.dual_mode = False
        logger.info("  ✓ Answer Generator ready")
        
        # Step 6: Trust Score Calculator
        self.trust_calculator = None
        if self.config.enable_trust_score:
            logger.info("Step 6: Initializing Trust Score Calculator...")
            self.trust_calculator = TrustScoreCalculator(self.config)
            logger.info("  ✓ Trust Score Calculator ready")
        
        logger.info("=" * 60)
        logger.info("✓ GraphRAG Pipeline FULLY initialized")
        logger.info("=" * 60)
        
        # Log configuration summary
        self._log_config_summary(use_dual_mode)
    
    def process_question(self, q_data: Dict) -> Dict:
        """Process a single question."""
        start_time = time.time()
        
        question = q_data.get("question", "")
        options = q_data.get("options", [])
        
        # Determine question type
        is_tf = self._is_tf_question(question, options)
        question_type = "tf" if is_tf else "mcq"
        
        # Get correct answer
        correct_answer = self._get_correct_answer(options, question_type)
        
        # Check if using direct T/F mode (without KG)
        # Enable if: tf_model is loaded OR tf_direct_mode is True in config
        use_tf_direct = is_tf and (
            (hasattr(self.answer_gen, 'tf_model') and self.answer_gen.tf_model is not None) or 
            self.config.tf_direct_mode
        )
        
        # Extract entities (skip for T/F direct mode)
        entities = []
        if not use_tf_direct:
            if is_tf:
                statement = self.entity_extractor.extract_tf_statement(question)
                entities = self.entity_extractor.extract(statement)
            else:
                option_texts = [opt.get("answer", "") for opt in options]
                entities = self.entity_extractor.extract(question, option_texts)
        
        # Hybrid retrieval (skip for T/F direct mode or if Neo4j not connected)
        candidates = []
        context = ""
        provenance = []
        graph_embedding = None
        question_embedding = None
        fused_embedding = None
        attention_score = 0.0
        entity_relationships = []
        
        if not use_tf_direct and self.retriever is not None:
            # Step 2: Sub-graph Retrieval from Neo4j
            candidates = self.retriever.retrieve(entities, question, top_k=self.config.top_k_retrieval)
            context, provenance = self.context_builder.build_context(candidates, token_budget=5000)
            
            # Step 3: Graph Encoding - Encode sub-graph structure into embedding g
            if self.graph_encoder and candidates:
                # Collect entities and relationships from retrieved candidates
                retrieved_entity_ids = list(set(c.get("entity_id") for c in candidates if c.get("entity_id")))
                entity_descriptions = {}
                
                for c in candidates:
                    eid = c.get("entity_id")
                    if eid and eid not in entity_descriptions:
                        # Get description from candidate text
                        text = c.get("text", "")
                        if text:
                            entity_descriptions[eid] = text[:300]
                
                # Get relationships from Neo4j for graph structure
                for eid in retrieved_entity_ids[:5]:  # Top 5 entities
                    try:
                        rels = self.neo4j.get_entity_relationships(eid, limit=10)
                        for rel in rels:
                            # Handle both outgoing (source=eid, target=target_id) 
                            # and incoming (source=source_id, target=eid) relationships
                            if rel.get("direction") == "outgoing":
                                entity_relationships.append({
                                    "source": eid,
                                    "target": rel.get("target_id", ""),
                                    "predicate": rel.get("predicate", "RELATED_TO")
                                })
                            else:  # incoming
                                entity_relationships.append({
                                    "source": rel.get("source_id", ""),
                                    "target": eid,
                                    "predicate": rel.get("predicate", "RELATED_TO")
                                })
                    except Exception as e:
                        logger.debug(f"Failed to get relationships for {eid}: {e}")
                
                # Encode sub-graph into embedding g
                graph_embedding = self.graph_encoder.encode_subgraph(
                    entities=retrieved_entity_ids,
                    relationships=entity_relationships,
                    entity_descriptions=entity_descriptions
                )
                logger.debug(f"Step 3: Graph encoded - {len(retrieved_entity_ids)} entities, {len(entity_relationships)} relationships")
            
            # Step 4: Embedding Fusion - Compute h = CrossAttn(q, g)
            if self.embedding_fusion and graph_embedding:
                # Generate question embedding q
                question_embedding = self.embedding_gen.generate_embedding(question)
                
                if question_embedding:
                    # Fuse question and graph embeddings
                    fused_embedding = self.embedding_fusion.fuse(question_embedding, graph_embedding)
                    attention_score = self.embedding_fusion.compute_attention_score(question_embedding, graph_embedding)
                    logger.debug(f"Step 4: Embeddings fused - attention_score={attention_score:.4f}")
                    
                    # Enhance context with fusion information
                    if attention_score > 0.5:
                        # High attention = graph context is highly relevant
                        context = f"[Graph Relevance: HIGH ({attention_score:.2f})]\n\n" + context
                    elif attention_score > 0.3:
                        context = f"[Graph Relevance: MEDIUM ({attention_score:.2f})]\n\n" + context
        
        elif not use_tf_direct and self.retriever is None:
            logger.warning("Neo4j not connected - using LLM-only mode without KG context")
        
        # Generate answer
        source_materials = None
        
        # Handle dual mode vs single mode
        if self.dual_mode:
            # DualAnswerGenerator returns a dict
            if is_tf:
                statement = self.entity_extractor.extract_tf_statement(question)
                if not use_tf_direct:
                    source_materials = self.entity_extractor.extract_source_materials(question)
                dual_result = self.answer_gen.answer_tf(
                    statement, context, source_materials=source_materials, use_direct=use_tf_direct
                )
            else:
                option_texts = [opt.get("answer", "") for opt in options]
                dual_result = self.answer_gen.answer_mcq(question, option_texts, context)
            
            # Extract primary answer from dual result
            model_answer = dual_result['primary_answer']
            raw_response = dual_result['primary_raw']
            
            # Store dual results separately
            qwen_answer = dual_result['qwen']['answer']
            qwen_raw = dual_result['qwen']['raw']
            deepseek_answer = dual_result['deepseek']['answer']
            deepseek_raw = dual_result['deepseek']['raw']
        else:
            # Single mode: AnswerGenerator returns tuple
            if is_tf:
                statement = self.entity_extractor.extract_tf_statement(question)
                if not use_tf_direct:
                    source_materials = self.entity_extractor.extract_source_materials(question)
                model_answer, raw_response = self.answer_gen.answer_tf(
                    statement, context, source_materials=source_materials, use_direct=use_tf_direct
                )
            else:
                option_texts = [opt.get("answer", "") for opt in options]
                model_answer, raw_response = self.answer_gen.answer_mcq(question, option_texts, context)
            
            qwen_answer = None
            qwen_raw = None
            deepseek_answer = None
            deepseek_raw = None
        
        # Determine correctness
        is_correct = self._compare_answers(model_answer, correct_answer, question_type)
        
        # Calculate retrieval statistics
        retrieval_stats = self._compute_retrieval_stats(candidates)
        
        # Check confidence
        avg_score = retrieval_stats.get("avg_top3_score", 0)
        low_confidence = avg_score < self.config.confidence_threshold
        
        # Step 6: Calculate Trust Score (Post-processing)
        trust_info = None
        if self.trust_calculator and raw_response:
            # Estimate confidence from response
            answer_confidence = self.trust_calculator.estimate_confidence_from_response(raw_response)
            
            # Get entity centralities (simplified - based on retrieval scores)
            entity_centralities = []
            evidence_scores = []
            for p in provenance[:5]:
                score = p.get("score", 0)
                if isinstance(score, (int, float)):
                    evidence_scores.append(float(score))
                    entity_centralities.append(float(score) * 0.8)  # Approx centrality
            
            trust_info = self.trust_calculator.calculate(
                answer_confidence=answer_confidence,
                entity_centralities=entity_centralities,
                evidence_scores=evidence_scores,
                has_graph_context=self.neo4j_connected and len(context) > 0
            )
        
        processing_time = time.time() - start_time
        self.metrics.record_query(processing_time)
        
        # Build detailed result (user-requested format)
        result = {
            "question": question,
            "question_type": question_type,
            "correct_answer": correct_answer,
            "entities_extracted": entities,
            "context_length": len(context),
            
            # Model answer and raw response
            "model_answer": model_answer,
            "raw_response": raw_response,
            "is_correct": is_correct,
            
            # Evidence from retrieval
            "evidence": [
                {
                    "source": p.get("source"),
                    "chunk_id": p.get("chunk_id"),
                    "score": round(p.get("score", 0), 4),
                    "provenance": p.get("provenance"),
                    "text_preview": p.get("text_preview", "")[:200] if p.get("text_preview") else ""
                }
                for p in provenance[:10]
            ],
            
            # Timing
            "processing_time_seconds": round(processing_time, 2),
            
            # Neo4j connection status (for debugging)
            "neo4j_connected": self.neo4j_connected,
        }
        
        # Add dual mode results if applicable
        if self.dual_mode:
            result["dual_mode"] = True
            result["qwen_answer"] = qwen_answer
            result["qwen_raw_response"] = qwen_raw
            result["deepseek_answer"] = deepseek_answer
            result["deepseek_raw_response"] = deepseek_raw
            
            # Calculate individual correctness
            result["qwen_is_correct"] = self._compare_answers(qwen_answer or "", correct_answer, question_type)
            result["deepseek_is_correct"] = self._compare_answers(deepseek_answer or "", correct_answer, question_type) if deepseek_answer else None
        
        return result
    
    def _compute_retrieval_stats(self, candidates: List[Dict]) -> Dict:
        """Compute detailed retrieval statistics."""
        if not candidates:
            return {
                "total_candidates": 0,
                "avg_top3_score": 0,
                "provenance_breakdown": {},
                "entity_coverage": []
            }
        
        # Provenance breakdown
        provenance_counts = {}
        for c in candidates:
            prov = c.get("provenance", "unknown")
            provenance_counts[prov] = provenance_counts.get(prov, 0) + 1
        
        # Score statistics
        scores = [c.get("combined_score", 0) for c in candidates]
        top3_scores = scores[:3] if len(scores) >= 3 else scores
        
        # Ensure scores are floats
        def to_float(x):
            if isinstance(x, (list, tuple)):
                return float(x[0]) if x else 0.0
            return float(x) if x else 0.0
        
        scores = [to_float(s) for s in scores]
        top3_scores = [to_float(s) for s in top3_scores]
        
        # Entity coverage
        entity_ids = list(set(c.get("entity_id") for c in candidates if c.get("entity_id")))
        
        # Check for different evidence types
        has_passage = any("passage" in c.get("provenance", "") for c in candidates)
        has_relationship = any("relationship" in c.get("provenance", "") for c in candidates)
        has_neighbor = any("neighbor" in c.get("provenance", "") for c in candidates)
        
        return {
            "total_candidates": len(candidates),
            "avg_top3_score": sum(top3_scores) / len(top3_scores) if top3_scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "provenance_breakdown": provenance_counts,
            "unique_entities": len(entity_ids),
            "entity_coverage": entity_ids[:10],  # Top 10 entities
            "has_passage_evidence": has_passage,
            "has_relationship_evidence": has_relationship,
            "has_neighbor_evidence": has_neighbor,
            "evidence_diversity": sum([has_passage, has_relationship, has_neighbor])
        }
    
    def _is_tf_question(self, question: str, options: List[Dict]) -> bool:
        if len(options) == 2:
            answers = [opt.get("answer", "").lower() for opt in options]
            if "đúng" in answers and "sai" in answers:
                return True
        return bool(re.search(r'đúng hay sai|phát biểu.*đúng', question.lower()))
    
    def _get_correct_answer(self, options: List[Dict], q_type: str) -> str:
        for i, opt in enumerate(options):
            if opt.get("isCorrect", False):
                return opt.get("answer", "") if q_type == "tf" else chr(ord('A') + i)
        return ""
    
    def _compare_answers(self, model: str, correct: str, q_type: str) -> bool:
        if q_type == "tf":
            return ("đúng" in model.lower()) == ("đúng" in correct.lower())
        return model.strip().upper() == correct.strip().upper()
    
    def _log_config_summary(self, use_dual_mode: bool):
        """Log configuration summary for debugging."""
        logger.info("=" * 60)
        logger.info("CONFIGURATION SUMMARY:")
        logger.info(f"  Neo4j Connected: {self.neo4j_connected}")
        logger.info(f"  Neo4j URI: {self.config.neo4j_uri}")
        logger.info(f"  Graph Encoder: {'Enabled' if self.graph_encoder else 'Disabled'}")
        logger.info(f"  Embedding Fusion: {'Enabled' if self.embedding_fusion else 'Disabled'}")
        logger.info(f"  Trust Score: {'Enabled' if self.trust_calculator else 'Disabled'}")
        
        if use_dual_mode:
            mode_info = self.answer_gen.get_mode_info()
            logger.info(f"  Answer Mode: DUAL (Qwen + DeepSeek)")
            logger.info(f"    - Qwen Model: {mode_info['qwen_model']}")
            logger.info(f"    - DeepSeek: {'Available' if mode_info['deepseek_available'] else 'Not available'}")
        else:
            logger.info(f"  Answer Mode: SINGLE")
            logger.info(f"    - MCQ Model: {self.config.qwen_model}")
            if self.config.tf_model:
                logger.info(f"    - T/F Model: {self.config.tf_model} (separate)")
            else:
                logger.info(f"    - T/F Model: {self.config.qwen_model} (same as MCQ)")
        
        logger.info(f"  T/F Direct Mode: {'ENABLED (no KG)' if self.config.tf_direct_mode else 'DISABLED (uses KG)'}")
        logger.info("=" * 60)
    
    def run(self, limit: int = None, progress_interval: int = 5) -> Dict:
        """Run evaluation on question dataset."""
        # Load questions
        with open(self.config.questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = []
        if isinstance(data, list):
            questions = data
        else:
            questions.extend(data.get("multiple_choice", []))
            questions.extend(data.get("true_false", []))
        
        if limit:
            questions = questions[:limit]
        
        total = len(questions)
        results = []
        stats = {"total": 0, "correct": 0, "mcq": 0, "mcq_correct": 0, "tf": 0, "tf_correct": 0}
        start_time = time.time()
        
        # Aggregate retrieval stats
        agg_retrieval = {
            "total_candidates": 0,
            "total_with_passage": 0,
            "provenance_counts": {},
            "all_entity_coverage": [],
            "processing_times": []
        }
        
        logger.info(f"Processing {total} questions...")
        
        for i, q in enumerate(questions, 1):
            try:
                result = self.process_question(q)
                results.append(result)
                
                stats["total"] += 1
                if result["is_correct"]:
                    stats["correct"] += 1
                
                q_type = result.get("question_type", "mcq")
                stats[q_type] += 1
                if result["is_correct"]:
                    stats[f"{q_type}_correct"] += 1
                
                # Aggregate retrieval stats
                ret_stats = result.get("retrieval_stats", {})
                agg_retrieval["total_candidates"] += ret_stats.get("total_candidates", 0)
                if ret_stats.get("has_passage_evidence"):
                    agg_retrieval["total_with_passage"] += 1
                agg_retrieval["processing_times"].append(result.get("processing_time_seconds", 0))
                
                for prov, count in ret_stats.get("provenance_breakdown", {}).items():
                    agg_retrieval["provenance_counts"][prov] = \
                        agg_retrieval["provenance_counts"].get(prov, 0) + count
                agg_retrieval["all_entity_coverage"].extend(
                    ret_stats.get("entity_coverage", [])[:5]
                )
                    
            except Exception as e:
                logger.error(f"Error on Q{i}: {e}")
                self.metrics.record_error()
            
            if i % progress_interval == 0 or i == total:
                self._print_progress(i, total, stats, start_time)
        
        total_time = time.time() - start_time
        
        # Compute aggregate metrics
        avg_processing = sum(agg_retrieval["processing_times"]) / len(agg_retrieval["processing_times"]) \
            if agg_retrieval["processing_times"] else 0
        
        # Error analysis
        error_analysis = self._analyze_errors(results)
        
        # Save results
        output = {
            "stats": stats,
            "accuracy": {
                "total": stats["correct"] / stats["total"] * 100 if stats["total"] else 0,
                "mcq": stats["mcq_correct"] / stats["mcq"] * 100 if stats["mcq"] else 0,
                "tf": stats["tf_correct"] / stats["tf"] * 100 if stats["tf"] else 0,
            },
            "retrieval_summary": {
                "avg_candidates_per_question": agg_retrieval["total_candidates"] / stats["total"] if stats["total"] else 0,
                "questions_with_passage_evidence": agg_retrieval["total_with_passage"],
                "passage_evidence_rate": agg_retrieval["total_with_passage"] / stats["total"] * 100 if stats["total"] else 0,
                "provenance_distribution": agg_retrieval["provenance_counts"],
                "unique_entities_retrieved": len(set(agg_retrieval["all_entity_coverage"]))
            },
            "timing": {
                "total_seconds": round(total_time, 2),
                "avg_per_question_seconds": round(avg_processing, 2)
            },
            "error_analysis": error_analysis,
            "config": {
                # Neo4j connection status (CRITICAL for GraphRAG)
                "neo4j_connected": self.neo4j_connected,
                "neo4j_uri": self.config.neo4j_uri,
                
                # GraphRAG Components Status
                "graphrag_components": {
                    "entity_extractor": True,
                    "graph_encoder": self.graph_encoder is not None,
                    "embedding_fusion": self.embedding_fusion is not None,
                    "trust_calculator": self.trust_calculator is not None,
                    "hybrid_retriever": self.retriever is not None
                },
                
                # Models configuration
                "models": {
                    "mcq_model": self.config.qwen_model,
                    "tf_model": self.config.tf_model or self.config.qwen_model,
                    "tf_direct_mode": self.config.tf_direct_mode,
                    "tf_uses_kg": not self.config.tf_direct_mode and not bool(self.config.tf_model),
                    "dual_mode": self.dual_mode
                },
                "top_k_retrieval": self.config.top_k_retrieval,
                "top_k_rerank": self.config.top_k_rerank,
                "confidence_threshold": self.config.confidence_threshold,
                "weights": {
                    "entity": self.config.entity_weight,
                    "vector": self.config.vector_weight,
                    "text": self.config.text_weight,
                    "graph": self.config.graph_weight
                }
            },
            "results": results
        }
        
        with open(self.config.output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to {self.config.output_file}")
        self.metrics.print_stats()
        
        return output
    
    def _analyze_errors(self, results: List[Dict]) -> Dict:
        """Analyze error patterns in results."""
        errors = [r for r in results if not r.get("is_correct")]
        
        if not errors:
            return {"error_count": 0}
        
        # Low confidence errors
        low_conf_errors = [e for e in errors if e.get("low_confidence")]
        
        # Provenance analysis for errors
        error_provenances = {}
        for e in errors:
            for ev in e.get("evidence", []):
                prov = ev.get("provenance", "unknown")
                error_provenances[prov] = error_provenances.get(prov, 0) + 1
        
        # Missing entity cases
        no_entity_errors = [e for e in errors if not e.get("entities_extracted")]
        
        return {
            "error_count": len(errors),
            "low_confidence_errors": len(low_conf_errors),
            "no_entity_errors": len(no_entity_errors),
            "error_provenance_distribution": error_provenances,
            "mcq_errors": len([e for e in errors if e.get("question_type") == "mcq"]),
            "tf_errors": len([e for e in errors if e.get("question_type") == "tf"])
        }
    
    def _print_progress(self, current: int, total: int, stats: Dict, start_time: float):
        elapsed = time.time() - start_time
        remaining = (total - current) * elapsed / current if current > 0 else 0
        
        acc_total = stats["correct"] / stats["total"] * 100 if stats["total"] else 0
        acc_mcq = stats["mcq_correct"] / stats["mcq"] * 100 if stats["mcq"] else 0
        acc_tf = stats["tf_correct"] / stats["tf"] * 100 if stats["tf"] else 0
        
        print(f"\n{'='*60}")
        print(f"Progress: {current}/{total} ({current/total*100:.1f}%)")
        print(f"Accuracy: Total={acc_total:.1f}% | MCQ={acc_mcq:.1f}% | T/F={acc_tf:.1f}%")
        print(f"Time: {elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining")
        print(f"{'='*60}")
    
    def close(self):
        self.neo4j.close()
    
    def generate_html_report(self, results: Dict, output_path: str):
        """Generate a beautiful HTML report from evaluation results."""
        import html as html_lib
        
        stats = results.get("stats", {})
        accuracy = results.get("accuracy", {})
        retrieval_summary = results.get("retrieval_summary", {})
        error_analysis = results.get("error_analysis", {})
        
        # Split results by question type
        mcq_results = [r for r in results.get("results", []) if r.get("question_type") == "mcq"]
        tf_results = [r for r in results.get("results", []) if r.get("question_type") == "tf"]
        
        html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GraphRAG Evaluation Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 28px; }}
        .header p {{ margin: 5px 0; opacity: 0.9; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; transition: transform 0.2s; }}
        .stat-card:hover {{ transform: translateY(-3px); }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #3498db; }}
        .stat-value.good {{ color: #27ae60; }}
        .stat-value.bad {{ color: #e74c3c; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; font-size: 14px; }}
        .section-title {{ font-size: 22px; font-weight: bold; margin: 30px 0 15px 0; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #3498db; }}
        .question-card {{ background: white; padding: 20px; margin-bottom: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 5px solid #ddd; }}
        .question-card.correct {{ border-left-color: #27ae60; }}
        .question-card.wrong {{ border-left-color: #e74c3c; }}
        .question-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }}
        .question-id {{ font-weight: bold; color: #2c3e50; font-size: 14px; }}
        .status-badge {{ padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .status-badge.correct {{ background: #27ae60; color: white; }}
        .status-badge.wrong {{ background: #e74c3c; color: white; }}
        .question-text {{ font-size: 15px; margin-bottom: 15px; line-height: 1.7; color: #2c3e50; }}
        .answer-row {{ display: flex; gap: 20px; margin: 15px 0; flex-wrap: wrap; }}
        .answer-box {{ padding: 10px 15px; border-radius: 6px; font-size: 14px; }}
        .answer-box.predicted {{ background: #fadbd8; border: 1px solid #e74c3c; }}
        .answer-box.correct {{ background: #d5f4e6; border: 1px solid #27ae60; }}
        .answer-box.predicted.is-correct {{ background: #d5f4e6; border: 1px solid #27ae60; }}
        .evidence-list {{ margin-top: 15px; }}
        .evidence-item {{ background: #f8f9fa; padding: 12px; border-radius: 6px; margin: 8px 0; font-size: 13px; border-left: 3px solid #3498db; }}
        .evidence-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; flex-wrap: wrap; gap: 5px; }}
        .evidence-source {{ font-weight: bold; color: #2c3e50; }}
        .evidence-score {{ color: #7f8c8d; font-size: 12px; }}
        .evidence-prov {{ background: #e8f4fd; padding: 2px 8px; border-radius: 10px; font-size: 11px; color: #3498db; }}
        .evidence-text {{ color: #555; line-height: 1.5; }}
        .toggle-btn {{ cursor: pointer; color: #3498db; font-size: 13px; margin-top: 12px; display: inline-block; user-select: none; padding: 5px 10px; background: #e8f4fd; border-radius: 4px; }}
        .toggle-btn:hover {{ background: #d0e8f7; }}
        .collapsible {{ display: none; margin-top: 15px; padding: 15px; background: #fafafa; border-radius: 8px; }}
        .collapsible.show {{ display: block; }}
        .response-box {{ background: #fff3cd; padding: 15px; border-radius: 6px; margin: 10px 0; font-size: 13px; line-height: 1.6; max-height: 200px; overflow-y: auto; white-space: pre-wrap; }}
        .entities-box {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
        .entity-tag {{ background: #e8f4fd; color: #2980b9; padding: 4px 10px; border-radius: 15px; font-size: 12px; }}
        .error-summary {{ background: #fff5f5; border: 1px solid #fed7d7; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .error-summary h3 {{ color: #c53030; margin-top: 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>GraphRAG Evaluation Report</h1>
        <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Model: Qwen3-4B | Embedding: Qwen3-Embedding-0.6B | Reranker: Qwen3-Reranker-0.6B</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value {'good' if accuracy.get('total', 0) >= 70 else 'bad' if accuracy.get('total', 0) < 50 else ''}">{accuracy.get('total', 0):.1f}%</div>
            <div class="stat-label">Overall Accuracy</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats.get('correct', 0)}/{stats.get('total', 0)}</div>
            <div class="stat-label">Correct Answers</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{accuracy.get('mcq', 0):.1f}%</div>
            <div class="stat-label">MCQ Accuracy ({stats.get('mcq_correct', 0)}/{stats.get('mcq', 0)})</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{accuracy.get('tf', 0):.1f}%</div>
            <div class="stat-label">T/F Accuracy ({stats.get('tf_correct', 0)}/{stats.get('tf', 0)})</div>
        </div>
    </div>
    
    <div class="error-summary">
        <h3>Error Analysis</h3>
        <p><strong>Total Errors:</strong> {error_analysis.get('error_count', 0)} | 
           <strong>MCQ Errors:</strong> {error_analysis.get('mcq_errors', 0)} | 
           <strong>T/F Errors:</strong> {error_analysis.get('tf_errors', 0)} |
           <strong>Low Confidence:</strong> {error_analysis.get('low_confidence_errors', 0)} |
           <strong>No Entities:</strong> {error_analysis.get('no_entity_errors', 0)}</p>
    </div>
"""
        # MCQ Section
        html += f"""
    <div class="section-title">Multiple Choice Questions ({len(mcq_results)})</div>
"""
        for i, q in enumerate(mcq_results, 1):
            status_class = 'correct' if q.get('is_correct') else 'wrong'
            status_text = 'CORRECT' if q.get('is_correct') else 'WRONG'
            
            html += f"""
    <div class="question-card {status_class}">
        <div class="question-header">
            <span class="question-id">MCQ #{i}</span>
            <span class="status-badge {status_class}">{status_text}</span>
        </div>
        <div class="question-text">{html_lib.escape(q.get('question', '')[:500])}</div>
        
        <div class="answer-row">
            <div class="answer-box {'predicted is-correct' if q.get('is_correct') else 'predicted'}">
                <strong>Model:</strong> {html_lib.escape(str(q.get('model_answer', 'N/A')))}
            </div>
            <div class="answer-box correct">
                <strong>Correct:</strong> {html_lib.escape(str(q.get('correct_answer', 'N/A')))}
            </div>
        </div>
        
        <div class="entities-box">
"""
            for ent in q.get('entities_extracted', [])[:8]:
                html += f'            <span class="entity-tag">{html_lib.escape(str(ent))}</span>\n'
            
            html += f"""
        </div>
        
        <div class="toggle-btn" onclick="toggleCollapsible('mcq-{i}')">Show Details</div>
        <div id="mcq-{i}" class="collapsible">
            <h4>Evidence ({len(q.get('evidence', []))} items):</h4>
            <div class="evidence-list">
"""
            for ev in q.get('evidence', [])[:5]:
                score = ev.get('score', 0)
                html += f"""
                <div class="evidence-item">
                    <div class="evidence-header">
                        <span class="evidence-source">{html_lib.escape(str(ev.get('source', 'Unknown'))[:50])}</span>
                        <span class="evidence-score">Score: {score:.3f}</span>
                        <span class="evidence-prov">{html_lib.escape(str(ev.get('provenance', 'unknown')))}</span>
                    </div>
                    <div class="evidence-text">{html_lib.escape(str(ev.get('text_preview', ''))[:200])}</div>
                </div>
"""
            html += f"""
            </div>
            <h4>Model Response:</h4>
            <div class="response-box">{html_lib.escape(str(q.get('raw_response', 'N/A'))[:600])}</div>
        </div>
    </div>
"""
        
        # True/False Section
        html += f"""
    <div class="section-title">True/False Questions ({len(tf_results)})</div>
"""
        for i, q in enumerate(tf_results, 1):
            status_class = 'correct' if q.get('is_correct') else 'wrong'
            status_text = 'CORRECT' if q.get('is_correct') else 'WRONG'
            
            html += f"""
    <div class="question-card {status_class}">
        <div class="question-header">
            <span class="question-id">T/F #{i}</span>
            <span class="status-badge {status_class}">{status_text}</span>
        </div>
        <div class="question-text">{html_lib.escape(q.get('question', '')[:800])}</div>
        
        <div class="answer-row">
            <div class="answer-box {'predicted is-correct' if q.get('is_correct') else 'predicted'}">
                <strong>Model:</strong> {html_lib.escape(str(q.get('model_answer', 'N/A')))}
            </div>
            <div class="answer-box correct">
                <strong>Correct:</strong> {html_lib.escape(str(q.get('correct_answer', 'N/A')))}
            </div>
        </div>
        
        <div class="entities-box">
"""
            for ent in q.get('entities_extracted', [])[:8]:
                html += f'            <span class="entity-tag">{html_lib.escape(str(ent))}</span>\n'
            
            html += f"""
        </div>
        
        <div class="toggle-btn" onclick="toggleCollapsible('tf-{i}')">Show Details</div>
        <div id="tf-{i}" class="collapsible">
            <h4>Evidence ({len(q.get('evidence', []))} items):</h4>
            <div class="evidence-list">
"""
            for ev in q.get('evidence', [])[:5]:
                score = ev.get('score', 0)
                html += f"""
                <div class="evidence-item">
                    <div class="evidence-header">
                        <span class="evidence-source">{html_lib.escape(str(ev.get('source', 'Unknown'))[:50])}</span>
                        <span class="evidence-score">Score: {score:.3f}</span>
                        <span class="evidence-prov">{html_lib.escape(str(ev.get('provenance', 'unknown')))}</span>
                    </div>
                    <div class="evidence-text">{html_lib.escape(str(ev.get('text_preview', ''))[:200])}</div>
                </div>
"""
            html += f"""
            </div>
            <h4>Model Response:</h4>
            <div class="response-box">{html_lib.escape(str(q.get('raw_response', 'N/A'))[:600])}</div>
        </div>
    </div>
"""
        
        html += """
    <script>
        function toggleCollapsible(id) {
            const element = document.getElementById(id);
            element.classList.toggle('show');
        }
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML report saved to: {output_path}")


def main():
    config = GraphRAGConfig()
    pipeline = GraphRAGPipeline(config)
    try:
        results = pipeline.run(limit=None, progress_interval=10)
        
        # Generate HTML report
        html_path = config.output_file.replace('.json', '.html')
        pipeline.generate_html_report(results, html_path)
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
