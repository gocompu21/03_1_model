import os
import django

# 1. Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question


def check_missing():
    # Find questions with no infographic
    # Note: ImageField is usually empty string '' if no file, or None
    missing_qs = Question.objects.filter(infographic_image__in=["", None])

    count = missing_qs.count()
    print(f"Total questions without infographic: {count}")

    if count > 0:
        print("\nList of missing questions:")
        for q in missing_qs.order_by("exam__round_number", "number"):
            print(f"- {q.exam.round_number}회 {q.number}번 ({q.subject})")


if __name__ == "__main__":
    check_missing()
