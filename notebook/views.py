from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.paginator import Paginator
import sys
import os
import markdown

# Ensure project root is in path to import fileSearchStore
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fileSearchStore import GeminiStoreManager
except ImportError:
    GeminiStoreManager = None

from .models import NotebookHistory


@login_required
def index(request):
    # Default subject
    default_subject = "수목생리학"
    subject = request.GET.get("subject", default_subject)

    selected_history = None
    user_input = ""
    response_text = ""

    # If history_id is provided, try to load it first
    history_id = request.GET.get("history_id")
    if history_id:
        selected_history = get_object_or_404(
            NotebookHistory, id=history_id, user=request.user
        )
        # Override subject to match the selected history
        subject = selected_history.subject

        user_input = selected_history.user_input
        # Render saved Markdown directly
        response_text = markdown.markdown(
            selected_history.ai_response, extensions=["extra", "nl2br"]
        )

    # Filter history list by the (possibly updated) subject
    history_list = NotebookHistory.objects.filter(
        user=request.user, subject=subject
    ).order_by("-created_at")

    paginator = Paginator(history_list, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "user_input": user_input,
        "response_text": response_text,
        "page_obj": page_obj,
        "selected_history": selected_history,
        "current_subject": subject,
    }
    return render(request, "notebook/index.html", context)


@login_required
def api_ask(request):
    if request.method == "POST":
        user_input = request.POST.get("user_input", "").strip()
        if not user_input:
            return JsonResponse({"error": "No input provided"}, status=400)

        if not GeminiStoreManager:
            return JsonResponse(
                {"response_text": "오류: fileSearchStore 모듈을 찾을 수 없습니다."},
                status=500,
            )

        try:
            # Initialize Manager with API Key from settings
            api_key = settings.GEMINI_API_KEY
            manager = GeminiStoreManager(api_key=api_key)

            # Determine Target Store
            # Default to "Tree Doctor Examp" if not provided, or strictly follow user selection
            requested_store = request.POST.get("store_name", "").strip()
            target_store = requested_store if requested_store else "Tree Doctor Examp"
            print(
                f"DEBUG: Requested Store: '{requested_store}' -> Target: '{target_store}'"
            )

            if target_store not in manager.stores or not manager.stores[target_store]:
                print(
                    f"DEBUG: Store '{target_store}' missing or empty locally. Triggering full sync..."
                )
                manager.sync_all_stores()

                # Check again
                if (
                    target_store not in manager.stores
                    or not manager.stores[target_store]
                ):
                    print(
                        f"DEBUG: No files found for '{target_store}' even after full sync."
                    )
                    return JsonResponse(
                        {
                            "response_text": f"'{target_store}' 관련 파일을 찾을 수 없습니다. (클라우드 파일 동기화 실패)"
                        },
                        status=200,
                    )

            print(
                f"DEBUG: Store '{target_store}' ready. Files: {manager.stores[target_store]}"
            )

            # Query the store
            raw_text = manager.query_store(target_store, user_input)

            # Check for stale cache or empty store response
            if (
                "No valid (ACTIVE) files found" in raw_text
                or "Store is empty" in raw_text
            ):
                print(
                    "DEBUG: Stale files or empty store detected by API. Triggering full sync and retry..."
                )
                manager.sync_all_stores()

                # Retry Query
                raw_text = manager.query_store(target_store, user_input)

            # Save History
            history = NotebookHistory.objects.create(
                user=request.user,
                user_input=user_input,
                ai_response=raw_text,  # Save raw markdown
                is_success=True,
                subject=target_store,
            )

            # Convert Markdown to HTML for display and BBS
            # 'extra' includes fenced_code, tables, and more robust list handling.
            # 'nl2br' converts newlines to <br> tags.
            html_content = markdown.markdown(raw_text, extensions=["extra", "nl2br"])

            # Auto-create BBS Post
            try:
                from bbs.models import Post

                # Format content for Wysiwyg (Summernote)
                bbs_content = f'<p><span style="font-weight: bold; font-size: 1.2em; color: #2d6a4f;">[기본서 내용]</span></p>{html_content}'

                Post.objects.create(
                    author=request.user,
                    title=f"[기본서 질의] {user_input}"[
                        :200
                    ],  # Prepend prefix and truncate
                    content=bbs_content,  # Save formatted HTML
                )
            except Exception as e:
                print(f"DEBUG: Failed to auto-create BBS post: {e}")

            return JsonResponse(
                {
                    "response_text": html_content,
                    "user_input": user_input,
                    "history_id": history.id,
                }
            )

        except Exception as e:
            # Save breakdown history? Maybe later.
            return JsonResponse(
                {"response_text": f"오류가 발생했습니다: {str(e)}"}, status=500
            )

    return JsonResponse({"error": "Invalid method"}, status=405)
