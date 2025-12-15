"""
GraphRAG Pipeline - Main Pipeline and Answer Generation (Qwen Only)
Simplified version without DeepSeek API
"""

try:
    from kaggle_secrets import UserSecretsClient
    _KAGGLE_SECRETS_AVAILABLE = True
except Exception:
    _KAGGLE_SECRETS_AVAILABLE = False

import os
import re
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    genai = None

from .core import (
    GraphRAGConfig, chunk_text, VietnameseNormalizer, 
    logger, MetricsCollector
)
from .embeddings import EmbeddingGenerator, Reranker
from .neo4j_manager import Neo4jManager
from .retriever import HybridRetriever, ContextBuilder


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
        self.gemini = None
        if _GENAI_AVAILABLE:
            api_key = api_key or get_secret("GEMINI_API_KEY", None)
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    self.gemini = genai.GenerativeModel("gemini-1.5-flash")
                except Exception as e:
                    logger.warning(f"Failed to initialize Gemini: {e}")
        
        if not self.gemini:
            logger.info("Using keyword extraction only (no Gemini API)")
    
    def extract(self, question: str, options: List[str] = None) -> List[str]:
        """Extract entities using multiple methods."""
        entities = []
        
        VIETNAMESE_STOPWORDS = {
            "anh", "em", "tôi", "ta", "mình", "chúng", "họ", "ông", "bà", "cô", "chú",
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
        
        # Deduplicate and filter
        unique = []
        seen = set()
        
        GENERIC_ENTITIES = {
            'việt nam', 'trung quốc', 'mỹ', 'pháp', 'anh', 'liên xô',
            'nhật bản', 'đức', 'thế giới', 'châu á', 'châu âu'
        }
        
        specific_entities = []
        generic_entities = []
        
        for e in entities:
            e_lower = e.lower().strip()
            if e_lower in VIETNAMESE_STOPWORDS:
                continue
            if re.match(r'^\d{4}$', e):
                continue
            if e_lower and e_lower not in seen and len(e) > 1:
                seen.add(e_lower)
                if e_lower in GENERIC_ENTITIES:
                    generic_entities.append(e.strip())
                else:
                    specific_entities.append(e.strip())
        
        unique = specific_entities[:15] + generic_entities[:5]
        return unique[:20]
    
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
        """Extract the statement to be verified from T/F question."""
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
        """Extract "Tư liệu" content from T/F questions."""
        materials = {}
        
        pattern1 = r'Tư liệu\s*(\d+)?\s*:\s*["\"\"](.+?)["\"\"]'
        matches = re.findall(pattern1, question, re.DOTALL | re.IGNORECASE)
        for idx, content in matches:
            name = f"Tư liệu {idx}" if idx else "Tư liệu"
            materials[name] = content.strip()
        
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
# Answer Generator (Qwen Only - Multi-GPU Support)
# ================================================================================

class AnswerGenerator:
    """Generate answers using local Qwen model with multi-GPU support."""
    
    # REDESIGNED PROMPTS - MCQ: Bám sát context, T/F: Nới lỏng ngữ nghĩa
    MCQ_PROMPT = """Bạn là chuyên gia lịch sử. Trả lời câu hỏi dựa trên THÔNG TIN THAM KHẢO được cung cấp.

CÂU HỎI: {question}

CÁC ĐÁP ÁN:
A. {option_a}
B. {option_b}
C. {option_c}
D. {option_d}

THÔNG TIN THAM KHẢO:
{context}

QUY TẮC TRẢ LỜI:
1. ƯU TIÊN thông tin từ THÔNG TIN THAM KHẢO được cung cấp
2. Nếu THÔNG TIN THAM KHẢO có dữ liệu cụ thể (năm, số, tên) → sử dụng đó
3. CHỈ dùng kiến thức chung khi THÔNG TIN THAM KHẢO không đề cập
4. KHÔNG bịa số liệu hoặc chi tiết không có trong THÔNG TIN THAM KHẢO
5. Nếu không chắc chắn → chọn đáp án phù hợp nhất với THÔNG TIN THAM KHẢO

ĐÁP ÁN: [A/B/C/D]
Lý do ngắn:"""

    # T/F Prompt - RELAXED: Cho phép suy luận logic, chỉ SAI khi có thông tin sai thực sự
    TF_PROMPT = """Bạn là chuyên gia lịch sử Việt Nam.

PHÁT BIỂU: "{statement}"

THÔNG TIN THAM KHẢO:
{context}

NGUYÊN TẮC ĐÁNH GIÁ (NỚI LỎNG):
✓ ĐÚNG nếu:
  - Phát biểu đúng về NỘI DUNG CHÍNH (sự kiện, thời gian, nhân vật chính)
  - Phát biểu có thể SUY LUẬN LOGIC từ thông tin đã cho
  - Tư liệu hỗ trợ/không mâu thuẫn với phát biểu (dù không nói rõ 100%)
  - Diễn đạt khác từ ngữ nhưng GIỮ NGUYÊN ý nghĩa

✗ SAI CHỈ KHI:
  - Sai SỰ KIỆN cụ thể: sai năm, sai tên người, sai địa điểm, sai số liệu
  - Phát biểu MÂU THUẪN trực tiếp với tư liệu
  - Đảo ngược ý nghĩa (VD: "thành công" → "thất bại")

⚠ LƯU Ý:
- KHÔNG đánh SAI chỉ vì tư liệu không đề cập trực tiếp
- KHÔNG đánh SAI chỉ vì phát biểu diễn đạt ngắn gọn hơn tư liệu
- Cho phép khái quát hóa hợp lý từ thông tin cụ thể

KẾT LUẬN: [Đúng/Sai]
Lý do ngắn:"""

    # T/F with source materials - RELAXED
    TF_PROMPT_WITH_MATERIALS = """Bạn là chuyên gia lịch sử Việt Nam.

PHÁT BIỂU CẦN KIỂM TRA: "{statement}"

TƯ LIỆU GỐC:
{source_materials}

NGUYÊN TẮC ĐÁNH GIÁ (NỚI LỎNG):

✓ ĐÚNG nếu:
  1. Phát biểu đúng NỘI DUNG CHÍNH của tư liệu
  2. Phát biểu có thể SUY LUẬN LOGIC từ tư liệu (không cần nói nguyên văn)
  3. Phát biểu là DIỄN GIẢI/KHÁI QUÁT hợp lý của tư liệu
  4. Thông tin trong phát biểu KHÔNG MÂU THUẪN với tư liệu
  
✗ SAI CHỈ KHI:
  1. Phát biểu có thông tin SAI SỰ KIỆN (sai năm, sai tên, sai số)
  2. Phát biểu MÂU THUẪN với nội dung tư liệu
  3. Phát biểu ĐẢO NGƯỢC ý nghĩa của tư liệu
  4. Từ "tất cả/duy nhất/đầu tiên" mà tư liệu không khẳng định

⚠ QUAN TRỌNG:
- Tư liệu không nói rõ KHÔNG CÓ NGHĨA là phát biểu sai
- Diễn đạt khác từ ngữ nhưng đúng ý → ĐÚNG
- Suy luận logic hợp lý từ tư liệu → ĐÚNG

KẾT LUẬN: [Đúng/Sai]
Lý do ngắn:"""
    
    def __init__(self, config: GraphRAGConfig = None, 
                 model_name: str = "Qwen/Qwen3-4B",
                 device_map: str = "auto"):
        """
        Initialize AnswerGenerator with multi-GPU support.
        
        Args:
            config: GraphRAGConfig
            model_name: Model name to load
            device_map: "auto" for multi-GPU, "cuda:0" for single GPU
        """
        if isinstance(config, str):
            model_name = config
            config = None
        
        self.config = config if config is not None else GraphRAGConfig()
        self.model_name = model_name
        self.device_map = device_map
        
        logger.info(f"Loading model: {model_name}")
        logger.info(f"Device map: {device_map}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Load model with multi-GPU support
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map=device_map,  # "auto" enables multi-GPU
            trust_remote_code=True,
        )
        
        logger.info(f"✓ Model loaded with device_map={device_map}")
        
        # Log GPU allocation if multi-GPU
        if hasattr(self.model, 'hf_device_map'):
            logger.info(f"Model device map: {self.model.hf_device_map}")
    
    def prepare_prompt(self, prompt_text: str, max_tokens: int = 4000) -> str:
        """Truncate prompt if too long, keeping question intact."""
        tokens = self.tokenizer.encode(prompt_text)
        if len(tokens) <= max_tokens:
            return prompt_text
        # Only truncate context, not the question
        ratio = max_tokens / len(tokens)
        max_chars = int(len(prompt_text) * ratio * 0.85)
        return prompt_text[:max_chars] + "\n[...context truncated...]"
    
    def generate(self, prompt: str, max_new_tokens: int = 600) -> str:
        """Generate response using local model."""
        prompt = self.prepare_prompt(prompt)
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
        except Exception:
            text = f"User: {prompt}\n\nAssistant:"
        
        inputs = self.tokenizer([text], return_tensors="pt")
        
        # Move inputs to the correct device
        if hasattr(self.model, 'device'):
            inputs = inputs.to(self.model.device)
        else:
            # For multi-GPU, move to first device
            inputs = inputs.to("cuda:0")
        
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs, 
                max_new_tokens=max_new_tokens, 
                do_sample=False, 
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(
            output_ids[0][len(inputs.input_ids[0]):], skip_special_tokens=True
        )
        return response.strip()
    
    def answer_mcq(self, question: str, options: List[str], context: str) -> Tuple[str, str]:
        """Answer MCQ question."""
        while len(options) < 4:
            options.append("")
        
        # Truncate context if question is already long
        max_context_len = 3000
        if len(context) > max_context_len:
            context = context[:max_context_len] + "..."
        
        prompt = self.MCQ_PROMPT.format(
            context=context or "Không có thông tin chi tiết.",
            question=question,
            option_a=options[0], option_b=options[1],
            option_c=options[2], option_d=options[3]
        )
        
        raw = self.generate(prompt, max_new_tokens=400)  # MCQ needs shorter response
        answer = self._normalize_mcq(raw)
        return answer, raw
    
    def answer_tf(self, statement: str, context: str = None, 
                  source_materials: dict = None) -> Tuple[str, str]:
        """Answer True/False question."""
        if source_materials:
            materials_text = "\n".join([
                f"• {content[:1000]}" 
                for name, content in source_materials.items()
            ])
            # With source materials, minimize additional context to focus on materials
            prompt = self.TF_PROMPT_WITH_MATERIALS.format(
                source_materials=materials_text,
                statement=statement
            )
        else:
            # Truncate context for T/F
            max_context_len = 2500
            if context and len(context) > max_context_len:
                context = context[:max_context_len] + "..."
            prompt = self.TF_PROMPT.format(
                context=context or "Không có thông tin bổ sung.",
                statement=statement
            )
        
        raw = self.generate(prompt, max_new_tokens=400)  # T/F needs shorter response
        answer = self._normalize_tf(raw)
        return answer, raw

    
    def _normalize_mcq(self, response: str) -> str:
        """
        Extract MCQ answer (A/B/C/D) from model response.
        Uses multiple strategies with priority for final answer patterns.
        """
        if not response:
            return "A"
        
        response_upper = response.upper()
        
        # === PRIORITY 1: Pattern with answer followed by option text ===
        # Matches: "ĐÁP ÁN: D. Ô nhiễm môi trường" or "**ĐÁP ÁN: A. Đáp án...**"
        answer_with_text_patterns = [
            r'\*\*ĐÁP ÁN[:\s]*([ABCD])[\.\s]',  # **ĐÁP ÁN: D. text
            r'ĐÁP ÁN[:\s]+([ABCD])[\.\s]',      # ĐÁP ÁN: D. text
            r'ĐÁP ÁN[:\s]+([ABCD])\b',          # ĐÁP ÁN: D
        ]
        
        for pattern in answer_with_text_patterns:
            match = re.search(pattern, response_upper)
            if match:
                return match.group(1)
        
        # === PRIORITY 2: Check first 5 lines for "ĐÁP ÁN: X" ===
        lines = response.strip().split('\n')
        for line in lines[:5]:
            line_clean = line.strip().upper()
            # Match "ĐÁP ÁN: A" or "**ĐÁP ÁN: A**" or "ĐÁP ÁN: A. text"
            ans_match = re.search(r'ĐÁP ÁN[:\s]+\*?\*?([ABCD])', line_clean)
            if ans_match:
                return ans_match.group(1)
        
        # === PRIORITY 3: Explicit final answer patterns ===
        final_patterns = [
            r'ĐÁP ÁN ĐÚNG NHẤT[:\s]*[:\s]*([ABCD])',
            r'ĐÁP ÁN ĐÚNG LÀ[:\s]*([ABCD])',
            r'CHỌN[:\s]*\*?\*?([ABCD])',
            r'VẬY ĐÁP ÁN[:\s]*([ABCD])',
            r'KẾT LUẬN[:\s]*([ABCD])',
        ]
        
        for pattern in final_patterns:
            matches = list(re.finditer(pattern, response_upper, re.IGNORECASE))
            if matches:
                return matches[-1].group(1).upper()
        
        # === PRIORITY 4: Check for standalone answer at end ===
        for line in reversed(lines[-3:]):
            line_upper = line.strip().upper()
            # Match "**A**" or "A." or just "A" at line
            if re.match(r'^\*?\*?([ABCD])[\.\*]*\*?$', line_upper):
                match = re.match(r'^\*?\*?([ABCD])', line_upper)
                if match:
                    return match.group(1)
        
        # === PRIORITY 5: Find first standalone A/B/C/D ===
        all_letters = list(re.finditer(r'\b([ABCD])\b', response_upper))
        if all_letters:
            for m in all_letters:
                pos = m.start()
                before = response_upper[max(0, pos-1):pos] if pos > 0 else ' '
                after = response_upper[pos+1:pos+2] if pos+1 < len(response_upper) else ' '
                # Filter out false positives
                if not before.isalpha() and not after.isalpha():
                    return m.group(1)
        
        return "A"  # Default fallback
    
    def _normalize_tf(self, response: str) -> str:
        """
        Extract True/False answer from model response.
        Carefully handles cases where 'sai' appears in explanation but answer is 'Đúng'.
        """
        if not response:
            return "Đúng"
        
        response_lower = response.lower()
        
        # === PRIORITY 1: Check first 3 lines for "KẾT LUẬN: X" (new prompt format) ===
        lines = response.strip().split('\n')
        for line in lines[:3]:
            line_lower = line.strip().lower()
            # Match "KẾT LUẬN: Đúng" or "KẾT LUẬN: Sai" at start
            if re.search(r'^kết luận[:\s]+\[?(đúng|sai)\]?', line_lower):
                return "Sai" if "sai" in line_lower else "Đúng"
            # Match just "Đúng" or "Sai" at start
            if re.match(r'^(đúng|sai)[\.\s]', line_lower):
                return "Sai" if line_lower.startswith("sai") else "Đúng"
        
        # === PRIORITY 2: Explicit answer patterns anywhere ===
        final_patterns = [
            r'kết luận[:\s]+\[?(đúng|sai)\]?',  # KẾT LUẬN: Đúng
            r'\*\*kết luận[:\s]*\[?(đúng|sai)\]?\*\*',  # **KẾT LUẬN: Đúng**
            r'\*\*đáp án[:\s]*\[?(đúng|sai)\]?\*\*',  # **ĐÁP ÁN: Sai**
            r'đáp án[:\s]+\*?\*?(đúng|sai)',  # ĐÁP ÁN: Đúng
            r'phát biểu[:\s]+(đúng|sai)',  # Phát biểu: Đúng
            r'trả lời[:\s]+\*?\*?(đúng|sai)',  # Trả lời: Sai
        ]
        
        for pattern in final_patterns:
            matches = list(re.finditer(pattern, response_lower, re.IGNORECASE))
            if matches:
                # Return the FIRST match (new prompt puts answer first)
                first_match = matches[0].group(1).lower()
                return "Sai" if "sai" in first_match else "Đúng"
        
        # === PRIORITY 3: Check last few lines for conclusion ===
        for line in reversed(lines[-5:]):
            line_lower = line.strip().lower()
            # Match **đúng** or **sai**
            if re.search(r'\*\*(đúng|sai)\*\*', line_lower):
                match = re.search(r'\*\*(đúng|sai)\*\*', line_lower)
                return "Sai" if "sai" in match.group(1) else "Đúng"
            # Match standalone đúng/sai at end of line
            if re.search(r'^(đúng|sai)[\.!]*$', line_lower.strip()):
                return "Sai" if "sai" in line_lower else "Đúng"
            if re.search(r'(kết luận|đáp án)[:\s]*(đúng|sai)', line_lower):
                return "Sai" if "sai" in line_lower.split(":")[-1] else "Đúng"
        
        # === PRIORITY 3: Count explicit indicators ===
        # Words/phrases that clearly indicate the answer
        true_indicators = [
            r'\bphát biểu (là )?đúng\b',
            r'\bphát biểu trên (là )?đúng\b',
            r'\bnên là đúng\b',
            r'\bdo đó[,]? (phát biểu )?(là )?đúng\b',
            r'\bvì vậy[,]? (phát biểu )?(là )?đúng\b',
            r'\bkhẳng định.*đúng\b',
            r'\bhoàn toàn đúng\b',
            r'\bchính xác\b',
        ]
        
        false_indicators = [
            r'\bphát biểu (là )?sai\b',
            r'\bphát biểu trên (là )?sai\b',
            r'\bnên là sai\b',
            r'\bdo đó[,]? (phát biểu )?(là )?sai\b',
            r'\bvì vậy[,]? (phát biểu )?(là )?sai\b',
            r'\bkhông chính xác\b',
            r'\bkhông đúng\b',
            r'\bhoàn toàn sai\b',
        ]
        
        # Phrases where "sai" appears but doesn't mean the answer is SAI
        false_positive_sai = [
            r'không sai',
            r'sai lệch',
            r'sai lầm',
            r'sai khác',
            r'suy diễn sai',
            r'hiểu sai',
            r'nhận định sai',
            r'thông tin sai',
        ]
        
        true_count = sum(1 for p in true_indicators if re.search(p, response_lower))
        false_count = sum(1 for p in false_indicators if re.search(p, response_lower))
        
        if true_count > false_count:
            return "Đúng"
        if false_count > true_count:
            return "Sai"
        
        # === PRIORITY 4: Simple 'sai' check but filter false positives ===
        # Remove false positive phrases before checking
        cleaned = response_lower
        for fp in false_positive_sai:
            cleaned = re.sub(fp, '', cleaned)
        
        # Check for "sai" in the cleaned response
        if re.search(r'\bsai\b', cleaned):
            # But verify it's likely the answer, not just in explanation
            # Check if "đúng" appears after the last "sai"
            last_sai = cleaned.rfind('sai')
            last_dung = cleaned.rfind('đúng')
            if last_dung > last_sai:
                return "Đúng"
            return "Sai"
        
        return "Đúng"


# ================================================================================
# GraphRAG Pipeline (Simplified - Qwen Only)
# ================================================================================

class GraphRAGPipeline:
    """Complete GraphRAG pipeline for Vietnamese historical QA."""
    
    def __init__(self, config: GraphRAGConfig = None, device_map: str = "auto"):
        """
        Initialize GraphRAG Pipeline.
        
        Args:
            config: GraphRAGConfig with all settings
            device_map: "auto" for multi-GPU support
        """
        self.config = config or GraphRAGConfig()
        self.metrics = MetricsCollector()
        self.device_map = device_map
        
        logger.info("=" * 60)
        logger.info("Initializing GraphRAG Pipeline (Qwen Only)")
        logger.info(f"Device map: {device_map}")
        logger.info("=" * 60)
        
        # Initialize components
        self.entity_extractor = EntityExtractor()
        self.neo4j = Neo4jManager(self.config)
        self.embedding_gen = EmbeddingGenerator(self.config)
        self.reranker = Reranker(self.config)
        self.retriever = HybridRetriever(
            self.config, self.embedding_gen, self.neo4j, self.reranker
        )
        self.context_builder = ContextBuilder(self.config)
        
        # Initialize answer generator
        self.answer_gen = AnswerGenerator(
            config=self.config,
            model_name=self.config.qwen_model,
            device_map=device_map
        )
        
        logger.info("✓ GraphRAG Pipeline initialized")
        logger.info(f"  Model: {self.config.qwen_model}")
        logger.info("=" * 60)
    
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
        
        # Extract entities
        if is_tf:
            statement = self.entity_extractor.extract_tf_statement(question)
            entities = self.entity_extractor.extract(statement)
        else:
            option_texts = [opt.get("answer", "") for opt in options]
            entities = self.entity_extractor.extract(question, option_texts)
        
        # Hybrid retrieval
        candidates = self.retriever.retrieve(entities, question, top_k=self.config.top_k_retrieval)
        context, provenance = self.context_builder.build_context(candidates, token_budget=5000)
        
        # Generate answer
        if is_tf:
            statement = self.entity_extractor.extract_tf_statement(question)
            source_materials = self.entity_extractor.extract_source_materials(question)
            model_answer, raw_response = self.answer_gen.answer_tf(
                statement, context, source_materials=source_materials
            )
        else:
            option_texts = [opt.get("answer", "") for opt in options]
            model_answer, raw_response = self.answer_gen.answer_mcq(question, option_texts, context)
        
        # Determine correctness
        is_correct = self._compare_answers(model_answer, correct_answer, question_type)
        
        processing_time = time.time() - start_time
        self.metrics.record_query(processing_time)
        
        # Calculate trust score
        scores = [c.get("combined_score", 0) for c in candidates[:3]]
        if isinstance(scores[0] if scores else 0, (list, tuple)):
            scores = [s[0] if s else 0 for s in scores]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        result = {
            "question": question,
            "question_type": question_type,
            "correct_answer": correct_answer,
            "model_answer": model_answer,
            "is_correct": is_correct,
            "raw_response": raw_response,
            "entities_extracted": entities,
            "context_length": len(context),
            "num_candidates": len(candidates),
            "trust_score": round(avg_score, 4),
            "trust_level": "high" if avg_score > 0.7 else "medium" if avg_score > 0.5 else "low",
            "evidence": [
                {
                    "source": p.get("source"),
                    "score": round(p.get("score", 0), 4),
                    "provenance": p.get("provenance"),
                    "text_preview": p.get("text_preview", "")[:200]
                }
                for p in provenance[:10]
            ],
            "processing_time": round(processing_time, 2)
        }
        
        return result
    
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
    
    def run(self, limit: int = None, progress_interval: int = 5) -> Dict:
        """Run evaluation on question dataset."""
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
                    
            except Exception as e:
                logger.error(f"Error on Q{i}: {e}")
                self.metrics.record_error()
            
            if i % progress_interval == 0 or i == total:
                self._print_progress(i, total, stats, start_time)
        
        total_time = time.time() - start_time
        
        output = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "pipeline": "qwen-only",
            "model": self.config.qwen_model,
            "stats": {
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": round(stats["correct"] / stats["total"] * 100, 2) if stats["total"] else 0,
                "mcq": stats["mcq"],
                "mcq_correct": stats["mcq_correct"],
                "mcq_accuracy": round(stats["mcq_correct"] / stats["mcq"] * 100, 2) if stats["mcq"] else 0,
                "tf": stats["tf"],
                "tf_correct": stats["tf_correct"],
                "tf_accuracy": round(stats["tf_correct"] / stats["tf"] * 100, 2) if stats["tf"] else 0,
            },
            "timing": {
                "total_seconds": round(total_time, 2),
                "avg_per_question": round(total_time / stats["total"], 2) if stats["total"] else 0
            },
            "config": {
                "qwen_model": self.config.qwen_model,
                "embedding_model": self.config.embedding_model,
                "reranker_model": self.config.reranker_model,
                "device_map": self.device_map,
            },
            "results": results
        }
        
        with open(self.config.output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to {self.config.output_file}")
        
        return output
    
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


def main():
    config = GraphRAGConfig()
    pipeline = GraphRAGPipeline(config, device_map="auto")
    try:
        results = pipeline.run(limit=None, progress_interval=10)
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
