"""녹화강의 — 사용자는 과목을 골라 보고, 관리자는 링크를 등록한다."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, F, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from exam.models import Subject

from .models import Lecture, LectureView


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

    # 내가 본 강의는 목록에 표시해 준다
    seen = {
        v.lecture_id: v
        for v in LectureView.objects.filter(user=request.user, lecture__in=lectures)
    }
    lectures = list(lectures)
    for lec in lectures:
        lec.my_view = seen.get(lec.id)

    return render(request, "lecture/index.html", {
        "subjects": subjects,
        "lectures": lectures,
        "current": current,
        "total": Lecture.objects.filter(is_active=True).count(),
        "seen_count": len(seen),
    })


@login_required
def watch(request, lecture_id):
    """시청 기록을 남기고 영상 주소로 보낸다.

    영상이 외부(네이버 등)에서 재생되므로 사이트가 알 수 있는 것은
    여기까지다. 실제로 몇 분을 봤는지는 확인할 방법이 없다.
    """
    lecture = get_object_or_404(Lecture, id=lecture_id, is_active=True)

    view, created = LectureView.objects.get_or_create(
        lecture=lecture, user=request.user, defaults={"count": 1}
    )
    if not created:
        # 경쟁 상태에서도 세기가 어긋나지 않도록 DB에서 직접 올린다
        LectureView.objects.filter(id=view.id).update(
            count=F("count") + 1, last_viewed_at=timezone.now()
        )

    return redirect(lecture.video_url)


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

    lectures = (
        Lecture.objects.select_related("subject")
        .annotate(
            viewer_count=Count("views", distinct=True),  # 본 사람 수
            play_count=Sum("views__count"),              # 누른 횟수 합
        )
        # annotate()가 Meta.ordering을 무너뜨린다. 다시 명시한다
        .order_by("-lecture_date", "period", "id")
    )

    return render(request, "lecture/manage.html", {
        "subjects": Subject.objects.order_by("code"),
        "lectures": lectures,
        "editing": _editing(request),
    })


@user_passes_test(_is_admin)
@never_cache
def stats(request):
    """시청 현황.

    영상이 외부에서 재생되므로 **시청 시간은 집계할 수 없다.**
    누가 어떤 강의를 몇 번 열었는지와 마지막 시청 시각까지가 한계다.
    """
    lectures = (
        Lecture.objects.select_related("subject")
        .annotate(
            viewer_count=Count("views", distinct=True),
            play_count=Sum("views__count"),
            last_at=Max("views__last_viewed_at"),
        )
        .order_by("-lecture_date", "period", "id")
    )

    # 사용자별 집계
    people = (
        LectureView.objects.values("user__id", "user__username", "user__first_name")
        .annotate(
            lecture_count=Count("lecture", distinct=True),
            play_count=Sum("count"),
            last_at=Max("last_viewed_at"),
        )
        .order_by("-lecture_count", "-play_count")
    )

    # 한 강의만 파고들 때
    focus_id = request.GET.get("lecture")
    focus, focus_rows = None, []
    if focus_id and focus_id.isdigit():
        focus = Lecture.objects.filter(id=focus_id).select_related("subject").first()
        if focus:
            focus_rows = (
                focus.views.select_related("user").order_by("-count", "-last_viewed_at")
            )

    total_plays = LectureView.objects.aggregate(n=Sum("count"))["n"] or 0

    return render(request, "lecture/stats.html", {
        "lectures": lectures,
        "people": people,
        "focus": focus,
        "focus_rows": focus_rows,
        "total_plays": total_plays,
        "total_viewers": LectureView.objects.values("user").distinct().count(),
        "lecture_total": Lecture.objects.count(),
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
