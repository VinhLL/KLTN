# topic_processor.py
import re
import json
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from utils import extract_topic_and_lesson, create_overlapping_windows, split_into_sentences
from api_handler import call_deepseek_api
import config

API_REQUEST_COUNT = 0

class TopicProcessor:
    """Xử lý đặc thù theo từng chủ đề."""
    
    # Cấu hình cho tất cả chủ đề
    TOPIC_CONFIGS = {
        "Chủ đề 1": {
            "topic_name": "THẾ GIỚI TRONG VÀ SAU CHIẾN TRANH LẠNH",
            "focus_entities": ["Tổ chức quốc tế", "Quốc gia", "Sự kiện", "Hội nghị", "Văn kiện/Hiệp định", "Chiến lược/Chủ trương"],
            "key_relationships": ["thành_lập", "tham_gia", "ký_kết", "thông_qua", "đại_diện", "lãnh_đạo", "đối_đầu", "hợp_tác", "ảnh_hưởng", "thuộc_về", "thay_thế", "thúc_đẩy", "duy_trì", "phân_chi", "chiếm_đóng", "giải_thể", "đề_xuất", "triển_khai", "củng_cố", "tan_rã"],
            "thematic_focus": "Chủ đề tập trung vào cấu trúc quyền lực thế giới, các tổ chức quốc tế, quan hệ giữa các cường quốc, và sự chuyển đổi từ trật tự hai cực sang đa cực sau Chiến tranh Lạnh.",
            "relationship_patterns": {
                "Tổ chức quốc tế": ["thành_lập_bởi", "tham_gia_bởi", "đại_diện_cho", "thúc_đẩy", "duy_trì", "ký_kết", "thông_qua", "triển_khai", "củng_cố", "thay_thế"],
                "Quốc gia": ["tham_gia", "lãnh_đạo", "đối_đầu", "hợp_tác", "ảnh_hưởng", "chiếm_đóng", "ký_kết", "đề_xuất", "thành_lập", "phân_chi", "ủng_hộ", "phản_đối"],
                "Sự kiện": ["diễn_ra_tại", "tổ_chức_bởi", "tham_gia_bởi", "dẫn_đến", "kết_thúc_với", "bắt_đầu_vào", "có_ảnh_hưởng", "được_tiến_hành_bởi"],
                "Văn kiện/Hiệp định": ["được_ký_bởi", "được_thông_qua_bởi", "quy_định", "cam_kết", "thiết_lập", "cấm", "hạn_chế", "thúc_đẩy"],
                "Hội nghị": ["diễn_ra_tại", "tổ_chức_bởi", "tham_gia_bởi", "thông_qua", "đề_xuất", "quyết_định", "thỏa_thuận"]
            },
            "context_strategy": "window_focused",
            "window_size": 12,
            "step_size": 6
        },
        "Chủ đề 2": {
            "topic_name": "ASEAN: NHỮNG CHẶNG ĐƯỜNG LỊCH SỬ",
            "focus_entities": ["Tổ chức khu vực", "Quốc gia", "Văn kiện/Hiệp định", "Sự kiện", "Hội nghị", "Cộng đồng", "Trụ cột", "Khu vực mậu dịch"],
            "key_relationships": ["thành_lập", "tham_gia", "mở_rộng_thành", "ký_kết", "thông_qua", "khởi_xướng", "tạo_nền_móng", "phát_triển_thành", "xây_dựng", "hình_thành", "gia_nhập", "trở_thành_thành_viên", "đề_xuất", "thúc_đẩy", "hợp_tác_trong", "liên_kết", "gắn_kết", "chuyển_đổi_thành", "hoàn_thành", "củng_cố"],
            "thematic_focus": "Chủ đề tập trung vào quá trình hình thành, phát triển và mở rộng của ASEAN, từ tổ chức khu vực ban đầu đến Cộng đồng ASEAN với ba trụ cột. Đặc biệt quan tâm đến các giai đoạn phát triển, văn kiện quan trọng, và quá trình mở rộng thành viên.",
            "relationship_patterns": {
                "Tổ chức khu vực": ["thành_lập_bởi", "mở_rộng_từ", "phát_triển_thành", "chuyển_đổi_sang", "bao_gồm", "hợp_tác_với", "ký_kết_văn_kiện", "thông_qua_tuyên_bố", "xây_dựng_trụ_cột", "hình_thành_cộng_đồng"],
                "Quốc gia": ["sáng_lập", "tham_gia", "gia_nhập", "trở_thành_thành_viên", "ký_kết", "đề_xuất", "chủ_trì", "đóng_góp", "hợp_tác_trong", "tham_dự", "phê_chuẩn", "thực_hiện"],
                "Văn kiện/Hiệp định": ["được_ký_bởi", "được_thông_qua_tại", "quy_định", "thiết_lập", "cam_kết", "định_hướng", "tạo_cơ_sở", "củng_cố", "mở_đường_cho"],
                "Sự kiện": ["đánh_dấu", "khởi_đầu", "kết_thúc", "diễn_ra_tại", "dẫn_đến", "thúc_đẩy", "tạo_bước_ngoặt", "mở_ra_giai_đoạn"],
                "Cộng đồng": ["bao_gồm", "dựa_trên", "phát_triển_từ", "hình_thành_bởi", "gồm_các_trụ_cột", "hướng_tới", "đạt_được", "hoàn_thành"],
                "Trụ cột": ["thuộc_về", "hỗ_trợ", "liên_kết_với", "phát_triển_cùng", "đảm_bảo", "thúc_đẩy", "củng_cố", "hoàn_thiện"]
            },
            "context_strategy": "asean_phase_based",
            "window_size": 8,
            "step_size": 4,
            "asean_founding_members": ["In-đô-nê-xi-a", "Ma-lai-xi-a", "Phi-líp-pin", "Xin-ga-po", "Thái Lan"],
            "asean_expansion_phases": {
                "1967": "ASEAN 5: Thành lập",
                "1984": "ASEAN 6: Brunei gia nhập",
                "1995": "ASEAN 7: Việt Nam gia nhập",
                "1997": "ASEAN 9: Lào và Myanmar gia nhập",
                "1999": "ASEAN 10: Campuchia gia nhập"
            }
        },
        "Chủ đề 3": {
            "topic_name": "CÁCH MẠNG THÁNG TÁM NĂM 1945, CHIẾN TRANH GIẢI PHÓNG DÂN TỘC VÀ CHIẾN TRANH BẢO VỆ TỔ QUỐC TRONG LỊCH SỬ VIỆT NAM",
            "focus_entities": ["Sự kiện lịch sử", "Nhân Vật", "Tổ chức chính trị", "Chiến dịch/Trận đánh", "Địa điểm lịch sử", "Văn kiện/Hiệp định", "Chính quyền", "Lực lượng vũ trang"],
            "key_relationships": ["lãnh_đạo", "chỉ_huy", "thành_lập", "tham_gia", "diễn_ra_tại", "giải_phóng", "đánh_bại", "ký_kết", "tuyên_bố", "xâm_lược", "bảo_vệ", "hi_sinh", "ủng_hộ", "phát_động", "khởi_nghĩa", "chiến_thắng", "rút_lui", "đầu_hàng", "thành_lập_chính_quyền", "tấn_công", "phản_công", "giành_chính_quyền", "mở_chiến_dịch", "thành_lập_mặt_trận", "đề_ra_chiến_lược", "thực_hiện_kế_hoạch", "tiến_hành_chiến_dịch", "góp_phần", "tạo_điều_kiện", "chuyển_sang_giai_đoạn"],
            "thematic_focus": "Chủ đề tập trung vào các cuộc đấu tranh giải phóng dân tộc và bảo vệ Tổ quốc của Việt Nam từ 1945 đến nay. Bao gồm: Cách mạng tháng Tám, kháng chiến chống Pháp, chống Mỹ, và các cuộc chiến tranh bảo vệ biên giới, biển đảo.",
            "relationship_patterns": {
                "Sự kiện lịch sử": ["dẫn_đến", "tạo_bước_ngoặt", "mở_ra_thời_kỳ", "đánh_dấu", "diễn_ra_tại", "do_ai_lãnh_đạo", "có_ý_nghĩa", "kết_thúc_với"],
                "Nhân Vật": ["lãnh_đạo", "chỉ_huy", "tham_gia", "đề_xuất", "phát_động", "thành_lập", "ký_kết", "tuyên_bố", "hi_sinh", "đóng_góp"],
                "Tổ chức chính trị": ["thành_lập", "lãnh_đạo", "phát_động", "tham_gia", "đề_ra", "thông_qua", "chỉ_đạo", "phối_hợp", "hợp_nhất", "giải_thể"],
                "Chiến dịch/Trận đánh": ["diễn_ra_tại", "do_ai_chỉ_huy", "đánh_bại", "giải_phóng", "mở_đầu", "kết_thúc", "có_ý_nghĩa", "tạo_thế_chủ_động"],
                "Văn kiện/Hiệp định": ["được_ký_bởi", "được_thông_qua", "quy_định", "cam_kết", "chấm_dứt", "tạo_cơ_sở", "công_nhận", "quy_định_ranh_giới"],
                "Địa điểm lịch sử": ["diễn_ra_tại", "giải_phóng_vào", "thuộc_địa_bàn", "là_căn_cứ", "là_nơi", "được_chiếm_đóng_bởi", "được_bảo_vệ_bởi"],
                "Lực lượng vũ trang": ["thành_lập_bởi", "do_ai_chỉ_huy", "tham_gia", "giải_phóng", "đánh_bại", "bảo_vệ", "hi_sinh", "phối_hợp_với"]
            },
            "context_strategy": "war_period_based",
            "window_size": 10,
            "step_size": 5,
            "war_periods": {
                "cmtt_1945": "Cách mạng tháng Tám 1945",
                "kccp_1945_1954": "Kháng chiến chống Pháp 1945-1954",
                "kcmcn_1954_1975": "Kháng chiến chống Mỹ 1954-1975",
                "bvtq_sau_1975": "Bảo vệ Tổ quốc sau 1975",
                "bien_gioi_tay_nam": "Chiến tranh biên giới Tây Nam 1977-1979",
                "bien_gioi_phia_bac": "Chiến tranh biên giới phía Bắc 1979",
                "bien_dong": "Đấu tranh bảo vệ chủ quyền Biển Đông"
            }
        },
        "Chủ đề 4": {
            "topic_name": "CÔNG CUỘC ĐỔI MỚI Ở VIỆT NAM TỪ NĂM 1986 ĐẾN NAY",
            "focus_entities": ["Chính sách kinh tế", "Sự kiện chính trị", "Văn kiện/Nghị quyết", "Chỉ tiêu kinh tế", "Thành tựu phát triển", "Chiến lược phát triển", "Tổ chức quốc tế", "Hiệp định thương mại", "Lĩnh vực đổi mới", "Công trình hạ tầng"],
            "key_relationships": ["khởi_xướng", "đề_ra", "thông_qua", "triển_khai", "thực_hiện", "đạt_được", "chuyển_đổi_sang", "cải_cách", "hội_nhập", "ký_kết", "tham_gia", "phát_triển_thành", "tăng_trưởng", "giảm_xuống", "tăng_lên", "hoàn_thành", "xây_dựng", "củng_cố", "mở_rộng", "nâng_cao", "chuyển_dịch", "ổn_định", "kiểm_soát", "bãi_bỏ", "hình_thành"],
            "thematic_focus": "Chủ đề tập trung vào quá trình Đổi mới toàn diện đất nước Việt Nam từ năm 1986, bao gồm các lĩnh vực kinh tế, chính trị, văn hóa - xã hội, đối ngoại; các giai đoạn đổi mới, thành tựu đạt được và bài học kinh nghiệm.",
            "relationship_patterns": {
                "Chính sách kinh tế": ["được_đề_ra_tại", "triển_khai_từ", "thay_đổi_từ", "chuyển_đổi_sang", "tạo_ra", "thúc_đẩy", "kiểm_soát", "ổn_định", "phát_triển", "cải_cách"],
                "Sự kiện chính trị": ["đánh_dấu", "mở_ra", "thông_qua", "quyết_định", "khởi_xướng", "triển_khai", "thực_hiện", "hoàn_thành", "bổ_sung"],
                "Văn kiện/Nghị quyết": ["được_thông_qua_tại", "đề_ra", "quy_định", "định_hướng", "chỉ_đạo", "cam_kết", "tạo_cơ_sở", "làm_căn_cứ", "bổ_sung"],
                "Chỉ tiêu kinh tế": ["tăng_lên", "giảm_xuống", "đạt_mức", "vượt_mức", "phản_ánh", "thể_hiện", "so_sánh_với", "thay_đổi_từ", "cải_thiện"],
                "Thành tựu phát triển": ["đạt_được", "thể_hiện_qua", "phản_ánh", "khẳng_định", "chứng_minh", "góp_phần_vào", "nâng_cao", "cải_thiện", "tăng_cường"],
                "Chiến lược phát triển": ["được_xác_định_tại", "hướng_tới", "tập_trung_vào", "bao_gồm", "nhằm_mục_đích", "đặt_trọng_tâm", "ưu_tiên"],
                "Tổ chức quốc tế": ["tham_gia", "ký_kết", "hợp_tác", "đàm_phán", "gia_nhập", "trở_thành_thành_viên", "tuân_thủ", "thực_hiện", "phê_chuẩn"],
                "Hiệp định thương mại": ["được_ký_kết", "có_hiệu_lực", "quy_định", "cam_kết", "tạo_điều_kiện", "thúc_đẩy", "mở_rộng", "ràng_buộc"],
                "Công trình hạ tầng": ["được_xây_dựng", "hoàn_thành", "đưa_vào_sử_dụng", "phục_vụ", "kết_nối", "nâng_cao", "hiện_đại_hóa", "cải_tạo"]
            },
            "context_strategy": "doi_moi_phase_based",
            "window_size": 12,
            "step_size": 6,
            "doi_moi_periods": {
                "1986_1995": "Giai đoạn khởi đầu Đổi mới (1986-1995)",
                "1996_2006": "Giai đoạn đẩy mạnh CNH-HĐH, hội nhập kinh tế quốc tế (1996-2006)",
                "2006_nay": "Giai đoạn tiếp tục đẩy mạnh CNH-HĐH, hội nhập quốc tế sâu rộng (2006-nay)"
            },
            "key_milestones": {
                "1986": "Đại hội VI - Khởi xướng Đổi mới",
                "1989": "Bãi bỏ tem phiếu",
                "1991": "Đại hội VII - Bổ sung đường lối Đổi mới",
                "1993": "Hoàn thành đường dây 500 kV Bắc-Nam",
                "1996": "Đại hội VIII - Đẩy mạnh CNH-HĐH",
                "2006": "Đại hội X - Đẩy mạnh toàn diện Đổi mới",
                "2015": "Hoàn thành Mục tiêu Thiên niên kỷ",
                "2020": "Đạt nhiều thành tựu phát triển"
            }
        },
        "Chủ đề 5": {
            "topic_name": "LỊCH SỬ ĐỐI NGOẠI CỦA VIỆT NAM THỜI CẬN – HIỆN ĐẠI",
            "focus_entities": ["Nhân Vật Lịch Sử", "Tổ chức Chính trị", "Quốc gia", "Hiệp định/Hội nghị", "Sự kiện Đối ngoại", "Mặt trận/Tổ chức Quốc tế", "Giai đoạn Lịch sử", "Chính sách Đối ngoại", "Hoạt động Ngoại giao", "Liên minh/Hợp tác"],
            "key_relationships": ["thành_lập", "tham_gia", "tham_gia_thành_lập", "ký_kết", "thiết_lập_quan_hệ", "gia_nhập", "đàm_phán_với", "hợp_tác_với", "tranh_thủ_ủng_hộ", "vận_động", "tiếp_xúc_với", "tìm_kiếm_giúp_đỡ", "phối_hợp_với", "ủng_hộ", "chống_lại", "giải_quyết_xung_đột", "bình_thường_hóa_quan_hệ", "nâng_cấp_quan_hệ", "thành_lập_tại", "hoạt_động_tại", "gửi_đại_biểu", "cử_người_liên_lạc", "tổ_chức_hội_nghị", "thông_qua", "phê_chuẩn", "cam_kết", "đấu_tranh_đòi", "tranh_thủ_thời_gian", "chuẩn_bị", "mở_rộng_quan_hệ", "củng_cố_quan_hệ"],
            "thematic_focus": "Chủ đề tập trung vào hoạt động đối ngoại của Việt Nam qua các thời kỳ lịch sử: Thời kỳ đấu tranh giành độc lập, Kháng chiến chống Pháp, Kháng chiến chống Mỹ, Thời kỳ 1975-1985, Thời kỳ Đổi mới (1986-nay).",
            "relationship_patterns": {
                "Nhân Vật Lịch Sử": ["thành_lập", "tham_gia_thành_lập", "tham_gia", "ký_kết", "đàm_phán_với", "tiếp_xúc_với", "tìm_kiếm_giúp_đỡ", "vận_động", "hoạt_động_tại", "gửi_đại_biểu", "cử_người_liên_lạc", "phối_hợp_với", "ủng_hộ"],
                "Tổ chức Chính trị": ["thành_lập", "tham_gia", "phối_hợp_với", "ủng_hộ", "chống_lại", "tranh_thủ_ủng_hộ", "thiết_lập_quan_hệ", "đấu_tranh_đòi", "tổ_chức_hội_nghị", "thông_qua", "cam_kết"],
                "Quốc gia": ["thiết_lập_quan_hệ", "bình_thường_hóa_quan_hệ", "nâng_cấp_quan_hệ", "hợp_tác_với", "đàm_phán_với", "ký_kết", "gia_nhập", "ủng_hộ", "chống_lại", "giải_quyết_xung_đột", "tranh_thủ_thời_gian"],
                "Hiệp định/Hội nghị": ["được_ký_kết_tại", "được_thông_qua_tại", "liên_quan_đến", "giải_quyết", "cam_kết", "ghi_nhận", "phê_chuẩn", "đánh_dấu"],
                "Sự kiện Đối ngoại": ["diễn_ra_tại", "liên_quan_đến", "dẫn_đến", "đánh_dấu", "tạo_bước_ngoặt", "mở_ra", "thúc_đẩy", "ngăn_chặn"],
                "Mặt trận/Tổ chức Quốc tế": ["tham_gia", "gia_nhập", "thành_lập", "ủng_hộ", "phối_hợp_với", "tranh_thủ_ủng_hộ", "tham_gia_thành_lập", "đại_diện_cho"]
            },
            "context_strategy": "diplomacy_timeline_based",
            "window_size": 10,
            "step_size": 5,
            "historical_periods": {
                "1900_1945": "Đấu tranh giành độc lập (1900-1945)",
                "1945_1954": "Kháng chiến chống Pháp (1945-1954)",
                "1954_1975": "Kháng chiến chống Mỹ (1954-1975)",
                "1975_1985": "Thời kỳ sau thống nhất (1975-1985)",
                "1986_nay": "Thời kỳ Đổi mới (1986-nay)"
            },
            "key_diplomatic_milestones": {
                "1905": "Phan Bội Châu sang Nhật Bản tìm sự giúp đỡ",
                "1912": "Thành lập Việt Nam Quang phục hội",
                "1920": "Nguyễn Ái Quốc tham gia sáng lập Đảng Cộng sản Pháp",
                "1925": "Thành lập Hội Liên hiệp các dân tộc bị áp bức ở Á Đông",
                "1946": "Ký Hiệp định Sơ bộ và Tạm ước Việt - Pháp",
                "1950": "Thiết lập quan hệ với Trung Quốc, Liên Xô",
                "1954": "Ký Hiệp định Giơ-ne-vơ",
                "1973": "Ký Hiệp định Pa-ri",
                "1978": "Việt Nam gia nhập SEV",
                "1991": "Bình thường hóa với Trung Quốc",
                "1995": "Bình thường hóa với Mỹ, gia nhập ASEAN",
                "2007": "Gia nhập WTO",
                "2008": "Ủy viên không thường trực HĐBA LHQ lần 1",
                "2020": "Ủy viên không thường trực HĐBA LHQ lần 2"
            }
        },
        "Chủ đề 6": {
            "topic_name": "HỒ CHÍ MINH TRONG LỊCH SỬ VIỆT NAM",
            "focus_entities": ["Nhân Vật Lịch Sử (Hồ Chí Minh và liên quan)", "Sự kiện Lịch sử", "Tổ chức Cách mạng", "Địa điểm Lịch sử", "Văn kiện/Tác phẩm", "Giai đoạn Cuộc đời", "Phong trào Cách mạng", "Chiến dịch/Trận đánh", "Di tích/Bảo tàng", "Tư tưởng/Đạo đức"],
            "key_relationships": ["sinh_ra_tại", "lớn_lên_tại", "học_tập_tại", "tham_gia", "thành_lập", "sáng_lập", "chủ_trì", "lãnh_đạo", "chỉ_đạo", "soạn_thảo", "viết", "đọc", "tuyên_bố", "kêu_gọi", "vận_động", "tìm_đường_cứu_nước", "đến_với_chủ_nghĩa", "trở_thành", "được_bầu_làm", "được_cử_làm", "trực_tiếp_lãnh_đạo", "chỉ_huy", "huấn_luyện", "đào_tạo", "truyền_bá", "tố_cáo", "phê_phán", "đấu_tranh", "khởi_xướng", "triệu_tập", "thông_qua", "quyết_định", "lựa_chọn", "chuyển_về", "quay_trở_lại", "ra_đi", "trở_về", "qua_đời_tại", "được_tôn_vinh", "được_đặt_tên", "để_lại_di_sản", "trở_thành_tấm_gương", "cống_hiến_trọn_đời", "ảnh_hưởng_đến", "được_kính_trọng_bởi"],
            "thematic_focus": "Chủ đề tập trung vào cuộc đời, sự nghiệp và di sản của Chủ tịch Hồ Chí Minh: Thời niên thiếu, hành trình tìm đường cứu nước, chuẩn bị thành lập Đảng, trực tiếp lãnh đạo cách mạng, lãnh đạo kháng chiến chống Pháp và chống Mỹ, di sản và ảnh hưởng.",
            "relationship_patterns": {
                "Nhân Vật Lịch Sử (Hồ Chí Minh và liên quan)": ["sinh_ra_tại", "lớn_lên_tại", "học_tập_tại", "tham_gia", "thành_lập", "sáng_lập", "lãnh_đạo", "chỉ_đạo", "soạn_thảo", "viết", "đọc", "tuyên_bố", "kêu_gọi", "tìm_đường_cứu_nước", "đến_với_chủ_nghĩa", "trở_thành", "được_bầu_làm", "được_cử_làm", "trực_tiếp_lãnh_đạo", "huấn_luyện", "đào_tạo", "truyền_bá", "tố_cáo", "phê_phán", "đấu_tranh", "khởi_xướng", "triệu_tập", "ra_đi", "trở_về", "qua_đời_tại", "cống_hiến_trọn_đời"],
                "Sự kiện Lịch sử": ["được_khởi_xướng_bởi", "được_lãnh_đạo_bởi", "được_chỉ_đạo_bởi", "diễn_ra_tại", "đánh_dấu_bởi", "liên_quan_đến", "dẫn_đến", "thành_công_nhờ"],
                "Tổ chức Cách mạng": ["được_thành_lập_bởi", "được_sáng_lập_bởi", "được_lãnh_đạo_bởi", "tham_gia_bởi", "đào_tạo_bởi", "truyền_bá_bởi", "do...chủ_trì"],
                "Địa điểm Lịch sử": ["nơi_sinh", "nơi_lớn_lên", "nơi_học_tập", "nơi_hoạt_động", "nơi_thành_lập", "nơi_lãnh_đạo", "nơi_qua_đời", "được_đặt_tên_theo"],
                "Văn kiện/Tác phẩm": ["được_soạn_thảo_bởi", "được_viết_bởi", "được_đọc_bởi", "được_tuyên_bố_bởi", "chứa_tư_tưởng_của", "phản_ánh_quan_điểm_của"],
                "Tư tưởng/Đạo đức": ["được_hình_thành_bởi", "được_phát_triển_bởi", "được_truyền_bá_bởi", "ảnh_hưởng_đến", "trở_thành_tấm_gương_cho", "được_học_tập_theo"]
            },
            "context_strategy": "ho_chi_minh_life_phases",
            "window_size": 8,
            "step_size": 4,
            "life_phases": {
                "1890_1911": "Thời niên thiếu và hoạt động đầu tiên",
                "1911_1920": "Hành trình tìm đường cứu nước",
                "1920_1930": "Chuẩn bị thành lập Đảng",
                "1930_1941": "Hoạt động ở nước ngoài",
                "1941_1945": "Trực tiếp lãnh đạo cách mạng",
                "1945_1954": "Lãnh đạo kháng chiến chống Pháp",
                "1954_1969": "Lãnh đạo kháng chiến chống Mỹ",
                "1969_nay": "Di sản và ảnh hưởng"
            },
            "key_milestones": {
                "1890": "Sinh ra tại làng Sen, Nam Đàn, Nghệ An",
                "1911": "Ra đi tìm đường cứu nước từ Bến Nhà Rồng",
                "1920": "Đến với chủ nghĩa Mác-Lênin, thành lập Đảng Cộng sản Pháp",
                "1930": "Thành lập Đảng Cộng sản Việt Nam",
                "1941": "Về nước trực tiếp lãnh đạo cách mạng",
                "1945": "Đọc Tuyên ngôn Độc lập, thành lập nước VNDCCH",
                "1954": "Lãnh đạo chiến thắng Điện Biên Phủ",
                "1969": "Qua đời tại Hà Nội"
            }
        }
    }
    
    @staticmethod
    def get_topic_config(topic_name: str) -> Dict[str, Any]:
        """Cấu hình riêng cho từng chủ đề."""
        return TopicProcessor.TOPIC_CONFIGS.get(topic_name, {})
    
    @staticmethod
    def create_topic_prompt(topic_name: str, window_text: str, existing_entities_str: str, **kwargs) -> str:
        """Tạo prompt đặc thù cho chủ đề."""
        topic_config = TopicProcessor.get_topic_config(topic_name)
        if not topic_config:
            # Pass empty dict as topic_config for unknown topics
            return TopicProcessor._create_default_prompt(window_text, existing_entities_str, {}, **kwargs)
        
        prompt_methods = {
            "Chủ đề 1": TopicProcessor._create_topic1_prompt,
            "Chủ đề 2": TopicProcessor._create_asean_prompt,
            "Chủ đề 3": TopicProcessor._create_vietnam_war_prompt,
            "Chủ đề 4": TopicProcessor._create_doi_moi_prompt,
            "Chủ đề 5": TopicProcessor._create_diplomacy_prompt,
            "Chủ đề 6": TopicProcessor._create_ho_chi_minh_prompt
        }
        
        method = prompt_methods.get(topic_name, TopicProcessor._create_default_prompt)
        return method(window_text, existing_entities_str, topic_config, **kwargs)
    
    @staticmethod
    def _create_default_prompt(window_text: str, existing_entities_str: str, topic_config: Dict[str, Any], **kwargs) -> str:
        """Prompt mặc định cho các chủ đề chưa có cấu hình đặc biệt."""
        return f"""Phân tích văn bản sau và trích xuất quan hệ giữa các thực thể:
        
VĂN BẢN:
{window_text}

DANH SÁCH THỰC THỂ:
{existing_entities_str}

YÊU CẦU: Trích xuất các quan hệ có ý nghĩa giữa các thực thể trên.
Định dạng JSON với các trường: subject_id, predicate, object_id, evidence, confidence."""
    
    @staticmethod
    def _create_topic1_prompt(window_text: str, existing_entities_str: str, topic_config: Dict[str, Any], **kwargs) -> str:
        """Prompt đặc thù cho Chủ đề 1 - Thế giới trong và sau Chiến tranh Lạnh."""
        target_entity_id = kwargs.get('target_entity_id')
        base_prompt = f"""Bạn là chuyên gia lịch sử quan hệ quốc tế, tập trung vào thời kỳ Chiến tranh Lạnh và trật tự thế giới hiện đại.

CHỦ ĐỀ PHÂN TÍCH: {topic_config['topic_name']}
TRỌNG TÂM CHỦ ĐỀ: {topic_config['thematic_focus']}

VĂN BẢN CẦN PHÂN TÍCH:
{window_text}

DANH SÁCH THỰC THỂ HIỆN CÓ (chỉ sử dụng các thực thể này):
{existing_entities_str}

QUAN HỆ ĐẶC TRƯNG CHO CHỦ ĐỀ NÀY - HÃY ƯU TIÊN:"""
        
        relationship_guidance = ""
        for rel_type, patterns in topic_config['relationship_patterns'].items():
            relationship_guidance += f"\n• Quan hệ cho thực thể loại '{rel_type}': {', '.join(patterns[:5])}"
        
        prompt_continuation = f"""
YÊU CẦU CHI TIẾT CHO CHỦ ĐỀ NÀY:
1. Tập trung vào quan hệ giữa các TỔ CHỨC QUỐC TẾ (Liên hợp quốc, NATO, Hiệp ước Vác-sa-va), QUỐC GIA có thể có các khái niệm
2. Chú ý các mối quan hệ về thành lập, tham gia, lãnh đạo trong bối cảnh Chiến tranh Lạnh
3. Phân tích quan hệ ảnh hưởng, phân chia phạm vi ảnh hưởng giữa các cường quốc
4. Nhận diện các quan hệ chuyển đổi: đối đầu → hợp tác, hai cực → đa cực
5. Chú trọng quan hệ về văn kiện, hiệp ước quốc tế và quá trình thông qua

VÍ DỤ QUAN HỆ ĐIỂN HÌNH:
- "Liên Xô, Mỹ, Anh → thành_lập → Liên hợp quốc"
- "Liên hợp quốc → thông_qua → Tuyên ngôn Nhân quyền"
- "Mỹ → lãnh_đạo → NATO"
- "Liên Xô → lãnh_đạo → Hiệp ước Vác-sa-va"
- "Hội Quốc liên → thay_thế → Liên hợp quốc"

NGUYÊN TẮC TRÍCH XUẤT:
1. Mỗi quan hệ phải có bằng chứng RÕ RÀNG trong văn bản
2. Sử dụng động từ/cụm động từ CHÍNH XÁC theo ngữ cảnh lịch sử
3. Đảm bảo subject và object là THỰC THỂ KHÁC NHAU
4. Ghi rõ câu chứng minh trong trường 'evidence'

ĐỊNH DẠNG ĐẦU RA JSON:
{{
  "relationships": [
    {{
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn cụ thể chứng minh quan hệ (trích nguyên văn)",
      "confidence": 0.9,
      "context_note": "Ghi chú ngữ cảnh bổ sung nếu cần"
    }}
  ]
}}
"""
        
        if target_entity_id:
            target_focus = f"\n\nTHỰC THỂ TRỌNG TÂM CẦN TẬP TRUNG: {target_entity_id}\nHãy tìm TẤT CẢ quan hệ có liên quan đến thực thể này trong ngữ cảnh."
            prompt_continuation = target_focus + prompt_continuation
        
        return base_prompt + relationship_guidance + prompt_continuation
    
    @staticmethod
    def _create_asean_prompt(window_text: str, existing_entities_str: str, topic_config: Dict[str, Any], **kwargs) -> str:
        """Prompt đặc thù cho Chủ đề 2 - ASEAN."""
        target_entity_id = kwargs.get('target_entity_id')
        asean_phase = kwargs.get('asean_phase')
        
        phase_info = ""
        if asean_phase:
            phase_info = f"\nGIAI ĐOẠN PHÂN TÍCH: {asean_phase}\n"
        
        base_prompt = f"""Bạn là chuyên gia về ASEAN và hội nhập khu vực Đông Nam Á. Hãy trích xuất các mối quan hệ lịch sử và thể chế quan trọng liên quan đến ASEAN.

CHỦ ĐỀ: {topic_config['topic_name']}
{phase_info}
TRỌNG TÂM: {topic_config['thematic_focus']}

VĂN BẢN CẦN PHÂN TÍCH:
{window_text}

DANH SÁCH THỰC THỂ CÓ THỂ SỬ DỤNG:
{existing_entities_str}

ĐẶC ĐIỂM QUAN HỆ ASEAN CẦN CHÚ Ý:
1. Quan hệ SÁNG LẬP và GIA NHẬP: Các nước thành viên với ASEAN
2. Quan hệ VĂN KIỆN: Các tuyên bố, hiệp ước quan trọng
3. Quan hệ PHÁT TRIỂN: Các giai đoạn phát triển của ASEAN
4. Quan hệ CỘNG ĐỒNG: Ba trụ cột và mối liên hệ giữa chúng
5. Quan hệ MỞ RỘNG: Từ ASEAN 5 đến ASEAN 10

QUAN HỆ ĐẶC TRƯNG CHO ASEAN - SỬ DỤNG ĐỘNG TỪ PHÙ HỢP:"""
        
        asean_specific_guidance = """
A. QUAN HỆ THÀNH LẬP VÀ MỞ RỘNG:
• thành_lập_bởi: Các nước sáng lập ASEAN
• tham_gia / gia_nhập: Các nước gia nhập sau
• mở_rộng_thành: ASEAN 5 → ASEAN 10
• trở_thành_thành_viên: Quá trình gia nhập cụ thể

B. QUAN HỆ VĂN KIỆN:
• ký_kết: Ký các tuyên bố, hiệp ước
• thông_qua: Thông qua tại hội nghị
• đề_xuất: Đưa ra sáng kiến, đề án
• phê_chuẩn: Phê chuẩn văn kiện

VÍ DỤ CỤ THỂ CHO ASEAN:
- "In-đô-nê-xi-a, Ma-lai-xi-a, Phi-líp-pin, Xin-ga-po, Thái Lan → thành_lập → ASEAN"
- "Việt Nam → gia_nhập → ASEAN (1995)"
- "ASEAN → ký_kết → Tuyên bố Băng Cốc"
- "ASEAN → mở_rộng_thành → ASEAN 10"
- "Hội nghị cấp cao ASEAN → thông_qua → Hiến chương ASEAN"

NGUYÊN TẮC QUAN TRỌNG:
1. LUÔN ghi rõ năm trong evidence nếu có (ví dụ: "năm 1995", "ngày 8-8-1967")
2. Sử dụng tên đầy đủ của các văn kiện (Tuyên bố Băng Cốc, Hiến chương ASEAN, TAC, v.v.)
3. Phân biệt rõ: sáng lập (1967) vs gia nhập (các năm sau)
4. Chú ý các mốc thời gian quan trọng trong phát triển ASEAN
5. Evidence phải rõ ràng, tốt nhất là trích nguyên văn câu có chứa thông tin

ĐỊNH DẠNG ĐẦU RA JSON:
{{
  "relationships": [
    {{
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn chứa thông tin (có năm nếu có)",
      "confidence": 0.9,
      "asean_context": "Ghi chú ngữ cảnh ASEAN nếu cần",
      "time_reference": "Năm/Thời gian được đề cập"
    }}
  ]
}}
"""
        
        if target_entity_id:
            target_focus = f"\n\nTHỰC THỂ TRỌNG TÂM: {target_entity_id}\n"
            target_type = ""
            for entity_line in existing_entities_str.split('\n'):
                if target_entity_id in entity_line:
                    if "Tổ chức khu vực" in entity_line:
                        target_type = "tổ chức"
                    elif "Quốc gia" in entity_line:
                        target_type = "quốc gia"
                    elif "Văn kiện" in entity_line:
                        target_type = "văn kiện"
                    break
            
            if target_type == "quốc gia":
                target_focus += "TÌM: Quan hệ thành viên (sáng lập/ gia nhập), vai trò, đóng góp cho ASEAN"
            elif target_type == "văn kiện":
                target_focus += "TÌM: Ai ký/ thông qua, tác động đến ASEAN, liên quan đến sự kiện nào"
            elif target_type == "tổ chức":
                target_focus += "TÌM: Thành lập bởi ai, phát triển thế nào, các văn kiện liên quan"
            
            asean_specific_guidance = target_focus + asean_specific_guidance
        
        return base_prompt + asean_specific_guidance
    
    @staticmethod
    def _create_vietnam_war_prompt(window_text: str, existing_entities_str: str, topic_config: Dict[str, Any], **kwargs) -> str:
        """Prompt đặc thù cho Chủ đề 3 - Lịch sử quân sự Việt Nam."""
        target_entity_id = kwargs.get('target_entity_id')
        war_period = kwargs.get('war_period')
        
        period_info = ""
        if war_period and war_period in topic_config['war_periods']:
            period_info = f"\nGIAI ĐOẠN LỊCH SỬ: {topic_config['war_periods'][war_period]}\n"
        
        base_prompt = f"""Bạn là chuyên gia lịch sử quân sự Việt Nam, tập trung vào các cuộc chiến tranh giải phóng dân tộc và bảo vệ Tổ quốc.

CHỦ ĐỀ: {topic_config['topic_name']}
{period_info}
TRỌNG TÂM: {topic_config['thematic_focus']}

VĂN BẢN CẦN PHÂN TÍCH:
{window_text}

DANH SÁCH THỰC THỂ CÓ THỂ SỬ DỤNG:
{existing_entities_str}

YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ CHIẾN TRANH VIỆT NAM:
1. ƯU TIÊN các quan hệ QUÂN SỰ, CHÍNH TRỊ có ý nghĩa lịch sử
2. Chú trọng quan hệ LÃNH ĐẠO, CHỈ HUY trong các chiến dịch
3. Ghi rõ thời gian (năm, tháng, ngày) nếu có trong evidence
4. Sử dụng động từ CHÍNH XÁC theo ngữ cảnh chiến tranh

LOẠI QUAN HỆ ĐẶC THÙ CHO LỊCH SỬ CHIẾN TRANH VIỆT NAM:"""
        
        war_specific_guidance = """
A. QUAN HỆ LÃNH ĐẠO VÀ CHỈ HUY:
• lãnh_đạo: Đảng, cá nhân lãnh đạo phong trào, tổ chức
• chỉ_huy: Chỉ huy chiến dịch, trận đánh, lực lượng vũ trang
• phát_động: Phát động khởi nghĩa, chiến dịch, phong trào
• đề_ra: Đề ra đường lối, chiến lược, kế hoạch

B. QUAN HỆ CHIẾN SỰ:
• đánh_bại / chiến_thắng: Thắng trận, thắng chiến dịch
• tấn_công / tiến_công: Mở cuộc tấn công, tiến công
• phản_công: Phản công lại đối phương
• giải_phóng: Giải phóng địa điểm, vùng lãnh thổ
• giành_chính_quyền: Giành được chính quyền tại địa phương

VÍ DỤ CỤ THỂ:
- "Hồ Chí Minh → lãnh_đạo → Cách mạng tháng Tám"
- "Võ Nguyên Giáp → chỉ_huy → Chiến dịch Điện Biên Phủ"
- "Quân đội Việt Nam → đánh_bại → quân Pháp tại Điện Biên Phủ"
- "Chiến dịch Hồ Chí Minh → giải_phóng → Sài Gòn (30-4-1975)"
- "Quân dân Việt Nam → bảo_vệ → biên giới phía Bắc"

NGUYÊN TẮC TRÍCH XUẤT QUAN HỆ:
1. LUÔN ghi rõ THỜI GIAN trong evidence nếu có (năm 1945, ngày 2-9-1945, v.v.)
2. Sử dụng tên ĐẦY ĐỦ của các chiến dịch, sự kiện
3. Phân biệt rõ: lãnh đạo chính trị vs chỉ huy quân sự
4. Chú ý các mối quan hệ NHÂN QUẢ trong lịch sử
5. Evidence phải RÕ RÀNG, CHÍNH XÁC về mặt sự kiện

ĐỊNH DẠNG ĐẦU RA JSON:
{
  "relationships": [
    {
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn chứa thông tin (có thời gian nếu có)",
      "confidence": 0.9,
      "time_reference": "Thời gian được đề cập",
      "war_context": "Bối cảnh chiến tranh/chính trị"
    }
  ]
}
"""
        
        if target_entity_id:
            target_focus = f"\n\nTHỰC THỂ TRỌNG TÂM CẦN TẬP TRUNG: {target_entity_id}\n"
            target_type = ""
            for entity_line in existing_entities_str.split('\n'):
                if target_entity_id in entity_line:
                    if "Nhân Vật" in entity_line:
                        target_focus += "TÌM: Vai trò lãnh đạo, chỉ huy, đóng góp trong các sự kiện lịch sử"
                    elif "Chiến dịch" in entity_line:
                        target_focus += "TÌM: Ai chỉ huy, diễn ra ở đâu, kết quả, ý nghĩa"
                    elif "Sự kiện" in entity_line:
                        target_focus += "TÌM: Nguyên nhân, diễn biến, kết quả, nhân vật liên quan"
                    elif "Tổ chức" in entity_line:
                        target_focus += "TÌM: Ai thành lập, lãnh đạo, vai trò trong chiến tranh"
                    break
            
            war_specific_guidance = target_focus + war_specific_guidance
        
        return base_prompt + war_specific_guidance
    
    @staticmethod
    def _create_doi_moi_prompt(window_text: str, existing_entities_str: str, topic_config: Dict[str, Any], **kwargs) -> str:
        """Prompt đặc thù cho Chủ đề 4 - Công cuộc Đổi mới."""
        target_entity_id = kwargs.get('target_entity_id')
        period = kwargs.get('period')
        
        period_info = ""
        if period and period in topic_config['doi_moi_periods']:
            period_info = f"\nGIAI ĐOẠN ĐỔI MỚI: {topic_config['doi_moi_periods'][period]}\n"
        
        base_prompt = f"""Bạn là chuyên gia kinh tế - chính trị Việt Nam, chuyên sâu về công cuộc Đổi mới từ năm 1986.

CHỦ ĐỀ: {topic_config['topic_name']}
{period_info}
TRỌNG TÂM: {topic_config['thematic_focus']}

VĂN BẢN CẦN PHÂN TÍCH:
{window_text}

DANH SÁCH THỰC THỂ CÓ THỂ SỬ DỤNG:
{existing_entities_str}

YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ ĐỔI MỚI VIỆT NAM:
1. Tập trung vào quan hệ CHÍNH SÁCH - KẾT QUẢ, CẢI CÁCH - THÀNH TỰU
2. Chú ý các mối quan hệ giữa Đại hội Đảng - Nghị quyết - Kết quả thực hiện
3. Ghi rõ THỜI GIAN (năm) và SỐ LIỆU CỤ THỂ trong evidence khi có
4. Sử dụng động từ phù hợp với ngữ cảnh cải cách, phát triển

LOẠI QUAN HỆ ĐẶC THÙ CHO ĐỔI MỚI VIỆT NAM:"""
        
        doi_moi_guidance = """
A. QUAN HỆ CHÍNH SÁCH - SỰ KIỆN:
• khởi_xướng / đề_ra: Đại hội Đảng, cá nhân lãnh đạo đề ra đường lối Đổi mới
• thông_qua: Thông qua nghị quyết, văn kiện quan trọng tại đại hội
• triển_khai / thực_hiện: Triển khai chính sách, kế hoạch, chương trình
• chuyển_đổi_sang / cải_cách: Chuyển đổi cơ chế, cải cách thể chế kinh tế

B. QUAN HỆ KINH TẾ - PHÁT TRIỂN:
• tăng_trưởng / phát_triển_thành: Tăng trưởng GDP, phát triển thành nền kinh tế thị trường
• đạt_được / hoàn_thành: Đạt mục tiêu, hoàn thành kế hoạch, chương trình
• giảm_xuống / tăng_lên: Thay đổi các chỉ số (nghèo, lạm phát, GDP, v.v.)
• cải_thiện / nâng_cao: Cải thiện đời sống, nâng cao chất lượng tăng trưởng

VÍ DỤ CỤ THỂ:
- "Đại hội VI (1986) → khởi_xướng → công cuộc Đổi mới"
- "Việt Nam → xóa_bỏ → cơ chế kinh tế tập trung bao cấp"
- "Năm 1989 → bãi_bỏ → chế độ tem phiếu"
- "GDP Việt Nam → tăng_trưởng → trên 6%/năm"
- "Tỉ lệ hộ nghèo → giảm_xuống → từ 38.06% (1986) xuống 11.88% (2022)"

NGUYÊN TẮC TRÍCH XUẤT QUAN TRỌNG:
1. LUÔN ghi rõ NĂM và SỐ LIỆU trong evidence nếu có (ví dụ: "năm 1986", "tăng 6%/năm", "từ 38.06% xuống 11.88%")
2. Sử dụng tên ĐẦY ĐỦ của các đại hội, nghị quyết, chính sách (Đại hội VI, Nghị quyết Đổi mới, v.v.)
3. Phân biệt rõ: chủ trương/chính sách vs kết quả/thành tựu thực tế
4. Chú ý các mối quan hệ NHÂN QUẢ trong quá trình đổi mới (chính sách → kết quả)
5. Evidence phải RÕ RÀNG, có SỐ LIỆU CỤ THỂ khi nói về thành tựu, chỉ tiêu

ĐỊNH DẠNG ĐẦU RA JSON:
{
  "relationships": [
    {
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn chứa thông tin (có số liệu, thời gian nếu có)",
      "confidence": 0.9,
      "time_reference": "Thời gian được đề cập",
      "data_point": "Số liệu cụ thể nếu có",
      "policy_context": "Bối cảnh chính sách/đổi mới"
    }
  ]
}
"""
        
        if target_entity_id:
            target_focus = f"\n\nTHỰC THỂ TRỌNG TÂM CẦN TẬP TRUNG: {target_entity_id}\n"
            target_type = ""
            for entity_line in existing_entities_str.split('\n'):
                if target_entity_id in entity_line:
                    if "Sự kiện chính trị" in entity_line or "Đại hội" in entity_id:
                        target_focus += "TÌM: Các chính sách/nghị quyết được thông qua; tác động/kết quả của sự kiện"
                    elif "Chính sách kinh tế" in entity_line:
                        target_focus += "TÌM: Ai đề ra, thời gian thực hiện, kết quả đạt được"
                    elif "Thành tựu" in entity_line or "Chỉ tiêu" in entity_line:
                        target_focus += "TÌM: Nguyên nhân đạt được, quá trình, so sánh trước-sau, số liệu cụ thể"
                    elif "Tổ chức quốc tế" in entity_line or "Hiệp định" in entity_line:
                        target_focus += "TÌM: Việt Nam tham gia khi nào, kết quả hợp tác, tác động đến phát triển"
                    break
            
            doi_moi_guidance = target_focus + doi_moi_guidance
        
        return base_prompt + doi_moi_guidance
    
    @staticmethod
    def _create_diplomacy_prompt(window_text: str, existing_entities_str: str, topic_config: Dict[str, Any], **kwargs) -> str:
        """Prompt đặc thù cho Chủ đề 5 - Lịch sử Đối ngoại."""
        target_entity_id = kwargs.get('target_entity_id')
        period = kwargs.get('period')
        
        period_info = ""
        if period and period in topic_config['historical_periods']:
            period_info = f"\nGIAI ĐOẠN LỊCH SỬ: {topic_config['historical_periods'][period]}\n"
        
        base_prompt = f"""Bạn là chuyên gia lịch sử ngoại giao Việt Nam. Hãy trích xuất các mối quan hệ đối ngoại quan trọng.

CHỦ ĐỀ: {topic_config['topic_name']}
{period_info}
TRỌNG TÂM: {topic_config['thematic_focus']}

VĂN BẢN CẦN PHÂN TÍCH:
{window_text}

DANH SÁCH THỰC THỂ CÓ THỂ SỬ DỤNG:
{existing_entities_str}

ĐẶC ĐIỂM QUAN HỆ ĐỐI NGOẠI VIỆT NAM CẦN CHÚ Ý:
1. Quan hệ TÌM KIẾM SỰ GIÚP ĐỠ của các nhân vật yêu nước
2. Quan hệ THÀNH LẬP TỔ CHỨC quốc tế, liên minh
3. Quan hệ KÝ KẾT HIỆP ĐỊNH, THỎA THUẬN ngoại giao
4. Quan hệ THIẾT LẬP QUAN HỆ NGOẠI GIAO chính thức
5. Quan hệ THAM GIA TỔ CHỨC QUỐC TẾ
6. Quan hệ ĐẤU TRANH NGOẠI GIAO, VẬN ĐỘNG QUỐC TẾ
7. Quan hệ GIẢI QUYẾT XUNG ĐỘT, TRANH CHẤP

LOẠI QUAN HỆ ĐẶC THÙ CHO NGOẠI GIAO VIỆT NAM:"""
        
        diplomacy_guidance = """
A. QUAN HỆ CỦA NHÂN VẬT LỊCH SỬ:
• tìm_kiếm_giúp_đỡ_từ: Tìm sự hỗ trợ của nước ngoài cho cách mạng
• tiếp_xúc_với: Gặp gỡ, tiếp xúc với đại diện nước ngoài
• vận_động: Vận động chính phủ, tổ chức nước ngoài
• tham_gia_thành_lập: Tham gia thành lập tổ chức quốc tế
• hoạt_động_tại: Hoạt động tại nước ngoài

B. QUAN HỆ CỦA TỔ CHỨC CHÍNH TRỊ:
• thành_lập: Thành lập tổ chức, mặt trận
• tham_gia: Tham gia tổ chức quốc tế
• phối_hợp_với: Phối hợp với tổ chức nước ngoài
• tranh_thủ_ủng_hộ: Tranh thủ sự ủng hộ quốc tế
• đấu_tranh_đòi: Đấu tranh đòi quyền lợi trên trường quốc tế

VÍ DỤ CỤ THỂ:
- "Phan Bội Châu → tìm_kiếm_giúp_đỡ_từ → Nhật Bản (1905)"
- "Nguyễn Ái Quốc → tham_gia_thành_lập → Đảng Cộng sản Pháp (1920)"
- "Chính phủ VNDCCH → ký_kết → Hiệp định Sơ bộ với Pháp (6-3-1946)"
- "Việt Nam → bình_thường_hóa_quan_hệ → với Mỹ (1995)"
- "Việt Nam → gia_nhập → WTO (2007)"

NGUYÊN TẮC TRÍCH XUẤT QUAN TRỌNG:
1. LUÔN ghi rõ THỜI GIAN (năm, ngày-tháng) trong evidence nếu có (ví dụ: "năm 1905", "ngày 6-3-1946", "tháng 7-1925")
2. Sử dụng tên CHÍNH XÁC của các hiệp định, hội nghị, tổ chức (Hiệp định Giơ-ne-vơ, Hội nghị Pa-ri, ASEAN, v.v.)
3. Phân biệt rõ: thành lập vs tham gia, ký kết vs thông qua, thiết lập quan hệ vs nâng cấp quan hệ
4. Chú ý bối cảnh lịch sử cụ thể của từng giai đoạn
5. Evidence phải RÕ RÀNG, có THÔNG TIN CỤ THỂ về hoạt động đối ngoại

ĐỊNH DẠNG ĐẦU RA JSON:
{
  "relationships": [
    {
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn chứa thông tin (có thời gian, địa điểm nếu có)",
      "confidence": 0.9,
      "time_reference": "Thời gian được đề cập",
      "location_reference": "Địa điểm được đề cập",
      "diplomatic_context": "Bối cảnh đối ngoại/ngoại giao"
    }
  ]
}
"""
        
        if target_entity_id:
            target_focus = f"\n\nTHỰC THỂ TRỌNG TÂM CẦN TẬP TRUNG: {target_entity_id}\n"
            target_type = ""
            for entity_line in existing_entities_str.split('\n'):
                if target_entity_id in entity_line:
                    if "Nhân Vật" in entity_line:
                        target_focus += "TÌM: Các hoạt động đối ngoại, tìm kiếm giúp đỡ, thành lập tổ chức, tiếp xúc với nước ngoài"
                    elif "Tổ chức Chính trị" in entity_line:
                        target_focus += "TÌM: Quan hệ với tổ chức quốc tế, các nước, hoạt động vận động quốc tế"
                    elif "Quốc gia" in entity_line:
                        target_focus += "TÌM: Quan hệ ngoại giao với Việt Nam, các hiệp định đã ký, mức độ quan hệ"
                    elif "Hiệp định/Hội nghị" in entity_line:
                        target_focus += "TÌM: Ai ký kết, tại đâu, thời gian, nội dung chính"
                    elif "Mặt trận/Tổ chức Quốc tế" in entity_line:
                        target_focus += "TÌM: Việt Nam tham gia khi nào, vai trò, đóng góp"
                    break
            
            diplomacy_guidance = target_focus + diplomacy_guidance
        
        return base_prompt + diplomacy_guidance
    
    @staticmethod
    def _create_ho_chi_minh_prompt(window_text: str, existing_entities_str: str, topic_config: Dict[str, Any], **kwargs) -> str:
        """Prompt đặc thù cho Chủ đề 6 - Hồ Chí Minh."""
        target_entity_id = kwargs.get('target_entity_id')
        life_phase = kwargs.get('life_phase')
        
        phase_info = ""
        if life_phase and life_phase in topic_config['life_phases']:
            phase_info = f"\nGIAI ĐOẠN CUỘC ĐỜI: {topic_config['life_phases'][life_phase]}\n"
        
        base_prompt = f"""Bạn là chuyên gia nghiên cứu về Chủ tịch Hồ Chí Minh. Hãy trích xuất các mối quan hệ về cuộc đời và sự nghiệp của Người.

CHỦ ĐỀ: {topic_config['topic_name']}
{phase_info}
TRỌNG TÂM: {topic_config['thematic_focus']}

VĂN BẢN CẦN PHÂN TÍCH:
{window_text}

DANH SÁCH THỰC THỂ CÓ THỂ SỬ DỤNG:
{existing_entities_str}

YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ HỒ CHÍ MINH:
1. Tập trung vào các mối quan hệ GẮN LIỀN VỚI HỒ CHÍ MINH
2. Chú ý các sự kiện, địa điểm, tổ chức liên quan trực tiếp đến Người
3. Ghi rõ THỜI GIAN (năm, ngày-tháng) và ĐỊA ĐIỂM cụ thể
4. Sử dụng động từ phù hợp với từng giai đoạn cuộc đời

LOẠI QUAN HỆ ĐẶC THÙ CHO HỒ CHÍ MINH:"""
        
        ho_chi_minh_guidance = """
A. QUAN HỆ THỜI NIÊN THIẾU VÀ GIA ĐÌNH:
• sinh_ra_tại: Nơi sinh, ngày sinh
• lớn_lên_tại: Nơi lớn lên, tuổi thơ
• học_tập_tại: Trường học, thầy giáo
• thuộc_gia_đình: Cha mẹ, quê hương

B. QUAN HỆ HÀNH TRÌNH TÌM ĐƯỜNG CỨU NƯỚC:
• ra_đi_từ: Nơi bắt đầu hành trình
• đến_với: Nước, địa điểm đến
• tìm_hiểu: Tìm hiểu cuộc sống, chế độ
• đọc: Đọc tác phẩm, văn kiện quan trọng
• đến_với_chủ_nghĩa: Tiếp thu chủ nghĩa Mác-Lênin

C. QUAN HỆ THÀNH LẬP TỔ CHỨC:
• tham_gia_thành_lập: Tham gia thành lập tổ chức
• sáng_lập: Sáng lập tổ chức cách mạng
• thành_lập: Thành lập tổ chức
• chủ_trì: Chủ trì hội nghị thành lập
• soạn_thảo: Soạn thảo văn kiện, cương lĩnh

VÍ DỤ CỤ THỂ:
- "Hồ Chí Minh → sinh_ra_tại → Làng Sen, Nam Đàn, Nghệ An (19-5-1890)"
- "Hồ Chí Minh → ra_đi_tìm_đường_cứu_nước_từ → Bến Nhà Rồng (5-6-1911)"
- "Nguyễn Ái Quốc → tham_gia_thành_lập → Đảng Cộng sản Pháp (1920)"
- "Hồ Chí Minh → chủ_trì → Hội nghị thành lập Đảng Cộng sản Việt Nam (6-1-1930)"
- "Hồ Chí Minh → đọc → Tuyên ngôn Độc lập (2-9-1945)"

NGUYÊN TẮC TRÍCH XUẤT QUAN TRỌNG:
1. LUÔN ghi rõ THỜI GIAN (năm, ngày-tháng) trong evidence nếu có (ví dụ: "19-5-1890", "5-6-1911", "2-9-1945")
2. Sử dụng tên CHÍNH XÁC của Hồ Chí Minh theo từng thời kỳ: Nguyễn Sinh Cung, Nguyễn Tất Thành, Nguyễn Ái Quốc, Hồ Chí Minh
3. Chú ý mối quan hệ NHÂN QUẢ trong hành trình cách mạng
4. Evidence phải RÕ RÀNG, có THÔNG TIN CỤ THỂ về địa điểm, thời gian, sự kiện
5. Ưu tiên các quan hệ TRỰC TIẾP liên quan đến Hồ Chí Minh

ĐỊNH DẠNG ĐẦU RA JSON:
{
  "relationships": [
    {
      "subject_id": "ID_thực_thể_nguồn",
      "predicate": "động_từ_mô_tả_quan_hệ",
      "object_id": "ID_thực_thể_đích",
      "evidence": "Câu văn chứa thông tin (có thời gian, địa điểm nếu có)",
      "confidence": 0.9,
      "time_reference": "Thời gian được đề cập",
      "location_reference": "Địa điểm được đề cập",
      "historical_context": "Bối cảnh lịch sử"
    }
  ]
}
"""
        
        if target_entity_id:
            target_focus = f"\n\nTHỰC THỂ TRỌNG TÂM CẦN TẬP TRUNG: {target_entity_id}\n"
            target_type = ""
            for entity_line in existing_entities_str.split('\n'):
                if target_entity_id in entity_line:
                    if "Hồ Chí Minh" in entity_line or "Nguyễn Ái Quốc" in entity_line:
                        target_focus += "TÌM: Các sự kiện trong cuộc đời, hoạt động cách mạng, thành lập tổ chức, lãnh đạo kháng chiến"
                    elif "Sự kiện" in entity_line:
                        target_focus += "TÌM: Vai trò của Hồ Chí Minh trong sự kiện này, thời gian, địa điểm"
                    elif "Tổ chức" in entity_line:
                        target_focus += "TÌM: Hồ Chí Minh có thành lập, tham gia, lãnh đạo tổ chức này không? Thời gian nào?"
                    elif "Địa điểm" in entity_line:
                        target_focus += "TÌM: Hồ Chí Minh đã đến, hoạt động, sinh sống tại địa điểm này khi nào?"
                    elif "Văn kiện" in entity_line:
                        target_focus += "TÌM: Hồ Chí Minh có soạn thảo, viết, đọc văn kiện này không? Trong hoàn cảnh nào?"
                    break
            
            ho_chi_minh_guidance = target_focus + ho_chi_minh_guidance
        
        return base_prompt + ho_chi_minh_guidance

