import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Subject, Exam


def initialize_data():
    # Subjects
    subjects = [
        (1, "수목병리학"),
        (2, "수목해충학"),
        (3, "수목생리학"),
        (4, "산림토양학"),
        (5, "수목관리학"),
    ]

    print("Initializing Subjects...")
    for code, name in subjects:
        subject, created = Subject.objects.get_or_create(
            code=code, defaults={"name": name}
        )
        if created:
            print(f"Created subject: {name}")
        else:
            print(f"Subject already exists: {name}")

    # Exams (5th to 11th)
    print("\nInitializing Exams...")
    for round_num in range(5, 12):
        exam, created = Exam.objects.get_or_create(round_number=round_num)
        if created:
            print(f"Created exam: {round_num}회")
        else:
            print(f"Exam already exists: {round_num}회")


if __name__ == "__main__":
    initialize_data()
