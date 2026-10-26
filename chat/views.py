from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
import google.generativeai as genai
import markdown
import io
import time
import re
import uuid
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from .models import ChatHistory, ChatImage
from dashboard.models import SiteSettings

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

## 출력 형식 (매우 중요 - 반드시 지킬 것)
반드시 아래 형식만 사용:

### 제목
본문 텍스트

### 제목
1. 첫번째 항목
2. 두번째 항목
3. 세번째 항목

표가 필요할 때만:
| 열1 | 열2 |
|-----|-----|
| 값1 | 값2 |

금지사항:
- 글머리 기호(-) 사용 금지
- 1) 2) 3) 형식 금지
- 한 줄에 여러 항목 나열 금지

질문: """

# 사진 첨부
MAX_IMAGES = 3                      # 한 질문에 붙일 수 있는 사진 수
MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 한 장 원본 크기 상한
MAX_IMAGE_SIDE = 1600               # 긴 변을 이만큼으로 줄여 보내고 저장한다
ALLOWED_IMAGE_FORMATS = {"JPEG", "MPO", "PNG", "WEBP", "GIF", "BMP"}
PHOTO_ONLY_QUESTION = "이 사진을 보고 진단해 주세요."

PHOTO_NOTE = """

(질문과 함께 사진 {n}장을 첨부했습니다. 반드시 사진을 직접 보고 답하세요.
답변 맨 앞에 '### 사진 소견' 제목으로 사진에서 보이는 수종·부위·병징/표징·해충의 형태와 피해 양상을
구체적으로 적고, 그것을 근거로 가능성이 높은 진단, 감별할 대상, 현장에서 확인할 방법과 방제를 설명하세요.
사진만으로 확정하기 어려우면 그렇다고 밝히고 무엇을 더 찍어 보면 좋을지 알려 주세요.
사진이 수목과 관계없으면 보이는 것을 짧게 말하고 그 점을 알려 주세요.)"""


class ImageError(ValueError):
    """사용자에게 그대로 보여 줄 사진 오류"""


def _prepare_images(files):
    """올린 사진을 검사하고 줄여서 JPEG 바이트 목록으로 돌려준다."""
    if len(files) > MAX_IMAGES:
        raise ImageError(f"사진은 {MAX_IMAGES}장까지 올릴 수 있습니다.")

    prepared = []
    for f in files:
        if f.size > MAX_IMAGE_BYTES:
            raise ImageError(
                f"사진 한 장은 {MAX_IMAGE_BYTES // (1024 * 1024)}MB 까지 올릴 수 있습니다."
            )
        try:
            img = Image.open(f)
            if img.format not in ALLOWED_IMAGE_FORMATS:
                raise ImageError("JPG, PNG, WEBP 사진만 올릴 수 있습니다.")
            img = ImageOps.exif_transpose(img)  # 휴대폰 사진의 회전 정보를 반영
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            if img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=85, optimize=True)
        except ImageError:
            raise
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ImageError("사진 파일을 읽을 수 없습니다. 다른 사진으로 다시 시도해 주세요.")
        prepared.append(buf.getvalue())
    return prepared


def _ask_tree_doctor(user_input, images):
    """Gemini 에 질문(과 사진)을 넘기고 (HTML 답변, 성공 여부)를 돌려준다."""
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        chat_model_name = SiteSettings.get_chat_model()
        model = genai.GenerativeModel(chat_model_name)
        # 시스템 프롬프트와 사용자 질문 결합
        full_prompt = SYSTEM_PROMPT + user_input
        if images:
            full_prompt += PHOTO_NOTE.format(n=len(images))
        contents = [full_prompt] + [
            {"mime_type": "image/jpeg", "data": data} for data in images
        ]
        response = model.generate_content(contents)

        # Convert (1), (2), (3) to 1), 2), 3) format
        response_raw = response.text
        response_raw = re.sub(r'\((\d+)\)', r'\1)', response_raw)

        # Convert Markdown to HTML for display
        return markdown.markdown(response_raw, extensions=['tables', 'fenced_code']), True

    except Exception as e:
        return f"Error: {str(e)}", False


def _save_images(history, images):
    """줄인 사진을 기록에 붙이고 저장된 ChatImage 목록을 돌려준다."""
    saved = []
    for data in images:
        ci = ChatImage(history=history)
        ci.image.save(f"{uuid.uuid4().hex}.jpg", ContentFile(data), save=True)
        saved.append(ci)
    return saved


def _photos_html(chat_images):
    """게시글 본문 맨 위에 넣을 사진 마크업"""
    if not chat_images:
        return ""
    imgs = "".join(
        f'<a href="{ci.image.url}" target="_blank" rel="noopener">'
        f'<img src="{ci.image.url}" alt="질문 사진" '
        f'style="max-width:100%; max-height:420px; border-radius:8px; margin:0 8px 8px 0;"></a>'
        for ci in chat_images
    )
    return f'<div class="chat-photos" style="margin-bottom:16px;">{imgs}</div>\n\n'


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
        user_input = (request.POST.get("user_input") or "").strip()
        image_error = ""
        try:
            images = _prepare_images(request.FILES.getlist("images"))
        except ImageError as e:
            images, image_error = [], str(e)
        if images and not user_input:
            user_input = PHOTO_ONLY_QUESTION
        if image_error:
            response_text = image_error
        elif user_input:
            start_time = time.time()
            response_text, is_success = _ask_tree_doctor(user_input, images)

            end_time = time.time()
            response_time = end_time - start_time

            # Save to Database
            selected_history = ChatHistory.objects.create(
                user=request.user,
                user_input=user_input,
                ai_response=response_text,
                response_time=response_time,
                is_success=is_success,
            )
            chat_images = _save_images(selected_history, images)

            # Auto-create BBS Post (Tree Doctor) - 실패한 응답은 게시하지 않음
            if is_success:
                try:
                    from bbs.models import Post, PostType
                    import os

                    post_type, _ = PostType.objects.get_or_create(name="주치의 질의")

                    p = Post.objects.create(
                        author=request.user,
                        title=f"[나무주치의] {user_input}"[:200],
                        content=_photos_html(chat_images) + str(response_text),
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
        user_input = (request.POST.get("user_input") or "").strip()
        try:
            images = _prepare_images(request.FILES.getlist("images"))
        except ImageError as e:
            return JsonResponse({"error": str(e)}, status=400)
        if images and not user_input:
            user_input = PHOTO_ONLY_QUESTION
        if not user_input:
            return JsonResponse({"error": "No input provided"}, status=400)

        start_time = time.time()
        response_text, is_success = _ask_tree_doctor(user_input, images)

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
        chat_images = _save_images(history, images)

        # Auto-create BBS Post (Tree Doctor) - 실패한 응답은 게시하지 않음
        if is_success:
            try:
                from bbs.models import Post, PostType
                import os

                post_type, _ = PostType.objects.get_or_create(name="주치의")

                p = Post.objects.create(
                    author=request.user,
                    title=user_input[:200],
                    content=_photos_html(chat_images) + str(response_text),
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
                "image_urls": [ci.image.url for ci in chat_images],
            }
        )

    return JsonResponse({"error": "Invalid method"}, status=405)
