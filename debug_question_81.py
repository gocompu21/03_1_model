import os
import sys
import django

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

def check_question():
    try:
        # Round 5, Question 81
        q = Question.objects.get(exam__round_number=5, number=81)
        
        with open('debug_q81_content.txt', 'w', encoding='utf-8') as f:
            f.write(f"Question ID: {q.id}\n")
            f.write(f"Content: {q.content}\n")
            f.write("-" * 20 + "\n")
            f.write("Textbook Chat:\n")
            f.write(q.textbook_chat or "None")
            f.write("\n" + "-" * 20 + "\n")
            f.write("General Chat:\n")
            f.write(q.general_chat or "None")
            f.write("\n" + "-" * 20 + "\n")
            
    except Question.DoesNotExist:
        print("Question not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_question()
