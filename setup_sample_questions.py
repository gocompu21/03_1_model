import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Subject, Exam, Question


def create_sample_questions():
    # Ensure we have the 5th exam and 1st subject
    exam = Exam.objects.get(round_number=5)
    subject = Subject.objects.get(code=1)  # 수목병리학

    # Check if questions exist
    if Question.objects.filter(exam=exam, subject=subject).exists():
        print("Sample questions already exist.")
        return

    print("Creating sample questions...")

    Question.objects.create(
        exam=exam,
        subject=subject,
        number=1,
        content="다음 중 수목병리학의 정의로 가장 적절한 것은?",
        choice1="나무의 해충을 연구하는 학문",
        choice2="나무의 생리적 기능을 연구하는 학문",
        choice3="수목의 병을 진단하고 치료하는 학문",
        choice4="산림의 토양을 연구하는 학문",
        choice5="나무의 유전적 특성을 연구하는 학문",
        answer=3,
        explanation="수목병리학은 수목에 발생하는 병의 원인, 발생기작, 진단 및 방제법을 연구하는 학문이다.",
    )

    Question.objects.create(
        exam=exam,
        subject=subject,
        number=2,
        content="파이토플라스마에 의한 수목병의 일반적인 방제법으로 옳은 것은?",
        choice1="살균제 살포",
        choice2="테트라사이클린계 항생제 수관주사",
        choice3="살충제 살포",
        choice4="토양 소독",
        choice5="가지치기",
        answer=2,
        explanation="파이토플라스마는 세균의 일종으로 테트라사이클린계 항생제에 반응한다.",
    )

    print("Created 2 sample questions for Exam 5, Subject 1.")


if __name__ == "__main__":
    create_sample_questions()
