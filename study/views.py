from django.shortcuts import render, get_object_or_404, redirect
from exam.models import Exam, Question, Subject, StudyNote
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.conf import settings
from exam.note_parser import parse_note_chapters
import json
import re
import struct


@login_required
def index(request):
    """
    List all available exam rounds and subjects.
    """
    from exam.models import TopicQuestionSet
    from collections import defaultdict
    
    exams = Exam.objects.exclude(round_number=0).order_by("round_number")
    subjects = Subject.objects.all().order_by("code")
    rounds = [e.round_number for e in exams]

    # Topic Tab Logic
    subject_id = request.GET.get('subject')
    active_tab = 'round' # Default tab
    
    if subject_id:
        active_tab = 'topic'
        try:
            selected_subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            selected_subject = subjects.filter(name__contains='수목병리').first() or subjects.first()
    else:
        # Default topic subject if tab is requested via other means (e.g. ?tab=topic)
        if request.GET.get('tab') == 'topic':
            active_tab = 'topic'
        selected_subject = subjects.filter(name__contains='수목병리').first() or subjects.first()
            
    # Filter topic sets
    topic_sets_qs = TopicQuestionSet.objects.filter(
        is_public=True,
        subject=selected_subject
    ).prefetch_related('items__question__exam').order_by('order', '-created_at')
    
    topic_sets_data = []
    for ts in topic_sets_qs:
        round_counts = defaultdict(int)
        for item in ts.items.all():
            if item.question and item.question.exam:
                round_counts[item.question.exam.round_number] += 1
        
        topic_sets_data.append({
            'id': ts.id,
            'title': ts.title,
            'description': ts.description,
            'total': ts.items.count(),
            'created_at': ts.created_at,
            'round_counts': dict(round_counts)
        })
    
    return render(request, "study/index.html", {
        "exams": exams, 
        "subjects": subjects,
        "rounds": rounds,
        "topic_sets": topic_sets_data,
        "selected_subject": selected_subject,
        "active_tab": active_tab,
    })


def detail(request, round_number):
    """
    Show all questions for a specific round.
    """
    # Get the exam object for context (title etc)
    # Using filter().first() or get_object_or_404 if we want to be strict
    # But wait, Question checks round_number via exam__round_number?
    # Or is Exam object keys by round_number?

    # Let's verify Exam model structure first.
    # Proceeding with assumption: Exam has round_number field.

    exam = Exam.objects.filter(round_number=round_number).first()

    # Get all questions
    questions = Question.objects.filter(exam__round_number=round_number).select_related('subject', 'exam').order_by(
        "number"
    )

    # Log study page view for authenticated users
    if request.user.is_authenticated:
        try:
            from .models import StudyViewLog
            StudyViewLog.objects.create(user=request.user, exam_round=round_number)
        except ImportError:
            pass

    # Note: Term matching moved to AJAX endpoint (api_question_terms) for performance

    context = {"round_number": round_number, "exam": exam, "questions": questions}
    return render(request, "study/detail.html", context)


def subject_detail(request, subject_name):
    """
    Show questions for a specific subject, filtered by round (via query param).
    Default to first available round if not specified.
    """
    # 1. Get All Exams for Tabs
    exams = Exam.objects.exclude(round_number=0).order_by("round_number")

    # 2. Determine Round Number
    round_param = request.GET.get("round")
    if round_param:
        try:
            current_round = int(round_param)
        except ValueError:
            current_round = exams.first().round_number if exams.exists() else 0
    else:
        # Default to first round
        current_round = exams.first().round_number if exams.exists() else 0

    # 3. Filter Questions
    # Note: Subject name might need decoding if passed in URL but Django handles unicode in URL params usually.
    questions = Question.objects.filter(
        subject__name=subject_name, exam__round_number=current_round
    ).order_by("number")

    context = {
        "subject_name": subject_name,
        "current_round": current_round,
        "exams": exams,
        "questions": questions,
    }
    return render(request, "study/study_by_subject.html", context)


