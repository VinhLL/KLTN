"""Xử lý thực thể: merge, tìm similar, post-process."""

import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
from collections import defaultdict
import config
import utils
from topic_processor import TopicProcessor


def should_skip_entity(entity: Dict, topic_config: Dict) -> bool:
    """Kiểm tra xem entity có thuộc danh sách blacklist không."""
    if not topic_config:
        topic_config = {}
    
    blacklist = topic_config.get('entity_blacklist', [])
    entity_id = entity.get('id', '').lower().strip()
    entity_description = entity.get('description', '').lower()
    entity_type = entity.get('type', '')
    
    # Kiểm tra xem entity có chứa từ blacklist không
    for blacklisted in blacklist:
        if blacklisted.lower() in entity_id or blacklisted.lower() in entity_description:
            return True
    
    # ===== BLACKLIST TOÀN CỤC CHO KHÁI NIỆM/KHẨU HIỆU/CỤM TỪ KHÔNG PHẢI ENTITY =====
    global_blacklist = [
        # Khẩu hiệu, tiêu ngữ, cụm từ chiến lược
        'thắng lợi quân sự', 'vừa đánh, vừa đàm', 'vừa đánh vừa đàm',
        'cuộc chiến tranh phi nghĩa', 'chiến tranh phi nghĩa',
        'kháng nhật, cứu nước', 'kháng nhật cứu nước',
        'đấu tranh ngoại giao', 'thắng lợi quyết định',
        
        # Khái niệm trừu tượng, mô tả chung
        'thống nhất đất nước', 'hội nhập quốc tế', 'giải trừ quân bị',
        'chạy đua vũ trang', 'phát triển kinh tế', 'thương mại quốc tế',
        'xoá đói giảm nghèo', 'hợp tác quốc tế', 'an ninh quốc tế',
        'phát triển bền vững', 'bình đẳng giới', 'chiến tranh nhân dân',
        'cách mạng thế giới', 'cách mạng vô sản thế giới',
        'an ninh nhân dân', 'công cuộc đổi mới', 'hệ thống chính trị',
        'tổ quốc', 'chiến lược', 'chủ trương', 'chính sách',
        
        # Cụm từ mô tả, không phải tên riêng
        'phi mỹ hoá', 'việt nam hoá chiến tranh', 
        'đổi mới toàn diện và đồng bộ', 'đổi mới kinh tế', 'đổi mới chính trị',
        'văn hoá – xã hội', 'văn hoá - xã hội', 'khoa học và công nghệ',
        'giáo dục và đào tạo', 'kinh tế tri thức', 'chế độ tem phiếu',
        
        # Khái niệm chính trị chung
        'kinh tế hàng hoá xã hội chủ nghĩa', 'kinh tế thị trường xã hội chủ nghĩa',
        'kinh tế thị trường định hướng xã hội chủ nghĩa',
        'nhà nước pháp quyền xã hội chủ nghĩa', 'tổ quốc xã hội chủ nghĩa',
        'cách mạng xã hội chủ nghĩa ở miền bắc',
        'cách mạng dân tộc dân chủ nhân dân ở miền nam',
        'cách mạng dân tộc dân chủ nhân dân',
        'sự nghiệp kháng chiến chống mỹ, cứu nước',
        
        # Cụm từ chỉ hoạt động, trạng thái
        'tổng tuyển cử thống nhất đất nước', 'hội nghị hiệp thương',
        'lực lượng yêu nước', 'kháng chiến',
        'các cuộc cách mạng tư sản', 'phong trào giải phóng dân tộc',
        
        # Các cụm từ mô tả tuổi, thời gian, số lượng
        'đảng mới 15 tuổi', 'đảng 15 tuổi',
        
        # Cụm từ quá chung về nhóm người
        'nhân dân tiến bộ trên thế giới', 'nhân dân các nước á, phi mỹ la-tinh',
        'các nước xã hội chủ nghĩa', 'nhân dân mỹ', 'nhân dân việt nam',
        'quân dân việt nam', 'quân dân cam-pu-chia',
        
        # Từ viết tắt đơn lẻ không rõ nghĩa
        'cải tổ', 'hiến chương',
    ]
    
    for blacklisted in global_blacklist:
        if entity_id == blacklisted or entity_id == blacklisted.replace(',', ''):
            return True
    
    # Kiểm tra các entity quá chung chung (chỉ từ đơn)
    general_terms = [
        'chính phủ', 'hội', 'trí tuệ con người', 'nhân dân thế giới',
        'nhân dân', 'thế giới', 'con người', 'trí tuệ', 'phe', 'quân',
        'đế quốc', 'phong kiến', 'chiến tranh', 'kháng chiến', 'cách mạng',
        'đồng minh', 'tổ quốc', 'đất nước', 'dân tộc', 'quốc gia'
    ]

    for term in general_terms:
        if entity_id == term:
            return True

    confusing_entities = [
        'chiến tranh thế giới thứ nhất',
        'chiến tranh thế giới thứ hai',
        'chiến tranh thế giới thứ ba',
        'hội nghị i-an-ta',
        'hội nghị tê-hê-ran',
        'hội nghị xan phran-xi-xcô'
    ]
    
    # Nếu entity có tên gần giống với các entity dễ nhầm, cần xử lý đặc biệt
    for confusing in confusing_entities:
        if confusing in entity_id and entity_type == "Sự kiện":
            # Đây là entity quan trọng, không nên bỏ qua nhưng cần xử lý cẩn thận
            pass
    
    # ===== KIỂM TRA ENTITY LÀ NGÀY/THÁNG/NĂM ĐƠN THUẦN (MỞ RỘNG) =====
    date_patterns = [
        r'^\d{1,2}\s*[-–]\s*\d{1,2}\s*[-–]\s*\d{4}$',  # 2-9-1945
        r'^\d{4}\s*[-–]\s*\d{4}$',  # 1955-1975
        r'^\d{4}$',  # 1945
        r'^tháng\s+\d{1,2}\s*[-–/]\s*\d{4}$',  # tháng 5-1972
        r'^ngày\s+\d{1,2}$',  # ngày 30
        r'^ngày\s+\d{1,2}\s+tháng\s+\d{1,2}$',  # ngày 30 tháng 4
        r'^ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}$',  # ngày 30 tháng 4 năm 1977
        r'^ngày\s+\d{1,2}\s*[-–/]\s*\d{1,2}\s*[-–/]\s*\d{4}$',  # ngày 30-4-1977
        r'^\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}$',  # 30 tháng 4 năm 1977
        r'^năm\s+\d{4}$',  # năm 1945
        r'^tháng\s+\d{1,2}$',  # tháng 5
        r'^đầu\s+năm\s+\d{4}$',  # đầu năm 1945
        r'^cuối\s+năm\s+\d{4}$',  # cuối năm 1945
        r'^giữa\s+năm\s+\d{4}$',  # giữa năm 1945
        r'^\d{1,2}/\d{1,2}/\d{4}$',  # 30/4/1975
        r'^\d{1,2}\s*[–\-]\s*\d{1,2}\s*[–\-]\s*\d{4}$',  # 30 – 4 – 1977 (với dấu cách)
        r'^\d{1,2}\s+[–\-]\s+\d{1,2}\s+[–\-]\s+\d{4}$',  # 5 – 1 – 1978
        r'^tháng\s+\w+\s+năm\s+\d{4}$',  # tháng Tám năm 1945
        r'^mùa\s+\w+\s+năm\s+\d{4}$',  # mùa thu năm 1945
        r'^xuân\s+\d{4}$',  # xuân 1975
        r'^hè\s+\d{4}$',  # hè 1954
        r'^thu\s+\d{4}$',  # thu 1950
        r'^đông\s+\d{4}$',  # đông 1953
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, entity_id, re.IGNORECASE):
            return True
    
    # Kiểm tra entity có dạng toàn số + dấu gạch
    if re.match(r'^[\d\s\-–]+$', entity_id):
        return True
    
    # Kiểm tra entity quá ngắn và không phải tên riêng
    if len(entity_id) < 3:
        return True
    
    # Kiểm tra entity chỉ là từ đơn và quá chung
    words = entity_id.split()
    if len(words) == 1 and len(entity_id) < 6:
        common_words = ['hội', 'phe', 'quân', 'ngày', 'năm', 'tháng', 'đảng']
        if entity_id in common_words:
            return True
    
    # Đặc biệt cho chủ đề Hồ Chí Minh: bỏ qua các từ chỉ cảm xúc, đánh giá chung
    if "HỒ CHÍ MINH" in str(topic_config):
        emotional_words = ['vĩ đại', 'thiêng liêng', 'bất tử', 'vĩnh cửu', 'thiên tài']
        for word in emotional_words:
            if word in entity_id or word in entity_description:
                return True
    
    # Kiểm tra entity type không ưu tiên - BỎ KIỂM TRA NÀY vì quá nghiêm ngặt
    # priority_types = topic_config.get('priority_entities', [])
    # if priority_types and entity_type not in priority_types:
    #     return len(entity_id.split()) < 2  # Logic này bỏ qua quá nhiều entity hợp lệ
    
    return False


