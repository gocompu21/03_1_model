import os
import django
import hashlib
import re
from pathlib import Path
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from exam.models import Question

def get_cleaned_text(text):
    if not text:
        return ""
    text = text.strip()
    # Remove bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Remove headers: # text
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove list markers: - text or * text
    text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)
    return text

def check_tts_status():
    tts_cache_dir = Path(settings.MEDIA_ROOT) / "tts"
    questions = Question.objects.all().order_by('exam__round_number', 'number')
    
    missing_list = []
    changed_list = []
    
    # Get all existing files in cache dir
    existing_files = list(tts_cache_dir.glob("round*_q*_narration_*.mp3"))
    file_map = defaultdict(list) # Key: "roundX_qY", Value: list of hashes
    
    for f in existing_files:
        # filename format: round{round_num}_q{q_num}_narration_{text_hash}.mp3
        parts = f.name.split('_')
        if len(parts) >= 4:
            key = f"{parts[0]}_{parts[1]}" # roundX_qY
            hash_val = parts[3].replace('.mp3', '')
            file_map[key].append(hash_val)

    print(f"Checking {questions.count()} questions...")
    
    for q in questions:
        if not q.narration:
            continue
            
        clean_text = get_cleaned_text(q.narration)
        if not clean_text:
            continue
            
        current_hash = hashlib.md5(clean_text.encode()).hexdigest()[:8]
        key = f"round{q.exam.round_number}_q{q.number}"
        
        has_exact_match = False
        has_any_file = False
        
        if key in file_map:
            has_any_file = True
            if current_hash in file_map[key]:
                has_exact_match = True
        
        if not has_any_file:
            missing_list.append(f"{q.exam.round_number}회 {q.number}번")
        elif not has_exact_match:
            changed_list.append(f"{q.exam.round_number}회 {q.number}번")

    print("\n" + "="*40)
    print(f"TTS 음성 누락 ({len(missing_list)}건):")
    for item in missing_list:
        print(f" - {item}")
        
    print("\n" + "="*40)
    print(f"나레이션 변경됨 (기존 파일 있음, 해시 불일치) ({len(changed_list)}건):")
    for item in changed_list:
        print(f" - {item}")

if __name__ == "__main__":
    check_tts_status()
