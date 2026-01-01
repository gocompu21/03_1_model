"""Generate infographics for specific questions."""
import os
import sys
import re
import time
import mimetypes
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.core.files.base import ContentFile
from exam.models import Question
from google import genai
from google.genai import types


def clean_html_for_prompt(html):
    if not html:
        return ''
    text = html
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()


def build_infographic_prompt(question):
    subject = question.subject.name
    round_num = question.exam.round_number
    q_num = question.number
    
    content = clean_html_for_prompt(question.content)
    choice1 = clean_html_for_prompt(question.choice1)
    choice2 = clean_html_for_prompt(question.choice2)
    choice3 = clean_html_for_prompt(question.choice3)
    choice4 = clean_html_for_prompt(question.choice4)
    choice5 = clean_html_for_prompt(question.choice5)
    
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
    prompt = build_infographic_prompt(question)
    
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(image_size="1K"),
    )
    
    for chunk in client.models.generate_content_stream(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=config,
    ):
        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data, part.inline_data.mime_type
    return None, None


def main():
    # Specific questions to generate
    questions_to_generate = [
        (9, 125),
    ]
    
    print(f"=== 인포그래픽 생성 ===")
    print(f"대상: {questions_to_generate}")
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    success = 0
    fail = 0
    
    for round_num, q_num in questions_to_generate:
        print(f"\n{round_num}회 {q_num}번 처리 중...", end=" ")
        
        question = Question.objects.filter(exam__round_number=round_num, number=q_num).first()
        if not question:
            print("❌ 문제 없음")
            fail += 1
            continue
        
        try:
            image_data, mime_type = generate_infographic(question, client)
            
            if not image_data:
                print("❌ 이미지 생성 실패")
                fail += 1
                continue
            
            file_ext = mimetypes.guess_extension(mime_type) or ".png"
            filename = f"infographic_{round_num}_{q_num}{file_ext}"
            
            if question.infographic_image:
                question.infographic_image.delete(save=False)
            
            question.infographic_image.save(filename, ContentFile(image_data), save=True)
            print(f"✅ {filename}")
            success += 1
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            fail += 1
            time.sleep(5)
    
    print(f"\n완료! 성공: {success}, 실패: {fail}")


if __name__ == "__main__":
    main()
