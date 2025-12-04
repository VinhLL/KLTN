"""Xử lý đặc thù theo từng chủ đề."""
import utils

import json
import re
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai

class TopicProcessor:
    """Xử lý đặc thù theo từng chủ đề."""
    
    @staticmethod
    def get_topic_config(topic_name: str) -> Dict[str, Any]:
        """Cấu hình riêng cho từng chủ đề."""
        configs = {
            "CHỦ ĐỀ 1: THẾ GIỚI TRONG VÀ SAU CHIẾN TRANH LẠNH": {
                "priority_entities": [
                    "Tổ chức", "Hội nghị", "Văn kiện/Hiệp định", 
                    "Quốc gia", "Nhân Vật", "Sự kiện", "Chiến dịch/Trận đánh"
                ],
                "entity_blacklist": [
                    "phát triển kinh tế", "hợp tác quốc tế", "giải trừ quân bị",
                    "chạy đua vũ trang", "xoá đói giảm nghèo", "an ninh quốc tế",
                    "phát triển bền vững", "bình đẳng giới", "thương mại quốc tế",
                    "hội nhập quốc tế", "toàn cầu hoá", "đối thoại hợp tác",
                    "quan hệ quốc tế", "trật tự thế giới", "xu thế phát triển",
                    "chính phủ", "hội", "trí tuệ con người", "nhân dân thế giới",
                    "nhân dân", "thế giới", "phe", "quân", "đế quốc", "phong kiến"
                ],
                "required_keywords": [
                    "Liên hợp quốc", "Hội nghị", "Hiệp định", "Hiến chương",
                    "Chiến tranh lạnh", "I-an-ta", "Tê-hê-ran", "Xô-Mỹ"
                ],
                "time_period": "1945-1991",
                "specific_rules": """
                1. ƯU TIÊN các tổ chức quốc tế: LHQ, NATO, WTO, ASEAN, EU
                2. ƯU TIÊN các hội nghị: I-an-ta, Tê-hê-ran, Xan Phran-xi-xcô
                3. ƯU TIÊN các hiệp định: Hiến chương LHQ, Hiệp ước cấm vũ khí hạt nhân
                4. ƯU TIÊN các nhân vật lãnh đạo: Hồ Chí Minh, Stalin, Roosevelt, Churchill
                5. Ghi nhận đầy đủ NGÀY THÁNG NĂM cho sự kiện
                6. Phân biệt rõ các giai đoạn: 1945-1970, 1970-1991, sau 1991
                """,
                "acronyms": {
                    "LHQ": "Liên hợp quốc",
                    "NATO": "Tổ chức Hiệp ước Bắc Đại Tây Dương",
                    "UN": "United Nations",
                    "WTO": "Tổ chức Thương mại Thế giới"
                }
            },
            
            "CHỦ ĐỀ 2: ASEAN: NHỮNG CHẶNG ĐƯỜNG LỊCH SỬ": {
                "priority_entities": [
                    "Tổ chức", "Hội nghị", "Văn kiện/Hiệp định", 
                    "Quốc gia", "Sự kiện", "Địa điểm", "Chiến lược/Chủ trương"
                ],
                "entity_blacklist": [
                    "phát triển kinh tế", "hợp tác quốc tế", "tăng trưởng kinh tế",
                    "tiến bộ xã hội", "phát triển văn hoá", "hoà bình và ổn định",
                    "hợp tác khu vực", "mở rộng quan hệ", "nâng cao uy tín",
                    "xây dựng cộng đồng", "thách thức và triển vọng", "hội nhập quốc tế",
                    "trí tuệ con người", "nhân dân thế giới",
                    "nhân dân", "thế giới", "phe", "quân", "đế quốc", "phong kiến"
                ],
                "required_keywords": [
                    "ASEAN", "Hiệp hội", "Đông Nam Á", "Tuyên bố", "Hiến chương",
                    "Cộng đồng", "trụ cột", "APSC", "AEC", "ASCC", "AFTA", "ARF"
                ],
                "time_period": "1967-nay",
                "specific_rules": """
                1. ƯU TIÊN các tổ chức ASEAN: ASEAN, APSC, AEC, ASCC, ARF, AFTA
                2. ƯU TIÊN các văn kiện ASEAN: Tuyên bố Băng Cốc, Hiến chương ASEAN, TAC
                3. ƯU TIÊN các hội nghị ASEAN: Hội nghị cấp cao ASEAN
                4. ƯU TIÊN các nước thành viên ASEAN: Việt Nam, Thái Lan, Indonesia,...
                5. Ghi nhận đầy đủ các giai đoạn: 1967-1976, 1976-1999, 1999-2015, 2015-nay
                6. Xử lý đúng các từ viết tắt: ASEAN, APSC, AEC, ASCC, ZOPFAN, TAC, ARF, AFTA
                """,
                "acronyms": {
                    "ASEAN": "Hiệp hội các quốc gia Đông Nam Á",
                    "APSC": "Cộng đồng Chính trị – An ninh ASEAN",
                    "AEC": "Cộng đồng Kinh tế ASEAN",
                    "ASCC": "Cộng đồng Văn hoá – Xã hội ASEAN",
                    "ZOPFAN": "Khu vực Hoà bình, Tự do và Trung lập",
                    "TAC": "Hiệp ước Thân thiện và Hợp tác ở Đông Nam Á",
                    "ARF": "Diễn đàn khu vực ASEAN",
                    "AFTA": "Khu vực Mậu dịch Tự do ASEAN",
                    "MAPHILINDO": "Liên minh Mã Lai-Philippines-Indonesia"
                },
                "member_countries": [
                    "Việt Nam", "Lào", "Campuchia", "Thái Lan", "Myanmar",
                    "Malaysia", "Singapore", "Indonesia", "Philippines", "Brunei",
                    "In-đô-nê-xi-a", "Ma-lai-xi-a", "Phi-líp-pin", "Xin-ga-po", "Thái Lan"
                ]
            },
            
            "CHỦ ĐỀ 3: CÁCH MẠNG THÁNG TÁM NĂM 1945,CHIẾN TRANH GIẢI PHÓNG DÂN TỘC VÀ CHIẾN TRANH BẢO VỆ TỔ QUỐC TRONG LỊCH SỬ VIỆT NAM (TỪ THÁNG 8 NĂM 1945 ĐẾN NAY)": {
                "priority_entities": [
                    "Nhân Vật", "Chiến dịch/Trận đánh", "Sự kiện",
                    "Tổ chức", "Văn kiện/Hiệp định", "Địa điểm",
                    "Chiến lược/Chủ trương", "Quốc gia"
                ],
                "entity_blacklist": [
                    "phát triển kinh tế", "xây dựng đất nước", "hoà bình và ổn định",
                    "đoàn kết dân tộc", "bài học kinh nghiệm", "nguyên nhân thắng lợi",
                    "ý nghĩa lịch sử", "nghệ thuật quân sự", "quốc phòng toàn dân",
                    "bảo vệ tổ quốc", "giải phóng dân tộc", "xây dựng chủ nghĩa xã hội",
                    "khôi phục kinh tế", "phát triển văn hoá", "củng cố chính quyền",
                    "tăng cường lực lượng", "mở rộng quan hệ", "nâng cao đời sống",
                    "chính phủ", "hội", "trí tuệ con người", "nhân dân thế giới",
                    "thế giới", "phe", "quân", "đế quốc", "phong kiến"
                ],
                "required_keywords": [
                    "Cách mạng tháng Tám", "Hồ Chí Minh", "Điện Biên Phủ",
                    "Hiệp định Giơ-ne-vơ", "Hiệp định Pa-ri", "Tuyên ngôn Độc lập",
                    "Việt Minh", "Mặt trận", "Quân Giải phóng", "Võ Nguyên Giáp",
                    "Chiến tranh chống Mỹ", "Chiến tranh chống Pháp", "Pôn Pốt",
                    "Biên giới Tây Nam", "Biên giới phía Bắc", "Biển Đông",
                    "Hoàng Sa", "Trường Sa", "Ngô Đình Diệm"
                ],
                "time_period": "1945-nay",
                "specific_rules": """
                1. ƯU TIÊN các nhân vật lãnh đạo: Hồ Chí Minh, Võ Nguyên Giáp, Ngô Đình Diệm, Pôn Pốt
                2. ƯU TIÊN các chiến dịch quân sự: Điện Biên Phủ, Tây Nguyên, Huế - Đà Nẵng, Hồ Chí Minh
                3. ƯU TIÊN các sự kiện chính trị: Cách mạng tháng Tám, Đồng khởi, Tổng tiến công Tết Mậu Thân
                4. ƯU TIÊN các tổ chức cách mạng: Việt Minh, Mặt trận Dân tộc Giải phóng, Đảng Cộng sản
                5. ƯU TIÊN các hiệp định quốc tế: Giơ-ne-vơ, Pa-ri
                6. Ghi nhận đầy đủ NGÀY THÁNG cho các sự kiện quân sự
                7. Phân biệt rõ các giai đoạn: 1945-1954, 1954-1975, 1975-nay
                8. Xử lý đúng tên các chiến lược quân sự: "Chiến tranh đặc biệt", "Việt Nam hoá chiến tranh"
                """,
                "acronyms": {
                    "VNCH": "Việt Nam Cộng hòa",
                    "MTDTGP": "Mặt trận Dân tộc Giải phóng miền Nam Việt Nam",
                    "QGP": "Quân Giải phóng miền Nam",
                    "VNDCCH": "Việt Nam Dân chủ Cộng hòa",
                    "CHXHCNVN": "Cộng hòa Xã hội Chủ nghĩa Việt Nam",
                    "UNCLOS": "Công ước Liên hợp quốc về Luật Biển",
                    "DOC": "Tuyên bố ứng xử của các bên ở Biển Đông"
                },
                "military_campaigns": [
                    "Điện Biên Phủ", "Việt Bắc", "Biên giới", "Tây Nguyên",
                    "Huế - Đà Nẵng", "Hồ Chí Minh", "Đường 9 - Nam Lào",
                    "Vạn Tường", "Ấp Bắc", "Đường 14 - Phước Long"
                ],
                "historical_figures": [
                    "Hồ Chí Minh", "Võ Nguyên Giáp", "Ngô Đình Diệm",
                    "Nguyễn Thị Định", "Pôn Pốt", "Đờ Ca-xtơ-ri",
                    "Ních-xơn", "Trần Trọng Kim", "Đắc-giăng-li-ơ"
                ],
                "key_documents": [
                    "Tuyên ngôn Độc lập", "Hiệp định Giơ-ne-vơ",
                    "Hiệp định Pa-ri", "Hiến chương Liên hợp quốc",
                    "Luật Biển Việt Nam", "Tuyên bố về lãnh hải"
                ]
            },
            
            "CHỦ ĐỀ 4: CÔNG CUỘC ĐỔI MỚI Ở VIỆT NAM TỪ NĂM 1986 ĐẾN NAY": {
                "priority_entities": [
                    "Chiến lược/Chủ trương", "Tổ chức", "Văn kiện/Hiệp định",
                    "Sự kiện", "Nhân Vật", "Quốc gia", "Công trình"
                ],
                "entity_blacklist": [
                    "phát triển kinh tế", "ổn định xã hội", "hoà bình và phát triển",
                    "công bằng xã hội", "tiến bộ và công bằng", "nâng cao đời sống",
                    "cải thiện đời sống", "phát triển văn hoá", "bảo vệ môi trường",
                    "hợp tác quốc tế", "giao lưu văn hoá", "trao đổi giáo dục",
                    "hỗ trợ nhân đạo", "cứu trợ thiên tai", "bài học kinh nghiệm",
                    "thành tựu cơ bản", "ý nghĩa lịch sử", "nguyên nhân thắng lợi",
                    "trí tuệ con người", "nhân dân thế giới",
                    "thế giới", "phe", "quân", "đế quốc", "phong kiến"
                ],
                "required_keywords": [
                    "Đổi mới", "Đại hội VI", "Đại hội VII", "Đại hội VIII", "Đại hội X",
                    "Kinh tế thị trường", "Công nghiệp hoá", "Hiện đại hoá",
                    "WTO", "ASEAN", "EVFTA", "RCEP", "Liên hợp quốc", "APEC",
                    "Tem phiếu", "Bao cấp", "GDP", "HDI", "COVID-19"
                ],
                "time_period": "1986-nay",
                "specific_rules": """
                1. ƯU TIÊN các đại hội Đảng: Đại hội VI (1986), Đại hội VII (1991), Đại hội VIII (1996)
                2. ƯU TIÊN các tổ chức quốc tế: WTO, ASEAN, APEC, Liên hợp quốc
                3. ƯU TIÊN các hiệp định thương mại: EVFTA, RCEP, AFTA
                4. ƯU TIÊN các chính sách kinh tế: Kinh tế thị trường, Công nghiệp hoá
                5. ƯU TIÊN các sự kiện kinh tế: Bãi bỏ tem phiếu (1-4-1989), Gia nhập WTO (2007)
                6. ƯU TIÊN các công trình: Đường dây 500kV Bắc-Nam
                7. Phân biệt các giai đoạn: 1986-1995, 1996-2006, 2006-nay
                """,
                "acronyms": {
                    "WTO": "Tổ chức Thương mại Thế giới",
                    "EVFTA": "Hiệp định Thương mại Tự do Việt Nam-EU",
                    "RCEP": "Hiệp định Đối tác Kinh tế Toàn diện Khu vực",
                    "AFTA": "Khu vực Mậu dịch Tự do ASEAN",
                    "APEC": "Diễn đàn Hợp tác Kinh tế châu Á-Thái Bình Dương",
                    "ASEAN": "Hiệp hội các quốc gia Đông Nam Á",
                    "GDP": "Tổng sản phẩm quốc nội",
                    "HDI": "Chỉ số Phát triển Con người",
                    "MDGs": "Mục tiêu Phát triển Thiên niên kỷ",
                    "UN": "Liên hợp quốc",
                    "SEV": "Hội đồng Tương trợ Kinh tế"
                },
                "key_policies": [
                    "Đổi mới", "Kinh tế thị trường định hướng XHCN",
                    "Công nghiệp hoá, Hiện đại hoá", "Hội nhập quốc tế",
                    "Đa phương hoá, Đa dạng hoá quan hệ đối ngoại"
                ],
                "international_organizations": [
                    "WTO", "ASEAN", "APEC", "Liên hợp quốc", "SEV",
                    "Phong trào Không liên kết", "Diễn đàn hợp tác Đông Á"
                ],
                "economic_indicators": [
                    "GDP", "HDI", "Tốc độ tăng trưởng", "Cơ cấu kinh tế",
                    "Xuất khẩu", "Nhập khẩu", "Đầu tư nước ngoài"
                ]
            },
            
            "CHỦ ĐỀ 5: LỊCH SỬ ĐỐI NGOẠI CỦA VIỆT NAM THỜI CẬN – HIỆN ĐẠI": {
                "priority_entities": [
                    "Nhân Vật", "Tổ chức", "Văn kiện/Hiệp định", 
                    "Sự kiện", "Quốc gia", "Chiến lược/Chủ trương", "Hội nghị"
                ],
                "entity_blacklist": [
                    "hoạt động đối ngoại", "quan hệ quốc tế", "hợp tác quốc tế",
                    "đoàn kết quốc tế", "liên minh quốc tế", "ủng hộ quốc tế",
                    "vận động quốc tế", "tranh thủ quốc tế", "mở rộng quan hệ",
                    "phát triển quan hệ", "củng cố quan hệ", "thiết lập quan hệ",
                    "bình thường hoá quan hệ", "nâng cấp quan hệ", "đối tác chiến lược",
                    "trí tuệ con người", "nhân dân thế giới",
                    "nhân dân", "thế giới", "phe", "quân", "đế quốc", "phong kiến"
                ],
                "required_keywords": [
                    "Phan Bội Châu", "Phan Châu Trinh", "Nguyễn Ái Quốc",
                    "Hiệp định Giơ-ne-vơ", "Hiệp định Pa-ri", "OSS",
                    "Việt Nam Quang phục hội", "Hội Liên hiệp thuộc địa",
                    "Quốc tế Cộng sản", "Liên Xô", "Trung Quốc", "Mỹ",
                    "ASEAN", "Liên hợp quốc", "Hội đồng Bảo an"
                ],
                "time_period": "1900-nay",
                "specific_rules": """
                1. ƯU TIÊN các nhân vật đối ngoại: Phan Bội Châu, Phan Châu Trinh, Hồ Chí Minh
                2. ƯU TIÊN các tổ chức quốc tế: Quốc tế Cộng sản, Liên hợp quốc, ASEAN
                3. ƯU TIÊN các hiệp định ngoại giao: Giơ-ne-vơ, Pa-ri, Hiệp định Sơ bộ
                4. ƯU TIÊN các hội nghị quốc tế: Hội nghị Giơ-ne-vơ, Hội nghị Pa-ri
                5. ƯU TIÊN các cơ quan ngoại giao: OSS, Uỷ ban Giám sát quốc tế
                6. Phân biệt các giai đoạn: Trước 1945, 1945-1975, 1975-1986, 1986-nay
                7. Xử lý đúng các tổ chức cách mạng quốc tế
                """,
                "acronyms": {
                    "OSS": "Cơ quan Tình báo Chiến lược Mỹ",
                    "SEV": "Hội đồng Tương trợ Kinh tế",
                    "UN": "Liên hợp quốc",
                    "ASEAN": "Hiệp hội các quốc gia Đông Nam Á",
                    "AFTA": "Khu vực Mậu dịch Tự do ASEAN",
                    "EVFTA": "Hiệp định Thương mại Tự do Việt Nam-EU",
                    "RCEP": "Hiệp định Đối tác Kinh tế Toàn diện Khu vực",
                    "APEC": "Diễn đàn Hợp tác Kinh tế châu Á-Thái Bình Dương"
                },
                "diplomatic_figures": [
                    "Phan Bội Châu", "Phan Châu Trinh", "Nguyễn Ái Quốc",
                    "Hồ Chí Minh", "Trần Trọng Kim", "Ngô Đình Diệm"
                ],
                "international_organizations_diplo": [
                    "Quốc tế Cộng sản", "Liên hợp quốc", "ASEAN",
                    "Hội đồng Bảo an Liên hợp quốc", "Phong trào Không liên kết",
                    "Hội đồng Tương trợ Kinh tế (SEV)", "OSS"
                ],
                "diplomatic_events": [
                    "Hội nghị Giơ-ne-vơ 1954", "Hội nghị Pa-ri 1973",
                    "Đại hội VI (1986)", "Việt Nam gia nhập ASEAN (1995)",
                    "Việt Nam gia nhập WTO (2007)", "Bình thường hoá với Mỹ (1995)"
                ],
                "diplomatic_documents": [
                    "Hiệp định Giơ-ne-vơ", "Hiệp định Pa-ri", "Hiệp định Sơ bộ",
                    "Tạm ước Việt - Pháp", "Hiệp ước Hoa - Pháp"
                ]
            },
            
            "CHỦ ĐỀ 6: HỒ CHÍ MINH TRONG LỊCH SỬ VIỆT NAM": {
                "priority_entities": [
                    "Nhân Vật", "Sự kiện", "Địa điểm", "Tổ chức",
                    "Văn kiện/Hiệp định", "Công trình", "Chiến lược/Chủ trương"
                ],
                "entity_blacklist": [
                    "tinh thần yêu nước", "lòng kính yêu", "sự kính trọng",
                    "biết ơn", "tấm gương đạo đức", "phong cách",
                    "tư tưởng lớn", "đạo đức cách mạng", "nhân cách",
                    "khát vọng độc lập", "ý chí kiên cường", "sự hy sinh",
                    "cống hiến", "đóng góp", "ảnh hưởng", "di sản",
                    "bài học", "tấm gương sáng", "nguồn cảm hứng",
                    "trí tuệ con người", "nhân dân thế giới",
                    "nhân dân", "thế giới", "phe", "quân", "đế quốc", "phong kiến"
                ],
                "required_keywords": [
                    "Hồ Chí Minh", "Nguyễn Ái Quốc", "Nguyễn Tất Thành",
                    "Nguyễn Sinh Cung", "Bến Nhà Rồng", "Pác Bó", "Tân Trào",
                    "Tuyên ngôn Độc lập", "Đảng Cộng sản Việt Nam", "Việt Minh",
                    "Hội Việt Nam Cách mạng Thanh niên", "UNESCO", "Lăng Chủ tịch"
                ],
                "time_period": "1890-nay",
                "specific_rules": """
                1. ƯU TIÊN các tên gọi của Hồ Chí Minh: Nguyễn Sinh Cung, Nguyễn Tất Thành, Nguyễn Ái Quốc, Hồ Chí Minh
                2. ƯU TIÊN các sự kiện trong đời: Sinh 19-5-1890, Ra đi tìm đường cứu nước 5-6-1911, Thành lập Đảng 1930, Đọc Tuyên ngôn Độc lập 2-9-1945
                3. ƯU TIÊN các địa điểm liên quan: Làng Sen, Huế, Bến Nhà Rồng, Pác Bó, Tân Trào, Quảng trường Ba Đình
                4. ƯU TIÊN các tổ chức Người sáng lập: Đảng Cộng sản Việt Nam, Việt Minh, Hội Việt Nam Cách mạng Thanh niên
                5. ƯU TIÊN các văn kiện: Tuyên ngôn Độc lập, Chính cương vắn tắt, Di chúc
                6. Phân biệt các giai đoạn: 1890-1911, 1911-1941, 1941-1945, 1945-1954, 1954-1969, sau 1969
                7. Ghi nhận đầy đủ NGÀY THÁNG sự kiện
                """,
                "acronyms": {
                    "UNESCO": "Tổ chức Giáo dục, Khoa học và Văn hoá Liên hợp quốc",
                    "OSS": "Cơ quan Tình báo Chiến lược Mỹ",
                    "VNDCCH": "Việt Nam Dân chủ Cộng hòa",
                    "CHXHCNVN": "Cộng hòa Xã hội Chủ nghĩa Việt Nam",
                    "TPHCM": "Thành phố Hồ Chí Minh"
                },
                "ho_chi_minh_names": [
                    "Nguyễn Sinh Cung", "Nguyễn Tất Thành", "Văn Ba",
                    "Nguyễn Ái Quốc", "Hồ Chí Minh", "Bác Hồ"
                ],
                "key_life_events": [
                    "Sinh ngày 19-5-1890", "Ra đi tìm đường cứu nước 5-6-1911",
                    "Đọc Sơ thảo luận cương Lê-nin 1920", "Thành lập Đảng 1930",
                    "Về nước 28-1-1941", "Đọc Tuyên ngôn Độc lập 2-9-1945",
                    "Qua đời 2-9-1969"
                ],
                "organizations_founded": [
                    "Đảng Cộng sản Việt Nam", "Việt Minh",
                    "Hội Việt Nam Cách mạng Thanh niên", "Hội Liên hiệp thuộc địa",
                    "Đội Việt Nam Tuyên truyền Giải phóng quân"
                ],
                "important_locations": [
                    "Làng Sen", "Làng Hoàng Trù", "Huế", "Phan Thiết",
                    "Bến Nhà Rồng", "Pác Bó", "Tân Trào", "Quảng trường Ba Đình",
                    "Hồng Công", "Quảng Châu", "Pa-ri", "Mát-xcơ-va"
                ],
                "key_documents_hcm": [
                    "Tuyên ngôn Độc lập", "Chính cương vắn tắt",
                    "Sách lược vắn tắt", "Di chúc", "Lời kêu gọi toàn quốc kháng chiến",
                    "Yêu sách của nhân dân An Nam"
                ],
                "family_members": [
                    "Nguyễn Sinh Sắc", "Hoàng Thị Loan", "Nguyễn Sinh Khiêm",
                    "Nguyễn Thị Thanh"
                ]
            }
        }
        return configs.get(topic_name, {})
    
    @staticmethod
    def create_topic_prompt(window_text: str, file_path: str, topic_config: Dict[str, Any]) -> str:
        """Tạo prompt đặc thù cho chủ đề."""
        topic, lesson = utils.extract_topic_and_lesson(file_path)
        
        # Xác định prompt theo chủ đề
        if "HỒ CHÍ MINH" in topic:
            return TopicProcessor._create_ho_chi_minh_prompt(window_text, topic, lesson, topic_config)
        elif "CÔNG CUỘC ĐỔI MỚI" in topic:
            return TopicProcessor._create_doi_moi_prompt(window_text, topic, lesson, topic_config)
        elif "LỊCH SỬ ĐỐI NGOẠI" in topic:
            return TopicProcessor._create_doi_ngoai_prompt(window_text, topic, lesson, topic_config)
        elif "CÁCH MẠNG THÁNG TÁM" in topic or "CHIẾN TRANH GIẢI PHÓNG" in topic:
            return TopicProcessor._create_vietnam_war_prompt(window_text, topic, lesson, topic_config)
        elif "ASEAN" in topic:
            return TopicProcessor._create_asean_prompt(window_text, topic, lesson, topic_config)
        else:
            return TopicProcessor._create_default_prompt(window_text, topic, lesson, topic_config)
    
    @staticmethod
    def _create_default_prompt(window_text: str, topic: str, lesson: str, topic_config: Dict[str, Any]) -> str:
        """Prompt mặc định cho các chủ đề khác."""
        prompt = f"""
        PHÂN TÍCH VĂN BẢN LỊCH SỬ VIỆT NAM - TRÍCH XUẤT THỰC THỂ CHÍNH XÁC

        VĂN BẢN:
        {window_text}

        YÊU CẦU QUAN TRỌNG - ĐỌC KỸ:
        1. CHỈ trích xuất các thực thể LỊCH SỬ CHÍNH THỐNG có ý nghĩa lịch sử quan trọng
        2. TUYỆT ĐỐI KHÔNG trích xuất các cụm từ chung chung, khái niệm trừu tượng
        3. Mỗi entity phải là MỘT TÊN RIÊNG hoặc SỰ KIỆN CỤ THỂ trong sử sách

        LOẠI THỰC THỂ HỢP LỆ (PHẢI LÀ TÊN RIÊNG):
        - Nhân Vật: Lãnh tụ, nhân vật lịch sử cụ thể (Hồ Chí Minh, Phan Bội Châu...)
        - Tổ chức: Tên chính thức của tổ chức (Liên hợp quốc, NATO, ASEAN...)
        - Quốc gia: Tên quốc gia cụ thể (Việt Nam, Mỹ, Liên Xô, Pháp...)
        - Sự kiện: Sự kiện lịch sử có tên riêng (Chiến tranh thế giới thứ hai, Cách mạng tháng Tám...)
        - Chiến dịch/Trận đánh: Tên chiến dịch quân sự (Điện Biên Phủ, Chiến dịch Hồ Chí Minh...)
        - Hội nghị: Hội nghị có tên riêng (Hội nghị I-an-ta, Hội nghị Tê-hê-ran...)
        - Văn kiện/Hiệp định: Văn bản có tên chính thức (Hiến chương Liên hợp quốc, Hiệp định Pa-ri...)
        - Địa điểm: Địa danh lịch sử cụ thể (Hà Nội, Sài Gòn, Pác Bó...)
        - Chiến lược/Chủ trương: Chiến lược có tên riêng (Đổi mới, Chiến lược quân sự...)
        - Công trình: Công trình có tên riêng (đường dây 500kV, Lăng Chủ tịch Hồ Chí Minh...)

        DANH SÁCH CỤM TỪ KHÔNG ĐƯỢC TRÍCH XUẤT:
        - "giải trừ quân bị", "chạy đua vũ trang", "phát triển kinh tế"
        - "thương mại quốc tế", "xoá đói giảm nghèo", "hợp tác quốc tế"
        - "an ninh quốc tế", "phát triển bền vững", "bình đẳng giới"
        - Các cụm từ chung chung không phải tên riêng
        - Các khái niệm trừu tượng không có tên cụ thể

        QUY TẮC NGHIÊM NGẶT:
        1. Entity phải là TÊN RIÊNG viết hoa hoặc có ý nghĩa như tên riêng
        2. KHÔNG trích xuất động từ, cụm động từ, tính từ chung
        3. Entity phải xuất hiện trong sách giáo khoa lịch sử
        4. Nếu không chắc chắn 100%, KHÔNG trích xuất

        QUY TẮC NGHIÊM NGẶT VỀ NGÀY THÁNG:
        1. KHÔNG trích xuất ngày/tháng/năm đơn thuần (ví dụ: "1945", "2-9-1945", "tháng 5-1972")
        2. Chỉ trích xuất SỰ KIỆN có tên riêng và ghi ngày tháng trong properties
        3. Ví dụ đúng: "Cách mạng tháng Tám (1945)" → extract sự kiện, properties: {{"năm": "1945"}}
        4. Ví dụ sai: "1945" → KHÔNG extract (chỉ là năm)

        VÍ DỤ ĐÚNG:
        - "Liên hợp quốc" → Tổ chức (ĐÚNG - tên riêng)
        - "Hồ Chí Minh" → Nhân Vật (ĐÚNG - tên riêng)
        - "Chiến tranh thế giới thứ hai" → Sự kiện (ĐÚNG - tên sự kiện)

        VÍ DỤ SAI (KHÔNG ĐƯỢC TRÍCH XUẤT):
        - "giải trừ quân bị" → KHÔNG (chỉ là hoạt động chung)
        - "phát triển kinh tế" → KHÔNG (khái niệm chung)
        - "chống chạy đua vũ trang" → KHÔNG (khẩu hiệu chung)

        ĐỊNH DẠNG ĐẦU RA JSON:
        {{
            "entities": [
                {{
                    "id": "tên chuẩn chính xác",
                    "label": ["tên chính", "tên khác nếu có"],
                    "type": "loại thực thể",
                    "description": "mô tả ngắn về ý nghĩa lịch sử",
                    "properties": {{"thông tin có cấu trúc"}},
                    "confidence": 0.9
                }}
            ]
        }}

        Chỉ trả về JSON, không giải thích thêm.
        """
        return prompt
    
    @staticmethod
    def _create_ho_chi_minh_prompt(window_text: str, topic: str, lesson: str, topic_config: Dict[str, Any]) -> str:
        """Prompt đặc thù cho Chủ đề 6 - Hồ Chí Minh."""
        # Implementation từ cải tiến số 6
        prompt = f"""
        PHÂN TÍCH TIỂU SỬ VÀ SỰ NGHIỆP HỒ CHÍ MINH
        CHỦ ĐỀ 6: HỒ CHÍ MINH TRONG LỊCH SỬ VIỆT NAM
        
        THÔNG TIN BÀI HỌC:
        - Chủ đề: {topic}
        - Bài: {lesson}
        - Giai đoạn: 1890 đến nay (Cuộc đời và di sản Hồ Chí Minh)
        
        VĂN BẢN CẦN PHÂN TÍCH:
        {window_text}
        
        === YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ HỒ CHÍ MINH ===
        CHỈ trích xuất các thực thể TRỰC TIẾP LIÊN QUAN ĐẾN HỒ CHÍ MINH
        
        DANH SÁCH THỰC THỂ BẮT BUỘC PHẢI TRÍCH XUẤT (nếu có trong văn bản):
        
        A. CÁC TÊN GỌI CỦA HỒ CHÍ MINH:
        1. Nguyễn Sinh Cung (tên khai sinh) - type: "Nhân Vật"
        2. Nguyễn Tất Thành (thời niên thiếu) - type: "Nhân Vật"
        3. Văn Ba (trên tàu La-tu-sơ Tơ-rê-vin) - type: "Nhân Vật"
        4. Nguyễn Ái Quốc (thời kỳ hoạt động ở nước ngoài) - type: "Nhân Vật"
        5. Hồ Chí Minh (từ 1942) - type: "Nhân Vật"
        6. Bác Hồ (cách gọi thân thương) - type: "Nhân Vật"
        
        B. THÂN NHÂN, GIA ĐÌNH:
        1. Nguyễn Sinh Sắc (cha) - type: "Nhân Vật"
        2. Hoàng Thị Loan (mẹ) - type: "Nhân Vật"
        3. Nguyễn Sinh Khiêm (anh) - type: "Nhân Vật"
        4. Nguyễn Thị Thanh (chị) - type: "Nhân Vật"
        
        C. SỰ KIỆN QUAN TRỌNG TRONG ĐỜI:
        1. Sinh ngày 19-5-1890 tại làng Hoàng Trù - type: "Sự kiện"
        2. Học tại Huế (Trường Tiểu học Pháp-Việt Đông Ba, Trường Quốc học) - type: "Sự kiện"
        3. Dạy học tại trường Dục Thanh (Phan Thiết) - type: "Sự kiện"
        4. Ra đi tìm đường cứu nước (5-6-1911 từ Bến Nhà Rồng) - type: "Sự kiện"
        5. Đọc Sơ thảo luận cương Lê-nin (7-1920) - type: "Sự kiện"
        6. Thành lập Hội Việt Nam Cách mạng Thanh niên (6-1925) - type: "Sự kiện"
        7. Thành lập Đảng Cộng sản Việt Nam (3-2-1930) - type: "Sự kiện"
        8. Về nước trực tiếp lãnh đạo cách mạng (28-1-1941) - type: "Sự kiện"
        9. Đọc Tuyên ngôn Độc lập (2-9-1945) - type: "Sự kiện"
        10. Qua đời (2-9-1969) - type: "Sự kiện"
        
        D. TỔ CHỨC DO NGƯỜI SÁNG LẬP/HOẠT ĐỘNG:
        1. Đảng Cộng sản Việt Nam - type: "Tổ chức"
        2. Việt Minh (Mặt trận Việt Nam Độc lập Đồng minh) - type: "Tổ chức"
        3. Hội Việt Nam Cách mạng Thanh niên - type: "Tổ chức"
        4. Hội Liên hiệp thuộc địa - type: "Tổ chức"
        5. Đội Việt Nam Tuyên truyền Giải phóng quân - type: "Tổ chức"
        6. Đảng Cộng sản Pháp (tham gia sáng lập) - type: "Tổ chức"
        
        E. ĐỊA ĐIỂM QUAN TRỌNG:
        1. Làng Sen, làng Hoàng Trù (quê nội, quê ngoại) - type: "Địa điểm"
        2. Huế (nơi học tập, tham gia phong trào chống thuế) - type: "Địa điểm"
        3. Phan Thiết (dạy học tại trường Dục Thanh) - type: "Địa điểm"
        4. Bến Nhà Rồng (nơi ra đi tìm đường cứu nước) - type: "Địa điểm"
        5. Pa-ri (Pháp) - nơi hoạt động cách mạng - type: "Địa điểm"
        6. Quảng Châu (Trung Quốc) - mở lớp huấn luyện - type: "Địa điểm"
        7. Pác Bó (Cao Bằng) - nơi về nước, Hội nghị Trung ương 8 - type: "Địa điểm"
        8. Tân Trào (Tuyên Quang) - nơi lãnh đạo Tổng khởi nghĩa - type: "Địa điểm"
        9. Quảng trường Ba Đình - đọc Tuyên ngôn Độc lập - type: "Địa điểm"
        
        F. VĂN KIỆN, TÁC PHẨM:
        1. Tuyên ngôn Độc lập (1945) - type: "Văn kiện/Hiệp định"
        2. Chính cương vắn tắt (1930) - type: "Văn kiện/Hiệp định"
        3. Sách lược vắn tắt (1930) - type: "Văn kiện/Hiệp định"
        4. Di chúc (1969) - type: "Văn kiện/Hiệp định"
        5. Lời kêu gọi toàn quốc kháng chiến (1946) - type: "Văn kiện/Hiệp định"
        6. Yêu sách của nhân dân An Nam (1919) - type: "Văn kiện/Hiệp định"
        7. Báo Người cùng khổ (Le Paria) - type: "Văn kiện/Hiệp định"
        8. Báo Thanh niên (1925) - type: "Văn kiện/Hiệp định"
        
        G. CÔNG TRÌNH TƯỞNG NIỆM:
        1. Lăng Chủ tịch Hồ Chí Minh - type: "Công trình"
        2. Bảo tàng Hồ Chí Minh - type: "Công trình"
        3. Khu di tích Kim Liên (Nghệ An) - type: "Công trình"
        4. Khu di tích Pác Bó (Cao Bằng) - type: "Công trình"
        5. Tượng đài Hồ Chí Minh tại các nước - type: "Công trình"
        
        H. TỔ CHỨC QUỐC TẾ CÔNG NHẬN:
        1. UNESCO (công nhận năm 1987) - type: "Tổ chức"
        2. Các nước có tượng đài Hồ Chí Minh: Lào, Nga, Pháp, Cu-ba...
        
        I. CHIẾN LƯỢC, TƯ TƯỞNG:
        1. "Độc lập dân tộc gắn liền với chủ nghĩa xã hội" - type: "Chiến lược/Chủ trương"
        2. "Đoàn kết toàn dân" - type: "Chiến lược/Chủ trương"
        3. "Toàn dân kháng chiến" - type: "Chiến lược/Chủ trương"
        
        DANH SÁCH CỤM TỪ TUYỆT ĐỐI KHÔNG ĐƯỢC TRÍCH XUẤT (vì quá chung):
        - "tinh thần yêu nước", "lòng kính yêu", "sự kính trọng"
        - "biết ơn", "tấm gương đạo đức", "phong cách"
        - "tư tưởng lớn", "đạo đức cách mạng", "nhân cách"
        - "khát vọng độc lập", "ý chí kiên cường", "sự hy sinh"
        - "cống hiến", "đóng góp", "ảnh hưởng", "di sản"
        - "bài học", "tấm gương sáng", "nguồn cảm hứng"
        - Các tính từ, cụm từ đánh giá chung chung
        
        QUY TẮC XỬ LÝ ĐẶC BIỆT CHO CHỦ ĐỀ HỒ CHÍ MINH:
        1. Ghi nhận đầy đủ NGÀY THÁNG CHI TIẾT: "19-5-1890", "5-6-1911"
        2. Phân biệt các TÊN GỌI theo từng thời kỳ: Nguyễn Sinh Cung → Nguyễn Tất Thành → Nguyễn Ái Quốc → Hồ Chí Minh
        3. Liên kết sự kiện - địa điểm - con người: Sinh tại làng Hoàng Trù, học tại Huế, ra đi từ Bến Nhà Rồng
        4. Ưu tiên extract THÔNG TIN THỰC TẾ, KHÁCH QUAN về cuộc đời Hồ Chí Minh
        5. Ghi nhận các MỐC THỜI GIAN quan trọng trong hành trình cách mạng
        6. Chỉ extract khi thông tin CỤ THỂ, RÕ RÀNG trong văn bản
        
        VÍ DỤ ĐÚNG (TRÍCH XUẤT):
        - "Nguyễn Ái Quốc" → type: "Nhân Vật", description: "Tên gọi của Hồ Chí Minh thời kỳ hoạt động ở nước ngoài"
        - "Bến Nhà Rồng" → type: "Địa điểm", description: "Nơi Hồ Chí Minh ra đi tìm đường cứu nước năm 1911"
        - "Đảng Cộng sản Việt Nam" → type: "Tổ chức", description: "Đảng do Hồ Chí Minh sáng lập năm 1930"
        - "Tuyên ngôn Độc lập" → type: "Văn kiện/Hiệp định", description: "Văn bản do Hồ Chí Minh soạn thảo và đọc ngày 2-9-1945"
        - "Lăng Chủ tịch Hồ Chí Minh" → type: "Công trình", description: "Nơi lưu giữ thi hài Chủ tịch Hồ Chí Minh"
        
        VÍ DỤ SAI (KHÔNG TRÍCH XUẤT):
        - "tinh thần yêu nước" → KHÔNG (tính từ chung)
        - "tấm gương đạo đức" → KHÔNG (đánh giá chung)
        - "di sản vĩ đại" → KHÔNG (khái niệm chung)
        
        ĐỊNH DẠNG ĐẦU RA JSON:
        {{
            "entities": [
                {{
                    "id": "tên chuẩn (ưu tiên tên đầy đủ, chính xác)",
                    "label": ["tên chính", "tên khác/biệt hiệu"],
                    "type": "một trong các loại hợp lệ",
                    "description": "mô tả ngắn về mối quan hệ với Hồ Chí Minh",
                    "properties": {{
                        "thời_gian": ["thời điểm liên quan"],
                        "địa_điểm": ["địa điểm liên quan"],
                        "vai_trò": ["vai trò đối với Hồ Chí Minh"],
                        "giai_đoạn": ["giai đoạn trong cuộc đời Hồ Chí Minh"],
                        "ngày_tháng": ["ngày tháng cụ thể nếu có"]
                    }},
                    "confidence": 0.9
                }}
            ]
        }}
        
        Chỉ trả về JSON hợp lệ, không giải thích thêm.
        """
        return prompt
    
    @staticmethod
    def _create_doi_moi_prompt(window_text: str, topic: str, lesson: str, topic_config: Dict[str, Any]) -> str:
        """Prompt đặc thù cho Chủ đề 4 - Công cuộc Đổi mới."""
        # Implementation từ cải tiến số 4
        prompt = f"""
        PHÂN TÍCH LỊCH SỬ KINH TẾ - CHÍNH TRỊ VIỆT NAM HIỆN ĐẠI
        CHỦ ĐỀ 4: CÔNG CUỘC ĐỔI MỚI Ở VIỆT NAM TỪ NĂM 1986 ĐẾN NAY
        
        THÔNG TIN BÀI HỌC:
        - Chủ đề: {topic}
        - Bài: {lesson}
        - Giai đoạn lịch sử: 1986 đến nay (Công cuộc Đổi mới)
        
        VĂN BẢN CẦN PHÂN TÍCH:
        {window_text}
        
        === YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ ĐỔI MỚI ===
        CHỈ trích xuất các thực thể KINH TẾ - CHÍNH TRỊ CỤ THỂ, có vai trò trong công cuộc Đổi mới
        
        DANH SÁCH THỰC THỂ BẮT BUỌC PHẢI TRÍCH XUẤT (nếu có trong văn bản):
        
        A. SỰ KIỆN, ĐẠI HỘI QUAN TRỌNG:
        1. Đại hội VI (1986) - Mở đầu công cuộc Đổi mới - type: "Sự kiện"
        2. Đại hội VII (1991) - type: "Sự kiện"
        3. Đại hội VIII (1996) - Đẩy mạnh CNH-HĐH - type: "Sự kiện"
        4. Đại hội X (2006) - type: "Sự kiện"
        5. Bãi bỏ tem phiếu (1-4-1989) - type: "Sự kiện"
        6. Gia nhập WTO (2007) - type: "Sự kiện"
        7. Gia nhập ASEAN (1995) - type: "Sự kiện"
        
        B. CHÍNH SÁCH, CHIẾN LƯỢC KINH TẾ:
        1. Đổi mới (từ 1986) - type: "Chiến lược/Chủ trương"
        2. Kinh tế thị trường định hướng XHCN - type: "Chiến lược/Chủ trương"
        3. Công nghiệp hoá, Hiện đại hoá - type: "Chiến lược/Chủ trương"
        4. Hội nhập quốc tế - type: "Chiến lược/Chủ trương"
        5. Ba chương trình kinh tế (LT-TP, HTD, HXK) - type: "Chiến lược/Chủ trương"
        6. Đa phương hoá, Đa dạng hoá quan hệ - type: "Chiến lược/Chủ trương"
        
        C. TỔ CHỨC QUỐC TẾ:
        1. WTO (Tổ chức Thương mại Thế giới) - type: "Tổ chức"
        2. ASEAN (Hiệp hội các quốc gia Đông Nam Á) - type: "Tổ chức"
        3. APEC (Diễn đàn Hợp tác Kinh tế châu Á-Thái Bình Dương) - type: "Tổ chức"
        4. Liên hợp quốc (UN) - type: "Tổ chức"
        5. SEV (Hội đồng Tương trợ Kinh tế) - type: "Tổ chức"
        6. Phong trào Không liên kết - type: "Tổ chức"
        
        D. HIỆP ĐỊNH, VĂN KIỆN QUỐC TẾ:
        1. Hiệp định EVFTA (Việt Nam-EU) - type: "Văn kiện/Hiệp định"
        2. Hiệp định RCEP - type: "Văn kiện/Hiệp định"
        3. Hiệp định AFTA (Khu vực Mậu dịch Tự do ASEAN) - type: "Văn kiện/Hiệp định"
        4. Nghị định thư Ki-ô-tô - type: "Văn kiện/Hiệp định"
        
        E. CHỈ TIÊU KINH TẾ (chỉ khi là tên riêng):
        1. GDP (Tổng sản phẩm quốc nội) - type: "Khái niệm"
        2. HDI (Chỉ số Phát triển Con người) - type: "Khái niệm"
        3. MDGs (Mục tiêu Phát triển Thiên niên kỷ) - type: "Khái niệm"
        
        F. CÔNG TRÌNH, DỰ ÁN LỚN:
        1. Đường dây 500kV Bắc-Nam - type: "Công trình"
        2. Các công trình kết cấu hạ tầng lớn - type: "Công trình"
        
        G. QUỐC GIA ĐỐI TÁC QUAN TRỌNG:
        1. Mỹ (Hoa Kỳ)
        2. Trung Quốc
        3. Liên bang Nga
        4. Nhật Bản
        5. Hàn Quốc
        6. EU (Liên minh châu Âu)
        7. Lào, Cam-pu-chia (quan hệ truyền thống)
        
        H. CÁC VẤN ĐỀ TOÀN CẦU:
        1. COVID-19 (đại dịch) - type: "Sự kiện"
        2. Biến đổi khí hậu - type: "Khái niệm"
        3. Ô nhiễm môi trường - type: "Khái niệm"
        
        DANH SÁCH CỤM TỪ TUYỆT ĐỐI KHÔNG ĐƯỢC TRÍCH XUẤT (vì quá chung):
        - "phát triển kinh tế", "ổn định xã hội", "hoà bình và phát triển"
        - "công bằng xã hội", "tiến bộ và công bằng", "nâng cao đời sống"
        - "cải thiện đời sống", "phát triển văn hoá", "bảo vệ môi trường"
        - "hợp tác quốc tế", "giao lưu văn hoá", "trao đổi giáo dục"
        - "hỗ trợ nhân đạo", "cứu trợ thiên tai", "bài học kinh nghiệm"
        - "thành tựu cơ bản", "ý nghĩa lịch sử", "nguyên nhân thắng lợi"
        - Các cụm từ chỉ mục tiêu, nguyên tắc chung
        
        QUY TẮC XỬ LÝ ĐẶC BIỆT CHO ĐỔI MỚI:
        1. Ghi nhận đầy đủ NĂM SỰ KIỆN: "1986", "1995", "2007" → properties.năm
        2. Xử lý đúng các từ VIẾT TẮT: WTO → Tổ chức Thương mại Thế giới
        3. Phân biệt các GIAI ĐOẠN: 1986-1995, 1996-2006, 2006-nay
        4. Ưu tiên extract TÊN CHÍNH THỨC của tổ chức, hiệp định
        5. Ghi nhận SỐ LIỆU KINH TẾ khi đi kèm với chỉ tiêu cụ thể
        6. Chỉ extract quốc gia khi được nhắc LÀ ĐỐI TÁC QUAN TRỌNG
        
        VÍ DỤ ĐÚNG (TRÍCH XUẤT):
        - "Đại hội VI (1986)" → type: "Sự kiện"
        - "WTO" → type: "Tổ chức", description: "Tổ chức Thương mại Thế giới"
        - "Kinh tế thị trường định hướng XHCN" → type: "Chiến lược/Chủ trương"
        - "Hiệp định EVFTA" → type: "Văn kiện/Hiệp định"
        - "Đường dây 500kV Bắc-Nam" → type: "Công trình"
        - "GDP" → type: "Khái niệm"
        
        VÍ DỤ SAI (KHÔNG TRÍCH XUẤT):
        - "phát triển kinh tế" → KHÔNG (khái niệm chung)
        - "hợp tác quốc tế" → KHÔNG (khái niệm chung)
        - "nâng cao đời sống" → KHÔNG (mục tiêu chung)
        
        ĐỊNH DẠNG ĐẦU RA JSON:
        {{
            "entities": [
                {{
                    "id": "tên chuẩn (ưu tiên tên tiếng Việt đầy đủ)",
                    "label": ["tên chính", "tên viết tắt", "tên tiếng Anh"],
                    "type": "một trong các loại hợp lệ",
                    "description": "mô tả ngắn về vai trò trong công cuộc Đổi mới",
                    "properties": {{
                        "thời_gian": ["năm/thời điểm"],
                        "giai_đoạn": ["giai đoạn lịch sử"],
                        "quốc_gia": ["quốc gia liên quan"],
                        "chỉ_số": ["chỉ số kinh tế liên quan"],
                        "kết_quả": ["kết quả/ý nghĩa"]
                    }},
                    "confidence": 0.9
                }}
            ]
        }}
        
        Chỉ trả về JSON hợp lệ, không giải thích thêm.
        """
        return prompt
    
    @staticmethod
    def _create_doi_ngoai_prompt(window_text: str, topic: str, lesson: str, topic_config: Dict[str, Any]) -> str:
        """Prompt đặc thù cho Chủ đề 5 - Lịch sử Đối ngoại."""
        # Implementation từ cải tiến số 5
        prompt = f"""
        PHÂN TÍCH LỊCH SỬ ĐỐI NGOẠI VIỆT NAM
        CHỦ ĐỀ 5: LỊCH SỬ ĐỐI NGOẠI CỦA VIỆT NAM THỜI CẬN – HIỆN ĐẠI
        
        THÔNG TIN BÀI HỌC:
        - Chủ đề: {topic}
        - Bài: {lesson}
        - Giai đoạn lịch sử: Đầu thế kỷ XX đến nay
        
        VĂN BẢN CẦN PHÂN TÍCH:
        {window_text}
        
        === YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ ĐỐI NGOẠI ===
        CHỈ trích xuất các thực thể ĐỐI NGOẠI - NGOẠI GIAO CỤ THỂ
        
        DANH SÁCH THỰC THỂ BẮT BUỘC PHẢI TRÍCH XUẤT (nếu có trong văn bản):
        
        A. NHÂN VẬT ĐỐI NGOẠI QUAN TRỌNG:
        1. Phan Bội Châu (hoạt động ở Nhật, Trung Quốc) - type: "Nhân Vật"
        2. Phan Châu Trinh (hoạt động ở Pháp) - type: "Nhân Vật"
        3. Nguyễn Ái Quốc/Hồ Chí Minh - type: "Nhân Vật"
        4. Các nhà ngoại giao Việt Nam khác
        
        B. TỔ CHỨC QUỐC TẾ, CÁCH MẠNG:
        1. Việt Nam Quang phục hội (1912) - type: "Tổ chức"
        2. Hội Liên hiệp thuộc địa (1921) - type: "Tổ chức"
        3. Quốc tế Cộng sản - type: "Tổ chức"
        4. Đảng Cộng sản Pháp - type: "Tổ chức"
        5. Hội Liên hiệp các dân tộc bị áp bức Á Đông (1925) - type: "Tổ chức"
        6. OSS (Cơ quan Tình báo Chiến lược Mỹ) - type: "Tổ chức"
        7. Uỷ ban Giám sát quốc tế - type: "Tổ chức"
        8. Liên hợp quốc - type: "Tổ chức"
        9. ASEAN - type: "Tổ chức"
        10. SEV (Hội đồng Tương trợ Kinh tế) - type: "Tổ chức"
        
        C. HIỆP ĐỊNH, VĂN KIỆN NGOẠI GIAO:
        1. Hiệp định Sơ bộ (6-3-1946) - type: "Văn kiện/Hiệp định"
        2. Tạm ước Việt - Pháp (14-9-1946) - type: "Văn kiện/Hiệp định"
        3. Hiệp định Giơ-ne-vơ (21-7-1954) - type: "Văn kiện/Hiệp định"
        4. Hiệp định Pa-ri (27-1-1973) - type: "Văn kiện/Hiệp định"
        5. Hiệp ước Hoa - Pháp (28-2-1946) - type: "Văn kiện/Hiệp định"
        6. Các hiệp định biên giới, lãnh hải
        
        D. HỘI NGHỊ QUỐC TẾ:
        1. Hội nghị Giơ-ne-vơ (1954) - type: "Hội nghị"
        2. Hội nghị Pa-ri (1968-1973) - type: "Hội nghị"
        3. Các hội nghị quốc tế khác
        
        E. SỰ KIỆN ĐỐI NGOẠI QUAN TRỌNG:
        1. Phan Bội Châu sang Nhật (1905) - type: "Sự kiện"
        2. Nguyễn Ái Quốc tham gia sáng lập Đảng Cộng sản Pháp (1920) - type: "Sự kiện"
        3. Nguyễn Ái Quốc đến Liên Xô (1923) - type: "Sự kiện"
        4. Thiết lập quan hệ với Trung Quốc, Liên Xô (1950) - type: "Sự kiện"
        5. Việt Nam gia nhập ASEAN (1995) - type: "Sự kiện"
        6. Bình thường hoá với Mỹ (1995) - type: "Sự kiện"
        7. Việt Nam gia nhập WTO (2007) - type: "Sự kiện"
        8. Việt Nam làm Uỷ viên Hội đồng Bảo an (2008-2009, 2020-2021) - type: "Sự kiện"
        
        F. QUỐC GIA ĐỐI TÁC:
        1. Nhật Bản (thời Phan Bội Châu)
        2. Trung Quốc (Quảng Châu, Trung Hoa Dân quốc)
        3. Pháp
        4. Liên Xô/Nga
        5. Mỹ (Hoa Kỳ)
        6. Lào, Cam-pu-chia
        7. Các nước ASEAN
        8. EU (Liên minh châu Âu)
        
        G. CHIẾN LƯỢC ĐỐI NGOẠI:
        1. "Đa phương hoá, đa dạng hoá" - type: "Chiến lược/Chủ trương"
        2. "Việt Nam muốn làm bạn với tất cả các nước" - type: "Chiến lược/Chủ trương"
        3. "Chủ động, tích cực hội nhập quốc tế" - type: "Chiến lược/Chủ trương"
        
        H. CƠ QUAN, VỊ TRÍ NGOẠI GIAO:
        1. Uỷ viên không thường trực Hội đồng Bảo an - type: "Khái niệm"
        2. Cơ quan Tuỳ viên Quốc phòng - type: "Khái niệm"
        3. Đại sứ quán, Công sứ - type: "Khái niệm"
        
        DANH SÁCH CỤM TỪ TUYỆT ĐỐI KHÔNG ĐƯỢC TRÍCH XUẤT (vì quá chung):
        - "hoạt động đối ngoại", "quan hệ quốc tế", "hợp tác quốc tế"
        - "đoàn kết quốc tế", "liên minh quốc tế", "ủng hộ quốc tế"
        - "vận động quốc tế", "tranh thủ quốc tế", "mở rộng quan hệ"
        - "phát triển quan hệ", "củng cố quan hệ", "thiết lập quan hệ"
        - "bình thường hoá quan hệ", "nâng cấp quan系", "đối tác chiến lược"
        - Các cụm từ chỉ hoạt động chung
        
        QUY TẮC XỬ LÝ ĐẶC BIỆT CHO ĐỐI NGOẠI:
        1. Ghi nhận đầy đủ THỜI GIAN, ĐỊA ĐIỂM: "1905", "Quảng Châu", "Giơ-ne-vơ"
        2. Xử lý đúng các TÊN TỔ CHỨC QUỐC TẾ: Quốc tế Cộng sản, ASEAN, Liên hợp quốc
        3. Phân biệt các GIAI ĐOẠN: Trước 1945, 1945-1975, 1975-1986, 1986-nay
        4. Liên kết nhân vật - tổ chức - sự kiện: Phan Bội Châu → Việt Nam Quang phục hội → Nhật Bản
        5. Ưu tiên extract TÊN CHÍNH THỨC của hiệp định, hội nghị
        6. Ghi nhận VAI TRÒ NGOẠI GIAO của các nhân vật
        
        VÍ DỤ ĐÚNG (TRÍCH XUẤT):
        - "Phan Bội Châu" → type: "Nhân Vật", description: "Nhà yêu nước, hoạt động ở Nhật Bản, Trung Quốc"
        - "Việt Nam Quang phục hội" → type: "Tổ chức"
        - "Hiệp định Giơ-ne-vơ 1954" → type: "Văn kiện/Hiệp định"
        - "Quốc tế Cộng sản" → type: "Tổ chức"
        - "Hội nghị Pa-ri" → type: "Hội nghị"
        - "Đa phương hoá, đa dạng hoá" → type: "Chiến lược/Chủ trương"
        
        VÍ DỤ SAI (KHÔNG TRÍCH XUẤT):
        - "hoạt động đối ngoại" → KHÔNG (khái niệm chung)
        - "quan hệ quốc tế" → KHÔNG (khái niệm chung)
        - "ủng hộ quốc tế" → KHÔNG (khái niệm chung)
        
        ĐỊNH DẠNG ĐẦU RA JSON:
        {{
            "entities": [
                {{
                    "id": "tên chuẩn (ưu tiên tên tiếng Việt đầy đủ)",
                    "label": ["tên chính", "tên khác/biệt hiệu"],
                    "type": "một trong các loại hợp lệ",
                    "description": "mô tả ngắn về vai trò trong lịch sử đối ngoại",
                    "properties": {{
                        "thời_gian": ["thời điểm hoạt động"],
                        "địa_điểm": ["địa bàn hoạt động"],
                        "tổ_chức": ["tổ chức liên quan"],
                        "quốc_gia": ["quốc gia liên quan"],
                        "vai_trò": ["vai trò đối ngoại"],
                        "giai_đoạn": ["giai đoạn lịch sử"]
                    }},
                    "confidence": 0.9
                }}
            ]
        }}
        
        Chỉ trả về JSON hợp lệ, không giải thích thêm.
        """
        return prompt
    
    @staticmethod
    def _create_vietnam_war_prompt(window_text: str, topic: str, lesson: str, topic_config: Dict[str, Any]) -> str:
        """Prompt đặc thù cho Chủ đề 3 - Lịch sử quân sự Việt Nam."""
        # Implementation từ cải tiến số 3
        prompt = f"""
        PHÂN TÍCH LỊCH SỬ QUÂN SỰ VIỆT NAM - CHỦ ĐỀ 3: CÁCH MẠNG THÁNG TÁM VÀ CÁC CUỘC CHIẾN TRANH BẢO VỆ TỔ QUỐC
        
        THÔNG TIN BÀI HỌC:
        - Chủ đề: {topic}
        - Bài: {lesson}
        - Giai đoạn lịch sử: 1945 đến nay (Cách mạng Tháng Tám, Kháng chiến chống Pháp, Kháng chiến chống Mỹ, Bảo vệ biên giới)
        
        VĂN BẢN CẦN PHÂN TÍCH:
        {window_text}
        
        === YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ LỊCH SỬ QUÂN SỰ VIỆT NAM ===
        CHỈ trích xuất các thực thể LỊCH SỬ QUÂN SỰ CỤ THỂ, có vai trò trong các cuộc chiến tranh bảo vệ Tổ quốc
        
        DANH SÁCH THỰC THỂ BẮT BUỘC PHẢI TRÍCH XUẤT (nếu có trong văn bản):
        
        A. NHÂN VẬT LỊCH SỬ QUAN TRỌNG:
        1. Lãnh đạo Việt Nam: Hồ Chí Minh, Võ Nguyên Giáp, Nguyễn Thị Định, Trần Trọng Kim
        2. Lãnh đạo nước ngoài: Ngô Đình Diệm, Pôn Pốt, Đờ Ca-xtơ-ri, Ních-xơn, Đắc-giăng-li-ơ
        3. Chỉ huy quân sự: Các tướng lĩnh chỉ huy chiến dịch
        
        B. CHIẾN DỊCH/TRẬN ĐÁNH QUAN TRỌNG:
        1. Thời kỳ chống Pháp (1945-1954): Điện Biên Phủ, Việt Bắc, Biên giới
        2. Thời kỳ chống Mỹ (1954-1975): Tây Nguyên, Huế - Đà Nẵng, Hồ Chí Minh, Đường 9 - Nam Lào
        3. Các trận đánh tiêu biểu: Ấp Bắc, Vạn Tường, Đường 14 - Phước Long
        4. Chiến dịch bảo vệ biên giới (1975-1989): Vị Xuyên, biên giới Tây Nam, biên giới phía Bắc
        
        C. SỰ KIỆN LỊCH SỬ LỚN:
        1. Cách mạng tháng Tám (1945)
        2. Ngày Độc lập 2-9-1945
        3. Đồng khởi (1959-1960)
        4. Tổng tiến công Tết Mậu Thân (1968)
        5. Giải phóng Sài Gòn (30-4-1975)
        6. Chiến tranh biên giới Tây Nam (1975-1979)
        7. Chiến tranh biên giới phía Bắc (1979)
        
        D. TỔ CHỨC, LỰC LƯỢNG VŨ TRANG:
        1. Việt Minh (Mặt trận Việt Nam Độc lập Đồng minh)
        2. Quân Giải phóng miền Nam (QGP)
        3. Mặt trận Dân tộc Giải phóng miền Nam Việt Nam (MTDTGP)
        4. Quân đội Nhân dân Việt Nam
        5. Chính quyền Sài Gòn (Việt Nam Cộng hòa)
        6. Quân tình nguyện Việt Nam
        
        E. VĂN KIỆN, HIỆP ĐỊNH QUỐC TẾ:
        1. Tuyên ngôn Độc lập (1945)
        2. Hiệp định Giơ-ne-vơ (1954)
        3. Hiệp định Pa-ri (1973)
        4. Luật Biển Việt Nam (2012)
        5. Tuyên bố về lãnh hải (1977)
        
        F. ĐỊA ĐIỂM CHIẾN LƯỢC:
        1. Tân Trào (Thủ đô kháng chiến)
        2. Điện Biên Phủ
        3. Sài Gòn (TP Hồ Chí Minh)
        4. Huế, Đà Nẵng
        5. Vị Xuyên (Hà Giang)
        6. Quần đảo Hoàng Sa, Trường Sa
        7. Căn cứ địa Việt Bắc
        
        G. CHIẾN LƯỢC/CHỦ TRƯƠNG QUÂN SỰ:
        1. "Chiến tranh đặc biệt" (Mỹ)
        2. "Chiến tranh cục bộ" (Mỹ)
        3. "Việt Nam hoá chiến tranh" (Mỹ)
        4. "Kế hoạch Na-va" (Pháp)
        5. "Toàn dân, toàn diện, trường kỳ, tự lực cánh sinh"
        
        H. QUỐC GIA THAM CHIẾN:
        1. Việt Nam (VNDCCH, CHXHCNVN)
        2. Mỹ (Hoa Kỳ)
        3. Pháp
        4. Trung Quốc
        5. Cam-pu-chia (Pôn Pốt)
        
        DANH SÁCH CỤM TỪ TUYỆT ĐỐI KHÔNG ĐƯỢC TRÍCH XUẤT (vì quá chung):
        - "phát triển kinh tế", "xây dựng đất nước", "hoà bình và ổn định"
        - "đoàn kết dân tộc", "bài học kinh nghiệm", "nguyên nhân thắng lợi"
        - "ý nghĩa lịch sử", "nghệ thuật quân sự", "quốc phòng toàn dân"
        - "bảo vệ tổ quốc", "giải phóng dân tộc", "xây dựng chủ nghĩa xã hội"
        - "khôi phục kinh tế", "phát triển văn hoá", "củng cố chính quyền"
        - Các cụm từ chỉ mục tiêu, nguyên tắc chung
        
        QUY TẮC XỬ LÝ ĐẶC BIỆT CHO LỊCH SỬ QUÂN SỰ VIỆT NAM:
        1. Ghi nhận đầy đủ NGÀY THÁNG CHI TIẾT: "13-3-1954 đến 7-5-1954" → properties.ngày_tháng
        2. Xử lý đúng các từ VIẾT TẮT: QGP → Quân Giải phóng miền Nam
        3. Phân biệt các GIAI ĐOẠN LỊCH SỬ: 1945-1954, 1954-1975, 1975-1989, 1989-nay
        4. Ghi nhận SỐ LIỆU QUÂN SỰ: số quân, vũ khí, thiệt hại (nếu có trong văn bản)
        5. Liên kết các thực thể: Chiến dịch → Nhân vật chỉ huy → Địa điểm
        6. Ưu tiên tên chính thức: "Chiến dịch Điện Biên Phủ" thay vì "trận Điện Biên Phủ"
        
        VÍ DỤ ĐÚNG (TRÍCH XUẤT):
        - "Hồ Chí Minh" → type: "Nhân Vật", description: "Chủ tịch nước, lãnh đạo kháng chiến"
        - "Chiến dịch Điện Biên Phủ" → type: "Chiến dịch/Trận đánh"
        - "Hiệp định Giơ-ne-vơ 1954" → type: "Văn kiện/Hiệp định"
        - "Quân Giải phóng miền Nam" → type: "Tổ chức"
        - "Hoàng Sa" → type: "Địa điểm", description: "Quần đảo thuộc chủ quyền Việt Nam"
        - "Chiến tranh đặc biệt" → type: "Chiến lược/Chủ trương"
        
        VÍ DỤ SAI (KHÔNG TRÍCH XUẤT):
        - "bảo vệ tổ quốc" → KHÔNG (khái niệm chung)
        - "bài học kinh nghiệm" → KHÔNG (khái niệm chung)
        - "phát triển kinh tế" → KHÔNG (không phải thực thể quân sự)
        
        ĐỊNH DẠNG ĐẦU RA JSON:
        {{
            "entities": [
                {{
                    "id": "tên chuẩn (ưu tiên tên tiếng Việt đầy đủ)",
                    "label": ["tên chính", "tên viết tắt", "tên khác"],
                    "type": "một trong các loại hợp lệ",
                    "description": "mô tả ngắn về vai trò trong lịch sử quân sự",
                    "properties": {{
                        "thời_gian": ["ngày tháng, năm diễn ra"],
                        "địa_điểm": ["địa điểm liên quan"],
                        "chỉ_huy": ["người chỉ huy"],
                        "lực_lượng": ["lực lượng tham gia"],
                        "kết_quả": ["kết quả/ý nghĩa"],
                        "giai_đoạn": ["giai đoạn lịch sử"],
                        "số_liệu": ["số liệu quân sự nếu có"]
                    }},
                    "confidence": 0.9
                }}
            ]
        }}
        
        Chỉ trả về JSON hợp lệ, không giải thích thêm.
        """
        return prompt
    
    @staticmethod
    def _create_asean_prompt(window_text: str, topic: str, lesson: str, topic_config: Dict[str, Any]) -> str:
        """Prompt đặc thù cho chủ đề ASEAN."""
        # Implementation từ cải tiến số 2
        prompt = f"""
        PHÂN TÍCH LỊCH SỬ KHU VỰC ĐÔNG NAM Á - CHỦ ĐỀ 2: ASEAN
        
        THÔNG TIN BÀI HỌC:
        - Chủ đề: {topic}
        - Bài: {lesson}
        - Giai đoạn lịch sử: 1967 đến nay (từ khi thành lập ASEAN)
        
        VĂN BẢN CẦN PHÂN TÍCH:
        {window_text}
        
        === YÊU CẦU ĐẶC BIỆT CHO CHỦ ĐỀ ASEAN ===
        CHỈ trích xuất các thực thể LIÊN QUAN TRỰC TIẾP ĐẾN ASEAN VÀ KHU VỰC ĐÔNG NAM Á
        
        DANH SÁCH THỰC THỂ BẮT BUỘC PHẢI TRÍCH XUẤT (nếu có trong văn bản):
        
        A. TỔ CHỨC ASEAN VÀ CƠ QUAN TRỰC THUỘC:
        1. ASEAN (Hiệp hội các quốc gia Đông Nam Á) - type: "Tổ chức"
        2. APSC (Cộng đồng Chính trị – An ninh ASEAN) - type: "Tổ chức"
        3. AEC (Cộng đồng Kinh tế ASEAN) - type: "Tổ chức"
        4. ASCC (Cộng đồng Văn hoá – Xã hội ASEAN) - type: "Tổ chức"
        5. ARF (Diễn đàn khu vực ASEAN) - type: "Tổ chức"
        6. AFTA (Khu vực Mậu dịch Tự do ASEAN) - type: "Chiến lược/Chủ trương"
        7. MAPHILINDO (1963) - type: "Tổ chức"
        8. Hiệp hội Đông Nam Á (1961) - type: "Tổ chức"
        
        B. VĂN KIỆN, HIỆP ĐỊNH ASEAN:
        1. Tuyên bố Băng Cốc (1967) - type: "Văn kiện/Hiệp định"
        2. Hiến chương ASEAN (2007) - type: "Văn kiện/Hiệp định"
        3. TAC (Hiệp ước Thân thiện và Hợp tác, 1976) - type: "Văn kiện/Hiệp định"
        4. Tuyên bố ZOPFAN (1971) - type: "Văn kiện/Hiệp định"
        5. Tuyên bố Ba-li I (1976) - type: "Văn kiện/Hiệp định"
        6. Tuyên bố Ba-li II (2003) - type: "Văn kiện/Hiệp định"
        7. Tuyên bố thành lập Cộng đồng ASEAN (2015) - type: "Văn kiện/Hiệp định"
        
        C. HỘI NGHỊ ASEAN QUAN TRỌNG:
        1. Hội nghị cấp cao ASEAN (các kỳ họp) - type: "Hội nghị"
        2. Hội nghị không chính thức ASEAN (1997) - type: "Hội nghị"
        3. Hội nghị cấp cao ASEAN 14 (2009) - type: "Hội nghị"
        4. Hội nghị Cấp cao ASEAN lần thứ 37 (2020) - type: "Hội nghị"
        
        D. QUỐC GIA THÀNH VIÊN ASEAN (chỉ khi được nhắc là thành viên):
        1. 5 nước sáng lập: In-đô-nê-xi-a, Ma-lai-xi-a, Phi-líp-pin, Xin-ga-po, Thái Lan
        2. Các nước gia nhập sau: Việt Nam, Lào, Myanmar, Campuchia, Brunei
        3. Tên tiếng Việt chuẩn: Indonesia, Malaysia, Philippines, Singapore, Thái Lan
        
        E. SỰ KIỆN LỊCH SỬ ASEAN:
        1. Ngày thành lập ASEAN (8-8-1967) - type: "Sự kiện"
        2. Việt Nam gia nhập ASEAN (1995) - type: "Sự kiện"
        3. Thành lập Cộng đồng ASEAN (31-12-2015) - type: "Sự kiện"
        4. Các giai đoạn mở rộng ASEAN - type: "Sự kiện"
        
        F. ĐỊA ĐIỂM QUAN TRỌNG:
        1. Băng Cốc (nơi ký Tuyên bố thành lập) - type: "Địa điểm"
        2. Hà Nội (nơi tổ chức Hội nghị cấp cao) - type: "Địa điểm"
        3. Ba-li (liên quan đến các tuyên bố) - type: "Địa điểm"
        
        DANH SÁCH CỤM TỪ TUYỆT ĐỐI KHÔNG ĐƯỢC TRÍCH XUẤT (vì quá chung):
        - "phát triển kinh tế", "hợp tác quốc tế", "tăng trưởng kinh tế"
        - "tiến bộ xã hội", "phát triển văn hoá", "hoà bình và ổn định"
        - "hợp tác khu vực", "mở rộng quan hệ", "nâng cao uy tín"
        - "xây dựng cộng đồng", "thách thức và triển vọng", "hội nhập quốc tế"
        - "ba trụ cột" (chỉ extract tên từng trụ cột cụ thể: APSC, AEC, ASCC)
        - Các cụm từ chỉ mục tiêu chung chung
        
        QUY TẮC XỬ LÝ ĐẶC BIỆT CHO ASEAN:
        1. Ghi nhận đầy đủ NGÀY THÁNG: "8-8-1967" → properties.ngày_tháng
        2. Xử lý đúng các từ VIẾT TẮT: ASEAN → giải thích đầy đủ trong description
        3. Phân biệt các GIAI ĐOẠN: 1967-1976, 1976-1999, 1999-2015, 2015-nay
        4. Chỉ extract quốc gia khi được nhắc LÀ THÀNH VIÊN ASEAN
        5. Ưu tiên extract TÊN CHÍNH THỨC của tổ chức, văn kiện
        
        VÍ DỤ ĐÚNG (TRÍCH XUẤT):
        - "ASEAN" → type: "Tổ chức", description: "Hiệp hội các quốc gia Đông Nam Á"
        - "Tuyên bố Băng Cốc" → type: "Văn kiện/Hiệp định"
        - "Cộng đồng Kinh tế ASEAN (AEC)" → type: "Tổ chức"
        - "Việt Nam" (khi được nhắc là thành viên) → type: "Quốc gia"
        - "Ngày 8-8-1967" → type: "Sự kiện", id: "Thành lập ASEAN"
        
        VÍ DỤ SAI (KHÔNG TRÍCH XUẤT):
        - "hợp tác khu vực" → KHÔNG (khái niệm chung)
        - "ba trụ cột" → KHÔNG (chỉ extract tên từng trụ cột cụ thể)
        - "phát triển kinh tế" → KHÔNG (mục tiêu chung)
        
        ĐỊNH DẠNG ĐẦU RA JSON:
        {{
            "entities": [
                {{
                    "id": "tên chuẩn (ưu tiên tên tiếng Việt đầy đủ)",
                    "label": ["tên chính", "tên viết tắt", "tên tiếng Anh"],
                    "type": "một trong các loại hợp lệ",
                    "description": "mô tả ngắn về vai trò, ý nghĩa trong ASEAN",
                    "properties": {{
                        "ngày_tháng": ["các mốc thời gian liên quan"],
                        "địa_điểm": ["địa điểm liên quan"],
                        "thành_viên": ["các nước thành viên liên quan"],
                        "giai_đoạn": ["giai đoạn lịch sử"],
                        "văn_kiện_liên_quan": ["các văn kiện liên quan"]
                    }},
                    "confidence": 0.9
                }}
            ]
        }}
        
        Chỉ trả về JSON hợp lệ, không giải thích thêm.
        """
        return prompt