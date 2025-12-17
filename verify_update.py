import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question


def verify():
    # Check a few random questions that should have been updated
    # Assuming the Excel contained data for Exam 5
    questions = Question.objects.filter(
        exam__round_number=5, textbook_chat__isnull=False
    ).exclude(textbook_chat="")

    print(f"Total questions with textbook_chat for Exam 5: {questions.count()}")

    if questions.exists():
        q = questions.first()
        print(f"Sample: {q}")
        print(f"Textbook Chat (first 50 chars): {q.textbook_chat[:50]}...")
    else:
        print("No questions found with updated textbook_chat for Exam 5.")


if __name__ == "__main__":
    verify()
