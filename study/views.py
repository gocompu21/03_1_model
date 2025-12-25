from django.shortcuts import render, get_object_or_404
from exam.models import Exam, Question, Subject
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import struct


@login_required
def index(request):
    """
    List all available exam rounds and subjects.
    """
    exams = Exam.objects.exclude(round_number=0).order_by("round_number")
    subjects = Subject.objects.all().order_by("code")
    return render(request, "study/index.html", {"exams": exams, "subjects": subjects})


def detail(request, round_number):
    """
    Show all questions for a specific round.
    """
    # Get the exam object for context (title etc)
    # Using filter().first() or get_object_or_404 if we want to be strict
    # But wait, Question checks round_number via exam__round_number?
    # Or is Exam object keys by round_number?

    # Let's verify Exam model structure first.
    # Proceeding with assumption: Exam has round_number field.

    exam = Exam.objects.filter(round_number=round_number).first()

    # Get all questions
    questions = Question.objects.filter(exam__round_number=round_number).order_by(
        "number"
    )

    context = {"round_number": round_number, "exam": exam, "questions": questions}
    return render(request, "study/detail.html", context)


def subject_detail(request, subject_name):
    """
    Show questions for a specific subject, filtered by round (via query param).
    Default to first available round if not specified.
    """
    # 1. Get All Exams for Tabs
    exams = Exam.objects.exclude(round_number=0).order_by("round_number")

    # 2. Determine Round Number
    round_param = request.GET.get("round")
    if round_param:
        try:
            current_round = int(round_param)
        except ValueError:
            current_round = exams.first().round_number if exams.exists() else 0
    else:
        # Default to first round
        current_round = exams.first().round_number if exams.exists() else 0

    # 3. Filter Questions
    # Note: Subject name might need decoding if passed in URL but Django handles unicode in URL params usually.
    questions = Question.objects.filter(
        subject__name=subject_name, exam__round_number=current_round
    ).order_by("number")

    context = {
        "subject_name": subject_name,
        "current_round": current_round,
        "exams": exams,
        "questions": questions,
    }
    return render(request, "study/study_by_subject.html", context)


def parse_audio_mime_type(mime_type: str) -> dict:
    """Parse bits per sample and rate from audio MIME type."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Convert raw audio data to WAV format."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    return header + audio_data


@login_required
def tts_generate(request):
    """Generate TTS audio using Gemini 2.5 Pro Preview TTS with caching."""
    import os
    import hashlib
    from pathlib import Path
    
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        question_id = data.get("question_id")
        tab = data.get("tab", "textbook")  # textbook or general
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not question_id:
        return JsonResponse({"error": "question_id required"}, status=400)

    # Get question
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"error": "Question not found"}, status=404)

    # Get explanation text based on tab
    if tab == "general":
        text = question.general_chat or ""
    else:
        text = question.textbook_chat or ""

    text = text.strip()
    if not text:
        return JsonResponse({"error": "No explanation available"}, status=404)

    # Create cache directory
    tts_cache_dir = Path(settings.MEDIA_ROOT) / "tts"
    tts_cache_dir.mkdir(parents=True, exist_ok=True)

    # Generate cache filename based on question_id, tab, and text hash
    # Hash ensures regeneration if explanation text changes
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    
    # Check for MP3 cache first (preferred)
    mp3_filename = f"q{question_id}_{tab}_{text_hash}.mp3"
    mp3_filepath = tts_cache_dir / mp3_filename
    
    if mp3_filepath.exists():
        with open(mp3_filepath, "rb") as f:
            mp3_data = f.read()
        response = HttpResponse(mp3_data, content_type="audio/mpeg")
        response["Content-Disposition"] = f'inline; filename="{mp3_filename}"'
        response["X-TTS-Cache"] = "HIT"
        return response
    
    # Fallback to WAV cache
    wav_filename = f"q{question_id}_{tab}_{text_hash}.wav"
    wav_filepath = tts_cache_dir / wav_filename
    
    if wav_filepath.exists():
        with open(wav_filepath, "rb") as f:
            wav_data = f.read()
        response = HttpResponse(wav_data, content_type="audio/wav")
        response["Content-Disposition"] = f'inline; filename="{wav_filename}"'
        response["X-TTS-Cache"] = "HIT"
        return response

    # Limit text length to avoid API issues (max ~5000 chars)
    if len(text) > 5000:
        text = text[:5000] + "... 이하 생략"

    try:
        # Lazy import to avoid conflict with google-generativeai package
        from google import genai
        from google.genai import types
        import io
        
        # Initialize Gemini client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        model = "gemini-2.5-flash-preview-tts"
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
                        voice_name="Kore"  # Korean voice
                    )
                )
            ),
        )

        # Collect audio chunks
        audio_chunks = []
        mime_type = None

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
                if mime_type is None:
                    mime_type = part.inline_data.mime_type

        if not audio_chunks:
            return JsonResponse({"error": "No audio generated"}, status=500)

        # Combine all audio chunks
        combined_audio = b"".join(audio_chunks)

        # Convert to WAV
        wav_data = convert_to_wav(combined_audio, mime_type or "audio/L16;rate=24000")

        # Convert to MP3 using ffmpeg
        try:
            import subprocess
            import tempfile
            import os as os_module
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                tmp_wav.write(wav_data)
                tmp_wav_path = tmp_wav.name
            
            try:
                result = subprocess.run(
                    ["ffmpeg", "-y", "-i", tmp_wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", str(mp3_filepath)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise Exception(f"ffmpeg error: {result.stderr}")
                
                with open(mp3_filepath, "rb") as f:
                    mp3_data = f.read()
                
                response = HttpResponse(mp3_data, content_type="audio/mpeg")
                response["Content-Disposition"] = f'inline; filename="{mp3_filename}"'
                response["X-TTS-Cache"] = "MISS"
                return response
            finally:
                if os_module.path.exists(tmp_wav_path):
                    os_module.remove(tmp_wav_path)
        except Exception:
            # Fallback to WAV if MP3 conversion fails
            with open(wav_filepath, "wb") as f:
                f.write(wav_data)
            
            response = HttpResponse(wav_data, content_type="audio/wav")
            response["Content-Disposition"] = f'inline; filename="{wav_filename}"'
            response["X-TTS-Cache"] = "MISS"
            return response

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