def validate_entity_type_for_topic(entity_type: str, topic_config: Dict) -> str:
    """Validate entity type với ưu tiên của chủ đề."""
    if entity_type in config.VALID_ENTITY_TYPES:
        return entity_type
    
    # Mapping đặc thù cho các chủ đề
    type_mapping = {
        "Tổ chức quốc tế": "Tổ chức",
        "Hội nghị quốc tế": "Hội nghị",
        "Hiệp ước": "Văn kiện/Hiệp định",
        "Văn bản quốc tế": "Văn kiện/Hiệp định",
        "Nhân vật lịch sử": "Nhân Vật",
        "Cường quốc": "Quốc gia",
        "Sự kiện lịch sử": "Sự kiện",
        "Chiến tranh": "Sự kiện",
        "Địa danh": "Địa điểm",
        "Văn kiện": "Văn kiện/Hiệp định",
        "Chiến dịch": "Chiến dịch/Trận đánh",
        "Trận đánh": "Chiến dịch/Trận đánh",
        "Chủ trương": "Chiến lược/Chủ trương"
    }
    
    return type_mapping.get(entity_type, "Khái niệm")


def find_similar_entity(new_entity: Dict, existing_entities: List[Dict]) -> Optional[Dict]:
    """Find similar entity in existing entities with improved deduplication.
    
    IMPORTANT: This function will NOT merge entities with different ordinal numbers
    (e.g., "Đại hội VI" and "Đại hội VII" are DIFFERENT entities).
    """
    new_id = new_entity['id'].lower()
    new_type = new_entity['type']
    
    # Rule 1: Check for exact ID and type match (case-insensitive)
    for existing in existing_entities:
        if existing['id'].lower() == new_id and existing['type'] == new_type:
            return existing
    
    # ===== HELPER FUNCTION: Trích xuất số thứ tự từ tên entity =====
    def extract_ordinal(name: str) -> Optional[str]:
        """Trích xuất số thứ tự (La Mã hoặc chữ số) từ tên entity."""
        name_lower = name.lower()
        
        # Pattern cho số La Mã (đứng độc lập hoặc sau "lần thứ", "thứ")
        roman_patterns = [
            r'\blần\s+thứ\s+(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',
            r'\bthứ\s+(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',
            r'\b(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b(?!\w)',
        ]
        
        for pattern in roman_patterns:
            match = re.search(pattern, name_lower)
            if match:
                return match.group(1) if match.lastindex else match.group(0)
        
        # Pattern cho số thứ tự tiếng Việt
        vn_ordinal_match = re.search(r'thứ\s+(nhất|hai|ba|tư|năm|sáu|bảy|tám|chín|mười|mười\s+một|mười\s+hai)', name_lower)
        if vn_ordinal_match:
            return vn_ordinal_match.group(1)
        
        # Pattern cho số (15, 21, etc.) - match nhiều trường hợp hơn
        num_patterns = [
            r'\blần\s+thứ\s+(\d+)\b',    # lần thứ 15
            r'\bsố\s+(\d+)\b',            # số 15
            r'\bthứ\s+(\d+)\b',           # thứ 15
            r'\s(\d+)\s*$',               # đứng cuối chuỗi
        ]
        
        for pattern in num_patterns:
            num_match = re.search(pattern, name_lower)
            if num_match:
                return num_match.group(1)
        
        return None
    
    # Helper: kiểm tra xem entity có chứa ordinal keyword không
    def has_ordinal_keyword(name: str) -> bool:
        """Kiểm tra xem tên entity có chứa từ khóa liên quan đến số thứ tự không."""
        ordinal_keywords = [
            'đại hội', 'hội nghị', 'chiến tranh thế giới', 'kế hoạch', 
            'quốc hội', 'hội nghị ban chấp hành', 'khoá', 'khóa',
            'lần thứ', 'thứ nhất', 'thứ hai', 'thứ ba', 'thứ tư', 'chỉ thị'
        ]
        name_lower = name.lower()
        return any(kw in name_lower for kw in ordinal_keywords)
    
    # ===== KIỂM TRA ĐẶC BIỆT: KHÔNG merge các entity có số thứ tự khác nhau =====
    new_ordinal = extract_ordinal(new_id)
    new_has_ordinal_keyword = has_ordinal_keyword(new_id)
    
    for existing in existing_entities:
        if existing['type'] != new_type:
            continue
        
        existing_id_lower = existing['id'].lower()
        existing_ordinal = extract_ordinal(existing_id_lower)
        existing_has_ordinal_keyword = has_ordinal_keyword(existing_id_lower)
        
        # Nếu cả hai entity đều có ordinal keyword
        if new_has_ordinal_keyword and existing_has_ordinal_keyword:
            # Nếu cùng có số thứ tự và khác nhau => KHÔNG bao giờ merge
            if new_ordinal and existing_ordinal and new_ordinal != existing_ordinal:
                continue  # Skip this existing entity, don't merge
            
            # Nếu cùng số thứ tự => có thể merge
            if new_ordinal and existing_ordinal and new_ordinal == existing_ordinal:
                # Kiểm tra thêm xem base name có giống nhau không
                # (ví dụ: "Đại hội VI" và "Đại hội đại biểu lần thứ VI" có thể merge)
                similarity = SequenceMatcher(None, new_id, existing_id_lower).ratio()
                if similarity > 0.6:  # Ngưỡng thấp vì đã match ordinal
                    return existing
    
    # Rule 2: Check for entities that are too similar (tăng ngưỡng lên cao)
    similarity_threshold = 0.92  # Tăng từ 0.9 lên 0.92 để chặt chẽ hơn
    
    for existing in existing_entities:
        if existing['type'] != new_type:
            continue
        
        existing_id_lower = existing['id'].lower()
        
        # Bỏ qua các entity có ordinal keyword khác nhau (đã xử lý ở trên)
        if has_ordinal_keyword(new_id) or has_ordinal_keyword(existing_id_lower):
            new_ord = extract_ordinal(new_id)
            existing_ord = extract_ordinal(existing_id_lower)
            if new_ord and existing_ord and new_ord != existing_ord:
                continue  # KHÔNG merge
            
        # Đặc biệt với các entity quan trọng như sự kiện lịch sử, chiến dịch
        # KHÔNG merge nếu tên khác nhau rõ ràng
        if new_type in ["Sự kiện", "Chiến dịch/Trận đánh", "Hội nghị"]:
            # Kiểm tra xem có phải là cùng một loại sự kiện không
            new_words = set(new_id.split())
            existing_words = set(existing_id_lower.split())
            common_words = new_words.intersection(existing_words)
            
            # Nếu chỉ có 1-2 từ chung và nhiều từ khác nhau => có thể là khác
            if len(common_words) <= 2 and (len(new_words) > 2 or len(existing_words) > 2):
                similarity = SequenceMatcher(None, new_id, existing_id_lower).ratio()
                if similarity < 0.95:  # Ngưỡng rất cao cho sự kiện
                    continue  # Không merge
        
        # Check similarity between IDs
        id_similarity = SequenceMatcher(None, new_id, existing_id_lower).ratio()
        
        # Check similarity between labels
        label_similarity = 0
        for new_label in new_entity.get('label', []):
            for existing_label in existing.get('label', []):
                similarity = SequenceMatcher(None, new_label.lower(), existing_label.lower()).ratio()
                label_similarity = max(label_similarity, similarity)
        
        if id_similarity > similarity_threshold or label_similarity > similarity_threshold:
            return existing
    
    # Rule 3: Check for entities with same base name but different qualifiers
    # Remove common qualifiers for comparison
    def normalize_name(name: str) -> str:
        # Remove common prefixes/suffixes
        name = name.lower()
        # Remove parenthetical content
        name = re.sub(r'\([^)]*\)', '', name)
        # Remove common qualifiers
        qualifiers = [
            'thế giới', 'hai cực', 'trật tự', 'cộng hoà', 'dân chủ',
            'xã hội chủ nghĩa', 'chủ nghĩa', 'liên bang'
        ]
        for qualifier in qualifiers:
            name = name.replace(qualifier, '')
        # Remove extra spaces
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    new_normalized = normalize_name(new_id)
    for existing in existing_entities:
        if existing['type'] != new_type:
            continue
            
        existing_normalized = normalize_name(existing['id'].lower())
        if new_normalized == existing_normalized and len(new_normalized) > 3:
            # KIỂM TRA BỔ SUNG: Nếu là sự kiện lịch sử quan trọng, cần cẩn thận
            if new_type in ["Sự kiện", "Chiến dịch/Trận đánh"]:
                # Kiểm tra xem có phải là cùng một sự kiện không
                new_words = new_id.split()
                existing_words = existing['id'].lower().split()
                if len(set(new_words).intersection(set(existing_words))) >= 2:
                    return existing
            else:
                return existing
    
    return None

