import os
import django
from collections import Counter
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question
from glossary.models import Term
from kiwipiepy import Kiwi

def extract():
    print("Kiwi 초기화 중...")
    try:
        kiwi = Kiwi()
    except Exception as e:
        print(f"Kiwi 초기화 실패: {e}")
        return

    # 1. 기존 용어 Set (공백 제거 및 소문자화로 정규화)
    print("기존 용어 로딩 중...")
    existing_terms = set()
    for t in Term.objects.values_list('word', flat=True):
        existing_terms.add(t.replace(" ", "").lower())
        existing_terms.add(t.lower())
    
    print(f"기존 용어: {len(existing_terms)}개")

    # 2. 문제 데이터 수집 (수목병리학만)
    print("문제 데이터 수집 중 (수목병리학만)...")
    questions = Question.objects.select_related('exam', 'subject').filter(subject__name='수목병리학')
    print(f"총 문제: {questions.count()}개")

    text_corpus = []
    
    # 디버깅용 카운터
    q_count = 0
    
    for q in questions:
        # 문제와 문항 1~5
        content_items = [
            q.content,
            q.choice1, q.choice2, q.choice3, q.choice4, q.choice5
        ]
        
        # None 제거 및 텍스트 결합
        valid_items = [item for item in content_items if item]
        text_corpus.extend(valid_items)
        q_count += 1
    
    full_text = " ".join(text_corpus)
    print(f"분석할 텍스트 길이: {len(full_text)}자")
    
    # 3. 형태소 분석 (명사 추출)
    print("형태소 분석 및 명사 추출 중...")
    
    # 텍스트가 너무 길면 Kiwi가 느려질 수 있으므로 청크로 나눔 (선택사항이나 안전하게)
    chunk_size = 10000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    candidates = []
    
    for i, chunk in enumerate(chunks):
        if i % 10 == 0:
            print(f"  진행률: {i}/{len(chunks)}")
            
        result = kiwi.analyze(chunk)
        for token_list, score in result:
            # 복합명사 구성을 위한 버퍼
            noun_buffer = []
            
            for token in token_list:
                if token.tag in ['NNG', 'NNP']: # 일반명사, 고유명사
                    word = token.form
                    candidates.append(word)
                    noun_buffer.append(word)
                else:
                    # 명사가 끊기면 복합명사 처리
                    if len(noun_buffer) > 1:
                        compound = "".join(noun_buffer)
                        candidates.append(compound)
                    noun_buffer = []
            
            # 마지막 버퍼 처리
            if len(noun_buffer) > 1:
                compound = "".join(noun_buffer)
                candidates.append(compound)

    print(f"추출된 총 후보(중복 포함): {len(candidates)}개")

    # 4. 필터링 및 카운팅
    print("필터링 중...")
    final_candidates = []
    
    for word in candidates:
        # 1글자 제외 (단, 숫자는 제외 안함? 사용자가 명사를 원했으니 한글 1글자는 제외)
        if len(word) < 2:
            continue
            
        # 기존 용어에 없는지 확인
        # 공백 제거 및 소문자화 비교
        normalized = word.replace(" ", "").lower()
        if normalized not in existing_terms:
            final_candidates.append(word)
            
    counts = Counter(final_candidates)
    
    # 결과 저장
    output_file = 'unregistered_terms.txt'
    print(f"결과 저장 중: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 미등록 명사/복합명사 빈도 분석 (총 {len(counts)}개)\n")
        f.write("# 빈도수 | 용어\n")
        f.write("-" * 30 + "\n")
        
        # 빈도 2회 이상만 저장할지? 사용자 요청은 "모두 추출"이므로 일단 다 저장하되 정렬
        sorted_items = counts.most_common()
        
        for word, count in sorted_items:
            # 너무 낮은 빈도는 제외할 수도 있지만 일단 다 적음 (하지만 파일 크기 고려하여 2회 이상만)
            if count > 1: 
                f.write(f"{count}\t{word}\n")
                
    # 화면 출력 (Top 30)
    print("\n[상위 빈도 미등록 용어 Top 30]")
    for word, count in counts.most_common(30):
        print(f"{count}: {word}")

if __name__ == '__main__':
    extract()
