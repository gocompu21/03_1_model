import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Subject


def setup_subjects():
    subjects = [
        {"name": "수목병리학", "code": 1},
        {"name": "수목해충학", "code": 2},
        {"name": "수목생리학", "code": 3},
        {"name": "산림토양학", "code": 4},
        {"name": "수목관리학", "code": 5},
    ]

    for data in subjects:
        subject, created = Subject.objects.get_or_create(
            code=data["code"], defaults={"name": data["name"]}
        )
        if created:
            print(f"Created: {subject}")
        else:
            print(f"Already exists: {subject}")


if __name__ == "__main__":
    setup_subjects()
