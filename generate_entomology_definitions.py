import os
import sys
import time
import django
from tqdm import tqdm

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from glossary.models import Subject, Term
try:
    from fileSearchStore import GeminiStoreManager
except ImportError:
    print("fileSearchStore 모듈을 찾을 수 없습니다.")
    sys.exit(1)

def generate_definitions():
    # 1. 수목해충학 과목 확인
    try:
        subject = Subject.objects.get(name__contains='수목해충학')
        print(f"대상 과목: {subject.name}")
    except Subject.DoesNotExist:
        print("오류: '수목해충학' 과목을 찾을 수 없습니다.")
        return

    # 2. 정의가 없는 용어 조회
    terms = Term.objects.filter(subjects=subject).filter(content__exact='')
    total_count = terms.count()
    print(f"정의 생성 대상 용어: {total_count}개")
    
    if total_count == 0:
        print("모든 용어에 정의가 존재합니다.")
        return

    # 3. Gemini Manager 초기화
    api_key = settings.GEMINI_API_KEY
    manager = GeminiStoreManager(api_key=api_key)
    target_store = "수목해충학"
    
    # 스토어 확인 및 동기화
    if target_store not in manager.stores or not manager.stores[target_store]:
        print(f"'{target_store}' 스토어 동기화 중...")
        manager.sync_all_stores()
        
    if target_store not in manager.stores:
        print(f"경고: '{target_store}' 스토어를 찾을 수 없습니다. (PDF 업로드 필요)")
        # 진행 여부 확인? 일단 진행 시도

    # 4. 정의 생성 루프
    success_count = 0
    error_count = 0
    
    print("=" * 50)
    print("용어 정의 생성 시작 (Ctrl+C로 중단 가능)")
    print("=" * 50)

    try:
        for i, term in enumerate(tqdm(terms)):
            word = term.word
            prompt = f"'{word}'에 대해 수목해충학 관점에서 서술형으로 설명해주세요."
            
            try:
                # 쿼리 실행
                definition = manager.query_store(target_store, prompt)
                
                # 결과 검증
                if not definition or "Error" in definition or "찾을 수 없습니다" in definition:
                    # 실패 시 로그만 남기고 넘어감 (유효하지 않은 용어일 수 있음)
                    print(f"\n[SKIP] '{word}': 결과 없음 또는 에러")
                    error_count += 1
                else:
                    # 저장
                    term.content = definition
                    term.save()
                    success_count += 1
                    # 내용 출력
                    print(f"\n[{i+1}/{total_count}] '{word}':")
                    print("-" * 40)
                    print(definition[:500] if len(definition) > 500 else definition)
                    print("-" * 40)
                    
            except Exception as e:
                print(f"\n[ERROR] '{word}': {e}")
                error_count += 1
            
            # Rate limiting (60초 대기)
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    
    print("\n" + "=" * 50)
    print("작업 완료")
    print(f"성공: {success_count}개")
    print(f"실패/스킵: {error_count}개")
    print("=" * 50)

if __name__ == "__main__":
    generate_definitions()