def normalize_entity(entity: Dict) -> Dict:
    """Chuẩn hóa entity để xử lý trùng lặp."""
    entity_id = entity.get('id', '')
    
    # Chuẩn hóa dấu gạch ngang
    entity_id = re.sub(r'[–—]', '-', entity_id)
    
    # Chuẩn hóa khoảng trắng
    entity_id = re.sub(r'\s+', ' ', entity_id).strip()
    
    # Chuẩn hóa viết hoa cho tên riêng
    if entity.get('type') in ['Nhân Vật', 'Tổ chức', 'Quốc gia', 'Địa điểm']:
        # Giữ nguyên cách viết hoa đặc biệt, chỉ chuẩn hóa khoảng trắng
        pass
    
    entity['id'] = entity_id
    return entity


def merge_entities(existing: Dict, new: Dict) -> bool:
    """Merge two entities with strict rules to avoid incorrect merging."""
    
    # ===== HELPER FUNCTION: Trích xuất số thứ tự =====
    def extract_ordinal_for_merge(name: str) -> Optional[str]:
        """Trích xuất số thứ tự từ tên để so sánh.
        
        Supports:
        - Roman numerals: VI, VII, VIII, etc.
        - Vietnamese ordinals: thứ nhất, thứ hai, etc.
        - Arabic numerals: 15, 21, etc.
        """
        name_lower = name.lower()
        
        # Số La Mã - pattern chính xác hơn
        # Tìm theo thứ tự ưu tiên: sau "lần thứ", sau "thứ", hoặc đứng độc lập cuối chuỗi
        roman_patterns = [
            r'lần\s+thứ\s+(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',
            r'\bthứ\s+(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',
            r'\s(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\s*$',  # Đứng cuối
            r'\b(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{0,3}|xiv|xv|xvi{0,3})\b',  # Fallback
        ]
        
        for pattern in roman_patterns:
            match = re.search(pattern, name_lower)
            if match:
                return match.group(1).strip()
        
        # Số thứ tự tiếng Việt
        vn_match = re.search(r'thứ\s+(nhất|hai|ba|tư|năm|sáu|bảy|tám|chín|mười)', name_lower)
        if vn_match:
            return vn_match.group(1)
        
        # Số thường - chỉ match khi đứng cuối hoặc sau "lần thứ"
        num_match = re.search(r'lần\s+thứ\s+(\d+)\b|\s(\d+)\s*$', name_lower)
        if num_match:
            return num_match.group(1) or num_match.group(2)
        
        return None
    
    # ===== KIỂM TRA ĐẶC BIỆT: Không merge các Đại hội/Hội nghị có số thứ tự khác nhau =====
    ordinal_keywords = ['đại hội', 'hội nghị', 'quốc hội', 'khoá', 'khóa', 'lần thứ', 'chỉ thị']
    
    existing_id_lower = existing['id'].lower()
    new_id_lower = new['id'].lower()
    
    # Kiểm tra xem cả hai có chứa ordinal keyword không
    existing_has_keyword = any(kw in existing_id_lower for kw in ordinal_keywords)
    new_has_keyword = any(kw in new_id_lower for kw in ordinal_keywords)
    
    if existing_has_keyword and new_has_keyword:
        existing_ordinal = extract_ordinal_for_merge(existing['id'])
        new_ordinal = extract_ordinal_for_merge(new['id'])
        
        if existing_ordinal and new_ordinal and existing_ordinal != new_ordinal:
            # Số thứ tự khác nhau => TUYỆT ĐỐI KHÔNG merge
            return False
    
    # Kiểm tra xem có thực sự giống nhau không
    if existing['id'] != new['id']:
        # KIỂM TRA ĐẶC BIỆT: Không merge các sự kiện lịch sử quan trọng nếu tên khác nhau
        if existing['type'] in ["Sự kiện", "Chiến dịch/Trận đánh", "Hội nghị"]:
            # Kiểm tra các từ khóa quan trọng
            important_keywords = [
                'chiến tranh thế giới', 'hội nghị', 'hiệp định', 
                'chiến dịch', 'trận', 'đại hội'
            ]
            
            for keyword in important_keywords:
                if keyword in existing['id'].lower() and keyword in new['id'].lower():
                    # Nếu cùng chứa từ khóa quan trọng, kiểm tra kỹ hơn
                    existing_words = set(existing['id'].lower().split())
                    new_words = set(new['id'].lower().split())
                    common_words = existing_words.intersection(new_words)
                    
                    # Nếu ít từ chung và nhiều từ khác nhau => có thể là khác
                    if len(common_words) <= 2 and (len(existing_words) > 3 or len(new_words) > 3):
                        similarity = SequenceMatcher(None, existing['id'].lower(), new['id'].lower()).ratio()
                        if similarity < 0.85:  # Ngưỡng thấp hơn để KHÔNG merge
                            return False
        
        # Kiểm tra độ tương đồng
        similarity = SequenceMatcher(None, existing['id'].lower(), new['id'].lower()).ratio()
        if similarity < 0.85:  # Tăng ngưỡng từ 0.8 lên 0.85 để chặt chẽ hơn
            return False
    
    # Kiểm tra type có giống nhau không
    if existing['type'] != new['type']:
        return False
    
    # THÊM: Không merge các entity có mô tả hoàn toàn khác nhau
    existing_desc = existing.get('description', '').lower()
    new_desc = new.get('description', '').lower()
    if existing_desc and new_desc:
        # Kiểm tra xem mô tả có tương đồng không
        desc_similarity = SequenceMatcher(None, existing_desc, new_desc).ratio()
        if desc_similarity < 0.5 and len(existing_desc) > 10 and len(new_desc) > 10:
            # Mô tả quá khác nhau => có thể là entity khác
            return False
    
    # ===== MERGE LABELS VỚI LOGIC CẢI TIẾN =====
    # Ưu tiên giữ label viết hoa đầu câu, loại bỏ duplicate chỉ khác case
    merged_labels = []
    seen_lower = set()
    
    # Helper: chọn label tốt nhất giữa hai label chỉ khác case
    def choose_best_label(label1: str, label2: str) -> str:
        """Chọn label tốt hơn (ưu tiên viết hoa đầu câu)."""
        # Ưu tiên label bắt đầu bằng chữ hoa
        if label1[0].isupper() and not label2[0].isupper():
            return label1
        if label2[0].isupper() and not label1[0].isupper():
            return label2
        # Nếu cả hai đều hoa hoặc đều thường, ưu tiên label ngắn hơn
        return label1 if len(label1) <= len(label2) else label2
    
    # Tạo dict để track label tốt nhất cho mỗi lowercase version
    best_labels = {}
    
    for label in existing['label'] + new['label']:
        label_lower = label.lower()
        if label_lower in best_labels:
            best_labels[label_lower] = choose_best_label(best_labels[label_lower], label)
        else:
            best_labels[label_lower] = label
    
    # Chuyển về list, ưu tiên label của existing entity
    for label in existing['label']:
        label_lower = label.lower()
        if label_lower not in seen_lower:
            seen_lower.add(label_lower)
            merged_labels.append(best_labels[label_lower])
    
    for label in new['label']:
        label_lower = label.lower()
        if label_lower not in seen_lower:
            seen_lower.add(label_lower)
            merged_labels.append(best_labels[label_lower])
    
    existing['label'] = merged_labels
    
    # Merge original_text without duplicates
    existing_texts = {(occ['topic'], occ['lesson'], occ['exact_text']) 
                     for occ in existing['original_text']}
    
    for new_occ in new['original_text']:
        key = (new_occ['topic'], new_occ['lesson'], new_occ['exact_text'])
        if key not in existing_texts:
            existing['original_text'].append(new_occ)
            existing_texts.add(key)
    
    existing['occurrence_count'] = len(existing['original_text'])
    
    # Merge window indices
    existing['window_indices'] = list(set(existing['window_indices'] + new['window_indices']))
    
    # Merge metadata
    merge_metadata(existing['metadata'], new['metadata'])
    
    # Merge properties (cẩn thận với các property quan trọng)
    for key, value in new.get('properties', {}).items():
        if key not in existing['properties']:
            existing['properties'][key] = value
        elif isinstance(existing['properties'][key], list) and isinstance(value, list):
            # Tránh trùng lặp trong list
            existing_set = set(str(item) for item in existing['properties'][key])
            new_set = set(str(item) for item in value)
            merged_list = list(existing_set.union(new_set))
            existing['properties'][key] = merged_list
    
    existing['confidence'] = max(existing['confidence'], new['confidence'])
    
    return True


