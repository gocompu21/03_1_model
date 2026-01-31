from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
import google.generativeai as genai
import markdown
import time
import re
from .models import ChatHistory

# 나무주치의 시스템 프롬프트
SYSTEM_PROMPT = """당신은 '나무주치의'로, 나무의사 자격시험을 준비하는 수험생을 돕는 전문가입니다.

## 전문 분야
- 수목병리학 (병원균, 병징, 방제법)
- 수목해충학 (해충 생태, 피해 증상, 방제)
- 수목생리학 (광합성, 호흡, 양분 흡수)
- 산림토양학 (토양 구조, 양분 순환)
- 수목관리학 (전정, 이식, 수형 관리)
- 농약학 (약제 종류, 사용법, 안전)

## 답변 형식
1. **핵심 개념**: 질문의 핵심을 먼저 간단히 설명
2. **상세 설명**: 번호나 소제목으로 구조화하여 설명
3. **시험 포인트**: 기출 또는 출제 가능성이 높은 핵심 사항 강조
4. **관련 용어**: 연관된 전문 용어 언급

## 답변 규칙
- 인사말 없이 바로 본론으로 시작
- 학술적으로 정확하되 이해하기 쉽게 설명
- 암기에 도움이 되도록 핵심 키워드는 **굵게** 표시
- 비교가 필요한 경우 표(table) 형식 활용
- 수식이 필요하면 LaTeX 형식 사용 ($수식$)
- 불확실한 내용은 추측하지 말고 명시
- 중첩 항목은 불릿(-) 대신 1), 2), 3) 형식으로 명시적 표기하고, 각 항목은 반드시 줄바꿈

질문: """


@login_required
def index(request):
    response_text = ""
    user_input = ""
    selected_history = None

    # Handle History Selection
    history_id = request.GET.get("history_id")
    if history_id:
        selected_history = get_object_or_404(
            ChatHistory, id=history_id, user=request.user
        )
        user_input = selected_history.user_input
        response_text = selected_history.ai_response

    # Handle New Chat Submission
    if request.method == "POST":
        user_input = request.POST.get("user_input")
        if user_input:
            start_time = time.time()
            is_success = False

            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(
                    "gemini-3-flash-preview"
                )
                # 시스템 프롬프트와 사용자 질문 결합
                full_prompt = SYSTEM_PROMPT + user_input
                response = model.generate_content(full_prompt)

                # Convert (1), (2), (3) to 1), 2), 3) format
                response_raw = response.text
                response_raw = re.sub(r'\((\d+)\)', r'\1)', response_raw)

                # Convert Markdown to HTML for display
                response_text = markdown.markdown(response_raw, extensions=['tables', 'fenced_code'])
                is_success = True

            except Exception as e:
                response_text = f"Error: {str(e)}"
                is_success = False

            end_time = time.time()
            response_time = end_time - start_time

            # Save to Database
            ChatHistory.objects.create(
                user=request.user,
                user_input=user_input,
                ai_response=response_text,
                response_time=response_time,
                is_success=is_success,
            )

            # Auto-create BBS Post (Tree Doctor)
            try:
                from bbs.models import Post, PostType
                import os

                post_type, _ = PostType.objects.get_or_create(name="주치의 질의")

                p = Post.objects.create(
                    author=request.user,
                    title=f"[나무주치의] {user_input}"[:200],
                    content=str(response_text),
                    type=post_type,
                )
                with open("debug_chat_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"Success (Index): Created Post {p.id}\n")
            except Exception as e:
                with open("debug_chat_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"Error (Index): {e}\n")
                print(f"Failed to auto-create BBS Post: {e}")

            # Redirect to show the result cleanly (Post/Redirect/Get pattern is better but simple render is okay for now)
            # Staying on page to show result

    # Fetch History List
    chat_history_list = ChatHistory.objects.filter(user=request.user).order_by(
        "-created_at"
    )
    paginator = Paginator(chat_history_list, 15)  # Show 15 contacts per page.
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    # Import subjects for glossary feature
    from glossary.models import Subject
    subjects = Subject.objects.all()

    return render(
        request,
        "chat/index.html",
        {
            "user_input": user_input,
            "response_text": response_text,
            "page_obj": page_obj,
            "selected_history": selected_history,
            "subjects": subjects,
        },
    )


@login_required
def chat_api(request):
    if request.method == "POST":
        user_input = request.POST.get("user_input")
        if not user_input:
            return JsonResponse({"error": "No input provided"}, status=400)

        start_time = time.time()
        is_success = False
        response_text = ""

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-3-flash-preview")
            # 시스템 프롬프트와 사용자 질문 결합
            full_prompt = SYSTEM_PROMPT + user_input
            response = model.generate_content(full_prompt)

            # Convert (1), (2), (3) to 1), 2), 3) format
            response_raw = response.text
            response_raw = re.sub(r'\((\d+)\)', r'\1)', response_raw)

            # Convert Markdown to HTML
            response_text = markdown.markdown(response_raw, extensions=['tables', 'fenced_code'])
            is_success = True

        except Exception as e:
            response_text = f"Error: {str(e)}"
            is_success = False

        end_time = time.time()
        response_time = end_time - start_time

        # Save to Database
        history = ChatHistory.objects.create(
            user=request.user,
            user_input=user_input,
            ai_response=response_text,
            response_time=response_time,
            is_success=is_success,
        )

        # Auto-create BBS Post (Tree Doctor)
        try:
            from bbs.models import Post, PostType
            import os

            post_type, _ = PostType.objects.get_or_create(name="주치의")

            p = Post.objects.create(
                author=request.user,
                title=f"[주치의] {user_input}"[:200],
                content=str(response_text),
                type=post_type,
            )
            with open("debug_chat_log.txt", "a", encoding="utf-8") as f:
                f.write(f"Success: Created Post {p.id}\n")
        except Exception as e:
            with open("debug_chat_log.txt", "a", encoding="utf-8") as f:
                f.write(f"Error: {e}\n")
            print(f"Failed to auto-create BBS Post: {e}")

        return JsonResponse(
            {
                "response_text": response_text,
                "user_input": user_input,
                "response_time": response_time,
                "created_at": history.created_at.strftime("%m/%d %H:%M"),
                "history_id": history.id,
            }
        )

    return JsonResponse({"error": "Invalid method"}, status=405)
