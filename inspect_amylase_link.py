import os
import sys
import django

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

def check_amylase_link():
    try:
        # 10회 60번 문제 조회
        q = Question.objects.get(exam__round_number=10, number=60)
        
        term = "amylase"
        found_in = []
        
        # 검색 대상 확인할 텍스트들
        fields = {
            'content': q.content,
            'choice1': q.choice1,
            'choice2': q.choice2,
            'choice3': q.choice3,
            'choice4': q.choice4,
            'choice5': q.choice5,
            'general_chat': q.general_chat, # 해설
        }
        
        print(f"=== [10회 60번] 문제 분석 (검색어: {term}) ===")
        print(f"문제 지문: {q.content}")
        print("-" * 20)
        
        for field, text in fields.items():
            if text and term in text: # 대소문자 구분 없이 하려면 .lower() 사용했어야 하는데, 링크 스크립트는 그냥 in 사용함.
                found_in.append(field)
                print(f"✅ Found in '{field}':")
                print(f"   -> {text}")
                print("-" * 20)
                
        if not found_in:
            print(f"❌ '{term}' not found in specific fields. (Maybe case sensitivity issue?)")
            
    except Question.DoesNotExist:
        print("Question 10-60 not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_amylase_link()