def merge_metadata(existing_metadata: Dict, new_metadata: Dict) -> None:
    """Merge metadata from two entities."""
    # Merge window indices
    existing_metadata['window_indices'] = list(set(
        existing_metadata.get('window_indices', []) + 
        new_metadata.get('window_indices', [])
    ))
    
    # Merge timeline events without duplicates
    existing_events = existing_metadata.get('timeline_events', [])
    new_events = new_metadata.get('timeline_events', [])
    
    existing_event_keys = set()
    for event in existing_events:
        key = (event.get('sentence', ''), tuple(event.get('dates', [])), tuple(event.get('years', [])))
        existing_event_keys.add(key)
    
    for event in new_events:
        key = (event.get('sentence', ''), tuple(event.get('dates', [])), tuple(event.get('years', [])))
        if key not in existing_event_keys:
            existing_events.append(event)
            existing_event_keys.add(key)
    
    existing_metadata['timeline_events'] = existing_events


def post_process_entities(entities: List[Dict]) -> List[Dict]:
    """Post-process entities to fix issues and ensure quality."""
    processed = []
    
    for entity in entities:
        # Clean entity ID
        entity['id'] = entity['id'].strip()
        
        # Clean labels
        entity['label'] = utils.clean_labels(entity['label'])
        
        # Ensure ID is in labels
        if entity['id'] not in entity['label']:
            entity['label'].insert(0, entity['id'])
        
        # Remove duplicate occurrences in original_text
        unique_occurrences = []
        seen_occurrences = set()
        
        for occ in entity['original_text']:
            key = (occ['topic'], occ['lesson'], occ['exact_text'])
            if key not in seen_occurrences:
                seen_occurrences.add(key)
                unique_occurrences.append(occ)
        
        entity['original_text'] = unique_occurrences
        entity['occurrence_count'] = len(unique_occurrences)
        
        # Simplify metadata further
        entity['metadata'] = simplify_metadata(entity['metadata'])
        
        processed.append(entity)
    
    return processed


