"""녹화강의 — 사용자는 과목을 골라 보고, 관리자는 링크를 등록한다."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from exam.models import Subject

from .models import Lecture


def _is_admin(user):
    return user.is_authenticated and user.is_staff


# ---------------------------------------------------------------- 사용자

@login_required
@never_cache
def index(request):
    """과목을 골라 강의를 본다.

    ?subject=<code> 로 과목을 좁힌다. 없으면 전체를 보여준다.
    """
    subjects = list(
        Subject.objects.annotate(
            lecture_count=Count("lectures", filter=Q(lectures__is_active=True))
        ).order_by("code")
    )

    lectures = Lecture.objects.filter(is_active=True).select_related("subject")

    code = request.GET.get("subject")
    current = None
    if code and code.isdigit():
        current = next((s for s in subjects if s.code == int(code)), None)
        if current:
            lectures = lectures.filter(subject=current)

    return render(request, "lecture/index.html", {
        "subjects": subjects,
        "lectures": lectures,
        "current": current,
        "total": Lecture.objects.filter(is_active=True).count(),
    })


# ---------------------------------------------------------------- 관리자

@user_passes_test(_is_admin)
@never_cache
def manage(request):
    """강의 등록·수정·삭제."""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            target = get_object_or_404(Lecture, id=request.POST.get("id"))
            target.delete()
            messages.success(request, "강의를 삭제했습니다.")
            return redirect("lecture:manage")

        if action == "toggle":
            target = get_object_or_404(Lecture, id=request.POST.get("id"))
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            messages.success(
                request, f"'{target.title}' 을(를) {'공개' if target.is_active else '비공개'}로 바꿨습니다."
            )
            return redirect("lecture:manage")

        error = _save(request)
        if error:
            messages.error(request, error)
        return redirect("lecture:manage")

    return render(request, "lecture/manage.html", {
        "subjects": Subject.objects.order_by("code"),
        "lectures": Lecture.objects.select_related("subject").all(),
        "editing": _editing(request),
    })


def _editing(request):
    """?edit=<id> 로 지목한 강의. 수정 폼을 채우는 데 쓴다."""
    edit_id = request.GET.get("edit")
    if not edit_id or not edit_id.isdigit():
        return None
    return Lecture.objects.filter(id=edit_id).select_related("subject").first()


def _save(request):
    """등록 또는 수정. 문제가 있으면 안내 문구를 돌려준다."""
    subject_id = request.POST.get("subject")
    date = request.POST.get("lecture_date")
    title = (request.POST.get("title") or "").strip()
    url = (request.POST.get("video_url") or "").strip()

    if not (subject_id and date and title and url):
        return "과목·일시·내용·영상 링크는 모두 채워야 합니다."

    subject = Subject.objects.filter(id=subject_id).first()
    if not subject:
        return "과목을 다시 선택해 주세요."

    fields = {
        "subject": subject,
        "lecture_date": date,
        "period": _int(request.POST.get("period"), 1),
        "title": title[:200],
        "duration_min": _int(request.POST.get("duration_min"), 0),
        "video_url": url[:500],
        "note": (request.POST.get("note") or "").strip(),
        "is_active": request.POST.get("is_active") == "on",
    }

    edit_id = request.POST.get("id")
    if edit_id:
        target = Lecture.objects.filter(id=edit_id).first()
        if not target:
            return "수정할 강의를 찾지 못했습니다."
        for key, value in fields.items():
            setattr(target, key, value)
        target.save()
        messages.success(request, f"'{target.title}' 을(를) 수정했습니다.")
        return None

    lecture = Lecture.objects.create(created_by=request.user, **fields)
    messages.success(request, f"'{lecture.title}' 을(를) 등록했습니다.")
    return None


def _int(value, default):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default
