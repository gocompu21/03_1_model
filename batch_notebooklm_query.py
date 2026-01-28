"""
NotebookLM CLI를 활용한 수목생리학 용어 설명 일괄 생성 스크립트
notebooklm ask 명령어를 반복 호출하여 용어별 설명을 수집합니다.

사용법:
    python batch_notebooklm_query.py --auto

사전 준비:
    1. notebooklm login (인증 완료 상태)
    2. notebooklm list 로 노트북 ID 확인
"""
import os
import sys
import json
import time
import subprocess
import django

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

# 설정
NOTEBOOK_ID = "d014605b"  # 수목생리학 노트북 ID (앞 8자리)
OUTPUT_FILE = "notebooklm_explanations.json"
DELAY_SECONDS = 10  # API 호출 간격 (너무 빠르면 차단될 수 있음)

def query_notebooklm(question: str, notebook_id: str) -> str:
    """NotebookLM CLI를 호출하여 질문에 대한 답변을 받습니다."""
    # venv 내의 notebooklm 실행 파일 경로
    notebooklm_path = os.path.join(os.path.dirname(sys.executable), "notebooklm.exe")
    
    # UTF-8 인코딩 강제
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        result = subprocess.run(
            [notebooklm_path, "ask", question, "--notebook", notebook_id],
            capture_output=True,
            env=env,
            timeout=60  # 60초 타임아웃
        )
        
        # Windows에서 인코딩 문제 해결: bytes로 받아서 여러 인코딩 시도
        try:
            output = result.stdout.decode('utf-8', errors='replace')
            err_output = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
        except:
            output = result.stdout.decode('cp949', errors='replace')
            err_output = result.stderr.decode('cp949', errors='replace') if result.stderr else ""
        
        full_output = output + err_output
        
        # "Answer:" 이후의 내용 추출
        if "Answer:" in output:
            answer_start = output.find("Answer:")
            answer = output[answer_start + len("Answer:"):].strip()
            # 마지막 줄 (turn 정보) 제거
            lines = answer.split('\n')
            clean_lines = [l for l in lines if not l.strip().startswith('(venv)') and 'turn' not in l]
            return '\n'.join(clean_lines).strip()
        else:
            return f"Error: {output[:200]}"
            
    except subprocess.TimeoutExpired:
        return "Error: Timeout"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("=== NotebookLM CLI 기반 수목생리학 용어 설명 생성 ===")
    
    target_subject_name = "수목생리학"
    
    # 과목 확인
    try:
        subject = Subject.objects.get(name=target_subject_name)
    except Subject.DoesNotExist:
        print(f"Error: Subject '{target_subject_name}' not found.")
        return

    # DB에서 필요한 데이터 로드 (빠르게)
    # 한글로 시작하는 용어만 필터링
    print(">>> DB에서 대상 용어 목록을 가져오는 중 (한글 용어 우선)...")
    terms_qs = Term.objects.filter(
        subjects=subject, 
        content__exact='',
        word__regex=r'^[가-힣]'  # 한글로 시작하는 용어만
    ).values('id', 'word').order_by('word')
    term_list = list(terms_qs)
    
    # DB 연결 해제
    django.db.connections.close_all()
    print(">>> DB 연결 해제됨.")
    
    total = len(term_list)
    print(f"'{target_subject_name}' 과목의 설명 없는 용어: {total}개")
    
    if total == 0:
        print("업데이트할 용어가 없습니다.")
        return

    # 사용자 확인
    if '--auto' in sys.argv:
        print("⚡ 자동 모드")
    else:
        confirm = input(f"{total}개 용어에 대해 NotebookLM 설명을 생성하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            return

    # 결과 저장용
    results = []
    processed_words = set()
    
    # 기존 파일 로드
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
            processed_words = set(item['word'] for item in results)
            print(f"📂 기존 파일 로드됨: {len(results)}개 항목")
        except:
            pass

    count_success = 0
    count_fail = 0

    print(f"🔗 NotebookLM 노트북 ID: {NOTEBOOK_ID}")
    print("=" * 50)

    for idx, term_data in enumerate(term_list, 1):
        term_id = term_data['id']
        term_word = term_data['word']
        
        if term_word in processed_words:
            print(f"[{idx}/{total}] 이미 처리됨: {term_word}")
            continue

        question = f"'{term_word}'에 대해 수목생리학 관점에서 자세히 설명해줘."
        print(f"[{idx}/{total}] 조회 중: {term_word}")
        
        try:
            response = query_notebooklm(question, NOTEBOOK_ID)
            
            if not response.startswith("Error"):
                result_item = {
                    'term_id': term_id,
                    'word': term_word,
                    'content': response + "\n\n---\n### NotebookLM (수목생리학)"
                }
                results.append(result_item)
                processed_words.add(term_word)
                
                # 중간 저장
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                
                count_success += 1
                print(f"  -> ✅ 저장 완료 ({len(response)}자)")
            else:
                count_fail += 1
                print(f"  -> ❌ {response[:80]}")
                
        except KeyboardInterrupt:
            print("\n⛔ 작업 중단됨")
            break
        except Exception as e:
            count_fail += 1
            print(f"  -> ❌ 예외: {e}")
        
        # API 호출 간격
        print(f"  -> {DELAY_SECONDS}초 대기...")
        time.sleep(DELAY_SECONDS)

    print("=" * 50)
    print(f"완료. 성공: {count_success}, 실패: {count_fail}")
    print(f"결과 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