def simplify_metadata(metadata: Dict) -> Dict:
    """Simplify metadata to remove unnecessary fields with better duplicate handling."""
    simplified = {
        'topic': metadata.get('topic', ''),
        'lesson': metadata.get('lesson', ''),
        'window_indices': metadata.get('window_indices', []),
        'timeline_events': metadata.get('timeline_events', [])
    }
    
    # Group timeline events by date/year with de-duplication
    timeline_summary = {}
    
    for event in simplified['timeline_events']:
        # Clean the sentence text
        sentence = event.get('sentence', '').strip()
        if not sentence:
            continue
        
        # For each date in the event
        for date in event.get('dates', []):
            if date not in timeline_summary:
                timeline_summary[date] = []
            
            # Check if similar sentence already exists for this date
            # Use string similarity to avoid exact duplicates
            is_duplicate = False
            for existing_sentence in timeline_summary[date]:
                similarity = SequenceMatcher(None, sentence, existing_sentence).ratio()
                if similarity > config.TIMELINE_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                timeline_summary[date].append(sentence)
        
        # For each year in the event
        for year in event.get('years', []):
            if year not in timeline_summary:
                timeline_summary[year] = []
            
            # Check if similar sentence already exists for this year
            is_duplicate = False
            for existing_sentence in timeline_summary[year]:
                similarity = SequenceMatcher(None, sentence, existing_sentence).ratio()
                if similarity > config.TIMELINE_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                timeline_summary[year].append(sentence)
    
    # Limit the number of sentences per date/year to avoid too much repetition
    for key in list(timeline_summary.keys()):
        # Remove empty entries
        if not timeline_summary[key]:
            del timeline_summary[key]
            continue
        
        # Remove exact duplicates (case-insensitive)
        unique_sentences = []
        seen_sentences = set()
        
        for sentence in timeline_summary[key]:
            # Normalize sentence for comparison
            normalized = sentence.lower().strip()
            if normalized not in seen_sentences:
                seen_sentences.add(normalized)
                unique_sentences.append(sentence)
        
        # Keep only first 3 unique sentences per date/year
        timeline_summary[key] = unique_sentences[:config.MAX_SENTENCES_PER_DATE]
    
    # Also filter out very similar sentences across different dates/years
    # by checking if a sentence appears in multiple places
    if timeline_summary:
        # Create a mapping of sentence to all its dates/years
        sentence_to_dates = defaultdict(list)
        for date_year, sentences in timeline_summary.items():
            for sentence in sentences:
                sentence_to_dates[sentence].append(date_year)
        
        # If a sentence appears in too many places, keep it only in the most relevant
        for sentence, dates in list(sentence_to_dates.items()):
            if len(dates) > 3:  # If appears in more than 3 dates/years
                # Remove from all but keep in the first occurrence
                for date in dates[3:]:
                    if date in timeline_summary and sentence in timeline_summary[date]:
                        timeline_summary[date].remove(sentence)
                        # If this date has no more sentences, remove it
                        if not timeline_summary[date]:
                            del timeline_summary[date]
    
    simplified['timeline_summary'] = timeline_summary
    
    return simplified


def apply_topic_specific_rules(entity: Dict, topic: str, topic_config: Dict) -> Dict:
    """Áp dụng rules đặc thù theo chủ đề."""
    if "HỒ CHÍ MINH" in topic:
        return apply_ho_chi_minh_rules(entity, topic_config)
    elif "CÔNG CUỘC ĐỔI MỚI" in topic:
        return apply_doi_moi_rules(entity, topic_config)
    elif "LỊCH SỬ ĐỐI NGOẠI" in topic:
        return apply_doi_ngoai_rules(entity, topic_config)
    elif "CÁCH MẠNG THÁNG TÁM" in topic or "CHIẾN TRANH GIẢI PHÓNG" in topic:
        return apply_vietnam_war_rules(entity, topic_config)
    elif "ASEAN" in topic:
        return apply_asean_specific_rules(entity, topic_config)
    return entity


