"""
TTS Generator Utility Module

Shared TTS generation logic used by:
- study/management/commands/generate_tts.py (CLI batch processing)
- mypage/views.py (Web API single question processing)

Uses Gemini TTS API with ffmpeg for MP3 conversion.
"""

import os
import struct
import subprocess
import tempfile
import uuid
from pathlib import Path

from django.conf import settings


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Convert raw audio data to WAV format.
    
    Args:
        audio_data: Raw audio bytes from Gemini TTS API
        mime_type: MIME type string (e.g., "audio/L16;rate=24000")
    
    Returns:
        WAV file bytes with proper header
    """
    # Parse MIME type
    bits_per_sample = 16
    sample_rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                sample_rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    num_channels = 1
    bytes_per_sample = bits_per_sample // 8
    byte_rate = sample_rate * num_channels * bytes_per_sample
    block_align = num_channels * bytes_per_sample
    data_size = len(audio_data)
    chunk_size = 36 + data_size

    # Build WAV header
    wav_header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size
        1,  # AudioFormat (PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    return wav_header + audio_data


def generate_tts_audio(
    text: str,
    output_filepath: str,
    voice_name: str = "Orus",
    model: str = "gemini-2.5-pro-preview-tts"
) -> dict:
    """Generate TTS audio from text using Gemini API.

    Args:
        text: Text to convert to speech
        output_filepath: Full path to save the MP3 file
        voice_name: Voice to use (default: "Orus")
        model: TTS model name (default: "gemini-2.5-pro-preview-tts")
    
    Returns:
        dict with keys:
            - success: bool
            - message: str (success message or error)
            - filepath: str (output file path if successful)
    """
    try:
        from google import genai
        from google.genai import types
        
        # Configure client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Limit text length
        if len(text) > 5000:
            text = text[:5000] + "... 이하 생략"
        
        # Build TTS request
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )
        
        # Collect audio chunks
        audio_chunks = []
        mime_type_received = None
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
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
                audio_chunks.append(part.inline_data.data)
                if mime_type_received is None:
                    mime_type_received = part.inline_data.mime_type
        
        if not audio_chunks:
            return {
                "success": False,
                "message": "TTS 생성에 실패했습니다. 음성 데이터가 없습니다.",
                "filepath": None
            }
        
        # Combine audio chunks
        combined_audio = b"".join(audio_chunks)
        
        # Convert to WAV
        wav_data = convert_to_wav(combined_audio, mime_type_received or "audio/L16;rate=24000")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        
        # Convert WAV to MP3 using ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav.write(wav_data)
            tmp_wav_path = tmp_wav.name
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", output_filepath],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"ffmpeg error: {result.stderr}")
        finally:
            if os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)
        
        return {
            "success": True,
            "message": f"TTS 생성 완료",
            "filepath": output_filepath
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": str(e),
            "filepath": None
        }


def generate_tts_for_question(question, tab: str = "narration") -> dict:
    """Generate TTS for a specific question.

    Args:
        question: Question model instance
        tab: Content tab to use ("narration", "textbook", "explanation")

    Returns:
        dict with success status, message, and file info
    """
    import hashlib
    import re

    # Select text based on tab
    if tab == "narration" and question.narration:
        text = question.narration
    elif tab == "textbook" and question.textbook_chat:
        text = question.textbook_chat
    elif question.explanation:
        text = question.explanation
    else:
        return {
            "success": False,
            "message": f"해당 컨텐츠가 없습니다 ({tab})",
            "filepath": None,
            "filename": None
        }

    # Clean text for hash calculation (same as study/views.py)
    clean_text = text
    clean_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', clean_text)
    clean_text = re.sub(r'\*([^*]+)\*', r'\1', clean_text)
    clean_text = re.sub(r'^#+\s+', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'^[\*\-]\s+', '', clean_text, flags=re.MULTILINE)

    # Generate filename using text hash (compatible with study/views.py)
    round_num = question.exam.round_number
    q_num = question.number
    text_hash = hashlib.md5(clean_text.encode()).hexdigest()[:8]
    filename = f"round{round_num}_q{q_num}_{tab}_{text_hash}.mp3"

    # Build output path
    tts_dir = os.path.join(settings.MEDIA_ROOT, "tts")
    filepath = os.path.join(tts_dir, filename)

    # Check if file already exists (cache hit)
    if os.path.exists(filepath):
        return {
            "success": True,
            "message": "TTS 캐시 사용",
            "filepath": filepath,
            "filename": filename,
            "file_url": f"{settings.MEDIA_URL}tts/{filename}",
            "cached": True
        }

    # Generate TTS
    result = generate_tts_audio(text, filepath)

    if result["success"]:
        result["filename"] = filename
        result["file_url"] = f"{settings.MEDIA_URL}tts/{filename}"

    return result
