# -*- coding: utf-8 -*-
"""
topic_config.py
Quan ly cau hinh topic dua tren cau truc JSON sach giao khoa.
File nay doc tu JSON va tao config phu hop cho tung chu de.
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


# Danh sach blacklist chung cho tat ca cac chu de
COMMON_BLACKLIST = [
    "phat trien kinh te", "hop tac quoc te", "giai tru quan bi",
    "chay dua vu trang", "xoa doi giam ngheo", "an ninh quoc te",
    "phat trien ben vung", "binh dang gioi", "thuong mai quoc te",
    "hoi nhap quoc te", "toan cau hoa", "doi thoai hop tac",
    "quan he quoc te", "trat tu the gioi", "xu the phat trien",
    "chinh phu", "tri tue con nguoi", "nhan dan the gioi",
    "nhan dan", "the gioi", "phe", "quan", "de quoc", "phong kien",
    "cac nuoc thanh vien", "cac nuoc dang phat trien",
    "dich benh", "bien doi khi hau", "moi truong"
]


@dataclass
class TopicConfig:
    """Cau hinh cho mot chu de cu the."""
    topic_id: str
    topic_description: str
    lessons: List[Dict[str, Any]] = field(default_factory=list)
    
    # Entity extraction config
    priority_entities: List[str] = field(default_factory=list)
    entity_blacklist: List[str] = field(default_factory=list)
    required_keywords: List[str] = field(default_factory=list)
    acronyms: Dict[str, str] = field(default_factory=dict)
    
    # Time period
    time_period: str = ""
    specific_rules: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyen sang dict de tuong thich voi code cu."""
        return {
            "topic_id": self.topic_id,
            "topic_description": self.topic_description,
            "lessons": self.lessons,
            "priority_entities": self.priority_entities,
            "entity_blacklist": self.entity_blacklist + COMMON_BLACKLIST,
            "required_keywords": self.required_keywords,
            "acronyms": self.acronyms,
            "time_period": self.time_period,
            "specific_rules": self.specific_rules
        }


