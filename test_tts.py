
import os
import django
from pathlib import Path
from google import genai
from google.genai import types
import hashlib
import time
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from exam.models import Question
from utils.tts_generator import convert_to_wav

def test_tts():
    print("Starting TTS test with Flash TTS model...")
    
    # Get Question 173 (5회 45번)
    try:
        q = Question.objects.get(exam__round_number=5, number=45)
        print(f"Found Question: {q}")
    except Question.DoesNotExist:
        print("Question not found!")
        return

    text = q.narration
    if not text:
        print("No narration found for this question.")
        return
        
    print(f"Narration length: {len(text)}")

    key = settings.GEMINI_API_KEY
    if not key:
        print("GEMINI_API_KEY is missing!")
        return
    
    client = genai.Client(api_key=key)

    # Cleaning
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)
    
    print(f"Cleaned text length: {len(text)}")

    tts_text = text
    
    # Split text into chunks of ~150 chars
    chunks = []
    current_chunk = ""
    for line in tts_text.split('\n'):
        if len(current_chunk) + len(line) < 150:
            current_chunk += line + "\n"
        else:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
    if current_chunk:
        chunks.append(current_chunk)
        
    print(f"Split into {len(chunks)} chunks.")
    
    final_audio_chunks = []
    mime_type = None
    
    # Config: Default voice (no 'voice_name')
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio"],
    )

    for i, chunk_text in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk_text)} chars)...")
        
        chunk_contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=chunk_text)],
            )
        ]
        
        start_time = time.time()
        try:
            got_chunk = False
            for chunk in client.models.generate_content_stream(
                model="gemini-2.5-flash-preview-tts", # Using Flash TTS
                contents=chunk_contents,
                config=generate_content_config,
            ):
                if (
                    chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                ):
                    continue

                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    final_audio_chunks.append(part.inline_data.data)
                    if mime_type is None:
                        mime_type = part.inline_data.mime_type
                    got_chunk = True
            
            elapsed = time.time() - start_time
            print(f"Chunk {i+1} done in {elapsed:.1f}s")
            
            if not got_chunk:
                print("Warning: No audio data in this chunk stream.")
                
        except Exception as e:
            print(f"Error in chunk {i+1}: {e}")
            return
            
        time.sleep(1) 

    if not final_audio_chunks:
        print("No audio chunks received.")
        return

    print(f"Received total {len(final_audio_chunks)} audio parts.")
    
    combined_audio = b"".join(final_audio_chunks)
    wav_data = convert_to_wav(combined_audio, mime_type or "audio/L16;rate=24000")
    
    filename = "test_tts_flash_output.wav"
    with open(filename, "wb") as f:
        f.write(wav_data)
    print(f"Saved {filename}")

if __name__ == "__main__":
    test_tts()
