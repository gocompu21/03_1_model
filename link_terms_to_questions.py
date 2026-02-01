# -*- coding: utf-8 -*-
"""
수목관리학 용어를 기출문제와 연결하는 스크립트
- 문제 지문, 보기, 해설에서 용어가 등장하면 TermReference 생성
"""
import sqlite3
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def main():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()

    # 1. 수목관리학 과목 ID 가져오기 (glossary)
    c.execute("SELECT id FROM glossary_subject WHERE name = ?", ("수목관리학",))
    g_subject_id = c.fetchone()[0]

    # 2. 수목관리학 과목 ID 가져오기 (exam)
    c.execute("SELECT id FROM exam_subject WHERE name = ?", ("수목관리학",))
    e_subject_id = c.fetchone()[0]

    print(f"glossary 수목관리학 ID: {g_subject_id}")
    print(f"exam 수목관리학 ID: {e_subject_id}")

    # 3. 수목관리학 용어 목록 가져오기
    c.execute("""
        SELECT t.id, t.word FROM glossary_term t
        JOIN glossary_term_subjects ts ON t.id = ts.term_id
        WHERE ts.subject_id = ?
    """, (g_subject_id,))
    terms = c.fetchall()
    print(f"수목관리학 용어 수: {len(terms)}개")

    # 용어를 길이 순으로 정렬 (긴 용어 먼저 매칭 - 부분 매칭 방지)
    terms_sorted = sorted(terms, key=lambda x: len(x[1]), reverse=True)

    # 4. 수목관리학 문제 가져오기
    c.execute("""
        SELECT q.id, e.round_number, q.number, q.content,
               q.choice1, q.choice2, q.choice3, q.choice4, q.choice5,
               q.general_chat
        FROM exam_question q
        JOIN exam_exam e ON q.exam_id = e.id
        WHERE q.subject_id = ?
    """, (e_subject_id,))
    questions = c.fetchall()
    print(f"수목관리학 문제 수: {len(questions)}개")

    # 5. 기존 TermReference 삭제 (수목관리학 문제에 대한 것만)
    question_ids = [q[0] for q in questions]
    placeholders = ','.join('?' * len(question_ids))
    c.execute(f"""
        DELETE FROM glossary_termreference
        WHERE source_type = 'question' AND source_id IN ({placeholders})
    """, question_ids)
    deleted = c.rowcount
    print(f"기존 참조 삭제: {deleted}개")

    # 6. 용어-문제 매칭 및 TermReference 생성
    created_count = 0
    matched_terms = set()

    for q_id, round_num, q_num, content, c1, c2, c3, c4, c5, explanation in questions:
        # 문제 전체 텍스트 결합
        full_text = f"{content} {c1} {c2} {c3} {c4} {c5} {explanation or ''}"

        for term_id, word in terms_sorted:
            # 용어가 텍스트에 포함되어 있는지 확인
            if word in full_text:
                # TermReference 생성
                source_title = f"{round_num}회 {q_num}번"
                try:
                    c.execute("""
                        INSERT INTO glossary_termreference
                        (term_id, source_type, source_id, source_title, created_at)
                        VALUES (?, 'question', ?, ?, datetime('now'))
                    """, (term_id, q_id, source_title))
                    created_count += 1
                    matched_terms.add(word)
                except sqlite3.IntegrityError:
                    # 이미 존재하는 경우 무시
                    pass

    conn.commit()
    conn.close()

    print(f"\n=== 결과 ===")
    print(f"생성된 참조: {created_count}개")
    print(f"매칭된 용어 종류: {len(matched_terms)}개")
    print(f"\n매칭된 용어 샘플 (처음 20개):")
    for i, word in enumerate(sorted(matched_terms)[:20]):
        print(f"  - {word}")


if __name__ == "__main__":
    main()
