# -*- coding: utf-8 -*-
"""
topic_config.py
Quản lý cấu hình topic cho Extract_kg package.
Tập trung vào relationship extraction từ các chủ đề lịch sử.
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


# Danh sách blacklist chung cho tất cả các chủ đề
COMMON_RELATIONSHIP_BLACKLIST = [
    # Các quan hệ quá chung chung
    "có", "là", "được", "bị", "thuộc", "gồm",
    # Các predicate trùng lặp với entity
    "và", "với", "của", "trong", "cho"
]


@dataclass
class RelationshipConfig:
    """Cấu hình quan hệ cho một chủ đề cụ thể."""
    topic_id: str
    topic_name: str
    topic_description: str
    
    # Focus entities - ưu tiên trích xuất quan hệ cho các loại thực thể này
    focus_entities: List[str] = field(default_factory=list)
    
    # Key relationships - các loại quan hệ quan trọng cần ưu tiên
    key_relationships: List[str] = field(default_factory=list)
    
    # Relationship patterns - mẫu quan hệ theo loại thực thể
    relationship_patterns: Dict[str, List[str]] = field(default_factory=dict)
    
    # Thematic focus - mô tả trọng tâm của chủ đề
    thematic_focus: str = ""
    
    # Context strategy - chiến lược xử lý ngữ cảnh
    context_strategy: str = "window_focused"
    
    # Window configuration
    window_size: int = 10
    step_size: int = 5
    
    # Time period
    time_period: str = ""
    
    # Historical periods/phases cụ thể
    historical_periods: Dict[str, str] = field(default_factory=dict)
    
    # Key milestones
    key_milestones: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển sang dict để tương thích với TopicProcessor."""
        return {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "topic_description": self.topic_description,
            "focus_entities": self.focus_entities,
            "key_relationships": self.key_relationships,
            "relationship_patterns": self.relationship_patterns,
            "thematic_focus": self.thematic_focus,
            "context_strategy": self.context_strategy,
            "window_size": self.window_size,
            "step_size": self.step_size,
            "time_period": self.time_period,
            "historical_periods": self.historical_periods,
            "key_milestones": self.key_milestones
        }


