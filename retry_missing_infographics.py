import os
import django
from django.core.files import File
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question

BASE_DIR = Path(r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data")

targets = [(8, 55), (10, 34), (10, 35)]


def retry_import():
    for round_num, q_num in targets:
        print(f"\nProcessing {round_num}회 {q_num}번...")

        # 1. Find Question
        qs = Question.objects.filter(exam__round_number=round_num, number=q_num)
        if not qs.exists():
            print(f"ERROR: Question object not found in DB!")
            continue
        question = qs.first()
        print(f"Found Question: {question}")

        # 2. Find File
        dir_path = BASE_DIR / f"{round_num}회"
        if not dir_path.exists():
            print(f"ERROR: Directory {dir_path} does not exist!")
            continue

        # Search for any matching file
        found_file = None
        for f in os.listdir(dir_path):
            if f.startswith(f"{round_num}-{q_num}."):  # Check 5-1.png or 5-01.png?
                # Be careful with 55 vs 550, but usually dot follows
                # Let's try flexible matching
                name_part = os.path.splitext(f)[0]
                if name_part == f"{round_num}-{q_num}":
                    found_file = f
                    break

        if not found_file:
            print(f"ERROR: Image file not found in {dir_path} for {round_num}-{q_num}")
            # Try listing close matches
            print("Files in dir that contain the number:")
            for f in os.listdir(dir_path):
                if str(q_num) in f:
                    print(f" - {f}")
            continue

        print(f"Found File: {found_file}")

        # 3. Save
        file_path = dir_path / found_file
        try:
            with open(file_path, "rb") as f:
                question.infographic_image.save(found_file, File(f), save=True)
            print("SUCCESS: Image saved.")
        except Exception as e:
            print(f"ERROR saving image: {e}")


if __name__ == "__main__":
    retry_import()