def format_entities_for_prompt(entity_lookup: Dict[str, Dict]) -> str:
    """Định dạng entities cho prompt với thông tin chi tiết."""
    entity_lines = []
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 4"]
    
    for entity_id, entity in entity_lookup.items():
        if entity_id == entity['id']:  # Chỉ hiển thị primary entities
            entity_type = entity.get('type', 'Unknown')
            labels = entity.get('context_labels', entity.get('label', []))
            description = entity.get('description', '')[:100]
            
            entity_info = f"- {entity_id}"
            if labels:
                entity_info += f" [Tên: {', '.join(labels[:3])}]"
            entity_info += f" (Loại: {entity_type})"
            if description:
                entity_info += f" - {description}"
            
            entity_lines.append(entity_info)
    
    return "\n".join(entity_lines[:50])

def assess_evidence_quality(evidence: str) -> float:
    """Đánh giá chất lượng của evidence (dùng chung)."""
    quality_score = 0.7
    
    if len(evidence) > 30:
        quality_score += 0.1
    if len(evidence) > 50:
        quality_score += 0.1
    
    if '"' in evidence or "'" in evidence:
        quality_score += 0.1
    
    if re.search(r'\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}', evidence) or re.search(r'năm\s+\d{4}', evidence):
        quality_score += 0.1
    
    return min(1.0, quality_score)

