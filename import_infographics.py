import os
import django
from django.core.files import File
from pathlib import Path

# 1. Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Exam, Question

# 2. Base Directory
BASE_DIR = Path(r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data")


def import_infographics():
    if not BASE_DIR.exists():
        print(f"Error: Directory not found at {BASE_DIR}")
        return

    print("Scanning for infographic images...")

    success_count = 0
    error_count = 0
    skip_count = 0

    # Walk through directory
    for root, dirs, files in os.walk(BASE_DIR):
        for filename in files:
            # Check extension
            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            # Parse filename: e.g., "5-01.png" -> round 5, number 1
            try:
                name_part = os.path.splitext(filename)[0]  # "5-01"
                if "-" not in name_part:
                    continue

                parts = name_part.split("-")
                if len(parts) < 2:
                    continue

                round_str = parts[0]  # "5"
                num_str = parts[1]  # "01" or "100"

                round_num = int(round_str)
                question_num = int(num_str)

                # Find Question
                try:
                    # Filter by exam round and question number
                    # We need to find the exam first to be safe, or direct query
                    questions = Question.objects.filter(
                        exam__round_number=round_num, number=question_num
                    )

                    if not questions.exists():
                        print(
                            f"Skipping {filename}: Question {round_num}회 {question_num}번 not found in DB."
                        )
                        skip_count += 1
                        continue

                    question = questions.first()

                    # Save Image
                    file_path = os.path.join(root, filename)
                    with open(file_path, "rb") as f:
                        # Save method: name, content, save=True
                        # We use the original filename
                        question.infographic_image.save(filename, File(f), save=True)
                        print(f"Imported: {filename} -> {question}")
                        success_count += 1

                except Exception as db_err:
                    print(f"Error saving {filename}: {db_err}")
                    error_count += 1

            except ValueError:
                # Not a round-number format, skip silently or log
                # print(f"Skipping file with invalid format: {filename}")
                continue

    print("-" * 30)
    print("Import Completed!")
    print(f"Success: {success_count}")
    print(f"Skipped: {skip_count} (Question not found)")
    print(f"Errors: {error_count}")


if __name__ == "__main__":
    import_infographics()
