"""
Django management command to generate infographic image for a question.
Usage: python manage.py generate_infographic --question_id=ID --prompt="..."
"""
import os
import json
import time
import mimetypes
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from exam.models import Question


class Command(BaseCommand):
    help = 'Generate infographic image for a question using Gemini API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--question_id',
            type=int,
            required=True,
            help='Question ID to generate infographic for',
        )
        parser.add_argument(
            '--prompt',
            type=str,
            help='Prompt for infographic generation (direct)',
        )
        parser.add_argument(
            '--prompt_file',
            type=str,
            help='Path to file containing the prompt (for long prompts)',
        )
        parser.add_argument(
            '--status_file',
            type=str,
            help='Path to status file for tracking progress',
        )

    def handle(self, *args, **options):
        from google import genai
        from google.genai import types

        question_id = options['question_id']
        prompt = options.get('prompt')
        prompt_file = options.get('prompt_file')
        status_file = options.get('status_file')

        # Read prompt from file if provided
        if prompt_file and os.path.exists(prompt_file):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt = f.read()
                # Clean up prompt file after reading
                os.remove(prompt_file)
            except Exception as e:
                self._update_status(status_file, 'error', error=f'프롬프트 파일 읽기 실패: {str(e)}')
                raise CommandError(f'Failed to read prompt file: {e}')

        if not prompt:
            self._update_status(status_file, 'error', error='프롬프트가 제공되지 않았습니다.')
            raise CommandError('No prompt provided. Use --prompt or --prompt_file')

        if not settings.GEMINI_API_KEY:
            self._update_status(status_file, 'error', error='GEMINI_API_KEY is not set')
            raise CommandError('GEMINI_API_KEY is not set')

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            self._update_status(status_file, 'error', error='Question not found')
            raise CommandError(f'Question {question_id} not found')

        round_num = question.exam.round_number
        q_num = question.number

        self.stdout.write(f"Generating infographic for {round_num}회 {q_num}번...")
        self._update_status(status_file, 'processing', message='인포그래픽 생성 중...')

        try:
            # Configure Gemini client
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            model = "gemini-3-pro-image"
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            generate_content_config = types.GenerateContentConfig(
                response_modalities=[
                    "IMAGE",
                    "TEXT",
                ],
                image_config=types.ImageConfig(
                    image_size="1K",
                ),
            )

            # Generate image
            image_data = None
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
                    image_data = part.inline_data.data
                    mime_type = part.inline_data.mime_type
                    break

            if not image_data:
                self._update_status(status_file, 'error', error='이미지 생성에 실패했습니다.')
                raise CommandError('No image data generated')

            # Determine file extension
            file_extension = mimetypes.guess_extension(mime_type) or ".png"

            # Add timestamp to filename
            timestamp = int(time.time())
            filename = f"infographic_{round_num}_{q_num}_{timestamp}{file_extension}"

            # Save to temporary folder
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_infographics')
            os.makedirs(temp_dir, exist_ok=True)
            temp_filepath = os.path.join(temp_dir, filename)

            with open(temp_filepath, 'wb') as f:
                f.write(image_data)

            # Generate URL for temporary file
            temp_url = os.path.join(settings.MEDIA_URL, 'temp_infographics', filename).replace('\\', '/')

            self.stdout.write(self.style.SUCCESS(f"Saved: {filename}"))
            self._update_status(
                status_file,
                'completed',
                message=f'인포그래픽 이미지 생성 완료: {filename}',
                image_url=temp_url,
                temp_filename=filename
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            self._update_status(status_file, 'error', error=str(e))
            raise CommandError(str(e))

    def _update_status(self, status_file, status, **kwargs):
        """Update status file with current progress."""
        if not status_file:
            return

        data = {'status': status, **kwargs}
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            self.stderr.write(f"Failed to update status file: {e}")