def apply_ho_chi_minh_rules(entity: Dict, topic_config: Dict) -> Dict:
    """Áp dụng rules đặc thù cho các entity liên quan đến Hồ Chí Minh."""
    entity_id = entity.get('id', '')
    entity_type = entity.get('type', '')
    
    # Xử lý các tên gọi của Hồ Chí Minh
    ho_chi_minh_names = topic_config.get('ho_chi_minh_names', [])
    if entity_id in ho_chi_minh_names and entity_type == "Nhân Vật":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm thông tin về thời kỳ sử dụng tên
        name_periods = {
            'Nguyễn Sinh Cung': '1890-1901 (tên khai sinh)',
            'Nguyễn Tất Thành': '1901-1911 (thời niên thiếu)',
            'Văn Ba': '1911 (trên tàu La-tu-sơ Tơ-rê-vin)',
            'Nguyễn Ái Quốc': '1919-1942 (thời kỳ hoạt động ở nước ngoài)',
            'Hồ Chí Minh': '1942-1969',
            'Bác Hồ': 'Cách gọi thân thương của nhân dân'
        }
        
        if entity_id in name_periods:
            entity['properties']['thời_kỳ_sử_dụng_tên'] = [name_periods[entity_id]]
            
            # Đảm bảo tất cả các tên đều có description liên kết với Hồ Chí Minh
            if not entity.get('description'):
                entity['description'] = f"Một trong những tên gọi của Chủ tịch Hồ Chí Minh"
    
    # Xử lý các thành viên gia đình
    family_members = topic_config.get('family_members', [])
    if entity_id in family_members and entity_type == "Nhân Vật":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm quan hệ với Hồ Chí Minh
        relationships = {
            'Nguyễn Sinh Sắc': 'Cha của Hồ Chí Minh',
            'Hoàng Thị Loan': 'Mẹ của Hồ Chí Minh',
            'Nguyễn Sinh Khiêm': 'Anh trai của Hồ Chí Minh',
            'Nguyễn Thị Thanh': 'Chị gái của Hồ Chí Minh'
        }
        
        if entity_id in relationships:
            entity['properties']['quan_hệ_với_HCM'] = [relationships[entity_id]]
    
    # Xử lý các tổ chức do Hồ Chí Minh sáng lập
    organizations_founded = topic_config.get('organizations_founded', [])
    if entity_id in organizations_founded and entity_type == "Tổ chức":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm năm thành lập và vai trò của Hồ Chí Minh
        founding_info = {
            'Đảng Cộng sản Việt Nam': {'năm': '1930', 'vai_trò': 'Người sáng lập'},
            'Việt Minh': {'năm': '1941', 'vai_trò': 'Người sáng lập'},
            'Hội Việt Nam Cách mạng Thanh niên': {'năm': '1925', 'vai_trò': 'Người sáng lập'},
            'Hội Liên hiệp thuộc địa': {'năm': '1921', 'vai_trò': 'Người sáng lập'},
            'Đội Việt Nam Tuyên truyền Giải phóng quân': {'năm': '1944', 'vai_trò': 'Người chỉ thị thành lập'}
        }
        
        if entity_id in founding_info:
            entity['properties']['năm_thành_lập'] = [founding_info[entity_id]['năm']]
            entity['properties']['vai_trò_HCM'] = [founding_info[entity_id]['vai_trò']]
    
    # Xử lý các văn kiện của Hồ Chí Minh
    key_documents_hcm = topic_config.get('key_documents_hcm', [])
    if entity_id in key_documents_hcm and entity_type == "Văn kiện/Hiệp định":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm năm soạn thảo
        document_years = {
            'Tuyên ngôn Độc lập': '1945',
            'Chính cương vắn tắt': '1930',
            'Sách lược vắn tắt': '1930',
            'Di chúc': '1969',
            'Lời kêu gọi toàn quốc kháng chiến': '1946',
            'Yêu sách của nhân dân An Nam': '1919'
        }
        
        if entity_id in document_years:
            entity['properties']['năm_soạn_thảo'] = [document_years[entity_id]]
            entity['properties']['tác_giả'] = ['Hồ Chí Minh']
    
    return entity


def apply_doi_moi_rules(entity: Dict, topic_config: Dict) -> Dict:
    """Áp dụng rules đặc thù cho các entity Đổi mới."""
    entity_id = entity.get('id', '')
    entity_type = entity.get('type', '')
    
    # Xử lý các từ viết tắt kinh tế
    if entity_id in topic_config.get('acronyms', {}):
        full_name = topic_config['acronyms'][entity_id]
        if 'label' not in entity:
            entity['label'] = []
        if full_name not in entity['label']:
            entity['label'].append(full_name)
        
        if not entity.get('description'):
            entity['description'] = f"{full_name} - trong công cuộc Đổi mới"
    
    # Xử lý các chính sách kinh tế
    key_policies = topic_config.get('key_policies', [])
    if entity_id in key_policies and entity_type == "Chiến lược/Chủ trương":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm thông tin về thời điểm
        policy_years = {
            'Đổi mới': '1986',
            'Kinh tế thị trường định hướng XHCN': '1986',
            'Công nghiệp hoá, Hiện đại hoá': '1996',
            'Hội nhập quốc tế': '1995'
        }
        
        if entity_id in policy_years:
            entity['properties']['năm_ban_hành'] = [policy_years[entity_id]]
    
    # Xử lý các tổ chức quốc tế
    international_orgs = topic_config.get('international_organizations', [])
    if entity_id in international_orgs and entity_type == "Tổ chức":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm năm Việt Nam tham gia
        join_years = {
            'WTO': '2007',
            'ASEAN': '1995',
            'APEC': '1998',
            'Liên hợp quốc': '1977',
            'SEV': '1978'
        }
        
        if entity_id in join_years:
            entity['properties']['năm_VN_tham_gia'] = [join_years[entity_id]]
    
    return entity