class TopicConfigManager:
    """Quản lý cấu hình cho tất cả các chủ đề từ file JSON và defaults."""
    
    # Các từ khóa để nhận diện topic
    TOPIC_KEYWORDS = {
        "THẾ GIỚI": "Chủ đề 1",
        "CHIẾN TRANH LẠNH": "Chủ đề 1",
        "ASEAN": "Chủ đề 2",
        "ĐÔNG NAM Á": "Chủ đề 2",
        "CÁCH MẠNG THÁNG TÁM": "Chủ đề 3",
        "CHIẾN TRANH GIẢI PHÓNG": "Chủ đề 3",
        "KHÁNG CHIẾN CHỐNG PHÁP": "Chủ đề 3",
        "KHÁNG CHIẾN CHỐNG MỸ": "Chủ đề 3",
        "ĐỔI MỚI": "Chủ đề 4",
        "XÂY DỰNG CNXH": "Chủ đề 4",
        "ĐỐI NGOẠI": "Chủ đề 5",
        "NGOẠI GIAO": "Chủ đề 5",
        "HỒ CHÍ MINH": "Chủ đề 6",
        "BÁC HỒ": "Chủ đề 6"
    }
    
    # Cấu hình mặc định cho từng topic - tập trung vào relationship extraction
    DEFAULT_CONFIGS = {
        "Chủ đề 1": RelationshipConfig(
            topic_id="Chủ đề 1",
            topic_name="THẾ GIỚI TRONG VÀ SAU CHIẾN TRANH LẠNH",
            topic_description="Thế giới trong và sau Chiến tranh Lạnh",
            focus_entities=["Tổ chức quốc tế", "Quốc gia", "Sự kiện", "Hội nghị", "Văn kiện/Hiệp định", "Chiến lược/Chủ trương"],
            key_relationships=[
                "thành_lập", "tham_gia", "ký_kết", "thông_qua", "đại_diện", "lãnh_đạo",
                "đối_đầu", "hợp_tác", "ảnh_hưởng", "thuộc_về", "thay_thế", "thúc_đẩy",
                "duy_trì", "phân_chi", "chiếm_đóng", "giải_thể", "đề_xuất", "triển_khai",
                "củng_cố", "tan_rã"
            ],
            relationship_patterns={
                "Tổ chức quốc tế": ["thành_lập_bởi", "tham_gia_bởi", "đại_diện_cho", "thúc_đẩy", "duy_trì", "ký_kết", "thông_qua"],
                "Quốc gia": ["tham_gia", "lãnh_đạo", "đối_đầu", "hợp_tác", "ảnh_hưởng", "chiếm_đóng", "ký_kết"],
                "Sự kiện": ["diễn_ra_tại", "tổ_chức_bởi", "tham_gia_bởi", "dẫn_đến", "kết_thúc_với"],
                "Văn kiện/Hiệp định": ["được_ký_bởi", "được_thông_qua_bởi", "quy_định", "cam_kết", "thiết_lập"],
                "Hội nghị": ["diễn_ra_tại", "tổ_chức_bởi", "tham_gia_bởi", "thông_qua", "quyết_định"]
            },
            thematic_focus="Chủ đề tập trung vào cấu trúc quyền lực thế giới, các tổ chức quốc tế, quan hệ giữa các cường quốc, và sự chuyển đổi từ trật tự hai cực sang đa cực sau Chiến tranh Lạnh.",
            context_strategy="window_focused",
            window_size=12,
            step_size=6,
            time_period="1945-1991"
        ),
        
        "Chủ đề 2": RelationshipConfig(
            topic_id="Chủ đề 2",
            topic_name="ASEAN: NHỮNG CHẶNG ĐƯỜNG LỊCH SỬ",
            topic_description="ASEAN: Những chặng đường lịch sử",
            focus_entities=["Tổ chức khu vực", "Quốc gia", "Văn kiện/Hiệp định", "Sự kiện", "Hội nghị", "Cộng đồng", "Trụ cột"],
            key_relationships=[
                "thành_lập", "tham_gia", "mở_rộng_thành", "ký_kết", "thông_qua",
                "khởi_xướng", "tạo_nền_móng", "phát_triển_thành", "xây_dựng", "hình_thành",
                "gia_nhập", "trở_thành_thành_viên", "đề_xuất", "thúc_đẩy", "hợp_tác_trong",
                "liên_kết", "gắn_kết", "chuyển_đổi_thành", "hoàn_thành", "củng_cố"
            ],
            relationship_patterns={
                "Tổ chức khu vực": ["thành_lập_bởi", "mở_rộng_từ", "phát_triển_thành", "chuyển_đổi_sang", "bao_gồm"],
                "Quốc gia": ["sáng_lập", "tham_gia", "gia_nhập", "trở_thành_thành_viên", "ký_kết", "đề_xuất"],
                "Văn kiện/Hiệp định": ["được_ký_bởi", "được_thông_qua_tại", "quy_định", "thiết_lập", "cam_kết"],
                "Sự kiện": ["đánh_dấu", "khởi_đầu", "kết_thúc", "diễn_ra_tại", "dẫn_đến"],
                "Cộng đồng": ["bao_gồm", "dựa_trên", "phát_triển_từ", "hình_thành_bởi", "gồm_các_trụ_cột"],
                "Trụ cột": ["thuộc_về", "hỗ_trợ", "liên_kết_với", "phát_triển_cùng", "đảm_bảo"]
            },
            thematic_focus="Chủ đề tập trung vào quá trình hình thành, phát triển và mở rộng của ASEAN, từ tổ chức khu vực ban đầu đến Cộng đồng ASEAN với ba trụ cột.",
            context_strategy="asean_phase_based",
            window_size=8,
            step_size=4,
            time_period="1967-nay",
            historical_periods={
                "1967": "ASEAN 5: Thành lập",
                "1984": "ASEAN 6: Brunei gia nhập",
                "1995": "ASEAN 7: Việt Nam gia nhập",
                "1997": "ASEAN 9: Lào và Myanmar gia nhập",
                "1999": "ASEAN 10: Campuchia gia nhập"
            }
        ),
        
        "Chủ đề 3": RelationshipConfig(
            topic_id="Chủ đề 3",
            topic_name="CÁCH MẠNG THÁNG TÁM NĂM 1945, CHIẾN TRANH GIẢI PHÓNG DÂN TỘC VÀ CHIẾN TRANH BẢO VỆ TỔ QUỐC",
            topic_description="Cách mạng tháng Tám năm 1945, chiến tranh giải phóng dân tộc và chiến tranh bảo vệ Tổ quốc",
            focus_entities=["Sự kiện lịch sử", "Nhân Vật", "Tổ chức chính trị", "Chiến dịch/Trận đánh", "Địa điểm lịch sử", "Văn kiện/Hiệp định", "Lực lượng vũ trang"],
            key_relationships=[
                "lãnh_đạo", "chỉ_huy", "thành_lập", "tham_gia", "diễn_ra_tại", "giải_phóng",
                "đánh_bại", "ký_kết", "tuyên_bố", "xâm_lược", "bảo_vệ", "hi_sinh", "ủng_hộ",
                "phát_động", "khởi_nghĩa", "chiến_thắng", "rút_lui", "đầu_hàng",
                "thành_lập_chính_quyền", "tấn_công", "phản_công", "giành_chính_quyền",
                "mở_chiến_dịch", "đề_ra_chiến_lược"
            ],
            relationship_patterns={
                "Sự kiện lịch sử": ["dẫn_đến", "tạo_bước_ngoặt", "mở_ra_thời_kỳ", "đánh_dấu", "diễn_ra_tại"],
                "Nhân Vật": ["lãnh_đạo", "chỉ_huy", "tham_gia", "đề_xuất", "phát_động", "thành_lập", "ký_kết"],
                "Tổ chức chính trị": ["thành_lập", "lãnh_đạo", "phát_động", "tham_gia", "đề_ra", "thông_qua"],
                "Chiến dịch/Trận đánh": ["diễn_ra_tại", "do_ai_chỉ_huy", "đánh_bại", "giải_phóng", "mở_đầu"],
                "Văn kiện/Hiệp định": ["được_ký_bởi", "được_thông_qua", "quy_định", "cam_kết", "chấm_dứt"],
                "Lực lượng vũ trang": ["thành_lập_bởi", "do_ai_chỉ_huy", "tham_gia", "giải_phóng", "đánh_bại"]
            },
            thematic_focus="Chủ đề tập trung vào các cuộc đấu tranh giải phóng dân tộc và bảo vệ Tổ quốc của Việt Nam từ 1945 đến nay.",
            context_strategy="war_period_based",
            window_size=10,
            step_size=5,
            time_period="1945-1975",
            historical_periods={
                "cmtt_1945": "Cách mạng tháng Tám 1945",
                "kccp_1945_1954": "Kháng chiến chống Pháp 1945-1954",
                "kcmcn_1954_1975": "Kháng chiến chống Mỹ 1954-1975",
                "bvtq_sau_1975": "Bảo vệ Tổ quốc sau 1975"
            }
        ),
        
        "Chủ đề 4": RelationshipConfig(
            topic_id="Chủ đề 4",
            topic_name="CÔNG CUỘC ĐỔI MỚI Ở VIỆT NAM TỪ NĂM 1986 ĐẾN NAY",
            topic_description="Công cuộc Đổi mới ở Việt Nam từ năm 1986 đến nay",
            focus_entities=["Chính sách kinh tế", "Sự kiện chính trị", "Văn kiện/Nghị quyết", "Chỉ tiêu kinh tế", "Thành tựu phát triển", "Tổ chức quốc tế"],
            key_relationships=[
                "khởi_xướng", "đề_ra", "thông_qua", "triển_khai", "thực_hiện", "đạt_được",
                "chuyển_đổi_sang", "cải_cách", "hội_nhập", "ký_kết", "tham_gia",
                "phát_triển_thành", "tăng_trưởng", "giảm_xuống", "tăng_lên", "hoàn_thành"
            ],
            relationship_patterns={
                "Chính sách kinh tế": ["được_đề_ra_tại", "triển_khai_từ", "thay_đổi_từ", "chuyển_đổi_sang", "tạo_ra"],
                "Sự kiện chính trị": ["đánh_dấu", "mở_ra", "thông_qua", "quyết_định", "khởi_xướng"],
                "Văn kiện/Nghị quyết": ["được_thông_qua_tại", "đề_ra", "quy_định", "định_hướng", "chỉ_đạo"],
                "Chỉ tiêu kinh tế": ["tăng_lên", "giảm_xuống", "đạt_mức", "vượt_mức", "phản_ánh"],
                "Thành tựu phát triển": ["đạt_được", "thể_hiện_qua", "phản_ánh", "khẳng_định", "chứng_minh"],
                "Tổ chức quốc tế": ["tham_gia", "ký_kết", "hợp_tác", "đàm_phán", "gia_nhập"]
            },
            thematic_focus="Chủ đề tập trung vào quá trình Đổi mới toàn diện đất nước Việt Nam từ năm 1986.",
            context_strategy="doi_moi_phase_based",
            window_size=12,
            step_size=6,
            time_period="1986-nay",
            historical_periods={
                "1986_1995": "Giai đoạn khởi đầu Đổi mới",
                "1996_2006": "Giai đoạn đẩy mạnh CNH-HĐH",
                "2006_nay": "Giai đoạn hội nhập quốc tế sâu rộng"
            },
            key_milestones={
                "1986": "Đại hội VI - Khởi xướng Đổi mới",
                "1989": "Bãi bỏ tem phiếu",
                "2007": "Gia nhập WTO",
                "2015": "Hoàn thành Mục tiêu Thiên niên kỷ"
            }
        ),
        
        "Chủ đề 5": RelationshipConfig(
            topic_id="Chủ đề 5",
            topic_name="LỊCH SỬ ĐỐI NGOẠI CỦA VIỆT NAM THỜI CẬN – HIỆN ĐẠI",
            topic_description="Lịch sử đối ngoại của Việt Nam thời cận - hiện đại",
            focus_entities=["Nhân Vật Lịch Sử", "Tổ chức Chính trị", "Quốc gia", "Hiệp định/Hội nghị", "Sự kiện Đối ngoại", "Mặt trận/Tổ chức Quốc tế"],
            key_relationships=[
                "thành_lập", "tham_gia", "tham_gia_thành_lập", "ký_kết", "thiết_lập_quan_hệ",
                "gia_nhập", "đàm_phán_với", "hợp_tác_với", "tranh_thủ_ủng_hộ", "vận_động",
                "bình_thường_hóa_quan_hệ", "nâng_cấp_quan_hệ", "phối_hợp_với"
            ],
            relationship_patterns={
                "Nhân Vật Lịch Sử": ["thành_lập", "tham_gia_thành_lập", "tham_gia", "ký_kết", "đàm_phán_với", "tiếp_xúc_với"],
                "Tổ chức Chính trị": ["thành_lập", "tham_gia", "phối_hợp_với", "ủng_hộ", "tranh_thủ_ủng_hộ"],
                "Quốc gia": ["thiết_lập_quan_hệ", "bình_thường_hóa_quan_hệ", "nâng_cấp_quan_hệ", "hợp_tác_với", "ký_kết"],
                "Hiệp định/Hội nghị": ["được_ký_kết_tại", "được_thông_qua_tại", "liên_quan_đến", "giải_quyết"],
                "Mặt trận/Tổ chức Quốc tế": ["tham_gia", "gia_nhập", "thành_lập", "ủng_hộ", "phối_hợp_với"]
            },
            thematic_focus="Chủ đề tập trung vào hoạt động đối ngoại của Việt Nam qua các thời kỳ lịch sử.",
            context_strategy="diplomacy_timeline_based",
            window_size=10,
            step_size=5,
            time_period="1945-nay",
            historical_periods={
                "1945_1954": "Kháng chiến chống Pháp",
                "1954_1975": "Kháng chiến chống Mỹ",
                "1975_1985": "Thời kỳ sau thống nhất",
                "1986_nay": "Thời kỳ Đổi mới"
            }
        ),
        
        "Chủ đề 6": RelationshipConfig(
            topic_id="Chủ đề 6",
            topic_name="HỒ CHÍ MINH TRONG LỊCH SỬ VIỆT NAM",
            topic_description="Chủ tịch Hồ Chí Minh - Anh hùng giải phóng dân tộc, Nhà văn hóa kiệt xuất",
            focus_entities=["Nhân Vật Lịch Sử", "Sự kiện Lịch sử", "Tổ chức Cách mạng", "Địa điểm Lịch sử", "Văn kiện/Tác phẩm", "Tư tưởng/Đạo đức"],
            key_relationships=[
                "sinh_ra_tại", "lớn_lên_tại", "học_tập_tại", "tham_gia", "thành_lập",
                "sáng_lập", "chủ_trì", "lãnh_đạo", "chỉ_đạo", "soạn_thảo", "viết", "đọc",
                "tuyên_bố", "kêu_gọi", "vận_động", "tìm_đường_cứu_nước", "đến_với_chủ_nghĩa",
                "trở_thành", "được_bầu_làm", "trực_tiếp_lãnh_đạo", "ra_đi", "trở_về", "qua_đời_tại"
            ],
            relationship_patterns={
                "Nhân Vật Lịch Sử": ["sinh_ra_tại", "lớn_lên_tại", "học_tập_tại", "tham_gia", "thành_lập", "sáng_lập", "lãnh_đạo", "soạn_thảo"],
                "Sự kiện Lịch sử": ["được_khởi_xướng_bởi", "được_lãnh_đạo_bởi", "được_chỉ_đạo_bởi", "diễn_ra_tại"],
                "Tổ chức Cách mạng": ["được_thành_lập_bởi", "được_sáng_lập_bởi", "được_lãnh_đạo_bởi", "tham_gia_bởi"],
                "Địa điểm Lịch sử": ["nơi_sinh", "nơi_lớn_lên", "nơi_học_tập", "nơi_hoạt_động", "nơi_thành_lập"],
                "Văn kiện/Tác phẩm": ["được_soạn_thảo_bởi", "được_viết_bởi", "được_đọc_bởi", "chứa_tư_tưởng_của"],
                "Tư tưởng/Đạo đức": ["được_hình_thành_bởi", "được_phát_triển_bởi", "được_truyền_bá_bởi", "ảnh_hưởng_đến"]
            },
            thematic_focus="Chủ đề tập trung vào cuộc đời, sự nghiệp và di sản của Chủ tịch Hồ Chí Minh.",
            context_strategy="ho_chi_minh_life_phases",
            window_size=8,
            step_size=4,
            time_period="1890-1969",
            historical_periods={
                "1890_1911": "Thời niên thiếu và hoạt động đầu tiên",
                "1911_1920": "Hành trình tìm đường cứu nước",
                "1920_1930": "Chuẩn bị thành lập Đảng",
                "1941_1945": "Trực tiếp lãnh đạo cách mạng",
                "1945_1954": "Lãnh đạo kháng chiến chống Pháp",
                "1954_1969": "Lãnh đạo kháng chiến chống Mỹ",
                "1969_nay": "Di sản và ảnh hưởng"
            },
            key_milestones={
                "1890": "Sinh ra tại làng Sen, Nam Đàn, Nghệ An",
                "1911": "Ra đi tìm đường cứu nước từ Bến Nhà Rồng",
                "1920": "Đến với chủ nghĩa Mác-Lênin",
                "1930": "Thành lập Đảng Cộng sản Việt Nam",
                "1941": "Về nước trực tiếp lãnh đạo cách mạng",
                "1945": "Đọc Tuyên ngôn Độc lập",
                "1954": "Lãnh đạo chiến thắng Điện Biên Phủ",
                "1969": "Qua đời tại Hà Nội"
            }
        )
    }
    
    def __init__(self, json_path: str = None):
        """
        Khởi tạo TopicConfigManager.
        
        Args:
            json_path: Đường dẫn tới file JSON sách giáo khoa
        """
        self.json_path = json_path
        self.topics: Dict[str, RelationshipConfig] = {}
        self._lesson_index: Dict[str, Dict] = {}
        
        # Load từ JSON nếu có
        if json_path and os.path.exists(json_path):
            self._load_from_json()
        else:
            self.topics = self.DEFAULT_CONFIGS.copy()
    
    def _load_from_json(self):
        """Load cấu trúc từ file JSON."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Nhóm theo topic_id
            topics_data = {}
            for lesson in data:
                topic_id = lesson.get("topic_id", "Unknown")
                if topic_id not in topics_data:
                    topics_data[topic_id] = {
                        "topic_description": lesson.get("topic_description", ""),
                        "lessons": []
                    }
                topics_data[topic_id]["lessons"].append({
                    "lesson_id": lesson.get("lesson_id", ""),
                    "lesson_title": lesson.get("lesson_title", ""),
                    "sections": lesson.get("sections", [])
                })
                
                # Tạo index cho lesson
                lesson_id = lesson.get("lesson_id", "")
                self._lesson_index[lesson_id] = {
                    "topic_id": topic_id,
                    "topic_description": lesson.get("topic_description", ""),
                    "lesson_title": lesson.get("lesson_title", "")
                }
            
            # Tạo RelationshipConfig cho mỗi topic
            for topic_id, topic_data in topics_data.items():
                default_config = self._find_default_config(topic_id, topic_data["topic_description"])
                
                if default_config:
                    # Sử dụng default config với thông tin từ JSON
                    config = RelationshipConfig(
                        topic_id=topic_id,
                        topic_name=default_config.topic_name,
                        topic_description=topic_data["topic_description"],
                        focus_entities=default_config.focus_entities,
                        key_relationships=default_config.key_relationships,
                        relationship_patterns=default_config.relationship_patterns,
                        thematic_focus=default_config.thematic_focus,
                        context_strategy=default_config.context_strategy,
                        window_size=default_config.window_size,
                        step_size=default_config.step_size,
                        time_period=default_config.time_period,
                        historical_periods=default_config.historical_periods,
                        key_milestones=default_config.key_milestones
                    )
                else:
                    # Tạo config cơ bản
                    config = RelationshipConfig(
                        topic_id=topic_id,
                        topic_name=topic_id,
                        topic_description=topic_data["topic_description"],
                        focus_entities=["Nhân Vật", "Tổ chức", "Sự kiện", "Địa điểm"],
                        key_relationships=["thành_lập", "tham_gia", "lãnh_đạo", "diễn_ra_tại"]
                    )
                
                self.topics[topic_id] = config
                # Thêm với topic_description để có thể tìm theo cả 2 cách
                self.topics[topic_data["topic_description"]] = config
                
        except Exception as e:
            print(f"[Warning] Could not load JSON: {e}")
            self.topics = self.DEFAULT_CONFIGS.copy()
    
    def _find_default_config(self, topic_id: str, topic_desc: str) -> Optional[RelationshipConfig]:
        """Tìm default config phù hợp với topic."""
        # Tìm theo topic_id trước
        for default_id, config in self.DEFAULT_CONFIGS.items():
            if default_id.lower() in topic_id.lower():
                return config
        
        # Tìm theo keywords trong topic_description
        topic_desc_upper = topic_desc.upper()
        for keyword, mapped_topic_id in self.TOPIC_KEYWORDS.items():
            if keyword in topic_desc_upper:
                return self.DEFAULT_CONFIGS.get(mapped_topic_id)
        
        return None
    
    def get_config(self, topic_name: str) -> Dict[str, Any]:
        """
        Lấy cấu hình cho một topic.
        
        Args:
            topic_name: Có thể là topic_id (Chủ đề 1) hoặc topic_description
            
        Returns:
            Dict cấu hình cho topic
        """
        # Tìm exact match trước
        if topic_name in self.topics:
            return self.topics[topic_name].to_dict()
        
        # Tìm partial match
        topic_upper = topic_name.upper()
        for key, config in self.topics.items():
            if topic_upper in key.upper() or key.upper() in topic_upper:
                return config.to_dict()
        
        # Tìm theo keywords
        for keyword, mapped_topic_id in self.TOPIC_KEYWORDS.items():
            if keyword in topic_upper:
                if mapped_topic_id in self.DEFAULT_CONFIGS:
                    return self.DEFAULT_CONFIGS[mapped_topic_id].to_dict()
        
        # Trả về config rỗng
        return {
            "topic_id": topic_name,
            "topic_name": topic_name,
            "topic_description": "",
            "focus_entities": ["Nhân Vật", "Tổ chức", "Sự kiện", "Địa điểm"],
            "key_relationships": ["thành_lập", "tham_gia", "lãnh_đạo"],
            "relationship_patterns": {},
            "thematic_focus": "",
            "context_strategy": "window_focused",
            "window_size": 10,
            "step_size": 5
        }
    
    def get_relationship_patterns(self, topic_name: str, entity_type: str = None) -> List[str]:
        """
        Lấy các mẫu quan hệ cho topic và loại thực thể cụ thể.
        
        Args:
            topic_name: Tên topic
            entity_type: Loại thực thể (optional)
            
        Returns:
            Danh sách các mẫu quan hệ
        """
        config = self.get_config(topic_name)
        patterns = config.get("relationship_patterns", {})
        
        if entity_type and entity_type in patterns:
            return patterns[entity_type]
        
        # Trả về tất cả patterns nếu không chỉ định entity_type
        all_patterns = set()
        for entity_patterns in patterns.values():
            all_patterns.update(entity_patterns)
        return list(all_patterns)
    
    def get_key_relationships(self, topic_name: str) -> List[str]:
        """Lấy danh sách các quan hệ quan trọng cho topic."""
        config = self.get_config(topic_name)
        return config.get("key_relationships", [])
    
    def get_lesson_info(self, lesson_id: str) -> Dict[str, str]:
        """Lấy thông tin lesson từ lesson_id."""
        return self._lesson_index.get(lesson_id, {})
    
    def get_all_topics(self) -> List[str]:
        """Lấy danh sách tất cả topic_id."""
        return [config.topic_id for config in self.topics.values() if hasattr(config, 'topic_id')]


# Singleton instance
_config_manager: Optional[TopicConfigManager] = None


def get_topic_config_manager(json_path: str = None) -> TopicConfigManager:
    """
    Lấy TopicConfigManager singleton.
    
    Args:
        json_path: Đường dẫn tới file JSON (chỉ cần truyền lần đầu)
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = TopicConfigManager(json_path)
    return _config_manager


