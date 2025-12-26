"""
Django management command to generate TTS audio for all questions.
Usage: python manage.py generate_tts [--all] [--question_id=ID] [--round=N]
"""
import os
import hashlib
import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from exam.models import Question


class Command(BaseCommand):
    help = 'Generate TTS audio files for question explanations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate TTS for all questions',
        )
        parser.add_argument(
            '--question_id',
            type=int,
            help='Generate TTS for a specific question ID',
        )
        parser.add_argument(
            '--round',
            type=int,
            help='Generate TTS for all questions in a specific round',
        )
        parser.add_argument(
            '--tab',
            type=str,
            default='both',
            choices=['textbook', 'general', 'both'],
            help='Which explanation tab to generate (default: both)',
        )

    def handle(self, *args, **options):
        # Lazy imports to avoid startup issues
        from google import genai
        from google.genai import types
        import struct

        if not settings.GEMINI_API_KEY:
            raise CommandError('GEMINI_API_KEY is not set')

        # Create cache directory
        tts_cache_dir = Path(settings.MEDIA_ROOT) / "tts"
        tts_cache_dir.mkdir(parents=True, exist_ok=True)

        # Get questions to process
        if options['question_id']:
            questions = Question.objects.filter(id=options['question_id'])
        elif options['round']:
            questions = Question.objects.filter(exam__round_number=options['round'])
        elif options['all']:
            questions = Question.objects.all()
        else:
            raise CommandError('Please specify --all, --question_id, or --round')

        total = questions.count()
        self.stdout.write(f"Processing {total} questions...")

        # Initialize Gemini client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        generated = 0
        skipped = 0
        errors = 0

        for i, question in enumerate(questions):
            self.stdout.write(f"\n[{i+1}/{total}] Question {question.id} ({question.exam.round_number}회 {question.number}번)")

            tabs_to_process = []
            # Always use narration only for TTS
            if question.narration:
                tabs_to_process.append(('textbook', question.narration))

            for tab, text in tabs_to_process:
                text = text.strip()
                if not text:
                    continue

                # Generate cache filename (MP3 format)
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                round_num = question.exam.round_number
                q_num = question.number
                cache_filename = f"round{round_num}_q{q_num}_narration_{text_hash}.mp3"
                cache_filepath = tts_cache_dir / cache_filename

                # Skip if already cached
                if cache_filepath.exists():
                    self.stdout.write(f"  [{tab}] Skipped (already cached)")
                    skipped += 1
                    continue

                # Limit text length
                if len(text) > 5000:
                    text = text[:5000] + "... 이하 생략"

                try:
                    # Generate TTS
                    self.stdout.write(f"  [{tab}] Generating TTS...")
                    
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
                                    voice_name="Orus"  # Mature, deep male voice
                                )
                            )
                        ),
                    )

                    # Collect audio chunks
                    audio_chunks = []
                    mime_type = None

                    for chunk in client.models.generate_content_stream(
                        model="gemini-2.5-flash-preview-tts",
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
                        self.stdout.write(self.style.WARNING(f"  [{tab}] No audio generated"))
                        errors += 1
                        continue

                    # Combine audio chunks
                    combined_audio = b"".join(audio_chunks)

                    # Convert to WAV first
                    wav_data = self.convert_to_wav(combined_audio, mime_type or "audio/L16;rate=24000")
                    
                    # Save WAV temporarily, then convert to MP3 using ffmpeg
                    import subprocess
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                        tmp_wav.write(wav_data)
                        tmp_wav_path = tmp_wav.name
                    
                    try:
                        # Convert WAV to MP3 using ffmpeg
                        result = subprocess.run(
                            ["ffmpeg", "-y", "-i", tmp_wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", str(cache_filepath)],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode != 0:
                            raise Exception(f"ffmpeg error: {result.stderr}")
                    finally:
                        # Clean up temp WAV file
                        import os
                        if os.path.exists(tmp_wav_path):
                            os.remove(tmp_wav_path)

                    self.stdout.write(self.style.SUCCESS(f"  [{tab}] Saved: {cache_filename}"))
                    generated += 1

                    # Rate limiting - wait between API calls (20s to avoid 429 errors)
                    time.sleep(20)

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  [{tab}] Error: {str(e)}"))
                    errors += 1

        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"Completed!")
        self.stdout.write(f"  Generated: {generated}")
        self.stdout.write(f"  Skipped (cached): {skipped}")
        self.stdout.write(f"  Errors: {errors}")

    def convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Convert raw audio data to WAV format."""
        import struct
        
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