def parse_audio_mime_type(mime_type: str) -> dict:
    """Parse bits per sample and rate from audio MIME type."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Convert raw audio data to WAV format."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    return header + audio_data


@login_required
def tts_generate(request):
    """Generate TTS audio using Gemini 2.5 Pro Preview TTS with caching."""
    import os
    import hashlib
    from pathlib import Path
    
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        question_id = data.get("question_id")
        tab = data.get("tab", "textbook")  # textbook or general
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not question_id:
        return JsonResponse({"error": "question_id required"}, status=400)

    # Get question
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"error": "Question not found"}, status=404)

    # Always use narration for TTS (ignoring tab parameter)
    text = question.narration or ""

    text = text.strip()
    if not text:
        return JsonResponse({"error": "나레이션이 없습니다."}, status=404)
    
    # Remove markdown formatting for TTS (clean text for speech)
    import re
    # Remove bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Remove headers: # text
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove list markers: - text or * text
    text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)

    # Create cache directory
    tts_cache_dir = Path(settings.MEDIA_ROOT) / "tts"
    tts_cache_dir.mkdir(parents=True, exist_ok=True)

    # Generate cache filename based on round, question number, and text hash
    # Hash ensures regeneration if explanation text changes
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    round_num = question.exam.round_number
    q_num = question.number

    # Check for MP3 cache first (preferred)
    mp3_filename = f"round{round_num}_q{q_num}_narration_{text_hash}.mp3"
    mp3_filepath = tts_cache_dir / mp3_filename

    if mp3_filepath.exists():
        with open(mp3_filepath, "rb") as f:
            mp3_data = f.read()
        response = HttpResponse(mp3_data, content_type="audio/mpeg")
        response["Content-Disposition"] = f'inline; filename="{mp3_filename}"'
        response["X-TTS-Cache"] = "HIT"
        return response

    # Fallback to WAV cache
    wav_filename = f"round{round_num}_q{q_num}_narration_{text_hash}.wav"
    wav_filepath = tts_cache_dir / wav_filename

    if wav_filepath.exists():
        with open(wav_filepath, "rb") as f:
            wav_data = f.read()
        response = HttpResponse(wav_data, content_type="audio/wav")
        response["Content-Disposition"] = f'inline; filename="{wav_filename}"'
        response["X-TTS-Cache"] = "HIT"
        return response

    # Limit text length to avoid API issues (max ~5000 chars)
    if len(text) > 5000:
        text = text[:5000] + "... 이하 생략"

    try:
        # Lazy import to avoid conflict with google-generativeai package
        from google import genai
        from google.genai import types
        import io
        
        # Initialize Gemini client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        model = "gemini-2.5-pro-preview-tts"
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Orus"  # Mature, deep male voice
                    )
                )
            ),
        )

        # Collect audio chunks
        audio_chunks = []
        mime_type = None

        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue

            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                audio_chunks.append(part.inline_data.data)
                if mime_type is None:
                    mime_type = part.inline_data.mime_type

        if not audio_chunks:
            return JsonResponse({"error": "No audio generated"}, status=500)

        # Combine all audio chunks
        combined_audio = b"".join(audio_chunks)

        # Convert to WAV
        wav_data = convert_to_wav(combined_audio, mime_type or "audio/L16;rate=24000")

        # Convert to MP3 using ffmpeg
        try:
            import subprocess
            import tempfile
            import os as os_module
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                tmp_wav.write(wav_data)
                tmp_wav_path = tmp_wav.name
            
            try:
                result = subprocess.run(
                    ["ffmpeg", "-y", "-i", tmp_wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", str(mp3_filepath)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise Exception(f"ffmpeg error: {result.stderr}")
                
                with open(mp3_filepath, "rb") as f:
                    mp3_data = f.read()
                
                response = HttpResponse(mp3_data, content_type="audio/mpeg")
                response["Content-Disposition"] = f'inline; filename="{mp3_filename}"'
                response["X-TTS-Cache"] = "MISS"
                return response
            finally:
                if os_module.path.exists(tmp_wav_path):
                    os_module.remove(tmp_wav_path)
        except Exception:
            # Fallback to WAV if MP3 conversion fails
            with open(wav_filepath, "wb") as f:
                f.write(wav_data)
            
            response = HttpResponse(wav_data, content_type="audio/wav")
            response["Content-Disposition"] = f'inline; filename="{wav_filename}"'
            response["X-TTS-Cache"] = "MISS"
            return response

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def api_question(request, question_id):
    """API: 문제 데이터 반환 (JSON)"""
    import markdown as md
    import re

    from exam.templatetags.markdown_extras import choice_note
    
    try:
        question = Question.objects.select_related('exam').get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"error": "Question not found"}, status=404)
    
    # 해설 마크다운을 HTML로 변환
    explanation_raw = question.textbook_chat or question.general_chat or ''
    
    # JSON에서 가져온 데이터의 이중 이스케이프 수정 (\\text -> \text)
    explanation_raw = explanation_raw.replace('\\\\', '\\')
    
    # LaTeX 수식을 임시로 보호 (마크다운 변환에서 제외)
    latex_formulas = []
    def save_latex(match):
        latex_formulas.append(match.group(0))
        return f'LATEXPLACEHOLDER{len(latex_formulas)-1}ENDLATEX'
    
    # Display math: $$...$$ (먼저 처리)
    explanation_raw = re.sub(r'\$\$(.+?)\$\$', save_latex, explanation_raw, flags=re.DOTALL)
    # Inline math: $...$
    explanation_raw = re.sub(r'\$([^\$\n]+?)\$', save_latex, explanation_raw)

    # 선지별 답변의 "* ①" 패턴에서 불필요한 * 제거
    explanation_raw = re.sub(r'^\*\s+([①②③④⑤])', r'\1', explanation_raw, flags=re.MULTILINE)
    # "* **① 내용:**" 패턴에서 *, ** 모두 제거 (볼드 마크다운 포함)
    explanation_raw = re.sub(r'^\*\s+\*\*([①②③④⑤][^*]*)\*\*', r'\1', explanation_raw, flags=re.MULTILINE)

    explanation_html = md.markdown(explanation_raw, extensions=['extra', 'nl2br', 'sane_lists'])

    # 선지별 답변(①②③④⑤로 시작하는 줄)을 별도 p 태그로 분리하고 번호를 span으로 감싸기
    explanation_html = re.sub(
        r'<br />\n([①②③④⑤])',
        r'</p>\n<p class="choice-explanation"><span class="choice-num">\1</span>',
        explanation_html
    )
    # 빈 줄 후 새 문단으로 시작하는 선지도 처리
    explanation_html = re.sub(
        r'<p>([①②③④⑤])',
        r'<p class="choice-explanation"><span class="choice-num">\1</span>',
        explanation_html
    )

    # LaTeX 수식 복원
    for i, formula in enumerate(latex_formulas):
        explanation_html = explanation_html.replace(f'LATEXPLACEHOLDER{i}ENDLATEX', formula)
    
    data = {
        "id": question.id,
        "exam_round": question.exam.round_number,
        "number": question.number,
        "content": question.content,
        "choice1": question.choice1,
        "choice2": question.choice2,
        "choice3": question.choice3,
        "choice4": question.choice4,
        "choice5": question.choice5,
        "answer": question.answer,
        "explanation": explanation_html,
        "image": question.image.url if question.image else None,
        # 선지별 설명. 용어 상세 화면에서 선지 밑에 붙인다
        "choice_notes": {
            str(k): str(choice_note(v))
            for k, v in (question.choice_notes or {}).items()
            if v
        },
    }
    return JsonResponse(data)


@login_required
def api_question_terms(request, question_id):
    """API: 문제의 관련 용어 반환 (AJAX 지연 로딩용)"""
    from glossary.utils import get_terms_pattern

    try:
        question = Question.objects.select_related('subject').get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"error": "Question not found"}, status=404)

    # 해당 과목의 용어 패턴 가져오기
    pattern, term_map = get_terms_pattern(question.subject.name)

    terms_data = []
    if pattern:
        # 검색 대상 텍스트 결합
        search_text = " ".join(filter(None, [
            question.content, question.choice1, question.choice2,
            question.choice3, question.choice4, question.choice5,
            question.general_chat, question.textbook_chat, question.narration
        ]))

        found_ids = set()
        for match in pattern.finditer(search_text):
            term = term_map.get(match.group(0))
            if term and term.id not in found_ids:
                found_ids.add(term.id)
                terms_data.append({
                    "id": term.id,
                    "word": term.word,
                    "reference_count": getattr(term, 'reference_count', 0)
                })

        # 단어순 정렬
        terms_data.sort(key=lambda t: t['word'])

    return JsonResponse({"terms": terms_data})


# ============================================================================
# 기출분석 Views
# ============================================================================

@login_required
def analysis_index(request):
    """회차 선택 화면"""
    from study.models import RoundAnalysis
    analyses = RoundAnalysis.objects.select_related("exam").order_by("-exam__round_number")
    return render(request, "study/analysis_index.html", {"analyses": analyses})


def _clean_summary(content):
    """문제 지문에서 보기·HTML 제거 후 핵심 질문만 추출"""
    # <div> 블록(보기 영역) 제거
    text = re.sub(r'<div[^>]*>.*?</div>', '', content, flags=re.DOTALL)
    # 나머지 HTML 태그 제거
    text = re.sub(r'<[^>]+>', ' ', text)
    # HTML 엔티티
    import html as _html
    text = _html.unescape(text)
    # 줄바꿈 → 공백, 연속 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    # 80자 제한
    return text[:80] if len(text) > 80 else text


@login_required
def analysis_detail(request, round_number):
    """회차별 출제 동향 분석 상세"""
    from study.models import RoundAnalysis, QuestionAnalysis
    from collections import OrderedDict

    exam = get_object_or_404(Exam, round_number=round_number)
    round_analysis = get_object_or_404(RoundAnalysis, exam=exam)

    # 과목별 문항 + 분석 데이터 조회
    questions = (
        Question.objects.filter(exam=exam)
        .select_related("subject")
        .order_by("subject__code", "number")
    )
    # prefetch 분석 데이터
    qa_map = {}
    for qa in QuestionAnalysis.objects.filter(question__exam=exam):
        qa_map[qa.question_id] = qa

    subjects = Subject.objects.all().order_by("code")
    subject_order = {s.name: s.code for s in subjects}

    # 과목별 그룹화
    subjects_data = OrderedDict()
    for q in questions:
        sname = q.subject.name
        if sname not in subjects_data:
            subjects_data[sname] = {
                "questions": [],
                "possible": 0,
                "impossible": 0,
            }
        qa = qa_map.get(q.id)
        possible = qa.textbook_possible if qa else True
        reason = qa.textbook_reason if qa else ""
        subjects_data[sname]["questions"].append({
            "number": q.number,
            "summary": q.summary or _clean_summary(q.content),
            "possible": possible,
            "reason": reason,
        })
        if possible:
            subjects_data[sname]["possible"] += 1
        else:
            subjects_data[sname]["impossible"] += 1

    # 과목별 교과서 예상 점수 계산
    for sname, sd in subjects_data.items():
        total = sd["possible"] + sd["impossible"]
        sd["score"] = round(sd["possible"] / total * 100) if total else 0

    # past_exam_data를 과목 코드 순으로 정렬 + 퍼센트 계산
    past_exam_data = round_analysis.past_exam_data
    sorted_past = OrderedDict()
    for sname in sorted(past_exam_data.keys(), key=lambda x: subject_order.get(x, 99)):
        d = dict(past_exam_data[sname])
        total = d.get("similar", 0) + d.get("related", 0) + d.get("new", 0)
        if total:
            d["similar_pct"] = round(d.get("similar", 0) / total * 100)
            d["related_pct"] = round(d.get("related", 0) / total * 100)
            d["new_pct"] = round(d.get("new", 0) / total * 100)
        sorted_past[sname] = d

    # 합계 계산
    total_possible = sum(sd["possible"] for sd in subjects_data.values())
    total_impossible = sum(sd["impossible"] for sd in subjects_data.values())
    gap = round(round_analysis.textbook_avg_score - round_analysis.past_exam_avg_score)

    # 요약 텍스트를 줄 단위로 분리
    insights = [line.strip() for line in round_analysis.summary.split("\n") if line.strip()]

    # detail_content 파싱
    dc = round_analysis.detail_content or {}

    context = {
        "exam": exam,
        "round_analysis": round_analysis,
        "subjects_data": subjects_data,
        "past_exam_data": sorted_past,
        "subject_names": list(subjects_data.keys()),
        "total_possible": total_possible,
        "total_impossible": total_impossible,
        "gap": gap,
        "insights": insights,
        "subject_areas": dc.get("subject_areas", {}),
        "impossible_categories": dc.get("impossible_categories", []),
        "trends": dc.get("trends", []),
        "priority": dc.get("priority", []),
        "strategy": dc.get("strategy", []),
    }
    return render(request, "study/analysis_detail.html", context)


@login_required
def topic_solve(request, set_id):
    """주제별 문제집 풀기"""
    from exam.models import TopicQuestionSet, UserTopicSetAttempt, UserTopicQuestionResult
    from django.utils import timezone
    from django.shortcuts import redirect
    
    topic_set = get_object_or_404(TopicQuestionSet, id=set_id)
    
    # 문제 가져오기 (순서대로)
    items = topic_set.items.select_related('question__exam', 'question__subject').order_by('order')
    questions = [item.question for item in items]
    
    if request.method == 'POST':
        # 채점 및 결과 저장
        attempt = UserTopicSetAttempt.objects.create(
            user=request.user,
            question_set=topic_set
        )
        
        correct_count = 0
        for q in questions:
            selected_choice = request.POST.get(f'question_{q.id}')
            if selected_choice:
                selected_choice = int(selected_choice)
                is_correct = selected_choice in q.answer
                if is_correct:
                    correct_count += 1
                
                UserTopicQuestionResult.objects.create(
                    attempt=attempt,
                    question=q,
                    selected_choice=selected_choice,
                    is_correct=is_correct
                )
                
                # 오답 시 복습 스케줄 등록
                if not is_correct:
                    from mypage.models import ReviewSchedule
                    
                    review_schedule, created = ReviewSchedule.objects.get_or_create(
                        user=request.user,
                        question=q,
                        defaults={
                            'last_wrong_date': timezone.now(),
                            'review_count': 0,
                            'next_review_date': timezone.localdate(),
                            'is_mastered': False,
                        }
                    )
                    if not created:
                        review_schedule.review_count = 0
                        review_schedule.last_wrong_date = timezone.now()
                        review_schedule.is_mastered = False
                        review_schedule.next_review_date = review_schedule.calculate_next_review_date()
                        review_schedule.save()
        
        attempt.total_score = correct_count
        attempt.end_time = timezone.now()
        attempt.save()
        
        return redirect('study:topic_result', set_id=set_id, attempt_id=attempt.id)
    
    return render(request, 'study/topic_solve.html', {
        'topic_set': topic_set,
        'questions': questions
    })


@login_required
def topic_result(request, set_id, attempt_id):
    """주제별 문제집 결과"""
    from exam.models import TopicQuestionSet, UserTopicSetAttempt, UserTopicQuestionResult
    
    topic_set = get_object_or_404(TopicQuestionSet, id=set_id)
    attempt = get_object_or_404(UserTopicSetAttempt, id=attempt_id)
    results = UserTopicQuestionResult.objects.filter(attempt=attempt).select_related('question__exam', 'question__subject')
    
    total_attempted = results.count()
    score_100 = (attempt.total_score / total_attempted * 100) if total_attempted > 0 else 0
    
    return render(request, 'study/topic_result.html', {
        'topic_set': topic_set,
        'attempt': attempt,
        'results': results,
        'score_100': score_100,
        'total_attempted': total_attempted
    })


@login_required
def topic_set_list(request):
    """주제별 문제집 목록"""
    from exam.models import TopicQuestionSet, Subject, Exam
    from collections import defaultdict
    
    subjects = Subject.objects.all().order_by('code')
    exams = Exam.objects.all().order_by('round_number')
    rounds = [e.round_number for e in exams]
    
    # 과목 필터 (기본값: 수목병리학)
    subject_id = request.GET.get('subject')
    if subject_id:
        try:
            selected_subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            selected_subject = subjects.filter(name__contains='수목병리').first() or subjects.first()
    else:
        selected_subject = subjects.filter(name__contains='수목병리').first() or subjects.first()
    
    # 해당 과목의 문제집 필터링
    topic_sets = TopicQuestionSet.objects.filter(
        is_public=True,
        subject=selected_subject
    ).prefetch_related('items__question__exam').order_by('order', '-created_at')
    
    # 각 문제집의 회차별 문제 수 계산
    topic_set_data = []
    for ts in topic_sets:
        round_counts = defaultdict(int)
        for item in ts.items.all():
            if item.question and item.question.exam:
                round_counts[item.question.exam.round_number] += 1
        
        topic_set_data.append({
            'id': ts.id,
            'title': ts.title,
            'description': ts.description,
            'total': ts.items.count(),
            'round_counts': dict(round_counts)
        })
    
    return render(request, 'study/topic_set_list.html', {
        'topic_sets': topic_set_data,
        'subjects': subjects,
        'selected_subject': selected_subject,
        'rounds': rounds
    })


@login_required
def topic_set_create(request):
    """주제별 문제집 생성 페이지"""
    from exam.models import Exam, Subject
    
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("관리자만 접근 가능합니다.")
    
    exams = Exam.objects.all().order_by('round_number')
    subjects = Subject.objects.all().order_by('code')
    
    return render(request, 'study/topic_set_create.html', {
        'exams': exams,
        'subjects': subjects
    })


@login_required
def topic_set_edit(request, set_id):
    """주제별 문제집 수정 페이지"""
    from exam.models import Exam, Subject, TopicQuestionSet
    import json
    
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("관리자만 접근 가능합니다.")
    
    topic_set = get_object_or_404(TopicQuestionSet, id=set_id)
    exams = Exam.objects.all().order_by('round_number')
    subjects = Subject.objects.all().order_by('code')
    
    # 초기 카트 데이터 생성
    initial_cart = []
    from django.utils.html import strip_tags
    
    for item in topic_set.items.select_related('question', 'question__exam').order_by('order'):
        q = item.question
        # 텍스트 정리
        text = strip_tags(q.content).strip()
        text = " ".join(text.split()) # 연속된 공백 제거
        text = text[:30] + '...' if len(text) > 30 else text
        
        initial_cart.append({
            'id': q.id,
            'text': text,
            'round': q.exam.round_number,
            'number': q.number
        })
    
    return render(request, 'study/topic_set_create.html', {
        'exams': exams,
        'subjects': subjects,
        'topic_set': topic_set,
        'initial_cart_json': json.dumps(initial_cart)
    })


@login_required
def delete_topic_set(request, set_id):
    """주제별 문제집 삭제 (AJAX)"""
    from exam.models import TopicQuestionSet
    
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': '관리자만 삭제할 수 있습니다.'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        topic_set = TopicQuestionSet.objects.get(id=set_id)
        topic_set.delete()
        return JsonResponse({'success': True})
    except TopicQuestionSet.DoesNotExist:
        return JsonResponse({'success': False, 'error': '문제집을 찾을 수 없습니다.'})


@login_required
def api_exam_questions(request):
    """특정 회차의 문제 목록 반환 (JSON)"""
    from exam.models import Exam, Question
    import re
    
    def strip_html(text):
        """HTML 태그 제거"""
        return re.sub(r'<[^>]+>', '', text)
    
    exam_id = request.GET.get('exam_id')
    if not exam_id:
        return JsonResponse({'questions': []})
    
    questions = Question.objects.filter(exam_id=exam_id).order_by('number')
    data = []
    for q in questions:
        clean_content = strip_html(q.content)
        if len(clean_content) > 40:
            full_text = f"{q.number}번 {clean_content[:40]}..."
        else:
            full_text = f"{q.number}번 {clean_content}"
        data.append({
            'id': q.id,
            'number': q.number,
            'full_text': full_text
        })
    
    return JsonResponse({'questions': data})


@login_required
def api_save_topic_set(request):
    """주제별 문제집 저장 (AJAX)"""
    from exam.models import TopicQuestionSet, TopicQuestionSetItem, Question, Subject
    
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': '관리자만 저장할 수 있습니다.'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        question_ids = data.get('question_ids', [])
        subject_id = data.get('subject_id')
        set_id = data.get('set_id') # 수정 시 ID
        
        if not title:
            return JsonResponse({'success': False, 'error': '제목을 입력해주세요.'})
        
        if not question_ids:
            return JsonResponse({'success': False, 'error': '문제를 선택해주세요.'})
        
        # 과목 가져오기
        subject = None
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass
        
        if set_id:
            # 수정 모드
            topic_set = get_object_or_404(TopicQuestionSet, id=set_id)
            topic_set.title = title
            topic_set.description = description
            topic_set.subject = subject
            topic_set.save()
            
            # 기존 아이템 삭제 후 재생성 (순서 재정렬 위해)
            TopicQuestionSetItem.objects.filter(question_set=topic_set).delete()
        else:
            # 생성 모드
            # 생성 모드
            from django.db.models import Max
            max_order = TopicQuestionSet.objects.filter(subject=subject).aggregate(Max('order'))['order__max']
            new_order = (max_order + 1) if max_order is not None else 0

            topic_set = TopicQuestionSet.objects.create(
                title=title,
                description=description,
                subject=subject,
                created_by=request.user,
                is_public=True,
                order=new_order
            )
        
        # 문제 추가 (순서 유지)
        for order, question_id in enumerate(question_ids, start=1):
            try:
                question = Question.objects.get(id=question_id)
                TopicQuestionSetItem.objects.create(
                    question_set=topic_set,
                    question=question,
                    order=order
                )
            except Question.DoesNotExist:
                pass
        
        return JsonResponse({'success': True, 'topic_set_id': topic_set.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_reorder_topic_set(request):
    """주제별 문제집 순서 변경 API"""
    from exam.models import TopicQuestionSet
    import json
    
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': '관리자만 권한이 있습니다.'}, status=403)
        
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
        
    try:
        data = json.loads(request.body)
        set_id = data.get('set_id')
        direction = data.get('direction') # 'up' or 'down'
        
        if not set_id or not direction:
            return JsonResponse({'success': False, 'error': 'Missing parameters'})
            
        target_set = get_object_or_404(TopicQuestionSet, id=set_id)
        
        # 필터링 조건 확인 (과목 등)
        subject_id = data.get('subject_id')
        
        qs = TopicQuestionSet.objects.filter(is_public=True)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
            
        # 정렬 기준대로 가져오기
        sets = list(qs.order_by('order', '-created_at'))
        
        # Order 초기화가 안되어있으면 (모두 0이면) 초기화
        if all(s.order == 0 for s in sets) and len(sets) > 1:
            for idx, s in enumerate(sets):
                s.order = (idx + 1) * 10
                s.save()
            # 다시 로드
            sets = list(qs.order_by('order', '-created_at'))
            target_set.refresh_from_db()
            
        current_idx = -1
        for i, s in enumerate(sets):
            if s.id == target_set.id:
                current_idx = i
                break
        
        if current_idx == -1:
            return JsonResponse({'success': False, 'error': 'Target not found in list'})
            
        swap_idx = -1
        if direction == 'up':
            if current_idx > 0:
                swap_idx = current_idx - 1
        elif direction == 'down':
            if current_idx < len(sets) - 1:
                swap_idx = current_idx + 1
                
        if swap_idx != -1:
            swap_set = sets[swap_idx]
            
            # Swap orders
            if target_set.order == swap_set.order:
                for idx, s in enumerate(sets):
                    s.order = (idx + 1) * 10
                    s.save()
                target_set = sets[current_idx]
                swap_set = sets[swap_idx]
            
            target_set.order, swap_set.order = swap_set.order, target_set.order
            target_set.save()
            swap_set.save()
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Cannot move further'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# 기본서 학습문제 관리 (Practice Question Management)
# ============================================================================
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def practice_manage(request):
    """기본서 학습문제 입력/수정 관리 페이지 (관리자 전용)"""
    return render(request, 'study/practice_manage.html')


# ============================================================================
# 쪽집게 노트 (StudyNote)
# ============================================================================

@login_required
def study_notes(request, subject_id):
    """과목별 쪽집게 노트 아코디언 표시"""
    subject = get_object_or_404(Subject, pk=subject_id)
    subjects = Subject.objects.all().order_by("code")

    notes_qs = StudyNote.objects.filter(subject=subject).order_by("order")
    note_chapters = []

    if notes_qs.exists():
        combined = "\n\n".join(n.content for n in notes_qs if n.content)
        if combined.strip():
            latest_updated = max(
                (n.updated_at for n in notes_qs if n.updated_at),
                default=None,
            )
            note_chapters = parse_note_chapters(
                combined, subject.pk,
                cache_version=str(latest_updated) if latest_updated else None,
            )

    return render(request, "study/study_notes.html", {
        "subject": subject,
        "subjects": subjects,
        "note_chapters": note_chapters,
        "study_notes_count": notes_qs.count(),
    })


@login_required
def notes_study(request, subject_id):
    """쪽집게 노트 관련 문제 학습모드 — ref 형식: R-N (회차-문제번호)"""
    subject = get_object_or_404(Subject, pk=subject_id)
    refs = request.GET.getlist("ref")

    if not refs:
        return redirect("study:study_notes", subject_id=subject.pk)

    # R-N 형식 파싱 → (round_number, question_number)
    q_filters = Q()
    for ref in refs:
        parts = ref.split("-")
        if len(parts) == 2:
            try:
                round_num, q_num = int(parts[0]), int(parts[1])
                q_filters |= Q(
                    subject=subject,
                    exam__round_number=round_num,
                    number=q_num,
                )
            except ValueError:
                continue

    questions = list(
        Question.objects.filter(q_filters)
        .select_related("exam", "subject")
        .order_by("exam__round_number", "number")
    )

    # 해당 절 제목 찾기 (breadcrumb용)
    section_title = ""
    ref_set = set(refs)
    for note in StudyNote.objects.filter(subject=subject).order_by("order"):
        for line in note.content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("### ") and not stripped.startswith("### 핵심"):
                current_section = stripped[4:]
            if "**관련 문제**" in stripped:
                found_refs = set(re.findall(r"\((\d{1,2}-\d+)\)", stripped))
                if found_refs & ref_set:
                    section_title = current_section
                    break
        if section_title:
            break

    return render(request, "study/study_by_subject.html", {
        "subject_name": subject.name,
        "current_round": "쪽집게 노트",
        "exams": Exam.objects.exclude(round_number=0).order_by("round_number"),
        "questions": questions,
        "is_notes_study": True,
        "section_title": section_title,
        "subject_id": subject.pk,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def question_update(request, question_id):
    """AJAX: 문제 인라인 수정 (staff only)"""
    question = get_object_or_404(Question, pk=question_id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "잘못된 요청"}, status=400)

    question.content = data.get("content", question.content)
    question.choice1 = data.get("choice1", question.choice1)
    question.choice2 = data.get("choice2", question.choice2)
    question.choice3 = data.get("choice3", question.choice3)
    question.choice4 = data.get("choice4", question.choice4)
    question.choice5 = data.get("choice5", question.choice5)

    if "answer" in data:
        ans = data["answer"]
        question.answer = ans if isinstance(ans, list) else [int(ans)]

    if "general_chat" in data:
        question.general_chat = data["general_chat"]

    question.save()
    return JsonResponse({"ok": True})