def get_topic_config(topic_name: str, json_path: str = None) -> Dict[str, Any]:
    """
    Hàm tiện ích để lấy config cho topic.
    
    Args:
        topic_name: Tên topic (topic_id hoặc topic_description)
        json_path: Đường dẫn tới file JSON (optional)
    """
    manager = get_topic_config_manager(json_path)
    return manager.get_config(topic_name)


def get_relationship_patterns(topic_name: str, entity_type: str = None) -> List[str]:
    """
    Hàm tiện ích để lấy relationship patterns.
    
    Args:
        topic_name: Tên topic
        entity_type: Loại thực thể (optional)
    """
    manager = get_topic_config_manager()
    return manager.get_relationship_patterns(topic_name, entity_type)


# Test
if __name__ == "__main__":
    # Test với file JSON
    json_path = r"D:\KLTN\KLTN\SGK\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json"
    
    manager = TopicConfigManager(json_path)
    
    print("=" * 60)
    print("TOPIC CONFIGS FOR RELATIONSHIP EXTRACTION")
    print("=" * 60)
    
    # Test get config
    test_names = [
        "Chủ đề 1",
        "THẾ GIỚI TRONG VÀ SAU CHIẾN TRANH LẠNH",
        "ASEAN",
        "Hồ Chí Minh"
    ]
    
    for name in test_names:
        config = manager.get_config(name)
        print(f"\n[{name}]")
        print(f"  topic_id: {config.get('topic_id')}")
        print(f"  focus_entities: {config.get('focus_entities')[:3]}...")
        print(f"  key_relationships: {config.get('key_relationships')[:5]}...")
        print(f"  thematic_focus: {config.get('thematic_focus')[:80]}...")
    
    # Test relationship patterns
    print("\n" + "=" * 60)
    print("RELATIONSHIP PATTERNS")
    print("=" * 60)
    
    patterns = manager.get_relationship_patterns("Chủ đề 1", "Tổ chức quốc tế")
    print(f"\nChủ đề 1 - Tổ chức quốc tế: {patterns[:5]}...")
    
    patterns = manager.get_relationship_patterns("Chủ đề 6", "Nhân Vật Lịch Sử")
    print(f"Chủ đề 6 - Nhân Vật: {patterns[:5]}...")