# ============================================================================
# HÀM XỬ LÝ ĐẶC THÙ CHO CHỦ ĐỀ 1
# ============================================================================

def process_topic_1_file(file_path: str, entity_lookup: Dict[str, Dict], existing_kg: Dict) -> Dict:
    """Xử lý file thuộc Chủ đề 1 với chiến lược đặc thù."""
    
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 1"]
    
    print(f"\n{'='*60}")
    print(f"XỬ LÝ CHỦ ĐỀ 1: {topic_config['topic_name']}")
    print(f"Trọng tâm: {topic_config['thematic_focus'][:100]}...")
    print(f"{'='*60}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return existing_kg
    
    topic, lesson = extract_topic_and_lesson(file_path)
    file_info = {
        'file_path': file_path,
        'topic': topic,
        'lesson': lesson,
        'topic_config': topic_config['topic_name']
    }
    
    all_entities = existing_kg.get('entities', [])
    prioritized_entities = []
    
    for entity in all_entities:
        if entity.get('type') in topic_config['focus_entities']:
            prioritized_entities.append(entity)
    
    related_entity_ids = set()
    for entity in prioritized_entities:
        for occ in entity.get('original_text', []):
            if occ.get('topic') == topic and occ.get('lesson') == lesson:
                exact_text = occ.get('exact_text', '').lower()
                for other_entity in all_entities:
                    if other_entity['id'] == entity['id']:
                        continue
                    for label in other_entity.get('label', []):
                        if label.lower() in exact_text and len(label) > 3:
                            related_entity_ids.add(other_entity['id'])
                            break
    
    filtered_entity_lookup = {}
    for entity in all_entities:
        if (entity.get('type') in topic_config['focus_entities'] or 
            entity['id'] in related_entity_ids):
            
            entity_copy = entity.copy()
            labels_in_context = []
            
            for occ in entity.get('original_text', []):
                if occ.get('topic') == topic and occ.get('lesson') == lesson:
                    labels_in_context.extend(occ.get('labels', entity.get('label', [])))
            
            if labels_in_context:
                entity_copy['context_labels'] = list(set(labels_in_context))
            else:
                entity_copy['context_labels'] = entity.get('label', [])
            
            filtered_entity_lookup[entity['id']] = entity_copy
            
            for label in entity_copy['context_labels']:
                if label not in filtered_entity_lookup:
                    filtered_entity_lookup[label] = entity_copy
    
    print(f"Đã lọc được {len(filtered_entity_lookup)} thực thể/trích dẫn cho chủ đề này")
    
    sentences = split_into_sentences(content)
    key_sections = identify_key_sections_topic1(sentences)
    
    all_relationships = []
    
    for section_name, section_sentences in key_sections.items():
        print(f"\nPhân tích đoạn: {section_name} ({len(section_sentences)} câu)")
        
        windows = create_overlapping_windows(
            section_sentences, 
            window_size=topic_config['window_size'],
            step=topic_config['step_size']
        )
        
        for window_idx, (start_idx, window_sentences) in enumerate(windows[:10]):
            print(f"  Window {window_idx+1}/{len(windows)}: ", end="", flush=True)
            
            existing_entities_str = format_entities_for_prompt(filtered_entity_lookup)
            window_text = " ".join(window_sentences)
            
            key_entities_in_window = []
            for entity_id, entity in filtered_entity_lookup.items():
                if entity_id == entity['id']:
                    for label in entity.get('context_labels', []):
                        if label in window_text and len(label) > 3:
                            key_entities_in_window.append(entity_id)
                            break
            
            if not key_entities_in_window:
                print("Không có thực thể quan trọng -> Bỏ qua")
                continue
            
            for target_entity_id in key_entities_in_window[:2]:
                prompt = TopicProcessor.create_topic_prompt(
                    "Chủ đề 1", 
                    window_text, 
                    existing_entities_str,
                    target_entity_id=target_entity_id
                )
                
                result = extract_relationships_with_topic_prompt(
                    prompt,
                    start_idx,
                    window_sentences,
                    filtered_entity_lookup,
                    file_info,
                    target_entity_id
                )
                
                if result:
                    relationships = result.get('relationships', [])
                    if relationships:
                        all_relationships.extend(relationships)
                        print(f"{len(relationships)}R ", end="", flush=True)
            
            print("")
            time.sleep(2)
    
    processed_relationships = post_process_topic1_relationships(all_relationships)
    
    triplets = []
    for rel in processed_relationships:
        triplet = {
            'subject_id': rel['subject_id'],
            'predicate': rel['predicate'],
            'object_id': rel['object_id'],
            'properties': rel.get('properties', {}),
            'metadata': {
                'extraction_method': 'topic_1_specialized',
                'file_info': file_info,
                'evidence_count': len(rel.get('supporting_sentences', [])),
                'topic_specific': True,
                'topic_focus': topic_config['topic_name'],
                'section': rel.get('section', 'general')
            },
            'supporting_sentences': rel.get('supporting_sentences', []),
            'confidence': rel.get('confidence', 0.9),
            'occurrence_count': rel.get('occurrence_count', 1)
        }
        triplets.append(triplet)
    
    existing_triplets = existing_kg.get('triplets', [])
    existing_entities = existing_kg.get('entities', [])
    
    triplet_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
    for triplet in triplets:
        key = (triplet['subject_id'], triplet['predicate'], triplet['object_id'])
        if key not in triplet_keys:
            existing_triplets.append(triplet)
            triplet_keys.add(key)
    
    return {
        'entities': existing_entities,
        'triplets': existing_triplets,
        'diagnostics': {
            'total_extracted': len(all_relationships),
            'after_processing': len(triplets),
            'key_sections_processed': len(key_sections)
        }
    }

def identify_key_sections_topic1(sentences: List[str]) -> Dict[str, List[str]]:
    """Nhận diện các đoạn quan trọng trong văn bản Chủ đề 1."""
    sections = {
        'liên_hợp_quốc': [],
        'chiến_tranh_lạnh': [],
        'hội_nghị': [],
        'hiệp_ước': [],
        'quan_hệ_quốc_tế': [],
        'khác': []
    }
    
    topic1_keywords = {
        'liên_hợp_quốc': ['liên hợp quốc', 'lhq', 'hiến chương', 'đại hội đồng', 'hội đồng bảo an'],
        'chiến_tranh_lạnh': ['chiến tranh lạnh', 'hai cực', 'đối đầu', 'xô - mỹ', 'nato', 'vác-sa-va'],
        'hội_nghị': ['hội nghị', 'i-an-ta', 'tê-hê-ran', 'xan phran-xi-xcô', 'họp', 'đại hội'],
        'hiệp_ước': ['hiệp ước', 'hiến chương', 'công ước', 'tuyên bố', 'văn kiện', 'nghị quyết'],
        'quan_hệ_quốc_tế': ['quan hệ quốc tế', 'ngoại giao', 'hợp tác', 'đối thoại', 'ảnh hưởng', 'phạm vi']
    }
    
    current_section = 'khác'
    section_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        detected_section = None
        for section_name, keywords in topic1_keywords.items():
            for keyword in keywords:
                if keyword in sentence_lower:
                    detected_section = section_name
                    break
            if detected_section:
                break
        
        if detected_section:
            if section_sentences:
                sections[current_section].extend(section_sentences)
            
            current_section = detected_section
            section_sentences = [sentence]
        else:
            section_sentences.append(sentence)
    
    if section_sentences:
        sections[current_section].extend(section_sentences)
    
    return {k: v for k, v in sections.items() if v}

def extract_relationships_with_topic_prompt(prompt: str, start_idx: int, window_sentences: List[str], 
                                          entity_lookup: Dict[str, Dict], file_info: Dict[str, str], 
                                          target_entity_id: str = None) -> Optional[Dict]:
    """Extract relationships với prompt đặc thù theo chủ đề - sử dụng DeepSeek API."""
    global API_REQUEST_COUNT
    
    API_REQUEST_COUNT += 1
    print(f"[DeepSeek #{API_REQUEST_COUNT}] Window {start_idx}", end=" ")
    
    # Gọi DeepSeek API
    result = call_deepseek_api(prompt, max_retries=3)
    
    if not result:
        print("No response")
        return None
    
    validated_relationships = []
    
    for rel in result.get('relationships', []):
        if validate_relationship_topic1(rel, entity_lookup):
            rel['window_info'] = {
                'start_idx': start_idx,
                'sentences': window_sentences[:3],
                'file_info': file_info,
                'target_entity': target_entity_id
            }
            
            evidence_quality = assess_evidence_quality(rel.get('evidence', ''))
            rel['confidence'] = min(0.95, rel.get('confidence', 0.8) * evidence_quality)
            
            validated_relationships.append(rel)
    
    print(f"-> {len(validated_relationships)} rels")
    
    return {
        'relationships': validated_relationships,
        'window_index': start_idx,
        'target_entity': target_entity_id
    }

def validate_relationship_topic1(relationship: Dict, entity_lookup: Dict[str, Dict]) -> bool:
    """Validate relationship với tiêu chí giảm nhẹ cho chủ đề 1."""
    subject_id = relationship.get('subject_id', '').strip()
    object_id = relationship.get('object_id', '').strip()
    predicate = relationship.get('predicate', '').strip()
    evidence = relationship.get('evidence', '').strip()
    
    # Kiểm tra cơ bản
    if not subject_id or not object_id or not predicate:
        return False
    
    if subject_id == object_id:
        return False
    
    # Giảm nhẹ: chỉ cần một thực thể tồn tại
    subject_found = False
    object_found = False
    
    # Kiểm tra trong entity_lookup và labels
    for entity in entity_lookup.values():
        if entity.get('id') == subject_id:
            subject_found = True
        if entity.get('id') == object_id:
            object_found = True
        
        if not subject_found:
            for label in entity.get('context_labels', entity.get('label', [])):
                if subject_id.lower() in label.lower() or label.lower() in subject_id.lower():
                    subject_found = True
                    break
        
        if not object_found:
            for label in entity.get('context_labels', entity.get('label', [])):
                if object_id.lower() in label.lower() or label.lower() in object_id.lower():
                    object_found = True
                    break
    
    # Chấp nhận nếu ít nhất một thực thể được tìm thấy
    if not subject_found and not object_found:
        return False
    
    # Giảm nhẹ độ dài predicate
    if len(predicate) < 2:
        return False
    
    # Giảm nhẹ độ dài evidence
    if len(evidence) < 10:
        return False
    
    # Không bắt buộc phải tìm thấy cả subject và object trong evidence
    return True

def post_process_topic1_relationships(relationships: List[Dict]) -> List[Dict]:
    """Hậu xử lý relationships cho chủ đề 1."""
    relationship_groups = defaultdict(list)
    
    for rel in relationships:
        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
        relationship_groups[key].append(rel)
    
    merged_relationships = []
    
    for key, rel_list in relationship_groups.items():
        if not rel_list:
            continue
        
        base_rel = rel_list[0].copy()
        base_rel['occurrence_count'] = len(rel_list)
        
        all_sentences = []
        for rel in rel_list:
            evidence = rel.get('evidence', '')
            window_info = rel.get('window_info', {})
            
            sentence_info = {
                'evidence': evidence,
                'window_start': window_info.get('start_idx', 0),
                'file_info': window_info.get('file_info', {}),
                'timestamp': time.time()
            }
            
            if not any(s['evidence'] == evidence for s in all_sentences):
                all_sentences.append(sentence_info)
        
        base_rel['supporting_sentences'] = all_sentences
        
        total_confidence = 0
        for rel in rel_list:
            confidence = rel.get('confidence', 0.8)
            evidence_quality = assess_evidence_quality(rel.get('evidence', ''))
            weighted_confidence = confidence * evidence_quality
            total_confidence += weighted_confidence
        
        if rel_list:
            base_rel['confidence'] = min(0.95, total_confidence / len(rel_list))
        
        merged_relationships.append(base_rel)
    
    merged_relationships.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    return merged_relationships

# ============================================================================
# HÀM XỬ LÝ ĐẶC THÙ CHO CHỦ ĐỀ 2 (ASEAN)
# ============================================================================

def process_asean_file(file_path: str, entity_lookup: Dict[str, Dict], existing_kg: Dict) -> Dict:
    """Xử lý file ASEAN với chiến lược đặc thù."""
    
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 2"]
    
    print(f"\n{'='*60}")
    print(f"XỬ LÝ ASEAN: {topic_config['topic_name']}")
    print(f"{'='*60}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return existing_kg
    
    topic, lesson = extract_topic_and_lesson(file_path)
    file_info = {
        'file_path': file_path,
        'topic': topic,
        'lesson': lesson,
        'topic_config': topic_config['topic_name'],
        'asean_focus': True
    }
    
    all_entities = existing_kg.get('entities', [])
    asean_priority_entities = []
    
    priority_order = [
        "ASEAN", "Hiệp hội các quốc gia Đông Nam Á",
        "Tuyên bố Băng Cốc", "Hiến chương ASEAN",
        "Cộng đồng ASEAN", "AEC", "APSC", "ASCC"
    ]
    
    asean_members = topic_config['asean_founding_members'] + [
        "Việt Nam", "Brunei", "Lào", "Myanmar", "Campuchia"
    ]
    
    for entity in all_entities:
        entity_id = entity['id']
        labels = entity.get('label', [])
        
        priority_score = 0
        
        for priority_term in priority_order:
            if any(priority_term in str(label) for label in labels) or priority_term in entity_id:
                priority_score += 3
        
        for member in asean_members:
            if any(member in str(label) for label in labels) or member in entity_id:
                priority_score += 2
        
        if any('asean' in str(label).lower() for label in labels) or 'asean' in entity_id.lower():
            priority_score += 1
        
        if entity.get('type') in ["Văn kiện/Hiệp định", "Hiệp ước"]:
            priority_score += 1
        
        if priority_score > 0:
            entity['asean_priority'] = priority_score
            asean_priority_entities.append(entity)
    
    asean_priority_entities.sort(key=lambda x: x.get('asean_priority', 0), reverse=True)
    
    filtered_entity_lookup = {}
    for entity in asean_priority_entities[:50]:
        entity_copy = entity.copy()
        
        labels_in_context = []
        for occ in entity.get('original_text', []):
            if occ.get('topic') == topic and occ.get('lesson') == lesson:
                labels_in_context.extend(occ.get('labels', entity.get('label', [])))
        
        if labels_in_context:
            entity_copy['context_labels'] = list(set(labels_in_context))
        else:
            entity_copy['context_labels'] = entity.get('label', [])
        
        filtered_entity_lookup[entity['id']] = entity_copy
        
        for label in entity_copy['context_labels']:
            if label not in filtered_entity_lookup:
                filtered_entity_lookup[label] = entity_copy
    
    print(f"Đã chọn {len(filtered_entity_lookup)} thực thể ưu tiên cho ASEAN")
    
    sentences = split_into_sentences(content)
    asean_phases = identify_asean_phases(sentences)
    
    all_relationships = []
    
    for phase_name, phase_sentences in asean_phases.items():
        if not phase_sentences:
            continue
            
        print(f"\nGiai đoạn: {phase_name} ({len(phase_sentences)} câu)")
        
        windows = create_overlapping_windows(
            phase_sentences,
            window_size=topic_config['window_size'],
            step=topic_config['step_size']
        )
        
        for window_idx, (start_idx, window_sentences) in enumerate(windows[:10]):
            print(f"  Window {window_idx+1}/{min(5, len(windows))}: ", end="", flush=True)
            
            phase_filtered_entities = filter_entities_for_asean_phase(
                filtered_entity_lookup, phase_name, window_sentences
            )
            
            if len(phase_filtered_entities) < 2:
                print("Ít thực thể -> Bỏ qua")
                continue
            
            existing_entities_str = format_asean_entities_for_prompt(phase_filtered_entities, phase_name)
            window_text = " ".join(window_sentences)
            
            asean_key_entities = []
            for entity_id, entity in phase_filtered_entities.items():
                if entity_id == entity['id']:
                    window_text_lower = window_text.lower()
                    entity_labels = entity.get('context_labels', [])
                    
                    for label in entity_labels:
                        if label.lower() in window_text_lower and len(label) > 3:
                            asean_key_entities.append(entity_id)
                            break
            
            if not asean_key_entities:
                print("Không có thực thể ASEAN -> Bỏ qua")
                continue
            
            primary_entity = asean_key_entities[0]
            
            prompt = TopicProcessor.create_topic_prompt(
                    "Chủ đề 2", 
                    window_text, 
                    existing_entities_str,
                    target_entity_id=primary_entity
                )
            
            result = extract_asean_relationships(
                prompt,
                start_idx,
                window_sentences,
                phase_filtered_entities,
                file_info,
                primary_entity,
                phase_name
            )
            
            if result:
                relationships = result.get('relationships', [])
                if relationships:
                    all_relationships.extend(relationships)
                    print(f"{len(relationships)}R ", end="", flush=True)
            
            print("")
            time.sleep(2)
    
    processed_relationships = post_process_asean_relationships(all_relationships)
    
    triplets = []
    for rel in processed_relationships:
        triplet = {
            'subject_id': rel['subject_id'],
            'predicate': rel['predicate'],
            'object_id': rel['object_id'],
            'properties': {
                'asean_context': rel.get('asean_context', ''),
                'time_reference': rel.get('time_reference', ''),
                'phase': rel.get('phase', '')
            },
            'metadata': {
                'extraction_method': 'asean_specialized',
                'file_info': file_info,
                'evidence_count': len(rel.get('supporting_sentences', [])),
                'asean_phase': rel.get('phase', 'unknown'),
                'priority_score': rel.get('priority_score', 1)
            },
            'supporting_sentences': rel.get('supporting_sentences', []),
            'confidence': rel.get('confidence', 0.9),
            'occurrence_count': rel.get('occurrence_count', 1)
        }
        triplets.append(triplet)
    
    existing_triplets = existing_kg.get('triplets', [])
    existing_entities = existing_kg.get('entities', [])
    
    triplet_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
    for triplet in triplets:
        key = (triplet['subject_id'], triplet['predicate'], triplet['object_id'])
        if key not in triplet_keys:
            existing_triplets.append(triplet)
            triplet_keys.add(key)
    
    print(f"\nĐã thêm {len(triplets)} quan hệ ASEAN từ file này")
    return {
        'entities': existing_entities,
        'triplets': existing_triplets
    }

def identify_asean_phases(sentences: List[str]) -> Dict[str, List[str]]:
    """Nhận diện các giai đoạn phát triển ASEAN trong văn bản."""
    phases = {
        'thanh_lap_1967': [],
        'mo_rong_1984_1999': [],
        'phat_trien_1976_1999': [],
        'cong_dong_1999_2015': [],
        'hien_tai_2015_nay': [],
        'khac': []
    }
    
    phase_keywords = {
        'thanh_lap_1967': [
            'thành lập asean', '8 – 8 – 1967', 'tuyên bố băng cốc',
            'asean 5', 'năm nước sáng lập', '1967'
        ],
        'mo_rong_1984_1999': [
            'mở rộng asean', 'gia nhập', 'trở thành thành viên',
            'asean 10', 'việt nam gia nhập', 'campuchia gia nhập',
            '1984', '1995', '1997', '1999'
        ],
        'phat_trien_1976_1999': [
            'tuyên bố ba-li', 'hiệp ước thân thiện', 'tac',
            'zopfan', '1976', '1992', 'afta', 'diễn đàn khu vực'
        ],
        'cong_dong_1999_2015': [
            'cộng đồng asean', 'hiến chương asean', 'aec',
            'apsc', 'ascc', 'tầm nhìn 2020', '2003', '2007',
            'lộ trình xây dựng', 'ba trụ cột'
        ],
        'hien_tai_2015_nay': [
            '2015', 'thành lập cộng đồng', 'sau 2015',
            'tầm nhìn 2025', 'chuyển đổi số', 'kinh tế số',
            '2020', '2025', 'hiện nay'
        ]
    }
    
    current_phase = 'khac'
    phase_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        detected_phase = None
        max_matches = 0
        
        for phase_name, keywords in phase_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in sentence_lower)
            if matches > max_matches:
                max_matches = matches
                detected_phase = phase_name
        
        if detected_phase and max_matches > 0:
            if phase_sentences:
                phases[current_phase].extend(phase_sentences)
            
            current_phase = detected_phase
            phase_sentences = [sentence]
        else:
            phase_sentences.append(sentence)
    
    if phase_sentences:
        phases[current_phase].extend(phase_sentences)
    
    return {k: v for k, v in phases.items() if v}

def filter_entities_for_asean_phase(entity_lookup: Dict[str, Dict], phase: str, 
                                   window_sentences: List[str]) -> Dict[str, Dict]:
    """Lọc entities phù hợp với giai đoạn ASEAN cụ thể."""
    filtered = {}
    window_text = " ".join(window_sentences).lower()
    
    for entity_id, entity in entity_lookup.items():
        if entity_id != entity['id']:
            continue
            
        entity_labels = entity.get('context_labels', [])
        
        in_window = False
        for label in entity_labels:
            if label.lower() in window_text and len(label) > 3:
                in_window = True
                break
        
        if not in_window:
            continue
        
        relevance_score = 0
        
        if phase == 'thanh_lap_1967':
            founding_members = ["In-đô-nê-xi-a", "Ma-lai-xi-a", "Phi-líp-pin", 
                              "Xin-ga-po", "Thái Lan", "ASEAN", "Tuyên bố Băng Cốc"]
            if any(member in str(label) for label in entity_labels for member in founding_members):
                relevance_score += 2
        
        elif phase == 'mo_rong_1984_1999':
            expansion_members = ["Việt Nam", "Brunei", "Lào", "Myanmar", "Campuchia"]
            if any(member in str(label) for label in entity_labels for member in expansion_members):
                relevance_score += 2
        
        elif phase == 'phat_trien_1976_1999':
            if entity.get('type') == "Văn kiện/Hiệp định":
                relevance_score += 2
        
        elif phase in ['cong_dong_1999_2015', 'hien_tai_2015_nay']:
            community_terms = ["Cộng đồng", "AEC", "APSC", "ASCC", "Hiến chương ASEAN"]
            if any(term in str(label) for label in entity_labels for term in community_terms):
                relevance_score += 2
        
        if relevance_score > 0 or in_window:
            entity['phase_relevance'] = relevance_score
            filtered[entity_id] = entity
    
    return filtered

def format_asean_entities_for_prompt(entity_lookup: Dict[str, Dict], phase: str) -> str:
    """Định dạng entities cho prompt với thông tin ASEAN."""
    entity_lines = []
    
    for entity_id, entity in entity_lookup.items():
        if entity_id == entity['id']:
            entity_type = entity.get('type', 'Unknown')
            labels = entity.get('context_labels', [])
            relevance = entity.get('phase_relevance', 0)
            
            if relevance > 0 or entity_type in ["Tổ chức khu vực", "Quốc gia", "Văn kiện/Hiệp định"]:
                line = f"- {entity_id}"
                if labels:
                    line += f" [Tên: {', '.join(labels[:2])}]"
                line += f" (Loại: {entity_type})"
                
                if 'ASEAN' in entity_id or any('asean' in str(label).lower() for label in labels):
                    line += " [QUAN TRỌNG: Tổ chức ASEAN]"
                elif entity_type == "Quốc gia" and any(label in [
                    "Việt Nam", "In-đô-nê-xi-a", "Ma-lai-xi-a", "Phi-líp-pin", 
                    "Xin-ga-po", "Thái Lan", "Brunei", "Lào", "Myanmar", "Campuchia"
                ] for label in labels):
                    line += " [QUAN TRỌNG: Thành viên ASEAN]"
                
                entity_lines.append((relevance, line))
    
    entity_lines.sort(key=lambda x: x[0], reverse=True)
    
    return "\n".join([line[1] for line in entity_lines[:30]])

def extract_asean_relationships(prompt: str, start_idx: int, window_sentences: List[str],
                               entity_lookup: Dict[str, Dict], file_info: Dict[str, str],
                               target_entity_id: str, phase: str) -> Optional[Dict]:
    """Trích xuất quan hệ ASEAN với validation đặc thù."""
    global API_REQUEST_COUNT
    
    for attempt in range(3):
        try:
            time.sleep(2)
            
            api_key, key_idx = get_next_api_key()
            if not api_key:
                print("Không có API key")
                return None
                
            # DeepSeek API - configured in api_handler
            # model handled by call_deepseek_api
            
            API_REQUEST_COUNT += 1
            print(f"[ASEAN-API #{API_REQUEST_COUNT}]", end=" ")
            
            result = call_deepseek_api(prompt)
            
            if not response or not hasattr(response, 'text') or response.text is None:
                print(f"Lỗi: response rỗng (lần {attempt+1})")
                if attempt < 2:
                    time.sleep(3)
                continue
                    
            response_text = response.text
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                try:
                    json_str = json_match.group()
                    
                    # THÊM KIỂM TRA: loại bỏ các ký tự null hoặc không hợp lệ
                    json_str = json_str.replace('\x00', '').replace('\ufffd', '')
                    
                    # THÊM KIỂM TRA: cắt bỏ phần thừa nếu có multiple JSON objects
                    if json_str.count('{') > 1:
                        # Tìm JSON object đầu tiên
                        start = json_str.find('{')
                        end = json_str.rfind('}')
                        if end > start:
                            json_str = json_str[start:end+1]
                            
                    relationships_data = json.loads(json_match.group())
                    validated_relationships = []
                    
                    for rel in relationships_data.get('relationships', []):
                        if validate_asean_relationship(rel, entity_lookup, phase):
                            priority_score = calculate_asean_priority(rel, phase)
                            
                            rel['window_info'] = {
                                'start_idx': start_idx,
                                'sentences': window_sentences[:3],
                                'file_info': file_info,
                                'phase': phase,
                                'target_entity': target_entity_id
                            }
                            
                            rel['phase'] = phase
                            rel['priority_score'] = priority_score
                            
                            evidence_quality = assess_asean_evidence_quality(rel.get('evidence', ''), phase)
                            base_confidence = rel.get('confidence', 0.8)
                            rel['confidence'] = min(0.97, base_confidence * evidence_quality + (priority_score * 0.05))
                            
                            validated_relationships.append(rel)
                    
                    return {
                        'relationships': validated_relationships,
                        'window_index': start_idx,
                        'target_entity': target_entity_id,
                        'phase': phase
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"Lỗi JSON: {e}")
                    debug_file = f"asean_error_phase_{phase}_{start_idx}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"Prompt: {prompt[:2000]}...\n\nResponse: {response_text}\n\nError: {e}")
                    # THỬ CÁCH KHÁC: tìm tất cả JSON objects
                    try:
                        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
                        all_json = re.findall(json_pattern, response_text)
                        if all_json:
                            # Lấy JSON object đầu tiên
                            relationships_data = json.loads(all_json[0])
                            # ... xử lý tiếp ...
                    except:
                        pass
                        
        except Exception as e:
            print(f"Lỗi (lần {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(3)
    
    return None

def validate_asean_relationship(relationship: Dict, entity_lookup: Dict[str, Dict], 
                               phase: str) -> bool:
    """Validate quan hệ ASEAN với tiêu chí giảm nhẹ."""
    subject_id = relationship.get('subject_id', '').strip()
    object_id = relationship.get('object_id', '').strip()
    predicate = relationship.get('predicate', '').strip()
    evidence = relationship.get('evidence', '').strip()
    time_ref = relationship.get('time_reference', '')
    
    if not subject_id or not object_id or not predicate:
        return False
    
    if subject_id == object_id:
        return False
    
    # Giảm nhẹ: tìm thực thể trong labels
    subject_found = False
    object_found = False
    
    for entity in entity_lookup.values():
        # Kiểm tra trực tiếp
        if entity.get('id') == subject_id:
            subject_found = True
        if entity.get('id') == object_id:
            object_found = True
        
        # Kiểm tra trong labels
        if not subject_found:
            for label in entity.get('context_labels', []):
                if subject_id.lower() in label.lower():
                    subject_found = True
                    break
        
        if not object_found:
            for label in entity.get('context_labels', []):
                if object_id.lower() in label.lower():
                    object_found = True
                    break
    
    # Chỉ cần một thực thể được tìm thấy
    if not subject_found and not object_found:
        return False
    
    # Giảm nhẹ: chấp nhận nhiều predicate hơn
    if len(predicate) < 2:
        return False
    
    # Giảm nhẹ độ dài evidence
    if len(evidence) < 12:
        return False
    
    # KHÔNG bắt buộc phải có năm trong evidence nữa
    # Chỉ cảnh báo nếu không có năm cho các phase quan trọng
    if phase != 'khac' and not re.search(r'\d{4}', evidence):
        # Giảm confidence thay vì reject
        if 'confidence' in relationship:
            relationship['confidence'] = relationship['confidence'] * 0.95
    
    # KHÔNG bắt buộc phải tìm thấy cả subject và object trong evidence
    return True

def calculate_asean_priority(relationship: Dict, phase: str) -> int:
    """Tính điểm ưu tiên cho quan hệ ASEAN."""
    priority = 1
    
    subject = relationship.get('subject_id', '')
    predicate = relationship.get('predicate', '')
    object_ = relationship.get('object_id', '')
    
    if predicate == 'thành_lập' and 'ASEAN' in object_:
        priority += 3
    
    if predicate in ['tham_gia', 'gia_nhập', 'trở_thành_thành_viên'] and 'ASEAN' in object_:
        priority += 2
    
    if predicate in ['ký_kết', 'thông_qua'] and any(term in object_ for term in [
        'Hiến chương', 'Tuyên bố Băng Cốc', 'TAC', 'ZOPFAN'
    ]):
        priority += 2
    
    if predicate in ['xây_dựng', 'phát_triển_thành', 'hình_thành'] and 'Cộng đồng' in object_:
        priority += 2
    
    if phase != 'khac':
        priority += 1
    
    return priority

def assess_asean_evidence_quality(evidence: str, phase: str) -> float:
    """Đánh giá chất lượng evidence cho ASEAN."""
    quality = 0.7
    
    if len(evidence) > 30:
        quality += 0.1
    if len(evidence) > 50:
        quality += 0.1
    
    year_match = re.search(r'\d{4}', evidence)
    if year_match:
        quality += 0.2
        year = int(year_match.group())
        
        if phase == 'thanh_lap_1967' and year == 1967:
            quality += 0.1
        elif phase == 'mo_rong_1984_1999' and year in [1984, 1995, 1997, 1999]:
            quality += 0.1
    
    asean_countries = ['việt nam', 'in-đô-nê-xi-a', 'ma-lai-xi-a', 'phi-líp-pin',
                      'xin-ga-po', 'thái lan', 'brunei', 'là o', 'myanmar', 'campuchia']
    if any(country in evidence.lower() for country in asean_countries):
        quality += 0.1
    
    if 'asean' in evidence.lower():
        quality += 0.1
    
    important_docs = ['tuyên bố băng cốc', 'hiến chương asean', 'hiệp ước thân thiện',
                     'zopfan', 'tuyên bố ba-li', 'aec', 'apsc', 'ascc']
    if any(doc in evidence.lower() for doc in important_docs):
        quality += 0.1
    
    return min(1.0, quality)

def post_process_asean_relationships(relationships: List[Dict]) -> List[Dict]:
    """Hậu xử lý quan hệ ASEAN."""
    groups = defaultdict(list)
    
    for rel in relationships:
        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
        groups[key].append(rel)
    
    merged = []
    
    for key, rel_list in groups.items():
        if not rel_list:
            continue
        
        base = rel_list[0].copy()
        base['occurrence_count'] = len(rel_list)
        
        all_evidence = []
        for rel in rel_list:
            evidence = {
                'text': rel.get('evidence', ''),
                'phase': rel.get('phase', 'unknown'),
                'window_info': rel.get('window_info', {}),
                'timestamp': time.time()
            }
            
            if not any(e['text'] == evidence['text'] for e in all_evidence):
                all_evidence.append(evidence)
        
        base['supporting_sentences'] = all_evidence
        
        total_conf = 0
        total_weight = 0
        
        for rel in rel_list:
            conf = rel.get('confidence', 0.8)
            priority = rel.get('priority_score', 1)
            weight = priority
            
            total_conf += conf * weight
            total_weight += weight
        
        if total_weight > 0:
            base['confidence'] = min(0.98, total_conf / total_weight)
        
        base['asean_context'] = f"ASEAN phase: {base.get('phase', 'unknown')}"
        
        merged.append(base)
    
    merged.sort(key=lambda x: (
        x.get('priority_score', 0),
        x.get('confidence', 0)
    ), reverse=True)
    
    return merged

# ============================================================================
# HÀM XỬ LÝ ĐẶC THÙ CHO CHỦ ĐỀ 3 (CHIẾN TRANH VIỆT NAM)
# ============================================================================

def process_vietnam_war_file(file_path: str, entity_lookup: Dict[str, Dict], existing_kg: Dict) -> Dict:
    """Xử lý file thuộc Chủ đề 3 với chiến lược đặc thù."""
    
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 3"]
    
    print(f"\n{'='*60}")
    print(f"XỬ LÝ CHỦ ĐỀ 3: {topic_config['topic_name']}")
    print(f"Trọng tâm: {topic_config['thematic_focus'][:100]}...")
    print(f"{'='*60}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return existing_kg
    
    topic, lesson = extract_topic_and_lesson(file_path)
    file_info = {
        'file_path': file_path,
        'topic': topic,
        'lesson': lesson,
        'topic_config': topic_config['topic_name'],
        'war_history_focus': True
    }
    
    all_entities = existing_kg.get('entities', [])
    war_priority_entities = []
    
    high_priority_terms = [
        "Hồ Chí Minh", "Võ Nguyên Giáp", "Cách mạng tháng Tám",
        "Điện Biên Phủ", "Chiến dịch Hồ Chí Minh", "Việt Minh",
        "Đảng Cộng sản Đông Dương", "Quân đội nhân dân Việt Nam",
        "Tuyên ngôn Độc lập", "Hiệp định Geneva", "Hiệp định Paris",
        "Biên giới Tây Nam", "Biên giới phía Bắc", "Biển Đông",
        "Trường Sa", "Hoàng Sa", "Vị Xuyên", "Gạc Ma"
    ]
    
    medium_priority_terms = [
        "kháng chiến", "chiến dịch", "trận đánh", "giải phóng",
        "xâm lược", "bảo vệ", "chỉ huy", "lãnh đạo", "thành lập",
        "Mỹ", "Pháp", "Trung Quốc", "Cam-pu-chia", "Pôn Pốt"
    ]
    
    for entity in all_entities:
        entity_id = entity['id']
        labels = entity.get('label', [])
        entity_type = entity.get('type', '')
        
        priority_score = 0
        
        for term in high_priority_terms:
            if any(term in str(label) for label in labels) or term in entity_id:
                priority_score += 3
        
        for term in medium_priority_terms:
            if any(term in str(label).lower() for label in labels) or term.lower() in entity_id.lower():
                priority_score += 2
        
        if entity_type in topic_config['focus_entities']:
            priority_score += 1
        
        if entity_type in ["Chiến dịch/Trận đánh", "Sự kiện lịch sử", "Nhân Vật"]:
            priority_score += 1
        
        if priority_score > 0:
            entity['war_priority'] = priority_score
            war_priority_entities.append(entity)
    
    war_priority_entities.sort(key=lambda x: x.get('war_priority', 0), reverse=True)
    
    filtered_entity_lookup = {}
    for entity in war_priority_entities[:60]:
        entity_copy = entity.copy()
        
        labels_in_context = []
        for occ in entity.get('original_text', []):
            if occ.get('topic') == topic and occ.get('lesson') == lesson:
                labels_in_context.extend(occ.get('labels', entity.get('label', [])))
        
        if labels_in_context:
            entity_copy['context_labels'] = list(set(labels_in_context))
        else:
            entity_copy['context_labels'] = entity.get('label', [])
        
        filtered_entity_lookup[entity['id']] = entity_copy
        
        for label in entity_copy['context_labels']:
            if label not in filtered_entity_lookup:
                filtered_entity_lookup[label] = entity_copy
    
    print(f"Đã chọn {len(filtered_entity_lookup)} thực thể ưu tiên cho lịch sử chiến tranh Việt Nam")
    
    sentences = split_into_sentences(content)
    war_periods = identify_vietnam_war_periods(sentences)
    
    all_relationships = []
    
    for period_name, period_sentences in war_periods.items():
        if not period_sentences:
            continue
            
        print(f"\nGiai đoạn: {topic_config['war_periods'].get(period_name, period_name)} ({len(period_sentences)} câu)")
        
        windows = create_overlapping_windows(
            period_sentences,
            window_size=topic_config['window_size'],
            step=topic_config['step_size']
        )
        
        for window_idx, (start_idx, window_sentences) in enumerate(windows[:10]):
            print(f"  Window {window_idx+1}/{min(4, len(windows))}: ", end="", flush=True)
            
            period_filtered_entities = filter_entities_for_war_period(
                filtered_entity_lookup, period_name, window_sentences
            )
            
            if len(period_filtered_entities) < 2:
                print("Ít thực thể -> Bỏ qua")
                continue
            
            existing_entities_str = format_war_entities_for_prompt(period_filtered_entities, period_name)
            window_text = " ".join(window_sentences)
            
            key_entities_in_window = []
            for entity_id, entity in period_filtered_entities.items():
                if entity_id == entity['id']:
                    window_text_lower = window_text.lower()
                    entity_labels = entity.get('context_labels', [])
                    
                    for label in entity_labels:
                        if label.lower() in window_text_lower and len(label) > 3:
                            if entity.get('war_priority', 0) >= 2:
                                key_entities_in_window.append(entity_id)
                            break
            
            if not key_entities_in_window:
                print("Không có thực thể quan trọng -> Bỏ qua")
                continue
            
            primary_entity = key_entities_in_window[0]
            
            prompt = TopicProcessor.create_topic_prompt(
                    "Chủ đề 3", 
                    window_text, 
                    existing_entities_str,
                    target_entity_id=primary_entity
                )
            
            result = extract_vietnam_war_relationships(
                prompt,
                start_idx,
                window_sentences,
                period_filtered_entities,
                file_info,
                primary_entity,
                period_name
            )
            
            if result:
                relationships = result.get('relationships', [])
                if relationships:
                    all_relationships.extend(relationships)
                    print(f"{len(relationships)}R ", end="", flush=True)
            
            print("")
            time.sleep(2)
    
    processed_relationships = post_process_war_relationships(all_relationships)
    
    triplets = []
    for rel in processed_relationships:
        triplet = {
            'subject_id': rel['subject_id'],
            'predicate': rel['predicate'],
            'object_id': rel['object_id'],
            'properties': {
                'war_context': rel.get('war_context', ''),
                'time_reference': rel.get('time_reference', ''),
                'war_period': rel.get('war_period', ''),
                'battle_significance': rel.get('battle_significance', '')
            },
            'metadata': {
                'extraction_method': 'vietnam_war_specialized',
                'file_info': file_info,
                'evidence_count': len(rel.get('supporting_sentences', [])),
                'war_period': rel.get('war_period', 'unknown'),
                'priority_score': rel.get('priority_score', 1)
            },
            'supporting_sentences': rel.get('supporting_sentences', []),
            'confidence': rel.get('confidence', 0.9),
            'occurrence_count': rel.get('occurrence_count', 1)
        }
        triplets.append(triplet)
    
    existing_triplets = existing_kg.get('triplets', [])
    existing_entities = existing_kg.get('entities', [])
    
    triplet_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
    for triplet in triplets:
        key = (triplet['subject_id'], triplet['predicate'], triplet['object_id'])
        if key not in triplet_keys:
            existing_triplets.append(triplet)
            triplet_keys.add(key)
    
    print(f"\nĐã thêm {len(triplets)} quan hệ chiến tranh từ file này")
    return {
        'entities': existing_entities,
        'triplets': existing_triplets
    }

def identify_vietnam_war_periods(sentences: List[str]) -> Dict[str, List[str]]:
    """Nhận diện các giai đoạn chiến tranh trong văn bản."""
    periods = {
        'cmtt_1945': [],
        'kccp_1945_1954': [],
        'kcmcn_1954_1975': [],
        'bvtq_sau_1975': [],
        'bien_gioi_tay_nam': [],
        'bien_gioi_phia_bac': [],
        'bien_dong': [],
        'khac': []
    }
    
    period_keywords = {
        'cmtt_1945': [
            'cách mạng tháng tám', 'tháng 8 năm 1945', 'tổng khởi nghĩa',
            '19-8-1945', 'tuyên ngôn độc lập', '2-9-1945', 'hồ chí minh đọc',
            'việt minh', 'ủy ban khởi nghĩa', 'tân trào', '1945'
        ],
        'kccp_1945_1954': [
            'kháng chiến chống pháp', 'thực dân pháp', '1945-1954',
            'điện biên phủ', 'hiệp định geneva', 'chiến dịch việt bắc',
            'chiến dịch biên giới', 'kế hoạch na-va', '1954'
        ],
        'kcmcn_1954_1975': [
            'kháng chiến chống mỹ', 'đế quốc mỹ', '1954-1975',
            'chiến tranh đặc biệt', 'chiến tranh cục bộ',
            'việt nam hóa chiến tranh', 'hiệp định paris',
            'chiến dịch hồ chí minh', '30-4-1975', 'sài gòn giải phóng'
        ],
        'bien_gioi_tay_nam': [
            'biên giới tây nam', 'pôn pốt', 'cam-pu-chia',
            '1977-1979', 'phôm pênh', 'ba chúc', 'xâm lược biên giới'
        ],
        'bien_gioi_phia_bac': [
            'biên giới phía bắc', 'trung quốc xâm lược', '1979',
            'vị xuyên', 'hà giang', '17-2-1979', 'lạng sơn', 'cao bằng'
        ],
        'bien_dong': [
            'biển đông', 'trường sa', 'hoàng sa', 'chủ quyền biển đảo',
            'gạc ma', 'cô lin', 'len đao', '14-3-1988', 'hải quân việt nam'
        ]
    }
    
    current_period = 'khac'
    period_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        detected_period = None
        max_matches = 0
        
        for period_name, keywords in period_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in sentence_lower)
            if matches > max_matches:
                max_matches = matches
                detected_period = period_name
        
        if detected_period and max_matches > 0:
            if period_sentences:
                periods[current_period].extend(period_sentences)
            
            current_period = detected_period
            period_sentences = [sentence]
        else:
            period_sentences.append(sentence)
    
    if period_sentences:
        periods[current_period].extend(period_sentences)
    
    return {k: v for k, v in periods.items() if v}

def filter_entities_for_war_period(entity_lookup: Dict[str, Dict], period: str, 
                                  window_sentences: List[str]) -> Dict[str, Dict]:
    """Lọc entities phù hợp với giai đoạn chiến tranh cụ thể."""
    filtered = {}
    window_text = " ".join(window_sentences).lower()
    
    for entity_id, entity in entity_lookup.items():
        if entity_id != entity['id']:
            continue
            
        entity_labels = entity.get('context_labels', [])
        
        in_window = False
        for label in entity_labels:
            if label.lower() in window_text and len(label) > 3:
                in_window = True
                break
        
        if not in_window:
            continue
        
        relevance_score = 0
        
        if period == 'cmtt_1945':
            cmtt_entities = ["Hồ Chí Minh", "Việt Minh", "Đảng Cộng sản Đông Dương",
                           "Tân Trào", "Uỷ ban Khởi nghĩa", "Tuyên ngôn Độc lập"]
            if any(term in str(label) for label in entity_labels for term in cmtt_entities):
                relevance_score += 2
        
        elif period == 'kccp_1945_1954':
            kccp_entities = ["Võ Nguyên Giáp", "Điện Biên Phủ", "Hiệp định Geneva",
                           "Việt Bắc", "Chiến dịch Biên giới", "thực dân Pháp"]
            if any(term in str(label) for label in entity_labels for term in kccp_entities):
                relevance_score += 2
        
        elif period == 'kcmcn_1954_1975':
            kcmcn_entities = ["Mỹ", "Ngô Đình Diệm", "Chiến dịch Hồ Chí Minh",
                            "Hiệp định Paris", "Sài Gòn", "Quân Giải phóng"]
            if any(term in str(label) for label in entity_labels for term in kcmcn_entities):
                relevance_score += 2
        
        elif period == 'bien_gioi_tay_nam':
            taynam_entities = ["Pôn Pốt", "Cam-pu-chia", "Ba Chúc", "Phôm Pênh"]
            if any(term in str(label) for label in entity_labels for term in taynam_entities):
                relevance_score += 2
        
        elif period == 'bien_gioi_phia_bac':
            phiabac_entities = ["Trung Quốc", "Vị Xuyên", "Lạng Sơn", "Cao Bằng", "Hà Giang"]
            if any(term in str(label) for label in entity_labels for term in phiabac_entities):
                relevance_score += 2
        
        elif period == 'bien_dong':
            biendong_entities = ["Trường Sa", "Hoàng Sa", "Gạc Ma", "Cô Lin", "Hải quân"]
            if any(term in str(label) for label in entity_labels for term in biendong_entities):
                relevance_score += 2
        
        if relevance_score > 0 or in_window:
            entity['period_relevance'] = relevance_score
            filtered[entity_id] = entity
    
    return filtered

def format_war_entities_for_prompt(entity_lookup: Dict[str, Dict], period: str) -> str:
    """Định dạng entities cho prompt với thông tin chiến tranh."""
    entity_lines = []
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 3"]
    
    for entity_id, entity in entity_lookup.items():
        if entity_id == entity['id']:
            entity_type = entity.get('type', 'Unknown')
            labels = entity.get('context_labels', [])
            relevance = entity.get('period_relevance', 0)
            
            if relevance > 0 or entity_type in topic_config['focus_entities']:
                line = f"- {entity_id}"
                if labels:
                    line += f" [Tên: {', '.join(labels[:2])}]"
                line += f" (Loại: {entity_type})"
                
                if entity_type == "Nhân Vật":
                    line += " [Nhân vật lịch sử]"
                elif entity_type == "Chiến dịch/Trận đánh":
                    line += " [Sự kiện quân sự]"
                elif entity_type == "Sự kiện lịch sử":
                    line += " [Sự kiện quan trọng]"
                
                entity_lines.append((relevance, line))
    
    entity_lines.sort(key=lambda x: x[0], reverse=True)
    
    return "\n".join([line[1] for line in entity_lines[:35]])

def extract_vietnam_war_relationships(prompt: str, start_idx: int, window_sentences: List[str],
                                     entity_lookup: Dict[str, Dict], file_info: Dict[str, str],
                                     target_entity_id: str, period: str) -> Optional[Dict]:
    """Trích xuất quan hệ chiến tranh với validation đặc thù."""
    global API_REQUEST_COUNT
    
    for attempt in range(3):
        try:
            time.sleep(2)
            
            api_key, key_idx = get_next_api_key()
            if not api_key:
                print("Không có API key")
                return None
                
            # DeepSeek API - configured in api_handler
            # model handled by call_deepseek_api
            
            API_REQUEST_COUNT += 1
            print(f"[War-API #{API_REQUEST_COUNT}]", end=" ")
            
            # THÊM: Debug prompt nếu cần
            if attempt == 0 and API_REQUEST_COUNT % 5 == 0:
                debug_prompt_file = f"debug_prompt_war_{API_REQUEST_COUNT}.txt"
                with open(debug_prompt_file, 'w', encoding='utf-8') as f:
                    f.write(f"Prompt length: {len(prompt)}\n")
                    f.write(f"First 2000 chars:\n{prompt[:2000]}\n")
            
            result = call_deepseek_api(prompt)

            if not response or not hasattr(response, 'text') or response.text is None:
                print(f"Lỗi: response rỗng (lần {attempt+1})")
                if attempt < 2:
                    time.sleep(3)
                continue
                
            response_text = response.text
            
            # THÊM: Debug response
            if attempt == 0 and API_REQUEST_COUNT % 5 == 0:
                debug_response_file = f"debug_response_war_{API_REQUEST_COUNT}.txt"
                with open(debug_response_file, 'w', encoding='utf-8') as f:
                    f.write(f"Response length: {len(response_text)}\n")
                    f.write(f"First 1000 chars:\n{response_text[:1000]}\n")
            
            # Tìm JSON trong response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            
            if not json_match:
                # Thử tìm pattern khác
                json_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', response_text)
            
            if json_match:
                try:
                    json_str = json_match.group()
                    
                    # Làm sạch JSON string
                    json_str = clean_json_string(json_str)
                    
                    # Parse JSON
                    data = json.loads(json_str)
                    
                    # KIỂM TRA: data có phải là dictionary không?
                    if not isinstance(data, dict):
                        print(f"Dữ liệu không phải dictionary: {type(data)}")
                        # Thử parse lại nếu là list
                        if isinstance(data, list):
                            data = {"relationships": data}
                        else:
                            return None
                    
                    # KIỂM TRA: relationships có phải là list không?
                    relationships_list = data.get('relationships', [])
                    if not isinstance(relationships_list, list):
                        print(f"relationships không phải list: {type(relationships_list)}")
                        relationships_list = []
                    
                    validated_relationships = []
                    
                    for rel in relationships_list:
                        # Đảm bảo rel là dictionary
                        if not isinstance(rel, dict):
                            print(f"relationship không phải dict: {rel}")
                            continue
                        
                        # Đảm bảo các trường cần thiết tồn tại
                        rel.setdefault('subject_id', '')
                        rel.setdefault('object_id', '')
                        rel.setdefault('predicate', '')
                        rel.setdefault('evidence', '')
                        rel.setdefault('confidence', 0.8)
                        
                        # SỬA: Gọi hàm validate (dùng phiên bản đã sửa)
                        if validate_war_relationship(rel, entity_lookup, period):
                            priority_score = calculate_war_priority(rel, period)
                            
                            rel['window_info'] = {
                                'start_idx': start_idx,
                                'sentences': window_sentences[:3],
                                'file_info': file_info,
                                'period': period,
                                'target_entity': target_entity_id
                            }
                            
                            rel['war_period'] = period
                            rel['priority_score'] = priority_score
                            
                            evidence_quality = assess_war_evidence_quality(rel.get('evidence', ''), period)
                            base_confidence = rel.get('confidence', 0.8)
                            rel['confidence'] = min(0.97, base_confidence * evidence_quality + (priority_score * 0.05))
                            
                            if 'time_reference' not in rel:
                                time_match = re.search(r'\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}|\d{4}', rel.get('evidence', ''))
                                if time_match:
                                    rel['time_reference'] = time_match.group()
                            
                            validated_relationships.append(rel)
                    
                    print(f"{len(validated_relationships)}R", end="")
                    
                    return {
                        'relationships': validated_relationships,
                        'window_index': start_idx,
                        'target_entity': target_entity_id,
                        'period': period
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"Lỗi JSON: {e}")
                    debug_file = f"war_error_period_{period}_{start_idx}_{API_REQUEST_COUNT}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"Prompt (first 2000 chars):\n{prompt[:2000]}\n\n")
                        f.write(f"Response:\n{response_text}\n\n")
                        f.write(f"JSON string:\n{json_str if 'json_str' in locals() else 'N/A'}\n\n")
                        f.write(f"Error: {e}\n")
                    
                    if attempt < 2:
                        time.sleep(3)
            
            else:
                print(f"Không tìm thấy JSON trong response (lần {attempt+1})")
                # Debug: lưu response để phân tích
                debug_file = f"war_no_json_{API_REQUEST_COUNT}.txt"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"Prompt (first 1000 chars):\n{prompt[:1000]}\n\n")
                    f.write(f"Response:\n{response_text}\n")
                
                if attempt < 2:
                    time.sleep(3)
            
        except Exception as e:
            print(f"Lỗi (lần {attempt+1}): {type(e).__name__}: {str(e)[:100]}")
            if attempt < 2:
                time.sleep(3)
    
    return None

def validate_war_relationship(relationship: Dict, entity_lookup: Dict[str, Dict], 
                             period: str) -> bool:
    """Validate quan hệ chiến tranh với tiêu chí chặt chẽ."""
    # SỬA: Sử dụng str() để tránh lỗi NoneType
    subject_id = str(relationship.get('subject_id', '')).strip()
    object_id = str(relationship.get('object_id', '')).strip()
    predicate = str(relationship.get('predicate', '')).strip()
    evidence = str(relationship.get('evidence', '')).strip()
    
    # Kiểm tra cơ bản
    if not subject_id or not object_id or not predicate:
        return False
    
    if subject_id == object_id:
        return False
    
    # Kiểm tra sự tồn tại của entities trong lookup
    # SỬA: Kiểm tra đơn giản hơn
    subject_exists = False
    object_exists = False
    
    # Kiểm tra bằng ID trực tiếp
    if subject_id in entity_lookup:
        subject_exists = True
    else:
        # Kiểm tra trong labels
        for entity in entity_lookup.values():
            # SỬA: Kiểm tra entity có phải là dictionary không
            if isinstance(entity, dict):
                labels = entity.get('context_labels', entity.get('label', []))
                # SỬA: Đảm bảo labels là list
                if isinstance(labels, list):
                    for label in labels:
                        if label and subject_id.lower() in str(label).lower():
                            subject_exists = True
                            break
                if subject_exists:
                    break
    
    if object_id in entity_lookup:
        object_exists = True
    else:
        for entity in entity_lookup.values():
            if isinstance(entity, dict):
                labels = entity.get('context_labels', entity.get('label', []))
                if isinstance(labels, list):
                    for label in labels:
                        if label and object_id.lower() in str(label).lower():
                            object_exists = True
                            break
                if object_exists:
                    break
    
    # Chấp nhận nếu ít nhất một thực thể tồn tại
    if not subject_exists and not object_exists:
        return False
    
    # Kiểm tra predicate
    if len(predicate) < 2:
        return False
    
    # Kiểm tra evidence
    if len(evidence) < 10:
        return False
    
    # Kiểm tra evidence có chứa thực thể không (tùy chọn)
    evidence_lower = evidence.lower()
    
    # Chỉ cảnh báo nếu không tìm thấy, không reject
    subject_found_in_evidence = False
    object_found_in_evidence = False
    
    # Kiểm tra subject trong evidence
    if subject_id.lower() in evidence_lower:
        subject_found_in_evidence = True
    else:
        for entity in entity_lookup.values():
            if entity.get('id') == subject_id:
                labels = entity.get('context_labels', entity.get('label', []))
                if isinstance(labels, list):
                    for label in labels:
                        if label and str(label).lower() in evidence_lower:
                            subject_found_in_evidence = True
                            break
                break
    
    # Kiểm tra object trong evidence
    if object_id.lower() in evidence_lower:
        object_found_in_evidence = True
    else:
        for entity in entity_lookup.values():
            if entity.get('id') == object_id:
                labels = entity.get('context_labels', entity.get('label', []))
                if isinstance(labels, list):
                    for label in labels:
                        if label and str(label).lower() in evidence_lower:
                            object_found_in_evidence = True
                            break
                break
    
    # Nếu không tìm thấy cả hai, vẫn chấp nhận nhưng giảm confidence
    if not subject_found_in_evidence and not object_found_in_evidence:
        # Vẫn chấp nhận, nhưng ghi nhận confidence thấp hơn
        if 'confidence' in relationship:
            relationship['confidence'] = relationship.get('confidence', 0.95) * 0.85
    
    return True

def lenient_validate_relationship(relationship: Dict, entity_lookup: Dict[str, Dict]) -> bool:
    """Validate giảm nhẹ cho tất cả các chủ đề."""
    subject_id = relationship.get('subject_id', '').strip()
    object_id = relationship.get('object_id', '').strip()
    predicate = relationship.get('predicate', '').strip()
    evidence = relationship.get('evidence', '').strip()
    
    # Kiểm tra cơ bản tối thiểu
    if not subject_id or not object_id or not predicate:
        return False
    
    if subject_id == object_id:
        return False
    
    # Chỉ kiểm tra sự tồn tại cơ bản
    subject_exists = subject_id in entity_lookup
    object_exists = object_id in entity_lookup
    
    # Nếu không tồn tại, thử tìm trong labels
    if not subject_exists:
        subject_exists = any(subject_id.lower() in label.lower() 
                           for entity in entity_lookup.values() 
                           for label in entity.get('label', []))
    
    if not object_exists:
        object_exists = any(object_id.lower() in label.lower() 
                          for entity in entity_lookup.values() 
                          for label in entity.get('label', []))
    
    # Chấp nhận nếu ít nhất một thực thể tồn tại
    if not subject_exists and not object_exists:
        return False
    
    # Độ dài tối thiểu
    if len(predicate) < 2:
        return False
    
    if len(evidence) < 8:
        return False
    
    # Luôn trả về True để chấp nhận nhiều relationship hơn
    # Ghi nhận confidence thấp hơn nếu không đạt các tiêu chí khác
    current_confidence = relationship.get('confidence', 0.9)
    
    # Giảm confidence nếu không tìm thấy subject trong evidence
    evidence_lower = evidence.lower()
    subject_in_evidence = any(label.lower() in evidence_lower 
                            for entity in entity_lookup.values() 
                            if entity.get('id') == subject_id 
                            for label in entity.get('label', []))
    
    if not subject_in_evidence:
        current_confidence *= 0.7
    
    # Giảm confidence nếu không tìm thấy object trong evidence
    object_in_evidence = any(label.lower() in evidence_lower 
                           for entity in entity_lookup.values() 
                           if entity.get('id') == object_id 
                           for label in entity.get('label', []))
    
    if not object_in_evidence:
        current_confidence *= 0.7
    
    relationship['confidence'] = max(0.3, current_confidence)  # Giữ tối thiểu 0.3
    
    return True

def calculate_war_priority(relationship: Dict, period: str) -> int:
    """Tính điểm ưu tiên cho quan hệ chiến tranh."""
    priority = 1
    
    subject = relationship.get('subject_id', '')
    predicate = relationship.get('predicate', '')
    object_ = relationship.get('object_id', '')
    
    important_leaders = ["Hồ Chí Minh", "Võ Nguyên Giáp"]
    if predicate in ['lãnh_đạo', 'chỉ_huy'] and any(leader in subject for leader in important_leaders):
        priority += 2
    
    if predicate in ['đánh_bại', 'chiến_thắng', 'giải_phóng']:
        priority += 1
        if 'Điện Biên Phủ' in object_ or 'Sài Gòn' in object_:
            priority += 1
    
    if predicate == 'thành_lập' and any(org in object_ for org in [
        'Việt Nam Dân chủ Cộng hòa', 'Chính phủ lâm thời', 'Mặt trận Việt Minh'
    ]):
        priority += 2
    
    if predicate == 'ký_kết' and any(doc in object_ for doc in [
        'Hiệp định Geneva', 'Hiệp định Paris', 'Tuyên ngôn Độc lập'
    ]):
        priority += 2
    
    if predicate in ['xâm_lược', 'bảo_vệ'] and any(term in object_ for term in [
        'biên giới', 'biển đông', 'trường sa', 'hoàng sa'
    ]):
        priority += 1
    
    return priority

def assess_war_evidence_quality(evidence: str, period: str) -> float:
    """Đánh giá chất lượng evidence cho quan hệ chiến tranh."""
    quality = 0.7
    
    if len(evidence) > 30:
        quality += 0.1
    if len(evidence) > 50:
        quality += 0.1
    
    year_match = re.search(r'\d{4}', evidence)
    if year_match:
        quality += 0.2
        year = int(year_match.group())
        
        if period == 'cmtt_1945' and year == 1945:
            quality += 0.1
        elif period == 'kccp_1945_1954' and 1945 <= year <= 1954:
            quality += 0.1
        elif period == 'kcmcn_1954_1975' and 1954 <= year <= 1975:
            quality += 0.1
        elif period == 'bien_gioi_phia_bac' and year == 1979:
            quality += 0.1
        elif period == 'bien_dong' and year == 1988:
            quality += 0.1
    
    if re.search(r'\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}', evidence):
        quality += 0.1
    
    battle_locations = ['hà nội', 'huế', 'sài gòn', 'điện biên phủ', 
                       'việt bắc', 'tây nguyên', 'biên giới', 'vị xuyên']
    if any(location in evidence.lower() for location in battle_locations):
        quality += 0.1
    
    battle_names = ['chiến dịch', 'trận đánh', 'tổng tiến công', 'khởi nghĩa']
    if any(name in evidence.lower() for name in battle_names):
        quality += 0.1
    
    if re.search(r'\d+\s+(quân|binh sĩ|máy bay|tàu chiến|vũ khí)', evidence.lower()):
        quality += 0.1
    
    return min(1.0, quality)

def post_process_war_relationships(relationships: List[Dict]) -> List[Dict]:
    """Hậu xử lý quan hệ chiến tranh."""
    groups = defaultdict(list)
    
    for rel in relationships:
        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
        groups[key].append(rel)
    
    merged = []
    
    for key, rel_list in groups.items():
        if not rel_list:
            continue
        
        base = rel_list[0].copy()
        base['occurrence_count'] = len(rel_list)
        
        all_evidence = []
        for rel in rel_list:
            evidence = {
                'text': rel.get('evidence', ''),
                'period': rel.get('war_period', 'unknown'),
                'time_reference': rel.get('time_reference', ''),
                'window_info': rel.get('window_info', {}),
                'timestamp': time.time()
            }
            
            if not any(e['text'] == evidence['text'] for e in all_evidence):
                all_evidence.append(evidence)
        
        base['supporting_sentences'] = all_evidence
        
        total_conf = 0
        total_weight = 0
        
        for rel in rel_list:
            conf = rel.get('confidence', 0.8)
            priority = rel.get('priority_score', 1)
            weight = priority
            
            total_conf += conf * weight
            total_weight += weight
        
        if total_weight > 0:
            base['confidence'] = min(0.98, total_conf / total_weight)
        
        if 'war_context' not in base:
            base['war_context'] = f"Giai đoạn: {base.get('war_period', 'unknown')}"
        
        battle_terms = ['chiến dịch', 'trận', 'đánh bại', 'giải phóng']
        if any(term in base['predicate'] for term in battle_terms) or any(
            term in str(base.get('object_id', '')) for term in ['Điện Biên Phủ', 'Sài Gòn', 'Huế']
        ):
            base['battle_significance'] = "quan_trọng"
        
        merged.append(base)
    
    merged.sort(key=lambda x: (
        x.get('priority_score', 0),
        x.get('confidence', 0)
    ), reverse=True)
    
    return merged

# ============================================================================
# HÀM XỬ LÝ ĐẶC THÙ CHO CHỦ ĐỀ 4 (ĐỔI MỚI)
# ============================================================================

def process_doi_moi_file(file_path: str, entity_lookup: Dict[str, Dict], existing_kg: Dict) -> Dict:
    """Xử lý file thuộc Chủ đề 4 với chiến lược đặc thù."""
    
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 4"]
    
    print(f"\n{'='*60}")
    print(f"XỬ LÝ CHỦ ĐỀ 4: {topic_config['topic_name']}")
    print(f"Trọng tâm: {topic_config['thematic_focus'][:100]}...")
    print(f"{'='*60}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return existing_kg
    
    topic, lesson = extract_topic_and_lesson(file_path)
    file_info = {
        'file_path': file_path,
        'topic': topic,
        'lesson': lesson,
        'topic_config': topic_config['topic_name'],
        'doi_moi_focus': True
    }
    
    all_entities = existing_kg.get('entities', [])
    doi_moi_priority_entities = []
    
    high_priority_terms = [
        "Đại hội VI", "Đại hội VII", "Đại hội VIII", "Đại hội X",
        "Đổi mới", "công nghiệp hóa", "hiện đại hóa", "kinh tế thị trường",
        "hội nhập quốc tế", "GDP", "tăng trưởng", "xoá đói giảm nghèo",
        "tem phiếu", "cơ chế bao cấp", "nghị quyết", "đường lối"
    ]
    
    medium_priority_terms = [
        "chính sách", "cải cách", "chương trình", "thành tựu",
        "chỉ tiêu", "cơ cấu kinh tế", "xuất khẩu", "đầu tư nước ngoài",
        "quan hệ đối ngoại", "hợp tác quốc tế", "phát triển bền vững"
    ]
    
    economic_indicators = ["tăng trưởng", "lạm phát", "xuất khẩu", "nhập khẩu", 
                          "đầu tư", "thu nhập", "nghèo", "thất nghiệp", "GDP"]
    
    for entity in all_entities:
        entity_id = entity['id']
        labels = entity.get('label', [])
        entity_type = entity.get('type', '')
        
        priority_score = 0
        
        for term in high_priority_terms:
            if any(term in str(label) for label in labels) or term in entity_id:
                priority_score += 3
        
        for term in medium_priority_terms:
            if any(term in str(label).lower() for label in labels) or term.lower() in entity_id.lower():
                priority_score += 2
        
        for indicator in economic_indicators:
            if any(indicator in str(label).lower() for label in labels):
                priority_score += 1
        
        if entity_type in topic_config['focus_entities']:
            priority_score += 2
        
        if entity_type in ["Chỉ tiêu kinh tế", "Thành tựu phát triển"]:
            priority_score += 1
        
        if re.search(r'\d{4}', entity_id) or any(re.search(r'\d{4}', str(label)) for label in labels):
            priority_score += 1
        
        if priority_score > 0:
            entity['doi_moi_priority'] = priority_score
            doi_moi_priority_entities.append(entity)
    
    doi_moi_priority_entities.sort(key=lambda x: x.get('doi_moi_priority', 0), reverse=True)
    
    filtered_entity_lookup = {}
    for entity in doi_moi_priority_entities[:80]:
        entity_copy = entity.copy()
        
        labels_in_context = []
        for occ in entity.get('original_text', []):
            if occ.get('topic') == topic and occ.get('lesson') == lesson:
                labels_in_context.extend(occ.get('labels', entity.get('label', [])))
        
        if labels_in_context:
            entity_copy['context_labels'] = list(set(labels_in_context))
        else:
            entity_copy['context_labels'] = entity.get('label', [])
        
        filtered_entity_lookup[entity['id']] = entity_copy
        
        for label in entity_copy['context_labels']:
            if label not in filtered_entity_lookup:
                filtered_entity_lookup[label] = entity_copy
    
    print(f"Đã chọn {len(filtered_entity_lookup)} thực thể ưu tiên cho Đổi mới Việt Nam")
    
    sentences = split_into_sentences(content)
    doi_moi_periods = identify_doi_moi_periods(sentences)
    
    all_relationships = []
    
    for period_name, period_sentences in doi_moi_periods.items():
        if not period_sentences:
            continue
            
        print(f"\nGiai đoạn: {topic_config['doi_moi_periods'].get(period_name, period_name)} ({len(period_sentences)} câu)")
        
        windows = create_overlapping_windows(
            period_sentences,
            window_size=topic_config['window_size'],
            step=topic_config['step_size']
        )
        
        for window_idx, (start_idx, window_sentences) in enumerate(windows[:10]):
            print(f"  Window {window_idx+1}/{min(5, len(windows))}: ", end="", flush=True)
            
            period_filtered_entities = filter_entities_for_doi_moi_period(
                filtered_entity_lookup, period_name, window_sentences
            )
            
            if len(period_filtered_entities) < 2:
                print("Ít thực thể -> Bỏ qua")
                continue
            
            existing_entities_str = format_doi_moi_entities_for_prompt(period_filtered_entities, period_name)
            window_text = " ".join(window_sentences)
            
            key_entities_in_window = []
            for entity_id, entity in period_filtered_entities.items():
                if entity_id == entity['id']:
                    window_text_lower = window_text.lower()
                    entity_labels = entity.get('context_labels', [])
                    
                    for label in entity_labels:
                        if label.lower() in window_text_lower and len(label) > 3:
                            if entity.get('doi_moi_priority', 0) >= 3:
                                key_entities_in_window.append(entity_id)
                            break
            
            if not key_entities_in_window:
                print("Không có thực thể quan trọng -> Bỏ qua")
                continue
            
            primary_entity = key_entities_in_window[0]
            
            prompt = TopicProcessor.create_topic_prompt(
                    "Chủ đề 4", 
                    window_text, 
                    existing_entities_str,
                    target_entity_id=primary_entity
                )
            
            result = extract_doi_moi_relationships(
                prompt,
                start_idx,
                window_sentences,
                period_filtered_entities,
                file_info,
                primary_entity,
                period_name
            )
            
            if result:
                relationships = result.get('relationships', [])
                if relationships:
                    all_relationships.extend(relationships)
                    print(f"{len(relationships)}R ", end="", flush=True)
            
            print("")
            time.sleep(2)
    
    processed_relationships = post_process_doi_moi_relationships(all_relationships)
    
    triplets = []
    for rel in processed_relationships:
        triplet = {
            'subject_id': rel['subject_id'],
            'predicate': rel['predicate'],
            'object_id': rel['object_id'],
            'properties': {
                'doi_moi_context': rel.get('policy_context', ''),
                'time_reference': rel.get('time_reference', ''),
                'data_point': rel.get('data_point', ''),
                'period': rel.get('period', ''),
                'achievement_type': rel.get('achievement_type', '')
            },
            'metadata': {
                'extraction_method': 'doi_moi_specialized',
                'file_info': file_info,
                'evidence_count': len(rel.get('supporting_sentences', [])),
                'doi_moi_period': rel.get('period', 'unknown'),
                'priority_score': rel.get('priority_score', 1),
                'has_data': 'data_point' in rel
            },
            'supporting_sentences': rel.get('supporting_sentences', []),
            'confidence': rel.get('confidence', 0.9),
            'occurrence_count': rel.get('occurrence_count', 1)
        }
        triplets.append(triplet)
    
    existing_triplets = existing_kg.get('triplets', [])
    existing_entities = existing_kg.get('entities', [])
    
    triplet_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
    for triplet in triplets:
        key = (triplet['subject_id'], triplet['predicate'], triplet['object_id'])
        if key not in triplet_keys:
            existing_triplets.append(triplet)
            triplet_keys.add(key)
    
    print(f"\nĐã thêm {len(triplets)} quan hệ Đổi mới từ file này")
    return {
        'entities': existing_entities,
        'triplets': existing_triplets
    }

def identify_doi_moi_periods(sentences: List[str]) -> Dict[str, List[str]]:
    """Nhận diện các giai đoạn Đổi mới trong văn bản."""
    periods = {
        '1986_1995': [],
        '1996_2006': [],
        '2006_nay': [],
        'thanh_tuu_chung': [],
        'khac': []
    }
    
    period_keywords = {
        '1986_1995': [
            'đại hội vi', '1986', 'khởi đầu đổi mới', '1986-1995',
            'xoá bỏ bao cấp', 'tem phiếu', 'ba chương trình kinh tế',
            'kiểm soát lạm phát', 'đổi mới kinh tế', 'đại hội vii', '1991'
        ],
        '1996_2006': [
            'đại hội viii', '1996', 'công nghiệp hóa', 'hiện đại hóa',
            'kinh tế thị trường', '1996-2006', 'hội nhập kinh tế',
            'đường dây 500 kv', 'tăng trưởng 6%', 'phát triển cơ sở hạ tầng'
        ],
        '2006_nay': [
            'đại hội x', '2006', '2006 đến nay', 'hội nhập toàn diện',
            'nước đang phát triển', 'công nghiệp hiện đại', 'hiệp định thương mại',
            'quan hệ đối ngoại', 'thành tựu đổi mới', 'xoá đói giảm nghèo'
        ],
        'thanh_tuu_chung': [
            'thành tựu', 'kết quả', 'đạt được', 'tỉ lệ', 'tăng trưởng',
            'giảm xuống', 'tăng lên', 'chỉ số', 'so với', 'mức'
        ]
    }
    
    current_period = 'khac'
    period_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        detected_period = None
        max_matches = 0
        
        for period_name, keywords in period_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in sentence_lower)
            if matches > max_matches:
                max_matches = matches
                detected_period = period_name
        
        if detected_period and max_matches > 0:
            if period_sentences:
                periods[current_period].extend(period_sentences)
            
            current_period = detected_period
            period_sentences = [sentence]
        else:
            period_sentences.append(sentence)
    
    if period_sentences:
        periods[current_period].extend(period_sentences)
    
    return {k: v for k, v in periods.items() if v}

def filter_entities_for_doi_moi_period(entity_lookup: Dict[str, Dict], period: str, 
                                       window_sentences: List[str]) -> Dict[str, Dict]:
    """Lọc entities phù hợp với giai đoạn Đổi mới cụ thể."""
    filtered = {}
    window_text = " ".join(window_sentences).lower()
    
    for entity_id, entity in entity_lookup.items():
        if entity_id != entity['id']:
            continue
            
        entity_labels = entity.get('context_labels', [])
        
        in_window = False
        for label in entity_labels:
            if label.lower() in window_text and len(label) > 3:
                in_window = True
                break
        
        if not in_window:
            continue
        
        relevance_score = 0
        
        if period == '1986_1995':
            early_terms = ["Đại hội VI", "Đại hội VII", "tem phiếu", "bao cấp", 
                          "lạm phát", "chương trình kinh tế", "1986", "1991"]
            if any(term in str(label) for label in entity_labels for term in early_terms):
                relevance_score += 2
        
        elif period == '1996_2006':
            middle_terms = ["Đại hội VIII", "công nghiệp hóa", "hiện đại hóa", 
                          "kinh tế thị trường", "500 kV", "hội nhập", "1996"]
            if any(term in str(label) for label in entity_labels for term in middle_terms):
                relevance_score += 2
        
        elif period == '2006_nay':
            recent_terms = ["Đại hội X", "thành tựu", "GDP", "tăng trưởng", 
                          "hội nhập toàn diện", "quan hệ đối ngoại", "giảm nghèo",
                          "2006", "hiệp định thương mại"]
            if any(term in str(label) for label in entity_labels for term in recent_terms):
                relevance_score += 2
        
        elif period == 'thanh_tuu_chung':
            achievement_terms = ["tỉ lệ", "tăng", "giảm", "chỉ số", "mức", 
                               "thành tựu", "đạt được", "cải thiện", "nâng cao"]
            if any(term in str(label).lower() for label in entity_labels for term in achievement_terms):
                relevance_score += 2
        
        if relevance_score > 0 or in_window:
            entity['period_relevance'] = relevance_score
            filtered[entity_id] = entity
    
    return filtered

def format_doi_moi_entities_for_prompt(entity_lookup: Dict[str, Dict], period: str) -> str:
    """Định dạng entities cho prompt với thông tin Đổi mới."""
    entity_lines = []
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 4"]
    
    for entity_id, entity in entity_lookup.items():
        if entity_id == entity['id']:
            entity_type = entity.get('type', 'Unknown')
            labels = entity.get('context_labels', [])
            relevance = entity.get('period_relevance', 0)
            
            if relevance > 0 or entity_type in TopicProcessor.TOPIC_CONFIGS["Chủ đề 4"]['focus_entities']:
                line = f"- {entity_id}"
                if labels:
                    line += f" [Tên: {', '.join(labels[:2])}]"
                line += f" (Loại: {entity_type})"
                
                if "Đại hội" in entity_id:
                    line += " [Sự kiện chính trị quan trọng]"
                elif entity_type == "Chỉ tiêu kinh tế":
                    line += " [Số liệu thống kê]"
                    if 'description' in entity and re.search(r'\d+\.?\d*%?', entity['description']):
                        line += f" - {entity['description'][:50]}..."
                elif entity_type == "Thành tựu phát triển":
                    line += " [Kết quả đạt được]"
                elif "GDP" in entity_id or "tăng trưởng" in entity_id.lower():
                    line += " [Chỉ số kinh tế quan trọng]"
                elif "hội nhập" in entity_id.lower() or "hiệp định" in entity_id.lower():
                    line += " [Quan hệ quốc tế]"
                
                entity_lines.append((relevance, line))
    
    entity_lines.sort(key=lambda x: x[0], reverse=True)
    
    return "\n".join([line[1] for line in entity_lines[:45]])

def extract_doi_moi_relationships(prompt: str, start_idx: int, window_sentences: List[str],
                                 entity_lookup: Dict[str, Dict], file_info: Dict[str, str],
                                 target_entity_id: str, period: str) -> Optional[Dict]:
    """Trích xuất quan hệ Đổi mới với validation đặc thù."""
    global API_REQUEST_COUNT
    
    for attempt in range(3):
        try:
            time.sleep(2)
            
            api_key, key_idx = get_next_api_key()
            if not api_key:
                print("Không có API key")
                return None
                
            # DeepSeek API - configured in api_handler
            # model handled by call_deepseek_api
            
            API_REQUEST_COUNT += 1
            print(f"[DoiMoi-API #{API_REQUEST_COUNT}]", end=" ")
            
            result = call_deepseek_api(prompt)
            response_text = response.text
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                try:
                    relationships_data = json.loads(json_match.group())
                    validated_relationships = []
                    
                    for rel in relationships_data.get('relationships', []):
                        if validate_doi_moi_relationship(rel, entity_lookup, period):
                            priority_score = calculate_doi_moi_priority(rel, period)
                            
                            rel['window_info'] = {
                                'start_idx': start_idx,
                                'sentences': window_sentences[:3],
                                'file_info': file_info,
                                'period': period,
                                'target_entity': target_entity_id
                            }
                            
                            rel['period'] = period
                            rel['priority_score'] = priority_score
                            
                            evidence_quality = assess_doi_moi_evidence_quality(rel.get('evidence', ''), period)
                            base_confidence = rel.get('confidence', 0.8)
                            rel['confidence'] = min(0.97, base_confidence * evidence_quality + (priority_score * 0.05))
                            
                            if 'time_reference' not in rel:
                                time_match = re.search(r'\d{4}', rel.get('evidence', ''))
                                if time_match:
                                    rel['time_reference'] = time_match.group()
                            
                            data_match = re.search(r'\d+\.?\d*\%', rel.get('evidence', ''))
                            if data_match:
                                rel['data_point'] = data_match.group()
                            else:
                                numbers = re.findall(r'\d+\.?\d*', rel.get('evidence', ''))
                                if numbers and len(numbers) <= 3:
                                    rel['data_point'] = ', '.join(numbers[:2])
                            
                            rel = classify_doi_moi_achievement(rel)
                            
                            validated_relationships.append(rel)
                    
                    return {
                        'relationships': validated_relationships,
                        'window_index': start_idx,
                        'target_entity': target_entity_id,
                        'period': period
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"Lỗi JSON: {e}")
                    debug_file = f"doi_moi_error_period_{period}_{start_idx}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"Prompt: {prompt[:2000]}...\n\nResponse: {response_text}\n\nError: {e}")
                    try:
                        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
                        all_json = re.findall(json_pattern, response_text)
                        if all_json:
                            # Lấy JSON object đầu tiên
                            relationships_data = json.loads(all_json[0])
                            # ... xử lý tiếp ...
                    except:
                        pass
                    
                    if attempt < 2:
                        time.sleep(3)
            
        except Exception as e:
            print(f"Lỗi (lần {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(3)
    
    return None

def validate_doi_moi_relationship(relationship: Dict, entity_lookup: Dict[str, Dict], 
                                  period: str) -> bool:
    """Validate quan hệ Đổi mới với tiêu chí chặt chẽ."""
    subject_id = relationship.get('subject_id', '').strip()
    object_id = relationship.get('object_id', '').strip()
    predicate = relationship.get('predicate', '').strip()
    evidence = relationship.get('evidence', '').strip()
    
    if not subject_id or not object_id or not predicate:
        return False
    
    if subject_id == object_id:
        return False
    
    subject_exists = subject_id in entity_lookup
    object_exists = object_id in entity_lookup
    
    if not subject_exists or not object_exists:
        subject_found = any(subject_id in entity.get('context_labels', []) 
                          for entity in entity_lookup.values())
        object_found = any(object_id in entity.get('context_labels', []) 
                         for entity in entity_lookup.values())
        
        if not subject_found or not object_found:
            return False
    
    valid_doi_moi_predicates = [
        'khởi_xướng', 'đề_ra', 'thông_qua', 'triển_khai', 'thực_hiện',
        'đạt_được', 'chuyển_đổi_sang', 'cải_cách', 'hội_nhập', 'ký_kết',
        'tham_gia', 'phát_triển_thành', 'tăng_trưởng', 'giảm_xuống', 'tăng_lên',
        'hoàn_thành', 'xây_dựng', 'củng_cố', 'mở_rộng', 'nâng_cao'
    ]
    
    if predicate not in valid_doi_moi_predicates and not any(p in predicate for p in ['_']):
        if len(predicate) < 3 or len(predicate) > 60:
            return False
    
    if len(evidence) < 20:
        return False
    
    if not re.search(r'\d{4}', evidence) and period not in ['khac', 'thanh_tuu_chung']:
        if period not in ['khac', 'thanh_tuu_chung']:
            important_predicates = ['khởi_xướng', 'đề_ra', 'thông_qua', 'đạt_được', 'chuyển_đổi_sang']
            if predicate in important_predicates:
                return False
    
    evidence_lower = evidence.lower()
    subject_found_in_evidence = False
    object_found_in_evidence = False
    
    if subject_id in entity_lookup:
        subject_entity = entity_lookup[subject_id]
        for label in subject_entity.get('context_labels', []):
            if label.lower() in evidence_lower:
                subject_found_in_evidence = True
                break
    
    if object_id in entity_lookup:
        object_entity = entity_lookup[object_id]
        for label in object_entity.get('context_labels', []):
            if label.lower() in evidence_lower:
                object_found_in_evidence = True
                break
    
    if not subject_found_in_evidence and not object_found_in_evidence:
        return False
    
    return True

def calculate_doi_moi_priority(relationship: Dict, period: str) -> int:
    """Tính điểm ưu tiên cho quan hệ Đổi mới."""
    priority = 1
    
    subject = relationship.get('subject_id', '')
    predicate = relationship.get('predicate', '')
    object_ = relationship.get('object_id', '')
    evidence = relationship.get('evidence', '')
    
    if predicate == 'khởi_xướng' and 'Đại hội VI' in subject and 'Đổi mới' in object_:
        priority += 3
    
    if predicate == 'thông_qua' and any(term in subject for term in ['Đại hội VI', 'Đại hội VII', 'Đại hội VIII', 'Đại hội X']):
        priority += 2
    
    if predicate in ['đạt_được', 'hoàn_thành'] and any(term in object_ for term in [
        'tăng trưởng GDP', 'xoá đói giảm nghèo', 'hội nhập quốc tế', 'công nghiệp hóa'
    ]):
        priority += 2
    
    if 'data_point' in relationship:
        priority += 2
    
    if predicate == 'chuyển_đổi_sang' and 'kinh tế thị trường' in object_:
        priority += 2
    
    if predicate == 'bãi_bỏ' and 'tem phiếu' in object_:
        priority += 2
    
    if re.search(r'\d{4}', evidence):
        priority += 1
    
    if period != 'khac':
        priority += 1
    
    return priority

def assess_doi_moi_evidence_quality(evidence: str, period: str) -> float:
    """Đánh giá chất lượng evidence cho quan hệ Đổi mới."""
    quality = 0.7
    
    if len(evidence) > 30:
        quality += 0.1
    if len(evidence) > 50:
        quality += 0.1
    
    year_match = re.search(r'\d{4}', evidence)
    if year_match:
        quality += 0.2
        year = int(year_match.group())
        
        if period == '1986_1995' and 1986 <= year <= 1995:
            quality += 0.1
        elif period == '1996_2006' and 1996 <= year <= 2006:
            quality += 0.1
        elif period == '2006_nay' and year >= 2006:
            quality += 0.1
    
    if re.search(r'\d+\.?\d*\%', evidence):
        quality += 0.2
    
    numbers = re.findall(r'\d+\.?\d*', evidence)
    if len(numbers) >= 2:
        quality += 0.1
    
    if 'từ' in evidence and 'xuống' in evidence or 'từ' in evidence and 'lên' in evidence:
        quality += 0.1
    
    if any(term in evidence.lower() for term in ['đại hội', 'nghị quyết', 'chính sách']):
        quality += 0.1
    
    if 'đổi mới' in evidence.lower():
        quality += 0.1
    
    economic_terms = ['gdp', 'tăng trưởng', 'xuất khẩu', 'nhập khẩu', 'đầu tư', 
                     'lạm phát', 'nghèo', 'thu nhập', 'cơ cấu']
    if any(term in evidence.lower() for term in economic_terms):
        quality += 0.1
    
    return min(1.0, quality)

def classify_doi_moi_achievement(relationship: Dict) -> Dict:
    """Phân loại thành tựu Đổi mới."""
    predicate = relationship.get('predicate', '')
    object_ = relationship.get('object_id', '')
    evidence = relationship.get('evidence', '')
    
    achievement_types = {
        'kinh_te': ['GDP', 'tăng trưởng', 'xuất khẩu', 'nhập khẩu', 'đầu tư', 'lạm phát'],
        'xa_hoi': ['nghèo', 'giáo dục', 'y tế', 'đời sống', 'phúc lợi', 'HDI'],
        'co_cau': ['cơ cấu', 'chuyển dịch', 'tỷ trọng', 'ngành', 'khu vực'],
        'hoi_nhap': ['hội nhập', 'quan hệ', 'hiệp định', 'đối tác', 'tổ chức quốc tế'],
        'ha_tang': ['cơ sở hạ tầng', 'công trình', 'đường dây', 'xây dựng']
    }
    
    for achi_type, keywords in achievement_types.items():
        for keyword in keywords:
            if keyword.lower() in evidence.lower() or keyword in object_:
                relationship['achievement_type'] = achi_type
                return relationship
    
    return relationship

def post_process_doi_moi_relationships(relationships: List[Dict]) -> List[Dict]:
    """Hậu xử lý quan hệ Đổi mới."""
    groups = defaultdict(list)
    
    for rel in relationships:
        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
        groups[key].append(rel)
    
    merged = []
    
    for key, rel_list in groups.items():
        if not rel_list:
            continue
        
        base = rel_list[0].copy()
        base['occurrence_count'] = len(rel_list)
        
        all_evidence = []
        for rel in rel_list:
            evidence = {
                'text': rel.get('evidence', ''),
                'period': rel.get('period', 'unknown'),
                'time_reference': rel.get('time_reference', ''),
                'data_point': rel.get('data_point', ''),
                'window_info': rel.get('window_info', {}),
                'timestamp': time.time()
            }
            
            if not any(e['text'] == evidence['text'] for e in all_evidence):
                all_evidence.append(evidence)
        
        base['supporting_sentences'] = all_evidence
        
        total_conf = 0
        total_weight = 0
        
        for rel in rel_list:
            conf = rel.get('confidence', 0.8)
            priority = rel.get('priority_score', 1)
            weight = priority
            
            total_conf += conf * weight
            total_weight += weight
        
        if total_weight > 0:
            base['confidence'] = min(0.98, total_conf / total_weight)
        
        if 'policy_context' not in base:
            achievement_desc = ""
            if 'achievement_type' in base:
                type_map = {
                    'kinh_te': 'Kinh tế',
                    'xa_hoi': 'Xã hội',
                    'co_cau': 'Cơ cấu',
                    'hoi_nhap': 'Hội nhập',
                    'ha_tang': 'Hạ tầng'
                }
                achievement_desc = f" - Thành tựu {type_map.get(base['achievement_type'], '')}"
            
            base['policy_context'] = f"Giai đoạn: {base.get('period', 'unknown')}{achievement_desc}"
        
        merged.append(base)
    
    merged.sort(key=lambda x: (
        x.get('priority_score', 0),
        x.get('confidence', 0)
    ), reverse=True)
    
    return merged

# ============================================================================
# HÀM XỬ LÝ ĐẶC THÙ CHO CHỦ ĐỀ 5 (ĐỐI NGOẠI)
# ============================================================================

def process_diplomacy_file(file_path: str, entity_lookup: Dict[str, Dict], existing_kg: Dict) -> Dict:
    """Xử lý file thuộc Chủ đề 5 với chiến lược đặc thù."""
    
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 5"]
    
    print(f"\n{'='*60}")
    print(f"XỬ LÝ CHỦ ĐỀ 5: {topic_config['topic_name']}")
    print(f"Trọng tâm: {topic_config['thematic_focus'][:100]}...")
    print(f"{'='*60}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return existing_kg
    
    topic, lesson = extract_topic_and_lesson(file_path)
    file_info = {
        'file_path': file_path,
        'topic': topic,
        'lesson': lesson,
        'topic_config': topic_config['topic_name'],
        'diplomacy_focus': True
    }
    
    all_entities = existing_kg.get('entities', [])
    diplomacy_priority_entities = []
    
    high_priority_terms = [
        "Phan Bội Châu", "Phan Châu Trinh", "Nguyễn Ái Quốc", "Hồ Chí Minh",
        "Đảng Cộng sản Đông Dương", "Việt Nam Dân chủ Cộng hòa", "Mặt trận Việt Minh",
        "Hiệp định", "Hội nghị", "đối ngoại", "ngoại giao", "thiết lập quan hệ",
        "ký kết", "tham gia", "gia nhập", "Liên hợp quốc", "ASEAN", "WTO"
    ]
    
    medium_priority_terms = [
        "Quốc tế Cộng sản", "OSS", "SEV", "APEC", "ASEM", "RCEP", "EVFTA",
        "đàm phán", "vận động", "tranh thủ", "ủng hộ", "hợp tác",
        "Trung Quốc", "Mỹ", "Liên Xô", "Nga", "Nhật Bản", "Pháp"
    ]
    
    key_events = [
        "Hiệp định Sơ bộ", "Tạm ước Việt-Pháp", "Hiệp định Giơ-ne-vơ",
        "Hiệp định Pa-ri", "Hội nghị Pa-ri", "Hội nghị Giơ-ne-vơ",
        "Việt Nam Quang phục hội", "Hội Liên hiệp các dân tộc bị áp bức",
        "Liên minh nhân dân Việt - Miên - Lào"
    ]
    
    for entity in all_entities:
        entity_id = entity['id']
        labels = entity.get('label', [])
        entity_type = entity.get('type', '')
        
        priority_score = 0
        
        for term in high_priority_terms:
            if any(term in str(label) for label in labels) or term in entity_id:
                priority_score += 3
        
        for term in medium_priority_terms:
            if any(term in str(label).lower() for label in labels) or term.lower() in entity_id.lower():
                priority_score += 2
        
        for event in key_events:
            if any(event in str(label) for label in labels) or event in entity_id:
                priority_score += 2
        
        if entity_type in topic_config['focus_entities']:
            priority_score += 2
        
        if re.search(r'\d{4}', entity_id) or any(re.search(r'\d{4}', str(label)) for label in labels):
            priority_score += 1
        
        if priority_score > 0:
            entity['diplomacy_priority'] = priority_score
            diplomacy_priority_entities.append(entity)
    
    diplomacy_priority_entities.sort(key=lambda x: x.get('diplomacy_priority', 0), reverse=True)
    
    filtered_entity_lookup = {}
    for entity in diplomacy_priority_entities[:70]:
        entity_copy = entity.copy()
        
        labels_in_context = []
        for occ in entity.get('original_text', []):
            if occ.get('topic') == topic and occ.get('lesson') == lesson:
                labels_in_context.extend(occ.get('labels', entity.get('label', [])))
        
        if labels_in_context:
            entity_copy['context_labels'] = list(set(labels_in_context))
        else:
            entity_copy['context_labels'] = entity.get('label', [])
        
        filtered_entity_lookup[entity['id']] = entity_copy
        
        for label in entity_copy['context_labels']:
            if label not in filtered_entity_lookup:
                filtered_entity_lookup[label] = entity_copy
    
    print(f"Đã chọn {len(filtered_entity_lookup)} thực thể ưu tiên cho Đối ngoại Việt Nam")
    
    sentences = split_into_sentences(content)
    historical_periods = identify_diplomacy_periods(sentences)
    
    all_relationships = []
    
    for period_name, period_sentences in historical_periods.items():
        if not period_sentences:
            continue
            
        print(f"\nGiai đoạn: {topic_config['historical_periods'].get(period_name, period_name)} ({len(period_sentences)} câu)")
        
        windows = create_overlapping_windows(
            period_sentences,
            window_size=topic_config['window_size'],
            step=topic_config['step_size']
        )
        
        for window_idx, (start_idx, window_sentences) in enumerate(windows[:10]):
            print(f"  Window {window_idx+1}/{min(4, len(windows))}: ", end="", flush=True)
            
            period_filtered_entities = filter_entities_for_diplomacy_period(
                filtered_entity_lookup, period_name, window_sentences
            )
            
            if len(period_filtered_entities) < 2:
                print("Ít thực thể -> Bỏ qua")
                continue
            
            existing_entities_str = format_diplomacy_entities_for_prompt(period_filtered_entities, period_name)
            window_text = " ".join(window_sentences)
            
            key_entities_in_window = []
            for entity_id, entity in period_filtered_entities.items():
                if entity_id == entity['id']:
                    window_text_lower = window_text.lower()
                    entity_labels = entity.get('context_labels', [])
                    
                    for label in entity_labels:
                        if label.lower() in window_text_lower and len(label) > 3:
                            if entity.get('diplomacy_priority', 0) >= 3:
                                key_entities_in_window.append(entity_id)
                            break
            
            if not key_entities_in_window:
                print("Không có thực thể quan trọng -> Bỏ qua")
                continue
            
            primary_entity = key_entities_in_window[0]
            
            prompt = TopicProcessor.create_topic_prompt(
                    "Chủ đề 5", 
                    window_text, 
                    existing_entities_str,
                    target_entity_id=primary_entity
                )
            
            result = extract_diplomacy_relationships(
                prompt,
                start_idx,
                window_sentences,
                period_filtered_entities,
                file_info,
                primary_entity,
                period_name
            )
            
            if result:
                relationships = result.get('relationships', [])
                if relationships:
                    all_relationships.extend(relationships)
                    print(f"{len(relationships)}R ", end="", flush=True)
            
            print("")
            time.sleep(2)
    
    processed_relationships = post_process_diplomacy_relationships(all_relationships)
    
    triplets = []
    for rel in processed_relationships:
        triplet = {
            'subject_id': rel['subject_id'],
            'predicate': rel['predicate'],
            'object_id': rel['object_id'],
            'properties': {
                'diplomatic_context': rel.get('diplomatic_context', ''),
                'time_reference': rel.get('time_reference', ''),
                'location_reference': rel.get('location_reference', ''),
                'period': rel.get('period', ''),
                'relationship_type': rel.get('relationship_type', '')
            },
            'metadata': {
                'extraction_method': 'diplomacy_specialized',
                'file_info': file_info,
                'evidence_count': len(rel.get('supporting_sentences', [])),
                'historical_period': rel.get('period', 'unknown'),
                'priority_score': rel.get('priority_score', 1),
                'has_time_reference': 'time_reference' in rel
            },
            'supporting_sentences': rel.get('supporting_sentences', []),
            'confidence': rel.get('confidence', 0.9),
            'occurrence_count': rel.get('occurrence_count', 1)
        }
        triplets.append(triplet)
    
    existing_triplets = existing_kg.get('triplets', [])
    existing_entities = existing_kg.get('entities', [])
    
    triplet_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
    for triplet in triplets:
        key = (triplet['subject_id'], triplet['predicate'], triplet['object_id'])
        if key not in triplet_keys:
            existing_triplets.append(triplet)
            triplet_keys.add(key)
    
    print(f"\nĐã thêm {len(triplets)} quan hệ Đối ngoại từ file này")
    return {
        'entities': existing_entities,
        'triplets': existing_triplets
    }

def identify_diplomacy_periods(sentences: List[str]) -> Dict[str, List[str]]:
    """Nhận diện các giai đoạn lịch sử trong văn bản về đối ngoại."""
    periods = {
        '1900_1945': [],
        '1945_1954': [],
        '1954_1975': [],
        '1975_1985': [],
        '1986_nay': [],
        'khac': []
    }
    
    period_keywords = {
        '1900_1945': [
            'phan bội châu', 'phan châu trinh', 'nguyễn ái quốc',
            'đầu thế kỷ xx', '1905', '1911', '1912', '1920', '1925',
            'việt nam quang phục hội', 'hội liên hiệp', 'quốc tế cộng sản',
            'trước cách mạng tháng tám', '1900-1945'
        ],
        '1945_1954': [
            'kháng chiến chống pháp', '1945-1954', 'hiệp định sơ bộ',
            'tạm ước việt-pháp', 'giơ-ne-vơ 1954', 'chiến tranh đông dương',
            'liên minh việt - miên - lào', 'thiết lập quan hệ 1950',
            'trung quốc 1950', 'liên xô 1950', 'chiến tranh đông dương lần thứ nhất'
        ],
        '1954_1975': [
            'kháng chiến chống mỹ', '1954-1975', 'hiệp định pa-ri',
            'hội nghị pa-ri', 'chiến tranh việt nam', 'mặt trận dân tộc giải phóng',
            'chính phủ cách mạng lâm thời', 'chiến tranh đông dương lần thứ hai',
            'vừa đánh vừa đàm', 'đàm phán pa-ri'
        ],
        '1975_1985': [
            'sau 1975', '1975-1985', 'hội đồng tương trợ kinh tế', 'sev',
            'ba nước đông dương', 'vấn đề campuchia', 'quan hệ với asean',
            'phong trào không liên kết', 'hợp tác với liên xô', 'xung đột biên giới'
        ],
        '1986_nay': [
            'đổi mới', 'từ 1986', 'bình thường hóa 1991', 'bình thường hóa 1995',
            'gia nhập asean 1995', 'gia nhập wto', 'evfta', 'rcep',
            'đối tác chiến lược', 'ủy viên hội đồng bảo an', 'hội nhập quốc tế'
        ]
    }
    
    current_period = 'khac'
    period_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        detected_period = None
        max_matches = 0
        
        for period_name, keywords in period_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in sentence_lower)
            if matches > max_matches:
                max_matches = matches
                detected_period = period_name
        
        if detected_period and max_matches > 0:
            if period_sentences:
                periods[current_period].extend(period_sentences)
            
            current_period = detected_period
            period_sentences = [sentence]
        else:
            period_sentences.append(sentence)
    
    if period_sentences:
        periods[current_period].extend(period_sentences)
    
    return {k: v for k, v in periods.items() if v}

def filter_entities_for_diplomacy_period(entity_lookup: Dict[str, Dict], period: str, 
                                         window_sentences: List[str]) -> Dict[str, Dict]:
    """Lọc entities phù hợp với giai đoạn đối ngoại cụ thể."""
    filtered = {}
    window_text = " ".join(window_sentences).lower()
    
    for entity_id, entity in entity_lookup.items():
        if entity_id != entity['id']:
            continue
            
        entity_labels = entity.get('context_labels', [])
        
        in_window = False
        for label in entity_labels:
            if label.lower() in window_text and len(label) > 3:
                in_window = True
                break
        
        if not in_window:
            continue
        
        relevance_score = 0
        
        if period == '1900_1945':
            early_terms = ["Phan Bội Châu", "Phan Châu Trinh", "Nguyễn Ái Quốc", 
                          "Việt Nam Quang phục hội", "Hội Liên hiệp", "Quốc tế Cộng sản",
                          "Đảng Cộng sản Pháp", "1905", "1912", "1920", "1925"]
            if any(term in str(label) for label in entity_labels for term in early_terms):
                relevance_score += 2
        
        elif period == '1945_1954':
            anti_french_terms = ["Hiệp định Sơ bộ", "Tạm ước Việt-Pháp", "Giơ-ne-vơ",
                                "Trung Quốc 1950", "Liên Xô 1950", "Liên minh Việt - Miên - Lào",
                                "Mặt trận Việt Minh", "OSS", "1946", "1950", "1954"]
            if any(term in str(label) for label in entity_labels for term in anti_french_terms):
                relevance_score += 2
        
        elif period == '1954_1975':
            anti_us_terms = ["Hiệp định Pa-ri", "Hội nghị Pa-ri", "Mặt trận Dân tộc giải phóng",
                            "Chính phủ Cách mạng lâm thời", "Mỹ", "Liên Xô", "Trung Quốc",
                            "1973", "đàm phán Pa-ri", "chiến tranh Việt Nam"]
            if any(term in str(label) for label in entity_labels for term in anti_us_terms):
                relevance_score += 2
        
        elif period == '1975_1985':
            post_war_terms = ["SEV", "Hội đồng tương trợ kinh tế", "Campuchia",
                             "ASEAN", "Phong trào Không liên kết", "Liên Xô",
                             "ba nước Đông Dương", "1978", "1979"]
            if any(term in str(label) for label in entity_labels for term in post_war_terms):
                relevance_score += 2
        
        elif period == '1986_nay':
            doi_moi_terms = ["ASEAN", "WTO", "EVFTA", "RCEP", "APEC", "ASEM",
                            "bình thường hóa", "đối tác chiến lược", "Hội đồng Bảo an",
                            "1991", "1995", "2007", "2008", "2020"]
            if any(term in str(label) for label in entity_labels for term in doi_moi_terms):
                relevance_score += 2
        
        if relevance_score > 0 or in_window:
            entity['period_relevance'] = relevance_score
            filtered[entity_id] = entity
    
    return filtered

def format_diplomacy_entities_for_prompt(entity_lookup: Dict[str, Dict], period: str) -> str:
    """Định dạng entities cho prompt với thông tin Đối ngoại."""
    entity_lines = []
    
    for entity_id, entity in entity_lookup.items():
        if entity_id == entity['id']:
            entity_type = entity.get('type', 'Unknown')
            labels = entity.get('context_labels', [])
            relevance = entity.get('period_relevance', 0)
            
            if relevance > 0 or entity_type in TopicProcessor.TOPIC_CONFIGS["Chủ đề 5"]['focus_entities']:
                line = f"- {entity_id}"
                if labels:
                    line += f" [Tên: {', '.join(labels[:2])}]"
                line += f" (Loại: {entity_type})"
                
                if any(name in entity_id for name in ["Phan Bội Châu", "Phan Châu Trinh", "Nguyễn Ái Quốc", "Hồ Chí Minh"]):
                    line += " [Nhân vật lịch sử quan trọng]"
                elif "Hiệp định" in entity_id or "Hội nghị" in entity_id:
                    line += " [Văn kiện ngoại giao]"
                    if 'description' in entity and re.search(r'\d{4}', entity['description']):
                        year_match = re.search(r'\d{4}', entity['description'])
                        if year_match:
                            line += f" - Năm: {year_match.group()}"
                elif entity_type == "Quốc gia":
                    line += " [Đối tác ngoại giao]"
                elif entity_type == "Tổ chức Chính trị":
                    line += " [Chủ thể đối ngoại]"
                elif entity_type == "Mặt trận/Tổ chức Quốc tế":
                    line += " [Tổ chức quốc tế]"
                
                entity_lines.append((relevance, line))
    
    entity_lines.sort(key=lambda x: x[0], reverse=True)
    
    return "\n".join([line[1] for line in entity_lines[:40]])

def extract_diplomacy_relationships(prompt: str, start_idx: int, window_sentences: List[str],
                                   entity_lookup: Dict[str, Dict], file_info: Dict[str, str],
                                   target_entity_id: str, period: str) -> Optional[Dict]:
    """Trích xuất quan hệ Đối ngoại với validation đặc thù."""
    global API_REQUEST_COUNT
    
    for attempt in range(3):
        try:
            time.sleep(2)
            
            api_key, key_idx = get_next_api_key()
            if not api_key:
                print("Không có API key")
                return None
                
            # DeepSeek API - configured in api_handler
            # model handled by call_deepseek_api
            
            API_REQUEST_COUNT += 1
            print(f"[Diplomacy-API #{API_REQUEST_COUNT}]", end=" ")
            
            result = call_deepseek_api(prompt)
            # THÊM KIỂM TRA NÀY: kiểm tra response và response.text
            if not response or not hasattr(response, 'text') or response.text is None:
                print(f"Lỗi: response rỗng (lần {attempt+1})")
                if attempt < 2:
                    time.sleep(3)
                continue
            response_text = response.text
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                try:
                    json_str = json_match.group()
                    
                    # THÊM KIỂM TRA: loại bỏ các ký tự null hoặc không hợp lệ
                    json_str = json_str.replace('\x00', '').replace('\ufffd', '')
                    
                    # THÊM KIỂM TRA: cắt bỏ phần thừa nếu có multiple JSON objects
                    if json_str.count('{') > 1:
                        # Tìm JSON object đầu tiên
                        start = json_str.find('{')
                        end = json_str.rfind('}')
                        if end > start:
                            json_str = json_str[start:end+1]
                            
                    relationships_data = json.loads(json_match.group())
                    validated_relationships = []
                    
                    for rel in relationships_data.get('relationships', []):
                        if validate_diplomacy_relationship(rel, entity_lookup, period):
                            priority_score = calculate_diplomacy_priority(rel, period)
                            
                            rel['window_info'] = {
                                'start_idx': start_idx,
                                'sentences': window_sentences[:3],
                                'file_info': file_info,
                                'period': period,
                                'target_entity': target_entity_id
                            }
                            
                            rel['period'] = period
                            rel['priority_score'] = priority_score
                            
                            evidence_quality = assess_diplomacy_evidence_quality(rel.get('evidence', ''), period)
                            base_confidence = rel.get('confidence', 0.8)
                            rel['confidence'] = min(0.97, base_confidence * evidence_quality + (priority_score * 0.05))
                            
                            if 'time_reference' not in rel:
                                time_match = re.search(r'\d{4}', rel.get('evidence', ''))
                                if time_match:
                                    rel['time_reference'] = time_match.group()
                            
                            evidence_lower = rel.get('evidence', '').lower()
                            location_indicators = ['tại', 'ở', 'từ', 'đến', 'về', 'sang']
                            for indicator in location_indicators:
                                if indicator in evidence_lower:
                                    words = rel.get('evidence', '').split()
                                    for i, word in enumerate(words):
                                        if word.lower() == indicator and i + 1 < len(words):
                                            location = words[i + 1]
                                            if len(location) > 2 and not location[0].isdigit():
                                                rel['location_reference'] = location
                                                break
                                    break
                            
                            rel = classify_diplomacy_relationship(rel)
                            
                            validated_relationships.append(rel)
                    
                    return {
                        'relationships': validated_relationships,
                        'window_index': start_idx,
                        'target_entity': target_entity_id,
                        'period': period
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"Lỗi JSON: {e}")
                    debug_file = f"diplomacy_error_period_{period}_{start_idx}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"Prompt: {prompt[:2000]}...\n\nResponse: {response_text}\n\nError: {e}")
                    try:
                        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
                        all_json = re.findall(json_pattern, response_text)
                        if all_json:
                            # Lấy JSON object đầu tiên
                            relationships_data = json.loads(all_json[0])
                            # ... xử lý tiếp ...
                    except:
                        pass
                    
                    if attempt < 2:
                        time.sleep(3)
            
        except Exception as e:
            print(f"Lỗi (lần {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(3)
    
    return None

def validate_diplomacy_relationship(relationship: Dict, entity_lookup: Dict[str, Dict], 
                                    period: str) -> bool:
    """Validate quan hệ Đối ngoại với tiêu chí chặt chẽ."""
    subject_id = relationship.get('subject_id', '').strip()
    object_id = relationship.get('object_id', '').strip()
    predicate = relationship.get('predicate', '').strip()
    evidence = relationship.get('evidence', '').strip()
    
    if not subject_id or not object_id or not predicate:
        return False
    
    if subject_id == object_id:
        return False
    
    subject_exists = subject_id in entity_lookup
    object_exists = object_id in entity_lookup
    
    if not subject_exists or not object_exists:
        subject_found = any(subject_id in entity.get('context_labels', []) 
                          for entity in entity_lookup.values())
        object_found = any(object_id in entity.get('context_labels', []) 
                         for entity in entity_lookup.values())
        
        if not subject_found or not object_found:
            return False
    
    valid_diplomacy_predicates = [
        'thành_lập', 'tham_gia', 'tham_gia_thành_lập', 'ký_kết', 
        'thiết_lập_quan_hệ', 'gia_nhập', 'đàm_phán_với', 'hợp_tác_với',
        'tranh_thủ_ủng_hộ', 'vận_động', 'tiếp_xúc_với', 'tìm_kiếm_giúp_đỡ',
        'phối_hợp_với', 'ủng_hộ', 'chống_lại', 'giải_quyết_xung_đột',
        'bình_thường_hóa_quan_hệ', 'nâng_cấp_quan_hệ', 'thành_lập_tại'
    ]
    
    if predicate not in valid_diplomacy_predicates and not any(p in predicate for p in ['_']):
        if len(predicate) < 3 or len(predicate) > 60:
            return False
    
    if len(evidence) < 20:
        return False
    
    if not re.search(r'\d{4}', evidence) and period not in ['khac']:
        if period not in ['khac']:
            important_predicates = ['thành_lập', 'ký_kết', 'thiết_lập_quan_hệ', 'gia_nhập']
            if predicate in important_predicates:
                return False
    
    evidence_lower = evidence.lower()
    subject_found_in_evidence = False
    object_found_in_evidence = False
    
    if subject_id in entity_lookup:
        subject_entity = entity_lookup[subject_id]
        for label in subject_entity.get('context_labels', []):
            if label.lower() in evidence_lower:
                subject_found_in_evidence = True
                break
    
    if object_id in entity_lookup:
        object_entity = entity_lookup[object_id]
        for label in object_entity.get('context_labels', []):
            if label.lower() in evidence_lower:
                object_found_in_evidence = True
                break
    
    if not subject_found_in_evidence and not object_found_in_evidence:
        return False
    
    return True

def calculate_diplomacy_priority(relationship: Dict, period: str) -> int:
    """Tính điểm ưu tiên cho quan hệ Đối ngoại."""
    priority = 1
    
    subject = relationship.get('subject_id', '')
    predicate = relationship.get('predicate', '')
    object_ = relationship.get('object_id', '')
    evidence = relationship.get('evidence', '')
    
    if predicate == 'thành_lập' and any(term in object_ for term in [
        'Việt Nam Quang phục hội', 'Hội Liên hiệp các dân tộc bị áp bức',
        'Liên minh nhân dân Việt - Miên - Lào'
    ]):
        priority += 3
    
    if predicate == 'ký_kết' and any(term in object_ for term in [
        'Hiệp định Sơ bộ', 'Tạm ước Việt-Pháp', 'Hiệp định Giơ-ne-vơ',
        'Hiệp định Pa-ri', 'Hiệp định về Campuchia'
    ]):
        priority += 3
    
    if predicate == 'thiết_lập_quan_hệ' and any(term in evidence for term in [
        '1950', '1975', '1991', '1995'
    ]):
        priority += 2
    
    if predicate == 'gia_nhập' and any(term in object_ for term in [
        'ASEAN', 'WTO', 'Liên hợp quốc', 'Hội đồng tương trợ kinh tế'
    ]):
        priority += 2
    
    if 'Nguyễn Ái Quốc' in subject or 'Hồ Chí Minh' in subject:
        priority += 2
    
    if predicate == 'bình_thường_hóa_quan_hệ':
        priority += 2
    
    if re.search(r'\d{4}', evidence):
        priority += 1
    
    location_indicators = ['tại', 'ở', 'từ', 'đến']
    if any(indicator in evidence for indicator in location_indicators):
        priority += 1
    
    if period != 'khac':
        priority += 1
    
    return priority

def assess_diplomacy_evidence_quality(evidence: str, period: str) -> float:
    """Đánh giá chất lượng evidence cho quan hệ Đối ngoại."""
    quality = 0.7
    
    if len(evidence) > 30:
        quality += 0.1
    if len(evidence) > 50:
        quality += 0.1
    
    year_match = re.search(r'\d{4}', evidence)
    if year_match:
        quality += 0.2
        year = int(year_match.group())
        
        if period == '1900_1945' and 1900 <= year <= 1945:
            quality += 0.1
        elif period == '1945_1954' and 1945 <= year <= 1954:
            quality += 0.1
        elif period == '1954_1975' and 1954 <= year <= 1975:
            quality += 0.1
        elif period == '1975_1985' and 1975 <= year <= 1985:
            quality += 0.1
        elif period == '1986_nay' and year >= 1986:
            quality += 0.1
    
    if re.search(r'\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}', evidence):
        quality += 0.2
    
    location_indicators = ['tại', 'ở', 'từ', 'đến', 'sang', 'về']
    if any(indicator in evidence for indicator in location_indicators):
        quality += 0.1
    
    if any(term in evidence.lower() for term in ['hiệp định', 'hội nghị', 'hiến chương', 'tuyên bố']):
        quality += 0.1
    
    org_terms = ['asean', 'wto', 'liên hợp quốc', 'quốc tế cộng sản', 'seb']
    if any(term in evidence.lower() for term in org_terms):
        quality += 0.1
    
    if any(term in evidence.lower() for term in ['ký', 'kí', 'thông qua', 'cam kết']):
        quality += 0.1
    
    return min(1.0, quality)

def classify_diplomacy_relationship(relationship: Dict) -> Dict:
    """Phân loại quan hệ Đối ngoại."""
    predicate = relationship.get('predicate', '')
    
    relationship_types = {
        'establishment': ['thành_lập', 'thành_lập_tại', 'tham_gia_thành_lập'],
        'participation': ['tham_gia', 'gia_nhập', 'thông_qua'],
        'diplomatic_action': ['ký_kết', 'thiết_lập_quan_hệ', 'bình_thường_hóa_quan_hệ', 
                             'nâng_cấp_quan_hệ', 'đàm_phán_với', 'giải_quyết_xung_đột'],
        'cooperation': ['hợp_tác_với', 'phối_hợp_với', 'tranh_thủ_ủng_hộ', 'ủng_hộ'],
        'seeking_help': ['tìm_kiếm_giúp_đỡ', 'vận_động', 'tiếp_xúc_với'],
        'activity': ['hoạt_động_tại', 'gửi_đại_biểu', 'cử_người_liên_lạc']
    }
    
    for rel_type, predicates in relationship_types.items():
        if predicate in predicates:
            relationship['relationship_type'] = rel_type
            return relationship
    
    return relationship

def post_process_diplomacy_relationships(relationships: List[Dict]) -> List[Dict]:
    """Hậu xử lý quan hệ Đối ngoại."""
    groups = defaultdict(list)
    
    for rel in relationships:
        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
        groups[key].append(rel)
    
    merged = []
    
    for key, rel_list in groups.items():
        if not rel_list:
            continue
        
        base = rel_list[0].copy()
        base['occurrence_count'] = len(rel_list)
        
        all_evidence = []
        for rel in rel_list:
            evidence = {
                'text': rel.get('evidence', ''),
                'period': rel.get('period', 'unknown'),
                'time_reference': rel.get('time_reference', ''),
                'location_reference': rel.get('location_reference', ''),
                'window_info': rel.get('window_info', {}),
                'timestamp': time.time()
            }
            
            if not any(e['text'] == evidence['text'] for e in all_evidence):
                all_evidence.append(evidence)
        
        base['supporting_sentences'] = all_evidence
        
        total_conf = 0
        total_weight = 0
        
        for rel in rel_list:
            conf = rel.get('confidence', 0.8)
            priority = rel.get('priority_score', 1)
            weight = priority
            
            total_conf += conf * weight
            total_weight += weight
        
        if total_weight > 0:
            base['confidence'] = min(0.98, total_conf / total_weight)
        
        if 'diplomatic_context' not in base:
            rel_type_desc = ""
            if 'relationship_type' in base:
                type_map = {
                    'establishment': 'Thành lập tổ chức',
                    'participation': 'Tham gia tổ chức',
                    'diplomatic_action': 'Hành động ngoại giao',
                    'cooperation': 'Hợp tác',
                    'seeking_help': 'Tìm kiếm sự giúp đỡ',
                    'activity': 'Hoạt động'
                }
                rel_type_desc = f" - Loại: {type_map.get(base['relationship_type'], '')}"
            
            base['diplomatic_context'] = f"Giai đoạn: {base.get('period', 'unknown')}{rel_type_desc}"
        
        merged.append(base)
    
    merged.sort(key=lambda x: (
        x.get('priority_score', 0),
        x.get('confidence', 0)
    ), reverse=True)
    
    return merged

# ============================================================================
# HÀM XỬ LÝ ĐẶC THÙ CHO CHỦ ĐỀ 6 (HỒ CHÍ MINH)
# ============================================================================

def process_ho_chi_minh_file(file_path: str, entity_lookup: Dict[str, Dict], existing_kg: Dict) -> Dict:
    """Xử lý file thuộc Chủ đề 6 với chiến lược đặc thù."""
    
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 6"]
    
    print(f"\n{'='*60}")
    print(f"XỬ LÝ CHỦ ĐỀ 6: {topic_config['topic_name']}")
    print(f"Trọng tâm: {topic_config['thematic_focus'][:100]}...")
    print(f"{'='*60}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return existing_kg
    
    topic, lesson = extract_topic_and_lesson(file_path)
    file_info = {
        'file_path': file_path,
        'topic': topic,
        'lesson': lesson,
        'topic_config': topic_config['topic_name'],
        'ho_chi_minh_focus': True
    }
    
    all_entities = existing_kg.get('entities', [])
    ho_chi_minh_priority_entities = []
    
    high_priority_terms = [
        "Hồ Chí Minh", "Nguyễn Ái Quốc", "Nguyễn Tất Thành", "Nguyễn Sinh Cung",
        "Chủ tịch Hồ Chí Minh", "Bác Hồ", "19-5-1890", "5-6-1911",
        "Tuyên ngôn Độc lập", "Đảng Cộng sản Việt Nam", "Mặt trận Việt Minh",
        "Bến Nhà Rồng", "Pác Bó", "Tân Trào"
    ]
    
    medium_priority_terms = [
        "Làng Sen", "Kim Liên", "Nam Đàn", "Nghệ An", "Huế", "Sài Gòn",
        "Báo Thanh niên", "Báo Người cùng khổ", "Hội Việt Nam Cách mạng Thanh niên",
        "Đội Việt Nam Tuyên truyền Giải phóng quân", "Việt Minh",
        "Quảng Châu", "Pa-ri", "Liên Xô", "Cao Bằng", "Tuyên Quang"
    ]
    
    key_events = [
        "Cách mạng tháng Tám", "Kháng chiến chống Pháp", "Kháng chiến chống Mỹ",
        "Hội nghị thành lập Đảng", "Hội nghị Trung ương 8", "Đại hội Quốc dân Tân Trào",
        "Chiến dịch Điện Biên Phủ", "Đại thắng mùa Xuân 1975"
    ]
    
    ho_chi_minh_names = [
        "Hồ Chí Minh", "Nguyễn Ái Quốc", "Nguyễn Tất Thành", 
        "Nguyễn Sinh Cung", "Văn Ba"
    ]
    
    for entity in all_entities:
        entity_id = entity['id']
        labels = entity.get('label', [])
        entity_type = entity.get('type', '')
        
        priority_score = 0
        
        for name in ho_chi_minh_names:
            if any(name in str(label) for label in labels) or name in entity_id:
                priority_score += 3
        
        for term in high_priority_terms:
            if any(term in str(label) for label in labels) or term in entity_id:
                priority_score += 2
        
        for term in medium_priority_terms:
            if any(term in str(label).lower() for label in labels) or term.lower() in entity_id.lower():
                priority_score += 1
        
        for event in key_events:
            if any(event in str(label) for label in labels) or event in entity_id:
                priority_score += 1
        
        if entity_type in topic_config['focus_entities']:
            priority_score += 2
        
        if re.search(r'\d{4}', entity_id) or any(re.search(r'\d{4}', str(label)) for label in labels):
            priority_score += 1
        
        if priority_score > 0:
            entity['ho_chi_minh_priority'] = priority_score
            ho_chi_minh_priority_entities.append(entity)
    
    ho_chi_minh_priority_entities.sort(key=lambda x: x.get('ho_chi_minh_priority', 0), reverse=True)
    
    filtered_entity_lookup = {}
    for entity in ho_chi_minh_priority_entities[:60]:
        entity_copy = entity.copy()
        
        labels_in_context = []
        for occ in entity.get('original_text', []):
            if occ.get('topic') == topic and occ.get('lesson') == lesson:
                labels_in_context.extend(occ.get('labels', entity.get('label', [])))
        
        if labels_in_context:
            entity_copy['context_labels'] = list(set(labels_in_context))
        else:
            entity_copy['context_labels'] = entity.get('label', [])
        
        filtered_entity_lookup[entity['id']] = entity_copy
        
        for label in entity_copy['context_labels']:
            if label not in filtered_entity_lookup:
                filtered_entity_lookup[label] = entity_copy
    
    print(f"Đã chọn {len(filtered_entity_lookup)} thực thể ưu tiên cho chủ đề Hồ Chí Minh")
    
    sentences = split_into_sentences(content)
    life_phases = identify_ho_chi_minh_life_phases(sentences)
    
    all_relationships = []
    
    for phase_name, phase_sentences in life_phases.items():
        if not phase_sentences:
            continue
            
        print(f"\nGiai đoạn: {topic_config['life_phases'].get(phase_name, phase_name)} ({len(phase_sentences)} câu)")
        
        windows = create_overlapping_windows(
            phase_sentences,
            window_size=topic_config['window_size'],
            step=topic_config['step_size']
        )
        
        for window_idx, (start_idx, window_sentences) in enumerate(windows[:10]):
            print(f"  Window {window_idx+1}/{min(4, len(windows))}: ", end="", flush=True)
            
            phase_filtered_entities = filter_entities_for_ho_chi_minh_phase(
                filtered_entity_lookup, phase_name, window_sentences
            )
            
            if len(phase_filtered_entities) < 2:
                print("Ít thực thể -> Bỏ qua")
                continue
            
            existing_entities_str = format_ho_chi_minh_entities_for_prompt(phase_filtered_entities, phase_name)
            window_text = " ".join(window_sentences)
            
            key_entities_in_window = []
            for entity_id, entity in phase_filtered_entities.items():
                if entity_id == entity['id']:
                    window_text_lower = window_text.lower()
                    entity_labels = entity.get('context_labels', [])
                    
                    for label in entity_labels:
                        if label.lower() in window_text_lower and len(label) > 3:
                            if entity.get('ho_chi_minh_priority', 0) >= 3:
                                key_entities_in_window.append(entity_id)
                            break
            
            if not key_entities_in_window:
                print("Không có thực thể quan trọng -> Bỏ qua")
                continue
            
            primary_entity = key_entities_in_window[0]
            
            prompt = TopicProcessor.create_topic_prompt(
                    "Chủ đề 6", 
                    window_text, 
                    existing_entities_str,
                    target_entity_id=primary_entity
                )
            
            result = extract_ho_chi_minh_relationships(
                prompt,
                start_idx,
                window_sentences,
                phase_filtered_entities,
                file_info,
                primary_entity,
                phase_name
            )
            
            if result:
                relationships = result.get('relationships', [])
                if relationships:
                    all_relationships.extend(relationships)
                    print(f"{len(relationships)}R ", end="", flush=True)
            
            print("")
            time.sleep(2)
    
    processed_relationships = post_process_ho_chi_minh_relationships(all_relationships)
    
    triplets = []
    for rel in processed_relationships:
        triplet = {
            'subject_id': rel['subject_id'],
            'predicate': rel['predicate'],
            'object_id': rel['object_id'],
            'properties': {
                'historical_context': rel.get('historical_context', ''),
                'time_reference': rel.get('time_reference', ''),
                'location_reference': rel.get('location_reference', ''),
                'life_phase': rel.get('life_phase', ''),
                'relationship_type': rel.get('relationship_type', '')
            },
            'metadata': {
                'extraction_method': 'ho_chi_minh_specialized',
                'file_info': file_info,
                'evidence_count': len(rel.get('supporting_sentences', [])),
                'life_phase': rel.get('life_phase', 'unknown'),
                'priority_score': rel.get('priority_score', 1),
                'has_time_reference': 'time_reference' in rel
            },
            'supporting_sentences': rel.get('supporting_sentences', []),
            'confidence': rel.get('confidence', 0.9),
            'occurrence_count': rel.get('occurrence_count', 1)
        }
        triplets.append(triplet)
    
    existing_triplets = existing_kg.get('triplets', [])
    existing_entities = existing_kg.get('entities', [])
    
    triplet_keys = set((t['subject_id'], t['predicate'], t['object_id']) for t in existing_triplets)
    for triplet in triplets:
        key = (triplet['subject_id'], triplet['predicate'], triplet['object_id'])
        if key not in triplet_keys:
            existing_triplets.append(triplet)
            triplet_keys.add(key)
    
    print(f"\nĐã thêm {len(triplets)} quan hệ về Hồ Chí Minh từ file này")
    return {
        'entities': existing_entities,
        'triplets': existing_triplets
    }

def identify_ho_chi_minh_life_phases(sentences: List[str]) -> Dict[str, List[str]]:
    """Nhận diện các giai đoạn cuộc đời Hồ Chí Minh trong văn bản."""
    phases = {
        '1890_1911': [],
        '1911_1920': [],
        '1920_1930': [],
        '1930_1941': [],
        '1941_1945': [],
        '1945_1954': [],
        '1954_1969': [],
        '1969_nay': [],
        'khac': []
    }
    
    phase_keywords = {
        '1890_1911': [
            'thời niên thiếu', 'nguyễn sinh cung', 'nguyễn tất thành',
            'làng sen', 'kim liên', 'nghệ an', 'huế', 'trường quốc học',
            'phong trào chống thuế', 'duc thanh', 'phan thiết',
            '1890', '1905', '1906', '1908', '1910', 'trước 1911'
        ],
        '1911_1920': [
            'hành trình tìm đường cứu nước', '5-6-1911', 'bến nhà rồng',
            'la-tu-sơ tơ-rê-vin', 'yêu sách của nhân dân an nam',
            'hội nghị véc-xai', 'sơ thảo luận cương', 'lê-nin',
            'đảng cộng sản pháp', 'trở thành người cộng sản',
            '1920', '1911-1920', 'tìm đường cứu nước'
        ],
        '1920_1930': [
            'hội liên hiệp thuộc địa', 'báo người cùng khổ', 'le paria',
            'hội việt nam cách mạng thanh niên', 'quảng châu',
            'báo thanh niên', 'hội nghị thành lập đảng',
            'đảng cộng sản việt nam', 'cương lĩnh chính trị',
            '6-1-1930', '1925', '1921-1930', 'chuẩn bị thành lập đảng'
        ],
        '1930_1941': [
            'hoạt động ở nước ngoài', 'liên xô', 'trung quốc',
            'xiêm', 'thái lan', '1933', '1938', '1930-1941',
            'trước khi về nước'
        ],
        '1941_1945': [
            'trực tiếp lãnh đạo cách mạng', 'về nước 1941',
            'pác bó', 'cao bằng', 'hội nghị trung ương 8',
            'mặt trận việt minh', 'đội việt nam tuyên truyền',
            'tân trào', 'đại hội quốc dân', 'cách mạng tháng tám',
            'tuyên ngôn độc lập', '2-9-1945', '1941-1945',
            'lãnh đạo tổng khởi nghĩa'
        ],
        '1945_1954': [
            'lãnh đạo kháng chiến chống pháp', 'hiệp định sơ bộ',
            'tạm ước việt-pháp', 'lời kêu gọi toàn quốc kháng chiến',
            '19-12-1946', 'chiến dịch điện biên phủ',
            'đảng lao động việt nam', '1951', '1954',
            '1945-1954', 'kháng chiến chống pháp'
        ],
        '1954_1969': [
            'lãnh đạo kháng chiến chống mỹ', 'xây dựng chủ nghĩa xã hội',
            'hội nghị trung ương 15', '1959', '1960', '1965',
            'chống mỹ cứu nước', 'qua đời 1969', '2-9-1969',
            '1954-1969', 'lãnh đạo hai miền'
        ],
        '1969_nay': [
            'di sản', 'tư tưởng hồ chí minh', 'đạo đức hồ chí minh',
            'tấm gương đạo đức', 'học tập và làm theo',
            'thành phố hồ chí minh', 'unesco', '1987',
            'bảo tàng hồ chí minh', 'lăng chủ tịch',
            'sau 1969', 'di sản để lại'
        ]
    }
    
    current_phase = 'khac'
    phase_sentences = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        detected_phase = None
        max_matches = 0
        
        for phase_name, keywords in phase_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in sentence_lower)
            if matches > max_matches:
                max_matches = matches
                detected_phase = phase_name
        
        if detected_phase and max_matches > 0:
            if phase_sentences:
                phases[current_phase].extend(phase_sentences)
            
            current_phase = detected_phase
            phase_sentences = [sentence]
        else:
            phase_sentences.append(sentence)
    
    if phase_sentences:
        phases[current_phase].extend(phase_sentences)
    
    return {k: v for k, v in phases.items() if v}

def filter_entities_for_ho_chi_minh_phase(entity_lookup: Dict[str, Dict], phase: str, 
                                          window_sentences: List[str]) -> Dict[str, Dict]:
    """Lọc entities phù hợp với giai đoạn cuộc đời Hồ Chí Minh cụ thể."""
    filtered = {}
    window_text = " ".join(window_sentences).lower()
    
    for entity_id, entity in entity_lookup.items():
        if entity_id != entity['id']:
            continue
            
        entity_labels = entity.get('context_labels', [])
        
        in_window = False
        for label in entity_labels:
            if label.lower() in window_text and len(label) > 3:
                in_window = True
                break
        
        if not in_window:
            continue
        
        relevance_score = 0
        
        if phase == '1890_1911':
            early_terms = ["Nguyễn Sinh Cung", "Nguyễn Tất Thành", "Làng Sen", 
                          "Kim Liên", "Huế", "Trường Quốc học", "Dục Thanh"]
            if any(term in str(label) for label in entity_labels for term in early_terms):
                relevance_score += 2
        
        elif phase == '1911_1920':
            finding_way_terms = ["Bến Nhà Rồng", "Yêu sách", "Véc-xai", 
                                "Lê-nin", "Đảng Cộng sản Pháp", "1911"]
            if any(term in str(label) for label in entity_labels for term in finding_way_terms):
                relevance_score += 2
        
        elif phase == '1920_1930':
            party_founding_terms = ["Hội Việt Nam Cách mạng Thanh niên", "Báo Thanh niên",
                                   "Đảng Cộng sản Việt Nam", "Cương lĩnh", "1930"]
            if any(term in str(label) for label in entity_labels for term in party_founding_terms):
                relevance_score += 2
        
        elif phase == '1941_1945':
            revolution_terms = ["Pác Bó", "Việt Minh", "Tân Trào", "Tuyên ngôn Độc lập",
                               "2-9-1945", "Cách mạng tháng Tám"]
            if any(term in str(label) for label in entity_labels for term in revolution_terms):
                relevance_score += 2
        
        elif phase == '1945_1954':
            anti_french_terms = ["Hiệp định Sơ bộ", "Toàn quốc kháng chiến", 
                                "Điện Biên Phủ", "Đảng Lao động Việt Nam"]
            if any(term in str(label) for label in entity_labels for term in anti_french_terms):
                relevance_score += 2
        
        elif phase == '1954_1969':
            anti_us_terms = ["Chống Mỹ cứu nước", "Hội nghị Trung ương 15",
                            "Xây dựng chủ nghĩa xã hội", "1969"]
            if any(term in str(label) for label in entity_labels for term in anti_us_terms):
                relevance_score += 2
        
        elif phase == '1969_nay':
            legacy_terms = ["Di sản", "Tư tưởng Hồ Chí Minh", "Thành phố Hồ Chí Minh",
                           "UNESCO", "Bảo tàng Hồ Chí Minh"]
            if any(term in str(label) for label in entity_labels for term in legacy_terms):
                relevance_score += 2
        
        if relevance_score > 0 or in_window:
            entity['phase_relevance'] = relevance_score
            filtered[entity_id] = entity
    
    return filtered

def format_ho_chi_minh_entities_for_prompt(entity_lookup: Dict[str, Dict], phase: str) -> str:
    """Định dạng entities cho prompt với thông tin Hồ Chí Minh."""
    entity_lines = []
    topic_config = TopicProcessor.TOPIC_CONFIGS["Chủ đề 4"]
    
    for entity_id, entity in entity_lookup.items():
        if entity_id == entity['id']:
            entity_type = entity.get('type', 'Unknown')
            labels = entity.get('context_labels', [])
            relevance = entity.get('phase_relevance', 0)
            
            if relevance > 0 or entity_type in TopicProcessor.TOPIC_CONFIGS["Chủ đề 6"]['focus_entities']:
                line = f"- {entity_id}"
                if labels:
                    line += f" [Tên: {', '.join(labels[:2])}]"
                line += f" (Loại: {entity_type})"
                
                if any(name in entity_id for name in ["Hồ Chí Minh", "Nguyễn Ái Quốc", "Nguyễn Tất Thành"]):
                    line += " [NHÂN VẬT CHÍNH: Hồ Chí Minh]"
                    other_names = []
                    for name in ["Nguyễn Sinh Cung", "Văn Ba", "Nguyễn Ái Quốc", "Nguyễn Tất Thành"]:
                        if name in str(labels) and name not in entity_id:
                            other_names.append(name)
                    if other_names:
                        line += f" (Còn gọi: {', '.join(other_names)})"
                elif "Đảng Cộng sản Việt Nam" in entity_id:
                    line += " [Tổ chức do Hồ Chí Minh sáng lập]"
                elif "Mặt trận Việt Minh" in entity_id:
                    line += " [Tổ chức do Hồ Chí Minh tham gia thành lập]"
                elif "Tuyên ngôn Độc lập" in entity_id:
                    line += " [Văn kiện do Hồ Chí Minh soạn thảo và đọc]"
                elif entity_type == "Địa điểm Lịch sử" and any(loc in str(labels) for loc in ["Làng Sen", "Pác Bó", "Tân Trào", "Bến Nhà Rồng"]):
                    line += " [Địa điểm quan trọng trong cuộc đời Hồ Chí Minh]"
                
                entity_lines.append((relevance, line))
    
    entity_lines.sort(key=lambda x: x[0], reverse=True)
    
    return "\n".join([line[1] for line in entity_lines[:35]])

def extract_ho_chi_minh_relationships(prompt: str, start_idx: int, window_sentences: List[str],
                                     entity_lookup: Dict[str, Dict], file_info: Dict[str, str],
                                     target_entity_id: str, life_phase: str) -> Optional[Dict]:
    """Trích xuất quan hệ Hồ Chí Minh với validation đặc thù."""
    global API_REQUEST_COUNT
    
    for attempt in range(3):
        try:
            time.sleep(2)
            
            api_key, key_idx = get_next_api_key()
            if not api_key:
                print("Không có API key")
                return None
                
            # DeepSeek API - configured in api_handler
            # model handled by call_deepseek_api
            
            API_REQUEST_COUNT += 1
            print(f"[HoChiMinh-API #{API_REQUEST_COUNT}]", end=" ")
            
            result = call_deepseek_api(prompt)
            response_text = response.text
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                try:
                    relationships_data = json.loads(json_match.group())
                    validated_relationships = []
                    
                    for rel in relationships_data.get('relationships', []):
                        if validate_ho_chi_minh_relationship(rel, entity_lookup, life_phase):
                            priority_score = calculate_ho_chi_minh_priority(rel, life_phase)
                            
                            rel['window_info'] = {
                                'start_idx': start_idx,
                                'sentences': window_sentences[:3],
                                'file_info': file_info,
                                'life_phase': life_phase,
                                'target_entity': target_entity_id
                            }
                            
                            rel['life_phase'] = life_phase
                            rel['priority_score'] = priority_score
                            
                            evidence_quality = assess_ho_chi_minh_evidence_quality(rel.get('evidence', ''), life_phase)
                            base_confidence = rel.get('confidence', 0.8)
                            rel['confidence'] = min(0.97, base_confidence * evidence_quality + (priority_score * 0.05))
                            
                            if 'time_reference' not in rel:
                                time_match = re.search(r'\d{4}', rel.get('evidence', ''))
                                if time_match:
                                    rel['time_reference'] = time_match.group()
                                else:
                                    date_match = re.search(r'\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}', rel.get('evidence', ''))
                                    if date_match:
                                        rel['time_reference'] = date_match.group()
                            
                            evidence_text = rel.get('evidence', '')
                            location_indicators = ['tại', 'ở', 'từ', 'đến', 'về', 'sang', 'trong', 'trên']
                            for indicator in location_indicators:
                                if indicator in evidence_text.lower():
                                    words = evidence_text.split()
                                    for i, word in enumerate(words):
                                        if word.lower() == indicator and i + 1 < len(words):
                                            location = words[i + 1]
                                            if len(location) > 2 and not location[0].isdigit():
                                                if any(loc_term in location.lower() for loc_term in ['hà', 'huế', 'sài', 'nghệ', 'cao', 'tuyên']):
                                                    rel['location_reference'] = location
                                                    break
                                    break
                            
                            rel = classify_ho_chi_minh_relationship(rel)
                            
                            validated_relationships.append(rel)
                    
                    return {
                        'relationships': validated_relationships,
                        'window_index': start_idx,
                        'target_entity': target_entity_id,
                        'life_phase': life_phase
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"Lỗi JSON: {e}")
                    debug_file = f"ho_chi_minh_error_phase_{life_phase}_{start_idx}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"Prompt: {prompt[:2000]}...\n\nResponse: {response_text}\n\nError: {e}")
                    try:
                        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
                        all_json = re.findall(json_pattern, response_text)
                        if all_json:
                            # Lấy JSON object đầu tiên
                            relationships_data = json.loads(all_json[0])
                            # ... xử lý tiếp ...
                    except:
                        pass
                    
                    if attempt < 2:
                        time.sleep(3)
            
        except Exception as e:
            print(f"Lỗi (lần {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(3)
    
    return None

def validate_ho_chi_minh_relationship(relationship: Dict, entity_lookup: Dict[str, Dict], 
                                      life_phase: str) -> bool:
    """Validate quan hệ Hồ Chí Minh với tiêu chí chặt chẽ."""
    subject_id = relationship.get('subject_id', '').strip()
    object_id = relationship.get('object_id', '').strip()
    predicate = relationship.get('predicate', '').strip()
    evidence = relationship.get('evidence', '').strip()
    
    if not subject_id or not object_id or not predicate:
        return False
    
    subject_exists = subject_id in entity_lookup
    object_exists = object_id in entity_lookup
    
    if not subject_exists or not object_exists:
        subject_found = any(subject_id in entity.get('context_labels', []) 
                          for entity in entity_lookup.values())
        object_found = any(object_id in entity.get('context_labels', []) 
                         for entity in entity_lookup.values())
        
        if not subject_found or not object_found:
            return False
    
    valid_ho_chi_minh_predicates = [
        'sinh_ra_tại', 'lớn_lên_tại', 'học_tập_tại', 'tham_gia', 
        'thành_lập', 'sáng_lập', 'chủ_trì', 'lãnh_đạo', 'chỉ_đạo',
        'soạn_thảo', 'viết', 'đọc', 'tuyên_bố', 'kêu_gọi', 'vận_động',
        'tìm_đường_cứu_nước', 'đến_với_chủ_nghĩa', 'trở_thành',
        'được_bầu_làm', 'được_cử_làm', 'trực_tiếp_lãnh_đạo',
        'huấn_luyện', 'đào_tạo', 'truyền_bá', 'tố_cáo', 'phê_phán',
        'đấu_tranh', 'khởi_xướng', 'triệu_tập', 'ra_đi', 'trở_về',
        'qua_đời_tại', 'cống_hiến_trọn_đời'
    ]
    
    if predicate not in valid_ho_chi_minh_predicates and not any(p in predicate for p in ['_']):
        if len(predicate) < 3 or len(predicate) > 60:
            return False
    
    if len(evidence) < 20:
        return False
    
    if not re.search(r'\d{4}', evidence) and life_phase not in ['khac', '1969_nay']:
        if life_phase not in ['khac', '1969_nay']:
            important_predicates = ['sinh_ra_tại', 'thành_lập', 'sáng_lập', 'đọc', 'tuyên_bố']
            if predicate in important_predicates:
                return False
    
    evidence_lower = evidence.lower()
    subject_found_in_evidence = False
    object_found_in_evidence = False
    
    if subject_id in entity_lookup:
        subject_entity = entity_lookup[subject_id]
        for label in subject_entity.get('context_labels', []):
            if label.lower() in evidence_lower:
                subject_found_in_evidence = True
                break
    
    if object_id in entity_lookup:
        object_entity = entity_lookup[object_id]
        for label in object_entity.get('context_labels', []):
            if label.lower() in evidence_lower:
                object_found_in_evidence = True
                break
    
    if not subject_found_in_evidence and not object_found_in_evidence:
        return False
    
    return True

def calculate_ho_chi_minh_priority(relationship: Dict, life_phase: str) -> int:
    """Tính điểm ưu tiên cho quan hệ Hồ Chí Minh."""
    priority = 1
    
    subject = relationship.get('subject_id', '')
    predicate = relationship.get('predicate', '')
    object_ = relationship.get('object_id', '')
    evidence = relationship.get('evidence', '')
    
    if any(name in subject for name in ["Hồ Chí Minh", "Nguyễn Ái Quốc", "Nguyễn Tất Thành"]):
        priority += 2
    
    if predicate == 'sinh_ra_tại' and "Làng Sen" in object_:
        priority += 3
    
    if predicate == 'thành_lập' and "Đảng Cộng sản Việt Nam" in object_:
        priority += 3
    
    if predicate == 'đọc' and "Tuyên ngôn Độc lập" in object_:
        priority += 3
    
    if re.search(r'\d{4}', evidence):
        priority += 1
    
    location_indicators = ['tại', 'ở', 'từ', 'đến']
    if any(indicator in evidence for indicator in location_indicators):
        priority += 1
    
    if life_phase != 'khac':
        priority += 1
    
    if predicate in ['để_lại_di_sản', 'trở_thành_tấm_gương', 'được_tôn_vinh']:
        priority += 1
    
    return priority

def assess_ho_chi_minh_evidence_quality(evidence: str, life_phase: str) -> float:
    """Đánh giá chất lượng evidence cho quan hệ Hồ Chí Minh."""
    quality = 0.7
    
    if len(evidence) > 30:
        quality += 0.1
    if len(evidence) > 50:
        quality += 0.1
    
    year_match = re.search(r'\d{4}', evidence)
    if year_match:
        quality += 0.2
        year = int(year_match.group())
        
        if life_phase == '1890_1911' and 1890 <= year <= 1911:
            quality += 0.1
        elif life_phase == '1911_1920' and 1911 <= year <= 1920:
            quality += 0.1
        elif life_phase == '1920_1930' and 1920 <= year <= 1930:
            quality += 0.1
        elif life_phase == '1941_1945' and 1941 <= year <= 1945:
            quality += 0.1
        elif life_phase == '1945_1954' and 1945 <= year <= 1954:
            quality += 0.1
    
    if re.search(r'\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{4}', evidence):
        quality += 0.2
    
    location_indicators = ['tại', 'ở', 'từ', 'đến', 'sang', 'về']
    if any(indicator in evidence for indicator in location_indicators):
        quality += 0.1
    
    if any(name in evidence for name in ["Hồ Chí Minh", "Nguyễn Ái Quốc", "Nguyễn Tất Thành", "Bác Hồ"]):
        quality += 0.1
    
    if any(term in evidence.lower() for term in ['thành lập', 'sáng lập', 'lãnh đạo', 'chủ trì']):
        quality += 0.1
    
    org_terms = ['đảng cộng sản', 'việt minh', 'mặt trận', 'hội việt nam']
    if any(term in evidence.lower() for term in org_terms):
        quality += 0.1
    
    return min(1.0, quality)

def classify_ho_chi_minh_relationship(relationship: Dict) -> Dict:
    """Phân loại quan hệ Hồ Chí Minh."""
    predicate = relationship.get('predicate', '')
    
    relationship_types = {
        'birth_childhood': ['sinh_ra_tại', 'lớn_lên_tại', 'học_tập_tại'],
        'journey': ['tìm_đường_cứu_nước', 'đến_với_chủ_nghĩa', 'ra_đi', 'trở_về'],
        'organization': ['thành_lập', 'sáng_lập', 'tham_gia_thành_lập'],
        'leadership': ['lãnh_đạo', 'chỉ_đạo', 'trực_tiếp_lãnh_đạo', 'chủ_trì'],
        'creation': ['soạn_thảo', 'viết', 'sáng_tác'],
        'declaration': ['đọc', 'tuyên_bố', 'kêu_gọi'],
        'recognition': ['được_bầu_làm', 'được_cử_làm', 'trở_thành'],
        'legacy': ['để_lại_di_sản', 'trở_thành_tấm_gương', 'được_tôn_vinh', 'qua_đời_tại']
    }
    
    for rel_type, predicates in relationship_types.items():
        if predicate in predicates:
            relationship['relationship_type'] = rel_type
            return relationship
    
    return relationship

def post_process_ho_chi_minh_relationships(relationships: List[Dict]) -> List[Dict]:
    """Hậu xử lý quan hệ Hồ Chí Minh."""
    groups = defaultdict(list)
    
    for rel in relationships:
        key = (rel['subject_id'], rel['predicate'], rel['object_id'])
        groups[key].append(rel)
    
    merged = []
    
    for key, rel_list in groups.items():
        if not rel_list:
            continue
        
        base = rel_list[0].copy()
        base['occurrence_count'] = len(rel_list)
        
        all_evidence = []
        for rel in rel_list:
            evidence = {
                'text': rel.get('evidence', ''),
                'life_phase': rel.get('life_phase', 'unknown'),
                'time_reference': rel.get('time_reference', ''),
                'location_reference': rel.get('location_reference', ''),
                'window_info': rel.get('window_info', {}),
                'timestamp': time.time()
            }
            
            if not any(e['text'] == evidence['text'] for e in all_evidence):
                all_evidence.append(evidence)
        
        base['supporting_sentences'] = all_evidence
        
        total_conf = 0
        total_weight = 0
        
        for rel in rel_list:
            conf = rel.get('confidence', 0.8)
            priority = rel.get('priority_score', 1)
            weight = priority
            
            total_conf += conf * weight
            total_weight += weight
        
        if total_weight > 0:
            base['confidence'] = min(0.98, total_conf / total_weight)
        
        if 'historical_context' not in base:
            rel_type_desc = ""
            if 'relationship_type' in base:
                type_map = {
                    'birth_childhood': 'Thời niên thiếu',
                    'journey': 'Hành trình tìm đường cứu nước',
                    'organization': 'Thành lập tổ chức',
                    'leadership': 'Lãnh đạo cách mạng',
                    'creation': 'Sáng tác, soạn thảo',
                    'declaration': 'Tuyên bố, kêu gọi',
                    'recognition': 'Được bầu, công nhận',
                    'legacy': 'Di sản, ảnh hưởng'
                }
                rel_type_desc = f" - Loại: {type_map.get(base['relationship_type'], '')}"
            
            base['historical_context'] = f"Giai đoạn: {base.get('life_phase', 'unknown')}{rel_type_desc}"
        
        merged.append(base)
    
    merged.sort(key=lambda x: (
        x.get('priority_score', 0),
        x.get('confidence', 0)
    ), reverse=True)
    
    return merged

def safe_extract_relationships(prompt_func, prompt: str, start_idx: int, window_sentences: List[str],
                              entity_lookup: Dict[str, Dict], file_info: Dict[str, str],
                              target_entity_id: str, context_param: str, context_value: str) -> Optional[Dict]:
    """Wrapper an toàn để xử lý lỗi khi gọi API."""
    global API_REQUEST_COUNT
    
    for attempt in range(3):
        try:
            time.sleep(2 + attempt)  # Tăng thời gian chờ sau mỗi lần thử
            
            api_key, key_idx = get_next_api_key()
            if not api_key:
                print(f"  Không có API key (lần {attempt+1})")
                continue
                
            # DeepSeek API - configured in api_handler
            # model handled by call_deepseek_api
            
            API_REQUEST_COUNT += 1
            print(f"[API #{API_REQUEST_COUNT}]", end=" ")
            
            # GIỚI HẠN ĐỘ DÀI PROMPT (quan trọng!)
            if len(prompt) > 10000:
                print(f"Prompt quá dài ({len(prompt)} chars), cắt bớt...")
                prompt = prompt[:10000] + "\n...[ĐÃ CẮT BỚT VÌ QUÁ DÀI]..."
            
            result = call_deepseek_api(prompt)
            
            # KIỂM TRA KỸ response
            if not response:
                print(f"Response None (lần {attempt+1})")
                continue
                
            if not hasattr(response, 'text'):
                print(f"Response không có thuộc tính text (lần {attempt+1})")
                continue
                
            response_text = response.text
            
            if not response_text:
                print(f"Response text rỗng (lần {attempt+1})")
                continue
                
            if len(response_text) < 20:
                print(f"Response quá ngắn: '{response_text}' (lần {attempt+1})")
                continue
            
            # Tìm JSON
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            
            if not json_match:
                # Thử tìm pattern khác
                json_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', response_text)
            
            if json_match:
                try:
                    json_str = json_match.group()
                    
                    # Làm sạch JSON string
                    json_str = clean_json_string(json_str)
                    
                    # Parse JSON
                    data = json.loads(json_str)
                    
                    # Gọi hàm xử lý cụ thể
                    return prompt_func(data, start_idx, window_sentences, entity_lookup, 
                                     file_info, target_entity_id, context_value)
                    
                except json.JSONDecodeError as e:
                    print(f"Lỗi JSON decode: {e}")
                    
                    # Debug: lưu response để phân tích
                    with open(f"api_error_{API_REQUEST_COUNT}.txt", 'w', encoding='utf-8') as f:
                        f.write(f"Prompt (first 2000 chars):\n{prompt[:2000]}\n\n")
                        f.write(f"Response:\n{response_text}\n\n")
                        f.write(f"Error: {e}\n")
                    
                    if attempt < 2:
                        time.sleep(3)
                    continue
            else:
                print(f"Không tìm thấy JSON trong response (lần {attempt+1})")
                if attempt < 2:
                    time.sleep(3)
                continue
                
        except Exception as e:
            print(f"Lỗi tổng quát (lần {attempt+1}): {str(e)[:100]}")
            if attempt < 2:
                time.sleep(3)
    
    return None

def clean_json_string(json_str: str) -> str:
    """Làm sạch string JSON trước khi parse."""
    if not json_str:
        return "{}"
    
    # Loại bỏ các ký tự không hợp lệ
    json_str = json_str.replace('\x00', '').replace('\ufffd', '')
    
    # Loại bỏ các ký tự điều khiển
    json_str = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', json_str)
    
    # Loại bỏ markdown code block nếu có
    json_str = re.sub(r'```json\s*', '', json_str)
    json_str = re.sub(r'```\s*$', '', json_str)
    
    # Đảm bảo chỉ có một JSON object
    if json_str.count('{') > 1:
        # Tìm object ngoài cùng
        start = json_str.find('{')
        end = json_str.rfind('}')
        if end > start:
            json_str = json_str[start:end+1]
    
    return json_str