def apply_doi_ngoai_rules(entity: Dict, topic_config: Dict) -> Dict:
    """Áp dụng rules đặc thù cho các entity Đối ngoại."""
    entity_id = entity.get('id', '')
    entity_type = entity.get('type', '')
    
    # Xử lý các từ viết tắt ngoại giao
    if entity_id in topic_config.get('acronyms', {}):
        full_name = topic_config['acronyms'][entity_id]
        if 'label' not in entity:
            entity['label'] = []
        if full_name not in entity['label']:
            entity['label'].append(full_name)
        
        if not entity.get('description'):
            entity['description'] = f"{full_name} - trong lịch sử đối ngoại Việt Nam"
    
    # Xử lý các nhân vật đối ngoại
    diplomatic_figures = topic_config.get('diplomatic_figures', [])
    if entity_id in diplomatic_figures and entity_type == "Nhân Vật":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm vai trò đối ngoại
        roles = {
            'Phan Bội Châu': 'Nhà yêu nước, hoạt động ở Nhật Bản, Trung Quốc',
            'Phan Châu Trinh': 'Nhà yêu nước, hoạt động ở Pháp',
            'Nguyễn Ái Quốc': 'Nhà cách mạng, hoạt động quốc tế',
            'Hồ Chí Minh': 'Chủ tịch nước, nhà ngoại giao'
        }
        
        if entity_id in roles:
            entity['properties']['vai_trò_đối_ngoại'] = [roles[entity_id]]
    
    # Xử lý các hiệp định ngoại giao
    diplomatic_docs = topic_config.get('diplomatic_documents', [])
    if entity_id in diplomatic_docs and entity_type == "Văn kiện/Hiệp định":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm năm ký kết
        doc_years = {
            'Hiệp định Sơ bộ': '1946',
            'Tạm ước Việt - Pháp': '1946',
            'Hiệp định Giơ-ne-vơ': '1954',
            'Hiệp định Pa-ri': '1973'
        }
        
        if entity_id in doc_years:
            entity['properties']['năm_ký_kết'] = [doc_years[entity_id]]
    
    return entity


def apply_vietnam_war_rules(entity: Dict, topic_config: Dict) -> Dict:
    """Áp dụng rules đặc thù cho các entity lịch sử quân sự Việt Nam."""
    entity_id = entity.get('id', '')
    entity_type = entity.get('type', '')
    
    # Xử lý các từ viết tắt quân sự
    if entity_id in topic_config.get('acronyms', {}):
        full_name = topic_config['acronyms'][entity_id]
        if 'label' not in entity:
            entity['label'] = []
        if full_name not in entity['label']:
            entity['label'].append(full_name)
        
        if not entity.get('description'):
            entity['description'] = f"{full_name} - trong lịch sử quân sự Việt Nam"
    
    # Xử lý các chiến dịch quân sự
    military_campaigns = topic_config.get('military_campaigns', [])
    if entity_id in military_campaigns and entity_type == "Chiến dịch/Trận đánh":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm thông tin về giai đoạn
        if "Điện Biên" in entity_id:
            entity['properties']['giai_đoạn'] = ['Kháng chiến chống Pháp (1945-1954)']
        elif any(x in entity_id for x in ['Tây Nguyên', 'Huế', 'Hồ Chí Minh', 'Mậu Thân']):
            entity['properties']['giai_đoạn'] = ['Kháng chiến chống Mỹ (1954-1975)']
        elif "Vị Xuyên" in entity_id or "biên giới" in entity_id.lower():
            entity['properties']['giai_đoạn'] = ['Bảo vệ biên giới (1975-1989)']
    
    # Xử lý các nhân vật lịch sử
    historical_figures = topic_config.get('historical_figures', [])
    if entity_id in historical_figures and entity_type == "Nhân Vật":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm vai trò
        roles = {
            'Hồ Chí Minh': 'Chủ tịch nước, lãnh đạo tối cao',
            'Võ Nguyên Giáp': 'Đại tướng, Tổng Tư lệnh',
            'Ngô Đình Diệm': 'Tổng thống Việt Nam Cộng hòa',
            'Nguyễn Thị Định': 'Nữ tướng, lãnh đạo Đồng khởi',
            'Pôn Pốt': 'Lãnh đạo Cam-pu-chia Dân chủ'
        }
        
        if entity_id in roles:
            entity['properties']['vai_trò'] = [roles[entity_id]]
    
    # Xử lý các văn kiện
    key_documents = topic_config.get('key_documents', [])
    if entity_id in key_documents and entity_type == "Văn kiện/Hiệp định":
        if 'properties' not in entity:
            entity['properties'] = {}
        
        # Thêm năm ký kết
        document_years = {
            'Tuyên ngôn Độc lập': '1945',
            'Hiệp định Giơ-ne-vơ': '1954',
            'Hiệp định Pa-ri': '1973',
            'Luật Biển Việt Nam': '2012',
            'Tuyên bố về lãnh hải': '1977'
        }
        
        if entity_id in document_years:
            entity['properties']['năm_ký_kết'] = [document_years[entity_id]]
    
    return entity


def apply_asean_specific_rules(entity: Dict, topic_config: Dict) -> Dict:
    """Áp dụng rules đặc thù cho các entity ASEAN."""
    entity_id = entity.get('id', '')
    
    # Xử lý các từ viết tắt ASEAN
    if entity_id in topic_config.get('acronyms', {}):
        full_name = topic_config['acronyms'][entity_id]
        # Thêm tên đầy đủ vào labels
        if 'label' not in entity:
            entity['label'] = []
        if full_name not in entity['label']:
            entity['label'].append(full_name)
        
        # Cập nhật description nếu chưa có
        if not entity.get('description'):
            entity['description'] = f"{full_name} - một tổ chức/thành phần của ASEAN"
    
    # Xử lý các nước thành viên ASEAN
    member_countries = topic_config.get('member_countries', [])
    if entity_id in member_countries and entity.get('type') == 'Quốc gia':
        # Thêm thông tin về tư cách thành viên ASEAN
        if 'properties' not in entity:
            entity['properties'] = {}
        
        entity['properties']['tư_cách_ASEAN'] = ['thành viên']
        
        # Xác định năm gia nhập nếu có thể
        join_years = {
            'Việt Nam': '1995',
            'Lào': '1997',
            'Myanmar': '1997',
            'Campuchia': '1999',
            'Brunei': '1984'
        }
        
        if entity_id in join_years:
            entity['properties']['năm_gia_nhập_ASEAN'] = [join_years[entity_id]]
    
    return entity


