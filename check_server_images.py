
import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question
from django.conf import settings

def check_images(round_num=11):
    print(f"=== {round_num}회차 이미지 상태 점검 ===")
    print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print("-" * 50)

    questions = Question.objects.filter(exam__round_number=round_num).order_by('number')
    if not questions.exists():
        print(f"{round_num}회차 문제가 없습니다.")
        return

    count_info = 0
    count_missing = 0
    
    for q in questions:
        # Check Infographic
        if q.infographic_image:
            # DB says file exists
            file_path = q.infographic_image.path
            file_url = q.infographic_image.url
            
            exists = os.path.exists(file_path)
            status = "✅ 존재함" if exists else "❌ 파일 없음"
            
            if exists:
                # Check permissions
                try:
                    mode = os.stat(file_path).st_mode
                    perm = oct(mode)[-3:]
                    uid = os.stat(file_path).st_uid
                    gid = os.stat(file_path).st_gid
                except:
                    perm = "???"
                    uid = "?"
                    gid = "?"
                status += f" (권한: {perm}, User: {uid}, Group: {gid})"
            else:
                count_missing += 1
                
            print(f"[Q{q.number}] DB: {q.infographic_image.name} -> {status}")
            count_info += 1
        else:
            # print(f"[Q{q.number}] 이미지 없음") # Too verbose
            pass

    print("-" * 50)
    print(f"총 문제 수: {questions.count()}")
    print(f"인포그래픽 DB 등록됨: {count_info}")
    print(f"실제 파일 유실됨: {count_missing}")
    
    # Check directory permissions
    dir_path = os.path.join(settings.MEDIA_ROOT, 'questions', 'explanations')
    if os.path.exists(dir_path):
        mode = os.stat(dir_path).st_mode
        print(f"\n디렉토리 권한 ({dir_path}): {oct(mode)[-3:]}")
    else:
        print(f"\n디렉토리 없음: {dir_path}")

if __name__ == "__main__":
    check_images()
