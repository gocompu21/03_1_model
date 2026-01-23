import os
import sys
import time
import django
import re
from tqdm import tqdm

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db.models import Q
from exam.models import Question, Subject
from glossary.models import Subject as GlossarySubject, Term

# fileSearchStore import
try:
    from fileSearchStore import GeminiStoreManager
except ImportError:
    print("fileSearchStore 모듈을 찾을 수 없습니다.")
    sys.exit(1)

def extract_and_generate_glossary():
    # 1. 수목해충학 과목 찾기
    try:
        exam_subject = Subject.objects.get(name__contains='수목해충학')
        glossary_subject, _ = GlossarySubject.objects.get_or_create(name='수목해충학')
        print(f"대상 과목: {exam_subject.name} (ID: {exam_subject.id})")
    except Subject.DoesNotExist:
        print("오류: '수목해충학' 과목을 찾을 수 없습니다.")
        return

    # 2. 관련 문제 수집
    questions = Question.objects.filter(subject=exam_subject)
    print(f"분석할 문제 수: {questions.count()}개")
    
    # 3. Gemini Manager 초기화
    api_key = settings.GEMINI_API_KEY
    manager = GeminiStoreManager(api_key=api_key)
    target_store = "수목해충학" # 텍스트북 스토어 이름

    # 4. 키워드 추출 (배치 처리)
    batch_size = 5
    all_keywords = set()
    
    # 기존 용어 제외
    existing_terms = set(Term.objects.values_list('word', flat=True))
    
    questions_list = list(questions)
    for i in tqdm(range(0, len(questions_list), batch_size), desc="키워드 추출 중"):
        batch = questions_list[i:i+batch_size]
        text_content = ""
        for q in batch:
            text_content += f"[문제] {q.content}\n"
            text_content += f"[보기] {q.choice1}, {q.choice2}, {q.choice3}, {q.choice4}, {q.choice5}\n\n"
        
        prompt = f"""
        다음은 수목해충학 기출문제 텍스트입니다. 
        이 텍스트에서 '수목해충학 용어사전'에 등재할 만한 중요한 전문 용어나 해충명, 개념을 추출해주세요.
        
        조건:
        1. 단순한 일반 명사는 제외하세요.
        2. 중복을 제거하고 쉼표(,)로 구분하여 나열하세요.
        3. 한국어 용어 위주로 추출하세요.
        
        텍스트:
        {text_content}
        """
        
        try:
            response = manager.query_store(target_store, prompt) # Use RAG to verify context if possible, or just plain generation
            # Note: query_store uses RAG. For simple extraction, plain generation might be cheaper but context helps specificity.
            # Let's verify store existence first.
            if target_store not in manager.stores or not manager.stores[target_store]:
                 # Fallback to no-store generation if store not ready, but usually we want textbook context
                 pass 

            # Parse keywords
            keywords = [k.strip() for k in response.split(',') if k.strip()]
            for k in keywords:
                # Basic cleaning
                k = re.sub(r'^\d+\.\s*', '', k) # Remove numbering
                k = re.sub(r'\s*\(.*?\)', '', k) # Remove contents in parenthesis
                
                if len(k) < 2: continue
                if k in existing_terms: continue
                
                all_keywords.add(k)
                
            time.sleep(2) # Rate limit
            
        except Exception as e:
            print(f"Error processing batch {i}: {e}")
            continue

    print(f"추출된 신규 키워드 후보: {len(all_keywords)}개")
    
    # 5. 용어 저장 (정의 생성 생략)
    success_count = 0
    
    for word in tqdm(list(all_keywords), desc="용어 저장 중"):
        try:
            # Check duplication again
            if Term.objects.filter(word=word).exists():
                continue
                
            # 정의는 나중에 생성하기 위해 빈 문자열로 저장
            term = Term.objects.create(
                word=word,
                content="" 
            )
            term.subjects.add(glossary_subject)
            success_count += 1
            
        except Exception as e:
            print(f"  -> 용어 저장 실패 ({word}): {e}")
            
    print(f"완료! 총 {success_count}개 용어 등록됨.")

if __name__ == "__main__":
    extract_and_generate_glossary()
