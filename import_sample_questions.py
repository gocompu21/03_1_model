"""
수목병리학 샘플 문제 입력 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Book, Chapter, PracticeQuestion

# 수목병리학 책 가져오기
book = Book.objects.get(name='수목병리학')

sample_questions = [
    # (목차코드, 문제내용, 선지1, 선지2, 선지3, 선지4, 선지5, 정답, 해설)
    (
        "1.1.1",
        "수목병리학(樹木病理學)의 정의로 가장 적절한 것은?",
        "나무의 생장을 촉진시키는 방법을 연구하는 학문",
        "나무의 병해를 연구하여 예방 및 치료 방법을 개발하는 학문",
        "나무의 해충만을 연구하는 학문",
        "나무의 목재 이용을 연구하는 학문",
        "산림의 경제적 가치를 평가하는 학문",
        2,
        "수목병리학은 '수목(樹木) + 병리학(病理學)'의 합성어로, 나무의 병에 대한 원인, 증상, 진단, 예방 및 치료에 관해 연구하는 학문입니다."
    ),
    (
        "1.1.2",
        "수목병의 중요성에 대한 설명으로 옳지 않은 것은?",
        "산림 생태계의 건강성 유지에 영향을 미친다",
        "경제적 손실을 초래할 수 있다",
        "도시 녹지 및 조경수의 관리에 필수적이다",
        "수목병은 대부분 자연적으로 치유되므로 관리가 불필요하다",
        "수목 자산 가치 평가 시 중요한 요소이다",
        4,
        "수목병은 자연적으로 치유되는 경우도 있지만, 많은 경우 적절한 관리와 치료가 필요합니다. 방치할 경우 병이 확산되어 더 큰 피해를 줄 수 있습니다."
    ),
    (
        "1.4.1",
        "수목병의 전염원(傳染源)에 해당하지 않는 것은?",
        "병원균의 포자",
        "감염된 식물체의 잔재",
        "오염된 토양",
        "깨끗한 빗물",
        "감염된 종자",
        4,
        "전염원은 병원균이 존재하여 새로운 감염을 일으킬 수 있는 출처를 말합니다. 깨끗한 빗물 자체에는 병원균이 포함되어 있지 않으므로 전염원이 아닙니다."
    ),
]

# 문제 입력
created_count = 0
for data in sample_questions:
    chapter_code = data[0]
    
    try:
        chapter = Chapter.objects.get(book=book, code=chapter_code)
    except Chapter.DoesNotExist:
        print(f"목차 {chapter_code}를 찾을 수 없음")
        continue
    
    # 문제 번호 자동 할당
    last_q = PracticeQuestion.objects.filter(chapter=chapter).order_by('-number').first()
    next_number = (last_q.number + 1) if last_q else 1
    
    PracticeQuestion.objects.create(
        chapter=chapter,
        number=next_number,
        content=data[1],
        choice1=data[2],
        choice2=data[3],
        choice3=data[4],
        choice4=data[5],
        choice5=data[6],
        answer=data[7],
        explanation=data[8],
    )
    created_count += 1
    print(f"[생성] {chapter_code} - 문제 {next_number}")

print(f"\n완료! {created_count}개 문제 생성됨")
