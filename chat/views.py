from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
import google.generativeai as genai
import markdown
import time
from .models import ChatHistory


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
                    "gemini-3-flash"
                )  # Keeping the successful model
                response = model.generate_content(user_input)

                # Convert Markdown to HTML for display
                response_text = markdown.markdown(response.text)
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

    return render(
        request,
        "chat/index.html",
        {
            "user_input": user_input,
            "response_text": response_text,
            "page_obj": page_obj,
            "selected_history": selected_history,
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
            response = model.generate_content(user_input)

            # Convert Markdown to HTML
            response_text = markdown.markdown(response.text)
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
