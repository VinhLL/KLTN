# -*- coding: utf-8 -*-
"""
Script chuyển đổi file văn bản SGK Lịch Sử sang định dạng JSON
Cấu trúc:
- Dòng đầu: Tên chủ đề (CHỦ ĐỀ X: description)
- Tên bài: Bài X: title hoặc BÀI X: title
- Mục lớn (section): Bắt đầu bằng số (1, 2, 3...) - chỉ có subsections, không có content riêng
- Mục con (subsection): Bắt đầu bằng a), b), c) - chứa content
- Nội dung: Các đoạn văn bản (nối các dòng có dấu ":" hoặc ";" với nhau)
"""

import re
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def parse_textbook_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse một file văn bản SGK và chuyển đổi sang cấu trúc JSON.
    Một file có thể chứa nhiều bài, sẽ trả về danh sách các bài.
    
    Args:
        file_path: Đường dẫn tới file văn bản
        
    Returns:
        List chứa các bài đã được cấu trúc hoá
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Chuẩn hóa newlines
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = content.split('\n')
    
    results = []
    current_topic_id = ""
    current_topic_description = ""
    current_result = None
    current_section = None
    current_subsection = None
    current_content_list = []
    pending_colon_line = None  # Dòng kết thúc bằng ":" chờ nối
    
    def save_content():
        """Lưu nội dung đã thu thập vào subsection hiện tại"""
        nonlocal current_content_list, pending_colon_line
        
        if pending_colon_line and current_content_list:
            # Nối dòng có dấu ":" với nội dung tiếp theo
            merged = pending_colon_line + " " + current_content_list[0]
            current_content_list[0] = merged
            pending_colon_line = None
        elif pending_colon_line:
            current_content_list.append(pending_colon_line)
            pending_colon_line = None
        
        if current_subsection and current_content_list:
            current_subsection["content"].extend(current_content_list)
        current_content_list = []
    
    def finalize_result():
        """Hoàn thiện result hiện tại và thêm vào danh sách"""
        nonlocal current_result
        save_content()
        if current_result and (current_result["lesson_id"] or current_result["sections"]):
            results.append(current_result)
        current_result = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Bỏ qua dòng trống
        if not line:
            i += 1
            continue
        
        # Pattern cho CHỦ ĐỀ (CHỦ ĐỀ X: description)
        chu_de_match = re.match(r'^CHỦ ĐỀ\s*(\d+)\s*[:\s]*(.*)$', line, re.IGNORECASE)
        if chu_de_match:
            current_topic_id = f"Chủ đề {chu_de_match.group(1)}"
            desc = chu_de_match.group(2).strip()
            current_topic_description = desc if desc else ""
            i += 1
            continue
        
        # Pattern cho tên bài (BÀI X: title hoặc Bài X: title)
        bai_match = re.match(r'^(Bài|BÀI)\s*(\d+)\s*[:\s]*(.*)$', line, re.IGNORECASE)
        if bai_match:
            # Hoàn thiện bài trước đó
            finalize_result()
            
            # Tạo bài mới
            current_result = {
                "topic_id": current_topic_id,
                "topic_description": current_topic_description,
                "lesson_id": f"Bài {bai_match.group(2)}",
                "lesson_title": bai_match.group(3).strip(),
                "sections": []
            }
            current_section = None
            current_subsection = None
            current_content_list = []
            pending_colon_line = None
            i += 1
            continue
        
        # Nếu chưa có bài nào, tạo bài mặc định
        if current_result is None:
            current_result = {
                "topic_id": current_topic_id,
                "topic_description": current_topic_description,
                "lesson_id": "",
                "lesson_title": "",
                "sections": []
            }
        
        # Pattern cho mục lớn (section): bắt đầu bằng số (1. hoặc 1 )
        # Ví dụ: "1. Một số vấn đề cơ bản về Liên hợp quốc:"
        section_match = re.match(r'^(\d+)[.\s]+(.+)$', line)
        if section_match:
            save_content()
            
            # Tạo section mới
            title = section_match.group(2).strip()
            # Loại bỏ dấu ":" cuối title nếu có
            title = title.rstrip(':')
            
            current_section = {
                "index": int(section_match.group(1)),
                "title": title,
                "subsections": []
            }
            current_result["sections"].append(current_section)
            current_subsection = None
            i += 1
            continue
        
        # Pattern cho mục con (subsection): bắt đầu bằng a), b), c)
        # Có thể có ký hiệu • hoặc ** trước
        subsection_match = re.match(r'^[•\*]{0,2}\s*([a-z])\)\s*(.*)$', line)
        if subsection_match:
            save_content()
            
            # Tạo subsection mới
            subsection_title = subsection_match.group(2).strip()
            # Loại bỏ ** và : cuối nếu có
            subsection_title = re.sub(r'\*{2}', '', subsection_title).strip().rstrip(':')
            
            current_subsection = {
                "label": subsection_match.group(1),  # Chỉ lấy "a", "b", "c" không có ")"
                "title": subsection_title,
                "content": []
            }
            
            if current_section:
                current_section["subsections"].append(current_subsection)
            else:
                # Nếu chưa có section, tạo section mặc định
                current_section = {
                    "index": 0,
                    "title": "",
                    "subsections": [current_subsection]
                }
                current_result["sections"].append(current_section)
            i += 1
            continue
        
        # Nội dung thông thường
        # Loại bỏ dấu ** (markdown bold)
        clean_line = re.sub(r'\*{2}', '', line).strip()
        
        # Xử lý các bullet point (•)
        if clean_line.startswith('•'):
            clean_line = clean_line[1:].strip()
        
        if clean_line:
            # Xử lý dòng kết thúc bằng ":" - chờ nối với dòng tiếp theo
            if clean_line.endswith(':'):
                if pending_colon_line:
                    # Đã có dòng chờ, nối với nhau
                    pending_colon_line = pending_colon_line + " " + clean_line
                else:
                    pending_colon_line = clean_line
            else:
                # Kiểm tra nếu có dòng đang chờ
                if pending_colon_line:
                    # Nối dòng chờ với dòng hiện tại
                    clean_line = pending_colon_line + " " + clean_line
                    pending_colon_line = None
                
                # Nếu chưa có subsection, tạo một subsection mặc định
                if current_subsection is None and current_section:
                    current_subsection = {
                        "label": "",
                        "title": "",
                        "content": []
                    }
                    current_section["subsections"].append(current_subsection)
                elif current_subsection is None:
                    # Tạo section và subsection mặc định
                    current_section = {
                        "index": 0,
                        "title": "",
                        "subsections": []
                    }
                    current_result["sections"].append(current_section)
                    current_subsection = {
                        "label": "",
                        "title": "",
                        "content": []
                    }
                    current_section["subsections"].append(current_subsection)
                
                current_content_list.append(clean_line)
        
        i += 1
    
    # Hoàn thiện bài cuối cùng
    finalize_result()
    
    return results