def enhance_properties_for_topic(entity: Dict, text: str, topic_config: Dict) -> Dict:
    """Tăng cường properties với thông tin đặc thù của chủ đề."""
    properties = entity.get('properties', {})
    
    # Trích xuất ngày tháng từ text
    date_patterns = [
        r'ngày\s+(\d{1,2}\s*[–\-]\s*\d{1,2}\s*[–\-]\s*\d{4})',
        r'ngày\s+(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})',
        r'(\d{1,2}\s*[–\-]\s*\d{1,2}\s*[–\-]\s*\d{4})',
        r'tháng\s+(\d{1,2})\s*năm\s*(\d{4})',
        r'năm\s+(\d{4})',
        r'(\d{4})\s*[–\-]\s*(\d{4})'  # Khoảng thời gian
    ]
    
    all_dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                if len(match) == 3:
                    date_str = f"{match[0]}-{match[1]}-{match[2]}"
                elif len(match) == 2:
                    date_str = f"{match[0]}-{match[1]}"
                else:
                    continue
            else:
                date_str = match
            
            # Chỉ lấy các năm từ 1960 trở đi (phù hợp với ASEAN)
            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                year = int(year_match.group(1))
                if year >= 1960:  # ASEAN thành lập 1967
                    all_dates.append(date_str)
    
    if all_dates:
        properties['các_mốc_thời_gian'] = list(set(all_dates))
    
    # Thêm thông tin về giai đoạn lịch sử
    if topic_config and 'time_period' in topic_config:
        properties['giai_đoạn_lịch_sử'] = topic_config['time_period']
        
        # Chi tiết hóa cho ASEAN
        if "ASEAN" in str(topic_config):
            asean_periods = {
                '1967-1976': 'Giai đoạn khởi đầu, xây dựng nền móng',
                '1976-1999': 'Giai đoạn mở rộng và hợp tác chính trị',
                '1999-2015': 'Giai đoạn hoàn thiện và hội nhập',
                '2015-nay': 'Giai đoạn Cộng đồng ASEAN'
            }
            properties['giai_đoạn_ASEAN'] = asean_periods
    
    return properties


def create_topic_specific_metadata(entity: Dict, window: Dict, topic: str, lesson: str, topic_config: Dict) -> Dict:
    """Tạo metadata đặc thù cho chủ đề."""
    metadata = {
        'topic': topic,
        'lesson': lesson,
        'window_indices': [window['window_index']],
        'topic_period': topic_config.get('time_period', '') if topic_config else '',
        'priority_level': 'high' if entity['type'] in topic_config.get('priority_entities', []) else 'medium'
    }
    
    # Trích xuất timeline events với trọng tâm vào chủ đề
    timeline_events = extract_timeline_events_with_context(window['text'], topic_config)
    if timeline_events:
        metadata['timeline_events'] = timeline_events
    
    return metadata


def extract_timeline_events_with_context(text: str, topic_config: Dict) -> List[Dict]:
    """Trích xuất sự kiện timeline với context phù hợp chủ đề."""
    from text_processor import extract_timeline_events
    
    events = extract_timeline_events(text)
    
    # Thêm context đặc thù cho chủ đề
    if topic_config and 'time_period' in topic_config:
        for event in events:
            event['topic_period'] = topic_config['time_period']
    
    return events

def cleanup_entities(entities: List[Dict]) -> List[Dict]:
    """Làm sạch danh sách entities cuối cùng.
    
    Loại bỏ:
    - Các entity là ngày tháng đơn thuần
    - Các entity quá chung
    - Các entity là khẩu hiệu/khái niệm trừu tượng
    - Fix labels trùng lặp về case
    """
    cleaned = []
    
    for entity in entities:
        entity_id = entity.get('id', '')
        entity_id_lower = entity_id.lower().strip()
        
        # Bỏ qua các entity là ngày tháng đơn thuần
        date_patterns = [
            r'^\d{4}$',
            r'^\d{1,2}\s*[-–]\s*\d{1,2}\s*[-–]\s*\d{4}$',
            r'^tháng\s+\d{1,2}\s*[-–]\s*\d{4}$',
            r'^ngày\s+\d{1,2}$',
            r'^năm\s+\d{4}$',
            r'^ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}$',
            r'^ngày\s+\d{1,2}\s*[-–]\s*\d{1,2}\s*[-–]\s*\d{4}$',
            r'^\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}$',
            r'^[\d\s\-–]+$',  # Toàn số và dấu gạch
        ]
        
        is_date = False
        for pattern in date_patterns:
            if re.match(pattern, entity_id, re.IGNORECASE):
                is_date = True
                break
        
        if is_date:
            continue
        
        # Bỏ qua các entity quá chung
        general_terms = [
            'chính phủ', 'hội', 'trí tuệ con người', 'nhân dân thế giới',
            'nhân dân', 'thế giới', 'phe', 'quân', 'đế quốc', 'đảng',
            'cải tổ', 'hiến chương', 'tổ quốc', 'chiến lược', 'chủ trương',
            'chính sách', 'kháng chiến', 'cách mạng', 'phong trào'
        ]
        
        if entity_id_lower in general_terms:
            continue
        
        # Bỏ qua các khẩu hiệu, khái niệm trừu tượng
        abstract_concepts = [
            'thắng lợi quân sự', 'vừa đánh, vừa đàm', 'vừa đánh vừa đàm',
            'cuộc chiến tranh phi nghĩa', 'chiến tranh phi nghĩa',
            'thống nhất đất nước', 'hội nhập quốc tế', 'an ninh nhân dân',
            'công cuộc đổi mới', 'hệ thống chính trị', 'đảng mới 15 tuổi',
            'đổi mới toàn diện và đồng bộ', 'đổi mới kinh tế', 'đổi mới chính trị',
            'văn hoá – xã hội', 'văn hoá - xã hội', 'khoa học và công nghệ',
            'giáo dục và đào tạo', 'kinh tế tri thức', 'chế độ tem phiếu',
            'kinh tế hàng hoá xã hội chủ nghĩa', 'kinh tế thị trường xã hội chủ nghĩa',
        ]
        
        if entity_id_lower in abstract_concepts:
            continue
        
        # Bỏ qua entity chỉ có 1 từ và quá ngắn
        if len(entity_id.split()) == 1 and len(entity_id) < 4:
            continue
        
        # ===== FIX LABELS TRÙNG LẶP VỀ CASE =====
        if 'label' in entity and entity['label']:
            # Loại bỏ duplicate case trong labels
            best_labels = {}
            for label in entity['label']:
                if not label or not label.strip():
                    continue
                label_clean = label.strip()
                label_lower = label_clean.lower()
                
                if label_lower not in best_labels:
                    best_labels[label_lower] = label_clean
                else:
                    # Ưu tiên label có chữ hoa đầu
                    existing = best_labels[label_lower]
                    if label_clean[0].isupper() and not existing[0].isupper():
                        best_labels[label_lower] = label_clean
            
            # Tái tạo labels theo thứ tự, ưu tiên ID trước
            new_labels = []
            seen_lower = set()
            
            # Đảm bảo ID là label đầu tiên
            if entity_id.lower() in best_labels:
                new_labels.append(best_labels[entity_id.lower()])
                seen_lower.add(entity_id.lower())
            
            # Thêm các labels còn lại
            for label_lower, label in best_labels.items():
                if label_lower not in seen_lower:
                    new_labels.append(label)
                    seen_lower.add(label_lower)
            
            entity['label'] = new_labels
        
        cleaned.append(entity)
    
    return cleaned