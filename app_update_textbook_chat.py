import os
import django
import pandas as pd
import sys

# 기본서 답변을 업데이트하는 프로그램

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question, Exam, Subject


def update_questions():
    # file_path = r"C:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data_5회_20251225_194854.xlsx"
    # file_path = r"C:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data_6회_20251226_143031.xlsx"
    file_path = r"C:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data_9회_20251227_182616.xlsx"

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    updated_count = 0
    not_found_count = 0
    skipped_count = 0

    print("Starting update process...")

    for index, row in df.iterrows():
        try:
            # Extract data from row
            exam_round = row["Exam"]
            subject_name = row["Subject"]
            question_number = row["Number"]
            textbook_explanation = row["Textbook Explanation"]

            # Check for NaN or empty explanation
            if pd.isna(textbook_explanation) or str(textbook_explanation).strip() == "":
                # print(f"Skipping row {index}: No explanation provided.")
                skipped_count += 1
                continue

            # Find Exam
            try:
                exam = Exam.objects.get(round_number=int(exam_round))
            except Exam.DoesNotExist:
                print(f"Exam not found: Round {exam_round}")
                not_found_count += 1
                continue

            # Find Subject
            try:
                subject = Subject.objects.get(name=subject_name)
            except Subject.DoesNotExist:
                print(f"Subject not found: {subject_name}")
                not_found_count += 1
                continue

            # Find Question
            try:
                question = Question.objects.get(
                    exam=exam, subject=subject, number=int(question_number)
                )
            except Question.DoesNotExist:
                print(
                    f"Question not found: Exam {exam_round}, Subject {subject_name}, No {question_number}"
                )
                not_found_count += 1
                continue

            # Update Question
            question.textbook_chat = textbook_explanation
            question.save()
            updated_count += 1
            # print(f"Updated: Exam {exam_round} - {subject_name} - Q{question_number}")

        except Exception as e:
            print(f"Error processing row {index}: {e}")
            skipped_count += 1

    print("-" * 30)
    print(f"Update Complete.")
    print(f"Updated: {updated_count}")
    print(f"Not Found: {not_found_count}")
    print(f"Skipped (No Content/Error): {skipped_count}")


if __name__ == "__main__":
    update_questions()