def merge_content_with_semicolons(content_list: List[str]) -> List[str]:
    """
    Nối các dòng kết thúc bằng ";" với dòng tiếp theo.
    """
    if not content_list:
        return []
    
    merged = []
    current_line = ""
    
    for line in content_list:
        if current_line:
            current_line = current_line + " " + line
        else:
            current_line = line
        
        # Nếu dòng không kết thúc bằng ";", hoàn thành dòng này
        if not current_line.rstrip().endswith(';'):
            merged.append(current_line)
            current_line = ""
    
    # Nếu còn dòng chưa hoàn thành
    if current_line:
        merged.append(current_line)
    
    return merged


def post_process_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hậu xử lý kết quả: nối các dòng có dấu ";" với nhau.
    """
    for section in result.get("sections", []):
        for subsection in section.get("subsections", []):
            if "content" in subsection:
                subsection["content"] = merge_content_with_semicolons(subsection["content"])
    return result


def process_single_file(input_file: str, output_file: str = None):
    """
    Xử lý một file văn bản và lưu kết quả JSON.
    
    Args:
        input_file: Đường dẫn file input
        output_file: Đường dẫn file output (mặc định cùng tên với .json)
    """
    if output_file is None:
        output_file = input_file.rsplit('.', 1)[0] + '.json'
    
    print(f"Processing: {input_file}")
    
    results = parse_textbook_file(input_file)
    
    # Post-process
    results = [post_process_result(r) for r in results]
    
    # Lưu file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"  -> Saved to: {output_file}")
    print(f"  -> Total lessons: {len(results)}")
    
    return results


def process_folder(input_folder: str, output_folder: str = None):
    """
    Xử lý tất cả các file trong một thư mục Chủ đề.
    
    Args:
        input_folder: Đường dẫn thư mục chứa các file bài
        output_folder: Đường dẫn thư mục output (mặc định cùng thư mục)
    """
    if output_folder is None:
        output_folder = input_folder
    
    os.makedirs(output_folder, exist_ok=True)
    
    all_results = []
    for file_name in sorted(os.listdir(input_folder)):
        if file_name.endswith('.txt') and not file_name.startswith('.'):
            file_path = os.path.join(input_folder, file_name)
            output_file = os.path.join(
                output_folder, 
                file_name.replace('.txt', '.json')
            )
            
            try:
                results = process_single_file(file_path, output_file)
                all_results.extend(results)
            except Exception as e:
                print(f"  Error processing {file_name}: {e}")
    
    return all_results


def process_all_chu_de(base_folder: str, output_base: str = None):
    """
    Xử lý tất cả các thư mục Chủ đề trong base_folder.
    
    Args:
        base_folder: Thư mục chứa các folder Chủ đề
        output_base: Thư mục output (mặc định là base_folder/../JSON)
    """
    if output_base is None:
        output_base = os.path.join(os.path.dirname(base_folder), "JSON")
    
    os.makedirs(output_base, exist_ok=True)
    
    all_data = []
    
    for folder_name in sorted(os.listdir(base_folder)):
        folder_path = os.path.join(base_folder, folder_name)
        if os.path.isdir(folder_path) and folder_name.startswith("Chủ đề"):
            print(f"\n{'='*60}")
            print(f"Processing folder: {folder_name}")
            print('='*60)
            
            output_folder = os.path.join(output_base, folder_name)
            results = process_folder(folder_path, output_folder)
            all_data.extend(results)
    
    # Lưu tất cả vào một file tổng hợp
    all_output = os.path.join(output_base, "all_lessons.json")
    with open(all_output, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*60}")
    print(f"All data saved to: {all_output}")
    print(f"Total lessons: {len(all_data)}")
    
    return all_data


# ===== MAIN =====
if __name__ == "__main__":
    # Xử lý file D:\KLTN\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc_formatted.txt
    input_file = r"D:\KLTN\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc_formatted.txt"
    output_file = r"D:\KLTN\SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.json"
    
    print("="*60)
    print("Processing SGK Lịch Sử 12 Kết Nối Tri Thức")
    print("="*60)
    
    results = process_single_file(input_file, output_file)
    
    # In mẫu kết quả của bài đầu tiên
    if results:
        print("\n" + "="*60)
        print("Sample output (first lesson):")
        print("="*60)
        sample = results[0]
        # In tóm tắt
        print(f"topic_id: {sample['topic_id']}")
        print(f"topic_description: {sample['topic_description']}")
        print(f"lesson_id: {sample['lesson_id']}")
        print(f"lesson_title: {sample['lesson_title']}")
        print(f"Number of sections: {len(sample['sections'])}")
        if sample['sections']:
            s = sample['sections'][0]
            print(f"  Section 1: index={s['index']}, title={s['title']}")
            print(f"    Number of subsections: {len(s['subsections'])}")
            if s['subsections']:
                sub = s['subsections'][0]
                print(f"    Subsection 1: label={sub['label']}, title={sub['title']}")
                print(f"      Content items: {len(sub['content'])}")
                if sub['content']:
                    print(f"      First content: {sub['content'][0][:100]}...")
