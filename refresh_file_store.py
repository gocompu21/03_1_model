"""
Gemini File Store 새로고침 프로그램
- 기존 파일 삭제 후 data/FileStore의 파일을 재업로드
- 48시간 TTL 만료 전에 주기적으로 실행

사용법:
    python refresh_file_store.py             # 전체 스토어 새로고침
    python refresh_file_store.py --list      # 현재 파일 상태 조회
    python refresh_file_store.py --store 수목해충학  # 특정 스토어만 새로고침
"""
import os
import sys
import time
import argparse
from pathlib import Path

# Django 환경 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
import google.generativeai as genai

# 스토어 정의 (스토어명: 파일 경로 리스트)
FILESTORE_BASE = Path(__file__).parent / "data" / "FileStore"

STORES = {
    "수목해충학": [FILESTORE_BASE / "수목해충학"],
    "수목병리학": [FILESTORE_BASE / "수목병리학"],
    "수목관리학": [FILESTORE_BASE / "수목관리학"],
    "산림토양학": [FILESTORE_BASE / "산림토양학"],
    "수목생리학": [FILESTORE_BASE / "수목생리학"],
}

# local_stores.json 경로
STORES_FILE = Path(__file__).parent / "local_stores.json"


def init_genai():
    """Gemini API 초기화"""
    if not settings.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)
    genai.configure(api_key=settings.GEMINI_API_KEY)


def list_cloud_files():
    """클라우드의 모든 파일 목록 조회"""
    print("\n=== 클라우드 파일 목록 ===")
    files = list(genai.list_files())
    
    if not files:
        print("  (파일 없음)")
        return []
    
    for f in files:
        expiry = f.expiration_time.strftime("%Y-%m-%d %H:%M") if f.expiration_time else "N/A"
        print(f"  - {f.display_name or f.name}")
        print(f"    상태: {f.state.name} | 만료: {expiry}")
        print(f"    URI: {f.uri}")
    
    return files


def delete_all_files():
    """클라우드의 모든 파일 삭제"""
    print("\n=== 클라우드 파일 삭제 중 ===")
    files = list(genai.list_files())
    
    if not files:
        print("  삭제할 파일이 없습니다.")
        return
    
    for f in files:
        try:
            genai.delete_file(f.name)
            print(f"  ✓ 삭제: {f.display_name or f.name}")
        except Exception as e:
            print(f"  ✗ 삭제 실패 ({f.name}): {e}")
    
    print(f"  총 {len(files)}개 파일 삭제 완료")


def upload_store_files(store_name, store_dirs):
    """특정 스토어의 파일 업로드"""
    print(f"\n=== [{store_name}] 파일 업로드 중 ===")
    
    uploaded_files = []
    
    for store_dir in store_dirs:
        if not store_dir.exists():
            print(f"  ✗ 디렉토리 없음: {store_dir}")
            continue
        
        # 디렉토리 내 모든 파일 업로드
        for file_path in store_dir.iterdir():
            if file_path.is_file():
                try:
                    print(f"  업로드 중: {file_path.name}...")
                    
                    # MIME 타입 결정
                    suffix = file_path.suffix.lower()
                    mime_types = {
                        '.txt': 'text/plain',
                        '.pdf': 'application/pdf',
                        '.md': 'text/markdown',
                    }
                    mime_type = mime_types.get(suffix, 'application/octet-stream')
                    
                    # 파일 업로드
                    uploaded = genai.upload_file(
                        path=str(file_path),
                        display_name=f"{store_name}_{file_path.name}",
                        mime_type=mime_type
                    )
                    
                    # 업로드 완료 대기
                    while uploaded.state.name == "PROCESSING":
                        print("    처리 중...")
                        time.sleep(2)
                        uploaded = genai.get_file(uploaded.name)
                    
                    if uploaded.state.name == "ACTIVE":
                        print(f"  ✓ 완료: {file_path.name} -> {uploaded.name}")
                        uploaded_files.append(uploaded.name)
                    else:
                        print(f"  ✗ 업로드 실패: {file_path.name} (상태: {uploaded.state.name})")
                    
                except Exception as e:
                    print(f"  ✗ 에러: {file_path.name} - {e}")
    
    return uploaded_files


def update_local_stores(stores_data):
    """local_stores.json 업데이트"""
    import json
    
    with open(STORES_FILE, "w", encoding="utf-8") as f:
        json.dump(stores_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ local_stores.json 업데이트 완료")


def refresh_all_stores():
    """전체 스토어 새로고침"""
    print("=" * 50)
    print("Gemini File Store 새로고침")
    print("=" * 50)
    
    # 1. 기존 파일 모두 삭제
    delete_all_files()
    
    # 2. 각 스토어별 파일 업로드
    all_stores_data = {}
    
    for store_name, store_dirs in STORES.items():
        uploaded_files = upload_store_files(store_name, store_dirs)
        all_stores_data[store_name] = uploaded_files
        time.sleep(1)  # API rate limiting
    
    # 3. local_stores.json 업데이트
    update_local_stores(all_stores_data)
    
    # 4. 결과 출력
    print("\n" + "=" * 50)
    print("새로고침 완료!")
    print("=" * 50)
    print("\n업로드 결과:")
    for store_name, files in all_stores_data.items():
        print(f"  {store_name}: {len(files)}개 파일")
    
    print(f"\n다음 새로고침: 48시간 이내 (TTL 만료 전)")


def refresh_single_store(store_name):
    """특정 스토어만 새로고침"""
    if store_name not in STORES:
        print(f"Error: '{store_name}' 스토어를 찾을 수 없습니다.")
        print(f"사용 가능한 스토어: {list(STORES.keys())}")
        return
    
    print(f"=== [{store_name}] 스토어 새로고침 ===")
    
    # 기존 파일 중 해당 스토어 파일만 삭제
    files = list(genai.list_files())
    for f in files:
        if f.display_name and store_name in f.display_name:
            try:
                genai.delete_file(f.name)
                print(f"  ✓ 삭제: {f.display_name}")
            except Exception as e:
                print(f"  ✗ 삭제 실패: {e}")
    
    # 새 파일 업로드
    uploaded_files = upload_store_files(store_name, STORES[store_name])
    
    # local_stores.json 업데이트
    import json
    if STORES_FILE.exists():
        with open(STORES_FILE, "r", encoding="utf-8") as f:
            stores_data = json.load(f)
    else:
        stores_data = {}
    
    stores_data[store_name] = uploaded_files
    update_local_stores(stores_data)
    
    print(f"\n✓ [{store_name}] 새로고침 완료: {len(uploaded_files)}개 파일")


def main():
    parser = argparse.ArgumentParser(description="Gemini File Store 새로고침")
    parser.add_argument("--list", action="store_true", help="현재 파일 목록 조회")
    parser.add_argument("--store", type=str, help="특정 스토어만 새로고침")
    parser.add_argument("--delete-all", action="store_true", help="모든 파일 삭제만 수행")
    
    args = parser.parse_args()
    
    init_genai()
    
    if args.list:
        list_cloud_files()
    elif args.delete_all:
        delete_all_files()
    elif args.store:
        refresh_single_store(args.store)
    else:
        refresh_all_stores()


if __name__ == "__main__":
    main()
