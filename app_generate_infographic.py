"""
Batch Infographic Image Generator
Generates infographic images for exam questions using Gemini API.
"""
import os
import sys
import re
import time
import mimetypes
import django

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.core.files.base import ContentFile
from exam.models import Question
from google import genai
from google.genai import types


def clean_html_for_prompt(html):
    """Convert HTML to clean text for prompt."""
    if not html:
        return ''
    
    text = html
    # <br> → newline
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # <div ...> remove
    text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)
    # </div> → newline
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    # <i>, <em>, <b>, <strong> → keep text only
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    # Remove duplicate newlines
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()


def build_infographic_prompt(question):
    """Build infographic prompt for a question."""
    subject = question.subject.name
    round_num = question.exam.round_number
    q_num = question.number
    
    # Clean HTML from content and choices
    content = clean_html_for_prompt(question.content)
    choice1 = clean_html_for_prompt(question.choice1)
    choice2 = clean_html_for_prompt(question.choice2)
    choice3 = clean_html_for_prompt(question.choice3)
    choice4 = clean_html_for_prompt(question.choice4)
    choice5 = clean_html_for_prompt(question.choice5)
    
    # Use textbook_chat as explanation (or general_chat if not available)
    explanation = question.textbook_chat or question.general_chat or ""
    
    prompt = f"""({subject}) {round_num}-{q_num}. {content}
① {choice1}
② {choice2}
③ {choice3}
④ {choice4}
⑤ {choice5}

{explanation}

위 내용으로 인포그래픽을 만들어 줘
요구사항：
１） １６：９ 비율
２） 한국어 텍스트 포함
３） 전문적이고 교육적인 스타일
４） 나무 병해 관련 시각 요소
５） 최상단칸은 "({subject}) {round_num}-{q_num}. {content}" 왼쪽 정렬해"""
    
    return prompt


def generate_infographic(question, client):
    """Generate infographic image for a question using Gemini API."""
    prompt = build_infographic_prompt(question)
    
    model = "gemini-3-pro-image-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(image_size="1K"),
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
    
    return image_data, mime_type


def main():
    # Configuration - Change these values as needed
    round_number = 9           # 회차 번호
    start_number = 1         # 시작 문제 번호
    end_number = 125           # 끝 문제 번호 (포함)
    
    print(f"=== 인포그래픽 이미지 배치 생성 ===")
    print(f"대상: {round_number}회차 {start_number}번 ~ {end_number}번")
    print()
    
    # Initialize Gemini client
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Get questions for the round within range
    questions = Question.objects.filter(
        exam__round_number=round_number,
        number__gte=start_number,
        number__lte=end_number
    ).order_by('number')
    total = questions.count()
    
    print(f"총 {total}개 문제 발견")
    print("-" * 50)
    
    success_count = 0
    fail_count = 0
    
    for i, question in enumerate(questions, 1):
        print(f"[{i}/{total}] {round_number}회 {question.number}번 처리 중...", end=" ")
        
        try:
            # Generate infographic
            image_data, mime_type = generate_infographic(question, client)
            
            if not image_data:
                print("❌ 이미지 생성 실패")
                fail_count += 1
                continue
            
            # Determine file extension
            file_extension = mimetypes.guess_extension(mime_type) or ".png"
            filename = f"infographic_{round_number}_{question.number}{file_extension}"
            
            # Delete existing image if exists
            if question.infographic_image:
                question.infographic_image.delete(save=False)
            
            # Save new image
            question.infographic_image.save(
                filename,
                ContentFile(image_data),
                save=True
            )
            
            print(f"✅ {filename}")
            success_count += 1
            
            # Rate limiting - wait between requests
            time.sleep(2)
            
        except Exception as e:
            import traceback
            print(f"❌ 오류: {e}")
            traceback.print_exc()
            fail_count += 1
            time.sleep(5)  # Wait longer on error
    
    print("-" * 50)
    print(f"완료! 성공: {success_count}, 실패: {fail_count}")


if __name__ == "__main__":
    main()
