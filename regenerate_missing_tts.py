import os
import django
import hashlib
import re
import time
import subprocess
import tempfile
from pathlib import Path
from collections import defaultdict
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from exam.models import Question
from google import genai
from google.genai import types

def get_cleaned_text(text):
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)
    return text

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    from utils.tts_generator import convert_to_wav
    return convert_to_wav(audio_data, mime_type)

def regenerate_tts():
    tts_cache_dir = Path(settings.MEDIA_ROOT) / "tts"
    tts_cache_dir.mkdir(parents=True, exist_ok=True)
    
    questions = Question.objects.all().order_by('exam__round_number', 'number')
    
    # Target list from previous check (hardcoded for safety and speed)
    targets = [
        # Missing (10)
        (6, 93), (7, 138),
        (8, 29), (8, 43), (8, 50), (8, 118),
        (9, 91),
        (10, 48), (10, 73), (10, 119),
        
        # Changed (49)
        (5, 14), (5, 131),
        (6, 1), (6, 4), (6, 18), (6, 49), (6, 54), (6, 76), (6, 77), (6, 79), (6, 84), 
        (6, 119), (6, 120), (6, 122), (6, 133), (6, 138), (6, 140),
        (7, 26), (7, 28), (7, 30), (7, 38), (7, 55), (7, 76), (7, 85), (7, 89), (7, 97), 
        (7, 102), (7, 103), (7, 108), (7, 112), (7, 113), (7, 115), (7, 117), (7, 134), (7, 139), (7, 140),
        (8, 90), (8, 123), (8, 124), (8, 125),
        (9, 13), (9, 52), (9, 105), (9, 109), (9, 110), (9, 114), (9, 124), (9, 125),
        (10, 27)
    ]
    
    target_set = set(targets)
    
    print(f"Regenerating {len(targets)} TTS files...")
    
    # Initialize Gemini client
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    processed = 0
    errors = 0

    for q in questions:
        if (q.exam.round_number, q.number) not in target_set:
            continue
            
        if not q.narration:
            print(f"Skipping {q.exam.round_number}회 {q.number}번: No narration")
            continue
            
        print(f"\n[{processed+1}/{len(targets)}] Processing {q.exam.round_number}회 {q.number}번...")
        
        try:
            text = q.narration.strip()
            # Clean text
            text = get_cleaned_text(text)
            
            # Generate filename
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            round_num = q.exam.round_number
            q_num = q.number
            cache_filename = f"round{round_num}_q{q_num}_narration_{text_hash}.mp3"
            cache_filepath = tts_cache_dir / cache_filename
            
            if cache_filepath.exists():
                print(f"  Already exists with correct hash: {cache_filename}")
                processed += 1
                continue
                
            # --- TTS Generation Logic (Copied from generate_tts.py) ---
            tts_text = text
            replacements = {
                '㉠': '기역', '㉡': '니은', '㉢': '디귿', '㉣': '리을',
                '㉤': '미음', '㉥': '비읍', '㉦': '시옷', '㉧': '이응',
                '㉨': '지읒', '㉩': '치읓', '㉪': '키읔', '㉫': '티읕', '㉬': '피읖',
                'ㄱ': '기역', 'ㄴ': '니은', 'ㄷ': '디귿', 'ㄹ': '리을',
                'ㅁ': '미음', 'ㅂ': '비읍', 'ㅅ': '시옷', 'ㅇ': '이응',
                'ㅈ': '지읒', 'ㅊ': '치읓', 'ㅋ': '키읔', 'ㅌ': '티읕', 'ㅍ': '피읖',
                '선지 1번': '1번', '선지 2번': '2번', '선지 3번': '3번', '선지 4번': '4번', '선지 5번': '5번',
                '1번 선지': '1번', '2번 선지': '2번', '3번 선지': '3번', '4번 선지': '4번', '5번 선지': '5번',
                'ANSI': '안시', 'CODIT': '코디트',
            }
            for old, new in replacements.items():
                tts_text = tts_text.replace(old, new)
            
            tts_text = "천천히, 또박또박 명확하게 읽어주세요:\n\n" + tts_text
            
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=tts_text)])]
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Orus")
                    )
                ),
            )
            
            audio_chunks = []
            mime_type = None
            
            for chunk in client.models.generate_content_stream(
                model="gemini-2.5-pro-preview-tts",
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    part = chunk.candidates[0].content.parts[0]
                    if part.inline_data and part.inline_data.data:
                        audio_chunks.append(part.inline_data.data)
                        if mime_type is None:
                            mime_type = part.inline_data.mime_type
                            
            if not audio_chunks:
                print(f"  Error: No audio generated")
                errors += 1
                continue
                
            combined_audio = b"".join(audio_chunks)
            wav_data = convert_to_wav(combined_audio, mime_type or "audio/L16;rate=24000")
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                tmp_wav.write(wav_data)
                tmp_wav_path = tmp_wav.name
            
            try:
                result = subprocess.run(
                    ["ffmpeg", "-y", "-i", tmp_wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", str(cache_filepath)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise Exception(f"ffmpeg error: {result.stderr}")
            finally:
                if os.path.exists(tmp_wav_path):
                    os.remove(tmp_wav_path)
                    
            print(f"  Saved: {cache_filename}")
            processed += 1
            time.sleep(15) # Rate limiting
            
        except Exception as e:
            print(f"  Error: {e}")
            errors += 1
            
    print(f"\nCompleted! Processed: {processed}, Errors: {errors}")

if __name__ == "__main__":
    regenerate_tts()
