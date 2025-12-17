import os
import django
import pandas as pd

# 1. Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Exam, Subject, Question

# 2. File Path
FILE_PATH = r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data\전체데이터_5회_11회_전체해설_인포그래픽추가본.xlsx"


def import_questions():
    if not os.path.exists(FILE_PATH):
        print(f"Error: File not found at {FILE_PATH}")
        return

    print("Loading Excel file...")
    try:
        df = pd.read_excel(FILE_PATH)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # Check required columns
    required_cols = [
        "회차",
        "문제번호",
        "과목",
        "문제",
        "①",
        "②",
        "③",
        "④",
        "⑤",
        "정답",
        "해설",
    ]
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing column '{col}' in Excel file.")
            return

    # 3. Iterate and Save
    success_count = 0
    error_count = 0

    # Answer Mapping
    answer_map = {
        "①": 1,
        "②": 2,
        "③": 3,
        "④": 4,
        "⑤": 5,
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
    }

    # Subject Mapping
    subject_map = {
        "산림 토양학": "산림토양학",
        "관리학": "수목관리학",
        "산림관리학": "수목관리학",
        "수목관리 답": "수목관리학",  # Handle header artifact if it appears
    }

    print("Starting import...")
    for index, row in df.iterrows():
        try:
            # A. Get or Create Exam
            try:
                round_num = int(row["회차"])
            except (ValueError, TypeError):
                # Skip header rows or invalid rows
                continue

            exam, _ = Exam.objects.get_or_create(round_number=round_num)

            # B. Get Subject
            raw_subject = str(row["과목"]).strip()
            # Normalize
            if raw_subject in subject_map:
                subject_name = subject_map[raw_subject]
            else:
                subject_name = raw_subject.replace(
                    " ", ""
                )  # Remove all spaces just in case

            try:
                subject = Subject.objects.get(name=subject_name)
            except Subject.DoesNotExist:
                # One last try check contains
                found_subjects = Subject.objects.filter(
                    name__icontains=subject_name[:2]
                )
                if found_subjects.exists():
                    subject = found_subjects.first()
                else:
                    print(
                        f"Skipping Row {index+2}: Subject '{raw_subject}' (clean: {subject_name}) not found."
                    )
                    error_count += 1
                    continue

            # C. Update or Create Question
            try:
                question_num = int(row["문제번호"])
            except ValueError:
                continue

            # Clean data
            content = str(row["문제"])
            if pd.isna(content) or content == "nan":
                content = "내용 없음"

            c1 = str(row["①"]) if not pd.isna(row["①"]) else ""
            c2 = str(row["②"]) if not pd.isna(row["②"]) else ""
            c3 = str(row["③"]) if not pd.isna(row["③"]) else ""
            c4 = str(row["④"]) if not pd.isna(row["④"]) else ""
            c5 = str(row["⑤"]) if not pd.isna(row["⑤"]) else ""

            # Handle Answer
            raw_ans = row["정답"]
            ans = 0

            # Try map
            if raw_ans in answer_map:
                ans = answer_map[raw_ans]
            else:
                # Try converting to int directly
                try:
                    ans = int(float(raw_ans))
                except (ValueError, TypeError):
                    # Handle special cases
                    s_ans = str(raw_ans).strip()
                    if s_ans in answer_map:
                        ans = answer_map[s_ans]
                    else:
                        print(
                            f"Row {index+2}: Unknown answer format '{raw_ans}'. Defaulting to 1."
                        )
                        ans = 1  # Fallback or skip? Let's default to 1.

            explanation = str(row["해설"])
            if pd.isna(explanation) or explanation == "nan":
                explanation = ""

            Question.objects.update_or_create(
                exam=exam,
                number=question_num,
                defaults={
                    "subject": subject,
                    "content": content,
                    "choice1": c1,
                    "choice2": c2,
                    "choice3": c3,
                    "choice4": c4,
                    "choice5": c5,
                    "answer": ans,
                    "explanation": explanation,
                },
            )
            success_count += 1

        except Exception as e:
            print(f"Error on Row {index+2}: {e}")
            error_count += 1

    print(f"\nImport Completed!")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")


if __name__ == "__main__":
    import_questions()