class TopicConfigManager:
    """Quan ly cau hinh cho tat ca cac chu de tu file JSON."""
    
    # Cac tu khoa de nhan dien topic
    TOPIC_KEYWORDS = {
        "THE GIOI": "Chu de 1",
        "CHIEN TRANH LANH": "Chu de 1",
        "ASEAN": "Chu de 2",
        "DONG NAM A": "Chu de 2",
        "CACH MANG THANG TAM": "Chu de 3",
        "CHIEN TRANH GIAI PHONG": "Chu de 3",
        "KHANG CHIEN CHONG PHAP": "Chu de 3",
        "KHANG CHIEN CHONG MY": "Chu de 3",
        "DOI MOI": "Chu de 4",
        "XAY DUNG CNXH": "Chu de 4",
        "DOI NGOAI": "Chu de 5",
        "NGOAI GIAO": "Chu de 5",
        "HO CHI MINH": "Chu de 6",
        "BAC HO": "Chu de 6"
    }
    
    # Cau hinh mac dinh cho tung topic
    DEFAULT_CONFIGS = {
        "Chu de 1": TopicConfig(
            topic_id="Chu de 1",
            topic_description="THE GIOI TRONG VA SAU CHIEN TRANH LANH",
            priority_entities=["To chuc", "Hoi nghi", "Van kien/Hiep dinh", "Quoc gia", "Nhan Vat", "Su kien"],
            required_keywords=["Lien hop quoc", "Hoi nghi", "Hiep dinh", "Hien chuong", "Chien tranh lanh", "I-an-ta"],
            acronyms={
                "LHQ": "Lien hop quoc",
                "NATO": "To chuc Hiep uoc Bac Dai Tay Duong",
                "WTO": "To chuc Thuong mai The gioi"
            },
            time_period="1945-1991",
            specific_rules="""
            1. UU TIEN cac to chuc quoc te: LHQ, NATO, WTO, ASEAN, EU
            2. UU TIEN cac hoi nghi: I-an-ta, Te-he-ran, Xan Phran-xi-xco
            3. UU TIEN cac hiep dinh: Hien chuong LHQ, Hiep uoc cam vu khi hat nhan
            4. Ghi nhan day du NGAY THANG NAM cho su kien
            """
        ),
        "Chu de 2": TopicConfig(
            topic_id="Chu de 2",
            topic_description="ASEAN: NHUNG CHANG DUONG LICH SU",
            priority_entities=["To chuc", "Hoi nghi", "Van kien/Hiep dinh", "Quoc gia", "Su kien", "Dia diem"],
            required_keywords=["ASEAN", "Hiep hoi", "Dong Nam A", "Tuyen bo", "Hien chuong", "Cong dong"],
            acronyms={
                "ASEAN": "Hiep hoi cac quoc gia Dong Nam A",
                "APSC": "Cong dong Chinh tri - An ninh ASEAN",
                "AEC": "Cong dong Kinh te ASEAN",
                "ASCC": "Cong dong Van hoa - Xa hoi ASEAN",
                "AFTA": "Khu vuc Mau dich Tu do ASEAN",
                "ARF": "Dien dan khu vuc ASEAN",
                "TAC": "Hiep uoc Than thien va Hop tac o Dong Nam A"
            },
            time_period="1967-nay",
            specific_rules="""
            1. UU TIEN cac to chuc ASEAN: ASEAN, APSC, AEC, ASCC, ARF, AFTA
            2. UU TIEN cac van kien ASEAN: Tuyen bo Bang Coc, Hien chuong ASEAN
            3. UU TIEN cac nuoc thanh vien: Viet Nam, Thai Lan, Indonesia, Malaysia, Singapore, Philippines, Brunei, Lao, Campuchia, Myanmar
            """
        ),
        "Chu de 3": TopicConfig(
            topic_id="Chu de 3",
            topic_description="CACH MANG THANG TAM NAM 1945, CHIEN TRANH GIAI PHONG DAN TOC VA CHIEN TRANH BAO VE TO QUOC",
            priority_entities=["Nhan Vat", "Chien dich/Tran danh", "Su kien", "To chuc", "Van kien/Hiep dinh", "Dia diem"],
            required_keywords=["Cach mang thang Tam", "Khang chien", "Dien Bien Phu", "Hiep dinh", "Chien dich", "Ho Chi Minh"],
            acronyms={
                "VNDCCH": "Viet Nam Dan chu Cong hoa",
                "LHQ": "Lien hop quoc"
            },
            time_period="1945-1975",
            specific_rules="""
            1. UU TIEN cac chien dich: Dien Bien Phu, Ho Chi Minh, Bien gioi, Viet Bac
            2. UU TIEN cac nhan vat: Ho Chi Minh, Vo Nguyen Giap, Pham Van Dong
            3. UU TIEN cac dia diem: Ha Noi, Dien Bien Phu, Sai Gon, Hue
            4. Ghi nhan day du NGAY THANG NAM cho moi su kien
            """
        ),
        "Chu de 4": TopicConfig(
            topic_id="Chu de 4",
            topic_description="CONG CUOC DOI MOI O VIET NAM TU NAM 1986 DEN NAY",
            priority_entities=["Su kien", "To chuc", "Chien luoc/Chu truong", "Nhan Vat", "Hoi nghi"],
            required_keywords=["Doi moi", "Dai hoi", "Dang Cong san", "Kinh te thi truong", "Hoi nhap"],
            acronyms={
                "WTO": "To chuc Thuong mai The gioi",
                "ASEAN": "Hiep hoi cac quoc gia Dong Nam A",
                "APEC": "Dien dan Hop tac Kinh te chau A - Thai Binh Duong"
            },
            time_period="1986-nay",
            specific_rules="""
            1. UU TIEN cac Dai hoi Dang: Dai hoi VI, VII, VIII, IX, X, XI, XII, XIII
            2. UU TIEN cac chinh sach: Doi moi, Kinh te thi truong, Hoi nhap quoc te
            3. Chu y cac moc thoi gian quan trong: 1986, 1991, 2007, 2015
            """
        ),
        "Chu de 5": TopicConfig(
            topic_id="Chu de 5",
            topic_description="LICH SU DOI NGOAI VIET NAM TU NAM 1945 DEN NAY",
            priority_entities=["Su kien", "Van kien/Hiep dinh", "To chuc", "Quoc gia", "Hoi nghi", "Nhan Vat"],
            required_keywords=["Ngoai giao", "Hiep dinh", "Hoi nghi", "Quan he", "Hop tac", "Doc lap"],
            acronyms={
                "LHQ": "Lien hop quoc",
                "ASEAN": "Hiep hoi cac quoc gia Dong Nam A",
                "WTO": "To chuc Thuong mai The gioi"
            },
            time_period="1945-nay",
            specific_rules="""
            1. UU TIEN cac hiep dinh: Hiep dinh Ge-ne-vo, Hiep dinh Pa-ri
            2. UU TIEN cac hoi nghi ngoai giao
            3. Chu y quan he Viet Nam voi cac nuoc lon: My, Trung Quoc, Lien Xo/Nga
            """
        ),
        "Chu de 6": TopicConfig(
            topic_id="Chu de 6",
            topic_description="CHU TICH HO CHI MINH - ANH HUNG GIAI PHONG DAN TOC, NHA VAN HOA KIET XUAT",
            priority_entities=["Nhan Vat", "Su kien", "Dia diem", "To chuc", "Van kien/Hiep dinh"],
            required_keywords=["Ho Chi Minh", "Nguyen Ai Quoc", "Nguyen Tat Thanh", "Dang Cong san", "Tuyen ngon Doc lap"],
            acronyms={
                "UNESCO": "To chuc Giao duc, Khoa hoc va Van hoa Lien hop quoc"
            },
            time_period="1890-1969",
            specific_rules="""
            1. UU TIEN cac ten goi cua Ho Chi Minh: Nguyen Sinh Cung, Nguyen Tat Thanh, Nguyen Ai Quoc, Ho Chi Minh
            2. UU TIEN cac su kien quan trong: Sinh 19-5-1890, Ra di tim duong cuu nuoc 5-6-1911, Thanh lap Dang 1930, Doc Tuyen ngon Doc lap 2-9-1945
            3. UU TIEN cac dia diem: Lang Sen, Hue, Ben Nha Rong, Pac Bo, Tan Trao, Quang truong Ba Dinh
            """
        )
    }
    
    def __init__(self, json_path: str = None):
        """
        Khoi tao TopicConfigManager.
        
        Args:
            json_path: Duong dan toi file JSON sach giao khoa
        """
        self.json_path = json_path
        self.topics: Dict[str, TopicConfig] = {}
        self._lesson_index: Dict[str, Dict] = {}  # lesson_id -> {topic_id, topic_desc, lesson_title}
        
        # Load tu JSON neu co
        if json_path and os.path.exists(json_path):
            self._load_from_json()
        else:
            # Su dung default configs
            self.topics = self.DEFAULT_CONFIGS.copy()
    
    def _load_from_json(self):
        """Load cau truc tu file JSON."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Nhom theo topic_id
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
                
                # Tao index cho lesson
                lesson_id = lesson.get("lesson_id", "")
                self._lesson_index[lesson_id] = {
                    "topic_id": topic_id,
                    "topic_description": lesson.get("topic_description", ""),
                    "lesson_title": lesson.get("lesson_title", "")
                }
            
            # Tao TopicConfig cho moi topic
            for topic_id, topic_data in topics_data.items():
                # Tim default config phu hop
                default_config = self._find_default_config(topic_id, topic_data["topic_description"])
                
                if default_config:
                    # Merge voi thong tin tu JSON
                    config = TopicConfig(
                        topic_id=topic_id,
                        topic_description=topic_data["topic_description"],
                        lessons=topic_data["lessons"],
                        priority_entities=default_config.priority_entities,
                        entity_blacklist=default_config.entity_blacklist,
                        required_keywords=default_config.required_keywords,
                        acronyms=default_config.acronyms,
                        time_period=default_config.time_period,
                        specific_rules=default_config.specific_rules
                    )
                else:
                    # Tao config co ban
                    config = TopicConfig(
                        topic_id=topic_id,
                        topic_description=topic_data["topic_description"],
                        lessons=topic_data["lessons"],
                        priority_entities=["Nhan Vat", "To chuc", "Su kien", "Dia diem"]
                    )
                
                self.topics[topic_id] = config
                # Them voi topic_description de co the tim theo ca 2 cach
                self.topics[topic_data["topic_description"]] = config
                
        except Exception as e:
            print(f"[Warning] Could not load JSON: {e}")
            self.topics = self.DEFAULT_CONFIGS.copy()
    
    def _find_default_config(self, topic_id: str, topic_desc: str) -> Optional[TopicConfig]:
        """Tim default config phu hop voi topic."""
        # Tim theo topic_id truoc
        for default_id, config in self.DEFAULT_CONFIGS.items():
            if default_id.lower() in topic_id.lower():
                return config
        
        # Tim theo keywords trong topic_description
        topic_desc_upper = topic_desc.upper()
        for keyword, mapped_topic_id in self.TOPIC_KEYWORDS.items():
            if keyword in topic_desc_upper:
                return self.DEFAULT_CONFIGS.get(mapped_topic_id)
        
        return None
    
    def get_config(self, topic_name: str) -> Dict[str, Any]:
        """
        Lay cau hinh cho mot topic.
        
        Args:
            topic_name: Co the la topic_id (Chu de 1) hoac topic_description
            
        Returns:
            Dict cau hinh cho topic
        """
        # Tim exact match truoc
        if topic_name in self.topics:
            return self.topics[topic_name].to_dict()
        
        # Tim partial match
        topic_upper = topic_name.upper()
        for key, config in self.topics.items():
            if topic_upper in key.upper() or key.upper() in topic_upper:
                return config.to_dict()
        
        # Tim theo keywords
        for keyword, mapped_topic_id in self.TOPIC_KEYWORDS.items():
            if keyword in topic_upper:
                if mapped_topic_id in self.DEFAULT_CONFIGS:
                    return self.DEFAULT_CONFIGS[mapped_topic_id].to_dict()
        
        # Tra ve config rong
        return {
            "topic_id": topic_name,
            "topic_description": "",
            "priority_entities": ["Nhan Vat", "To chuc", "Su kien", "Dia diem"],
            "entity_blacklist": COMMON_BLACKLIST,
            "required_keywords": [],
            "acronyms": {},
            "time_period": "",
            "specific_rules": ""
        }
    
    def get_lesson_info(self, lesson_id: str) -> Dict[str, str]:
        """Lay thong tin lesson tu lesson_id."""
        return self._lesson_index.get(lesson_id, {})
    
    def get_all_topics(self) -> List[str]:
        """Lay danh sach tat ca topic_id."""
        return [config.topic_id for config in self.topics.values() if hasattr(config, 'topic_id')]


# Singleton instance
_config_manager: Optional[TopicConfigManager] = None


def get_topic_config_manager(json_path: str = None) -> TopicConfigManager:
    """
    Lay TopicConfigManager singleton.
    
    Args:
        json_path: Duong dan toi file JSON (chi can truyen lan dau)
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = TopicConfigManager(json_path)
    return _config_manager


def get_topic_config(topic_name: str, json_path: str = None) -> Dict[str, Any]:
    """
    Ham tien ich de lay config cho topic.
    
    Args:
        topic_name: Ten topic (topic_id hoac topic_description)
        json_path: Duong dan toi file JSON (optional)
    """
    manager = get_topic_config_manager(json_path)
    return manager.get_config(topic_name)


# Test
if __name__ == "__main__":
    # Test voi file JSON
    json_path = r"D:\KLTN\KLTN\SGK\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json"
    
    manager = TopicConfigManager(json_path)
    
    print("=" * 60)
    print("TOPIC CONFIGS LOADED FROM JSON")
    print("=" * 60)
    
    # Test get config
    test_names = [
        "Chu de 1",
        "THE GIOI TRONG VA SAU CHIEN TRANH LANH",
        "ASEAN",
        "Ho Chi Minh"
    ]
    
    for name in test_names:
        config = manager.get_config(name)
        print(f"\n[{name}]")
        print(f"  topic_id: {config.get('topic_id')}")
        print(f"  priority_entities: {config.get('priority_entities')[:3]}...")
        print(f"  acronyms count: {len(config.get('acronyms', {}))}")
