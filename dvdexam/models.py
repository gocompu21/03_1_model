"""DVD 시험 — 수목·병해·해충 암기 데이터로 보는 시험.

관리자가 시험을 등록하면 응시자가 풀고 제출한다.
문제는 등록 시점에 암기 데이터에서 무작위로 뽑아 고정한다.
"""

import random

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Exam(models.Model):
    """관리자가 등록하는 시험."""

    SUBJECT_CHOICES = [
        ("tree", "수목"),
        ("disease", "병해"),
        ("pest", "해충"),
    ]
    KIND_CHOICES = [
        ("always", "상시시험"),
        ("live", "실시간 시험"),
    ]
    FORMAT_CHOICES = [
        ("choice", "객관식형"),
        ("typing", "주관식형"),
    ]

    title = models.CharField(max_length=120, verbose_name="시험명")
    subject = models.CharField(
        max_length=10, choices=SUBJECT_CHOICES, verbose_name="학습대상"
    )
    kind = models.CharField(
        max_length=10, choices=KIND_CHOICES, default="always", verbose_name="시험유형"
    )
    answer_format = models.CharField(
        max_length=10, choices=FORMAT_CHOICES, default="choice", verbose_name="선택유형"
    )

    question_count = models.IntegerField(default=20, verbose_name="문항 수")
    time_limit_min = models.IntegerField(
        default=0, verbose_name="제한 시간(분)", help_text="0이면 제한 없음"
    )

    # 실시간 시험 전용
    start_at = models.DateTimeField(null=True, blank=True, verbose_name="시작 시각")
    end_at = models.DateTimeField(null=True, blank=True, verbose_name="종료 시각")

    is_active = models.BooleanField(default=True, verbose_name="공개")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_dvd_exams", verbose_name="등록자",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DVD 시험"
        verbose_name_plural = "DVD 시험"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_subject_display()}] {self.title}"

    # ---- 실시간 시험 상태 ----

    @property
    def is_live(self):
        return self.kind == "live"

    @property
    def live_state(self):
        """실시간 시험의 현재 상태: before / open / closed."""
        if not self.is_live:
            return "open"
        now = timezone.now()
        if self.start_at and now < self.start_at:
            return "before"
        if self.end_at and now > self.end_at:
            return "closed"
        return "open"

    @property
    def is_open(self):
        """지금 응시할 수 있는지."""
        return self.is_active and self.live_state == "open"

    def deadline_for(self, attempt):
        """이 응시가 끝나야 하는 시각. 없으면 None.

        실시간 시험은 종료 시각과 개인 제한 시간 중 이른 쪽이다.

        제한 시간은 **이번에 풀기 시작한 시각**부터 잰다. 재응시라면
        retrying_since가 그 기준이다. 첫 응시의 started_at을 쓰면
        오래전에 시험을 본 사람은 재응시하는 순간 이미 마감이 지나
        곧바로 자동 제출되어 버린다.
        """
        limits = []
        if self.time_limit_min:
            begun = attempt.retrying_since or attempt.started_at
            limits.append(begun + timezone.timedelta(minutes=self.time_limit_min))
        if self.is_live and self.end_at:
            limits.append(self.end_at)
        return min(limits) if limits else None


class ExamQuestion(models.Model):
    """시험에 담긴 문제 한 개.

    암기 데이터의 종을 가리키되, 정답과 보기는 등록 시점에 확정해 둔다.
    원본이 바뀌어도 이미 치른 시험의 채점이 흔들리지 않게 하기 위해서다.
    """

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="questions", verbose_name="시험"
    )
    order = models.IntegerField(default=0, verbose_name="번호")

    source_id = models.IntegerField(verbose_name="원본 문제 ID")
    image_url = models.CharField(max_length=300, verbose_name="사진 경로")
    answer = models.CharField(max_length=200, verbose_name="정답")
    choices = models.JSONField(default=list, blank=True, verbose_name="보기 5개")

    class Meta:
        verbose_name = "DVD 시험 문제"
        verbose_name_plural = "DVD 시험 문제"
        ordering = ["exam", "order", "id"]

    def __str__(self):
        return f"{self.exam.title} #{self.order} - {self.answer}"

    def is_correct(self, given):
        """공백을 무시하고 정답과 비교한다."""
        return (given or "").replace(" ", "") == self.answer.replace(" ", "")


class ExamAttempt(models.Model):
    """응시 기록. 사용자 한 명이 시험 하나를 한 번 본다."""

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name="attempts", verbose_name="시험"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="dvd_exam_attempts", verbose_name="응시자"
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="시작 시각")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="제출 시각")
    score = models.IntegerField(default=0, verbose_name="맞은 개수")
    total = models.IntegerField(default=0, verbose_name="문항 수")
    auto_submitted = models.BooleanField(default=False, verbose_name="시간 종료 제출")

    class Meta:
        verbose_name = "DVD 시험 응시"
        verbose_name_plural = "DVD 시험 응시"
        unique_together = ("exam", "user")
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} - {self.exam.title} ({self.score}/{self.total})"

    last_saved_at = models.DateTimeField(null=True, blank=True, verbose_name="마지막 저장")
    # 재응시 중에는 이전 결과를 그대로 두고, 제출할 때만 갱신한다.
    # 중간에 그만두면 지난 점수가 남는다.
    retrying_since = models.DateTimeField(
        null=True, blank=True, verbose_name="재응시 시작",
        help_text="값이 있으면 재응시 진행 중",
    )

    # 응시를 시작해 놓고 이 시간이 지나도록 제출하지 않으면 버린 것으로 본다.
    # 첫 응시는 기록을 지우고, 재응시는 이전 기록으로 되돌린다
    ABANDON_HOURS = 1
    RETRY_ABANDON_HOURS = ABANDON_HOURS  # 예전 이름 (같은 값)

    @property
    def is_retrying(self):
        return self.retrying_since is not None

    @property
    def is_stale(self):
        """제출하지 않은 채 방치된 시간이 기준을 넘었는지."""
        if self.is_submitted and not self.is_retrying:
            return False  # 이미 제출을 마친 기록은 건드리지 않는다
        started = self.retrying_since or self.started_at
        return timezone.now() - started >= timezone.timedelta(hours=self.ABANDON_HOURS)

    def drop_stale_retry(self):
        """방치된 재응시를 폐기하고 이전 기록으로 되돌린다.

        재응시를 시작한 지 기준 시간이 지나도록 제출하지 않았으면 그 답안을
        지운다. 지난 점수·제출 시각은 손대지 않았으므로 그대로 살아난다.
        폐기했으면 True.
        """
        if not self.retrying_since:
            return False
        limit = timezone.timedelta(hours=self.ABANDON_HOURS)
        if timezone.now() - self.retrying_since < limit:
            return False

        self.answers.all().delete()
        self.retrying_since = None
        self.last_saved_at = None
        self.save(update_fields=["retrying_since", "last_saved_at"])
        return True

    def drop_if_stale(self):
        """방치된 응시를 정리한다.

        - 재응시 중이면 폐기하고 지난 기록을 되살린다
        - 첫 응시(제출 이력 없음)면 되돌릴 것이 없으므로 응시를 지운다

        정리했으면 True. 첫 응시를 지운 경우 이 객체는 DB에 없다.
        """
        if not self.is_stale:
            return False
        if self.is_retrying:
            return self.drop_stale_retry()
        if not self.is_submitted:
            self.delete()  # 답안은 CASCADE로 함께 사라진다
            return True
        return False

    @classmethod
    def sweep_stale(cls, exam=None):
        """방치된 응시를 한꺼번에 정리한다. 정리한 건수를 돌려준다."""
        limit = timezone.now() - timezone.timedelta(hours=cls.ABANDON_HOURS)
        qs = cls.objects.all()
        if exam is not None:
            qs = qs.filter(exam=exam)

        n = 0
        # 재응시: 답안만 지우고 지난 기록으로 되돌린다
        for a in qs.filter(retrying_since__lt=limit):
            n += bool(a.drop_stale_retry())
        # 첫 응시: 제출하지 않은 채 방치됐으면 응시를 지운다
        first = qs.filter(
            retrying_since__isnull=True, submitted_at__isnull=True,
            started_at__lt=limit,
        )
        # delete()가 돌려주는 수는 답안까지 합친 것이라 응시 수를 따로 센다
        n += first.count()
        first.delete()
        return n

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    @property
    def score_percent(self):
        return round(self.score * 100 / self.total) if self.total else 0

    @property
    def elapsed_seconds(self):
        """소요 시간(초). 제출 전이면 지금까지 걸린 시간.

        재응시 중이면 그 시작 시각부터 잰다(지난 기록의 시간이 아니라).
        """
        if self.retrying_since:
            return max(0, int((timezone.now() - self.retrying_since).total_seconds()))
        end = self.submitted_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds()))

    @property
    def elapsed_display(self):
        """소요 시간을 '12분 34초' 형태로."""
        seconds = self.elapsed_seconds
        hours, rest = divmod(seconds, 3600)
        minutes, secs = divmod(rest, 60)
        if hours:
            return f"{hours}시간 {minutes}분"
        if minutes:
            return f"{minutes}분 {secs}초"
        return f"{secs}초"

    @property
    def answered_count(self):
        """응답을 채운 문항 수 (제출 전에도 센다)."""
        return self.answers.exclude(given="").count()

    @property
    def answer_percent(self):
        """응답률."""
        total = self.total or self.exam.questions.count()
        return round(self.answered_count * 100 / total) if total else 0


class ExamAnswer(models.Model):
    """문항별 응답."""

    attempt = models.ForeignKey(
        ExamAttempt, on_delete=models.CASCADE, related_name="answers", verbose_name="응시"
    )
    question = models.ForeignKey(
        ExamQuestion, on_delete=models.CASCADE, related_name="answers", verbose_name="문제"
    )
    given = models.CharField(max_length=200, blank=True, default="", verbose_name="응답")
    is_correct = models.BooleanField(default=False, verbose_name="정답 여부")

    class Meta:
        verbose_name = "DVD 시험 응답"
        verbose_name_plural = "DVD 시험 응답"
        unique_together = ("attempt", "question")
        ordering = ["question__order"]

    def __str__(self):
        return f"{self.attempt.user.username} Q{self.question.order}"


# ---------------------------------------------------------------- 출제

def source_pool(subject):
    """학습대상별 (문제 목록, 이름 뽑는 함수) 반환."""
    if subject == "tree":
        from treeid.models import TreeQuestion
        qs = TreeQuestion.objects.filter(course__is_active=True).exclude(name="")
    elif subject == "disease":
        from diseaseid.models import DiseaseQuestion
        qs = DiseaseQuestion.objects.filter(course__is_active=True).exclude(name="")
    else:
        from pestid.models import PestQuestion
        qs = PestQuestion.objects.filter(course__is_active=True).exclude(name="")
    return list(qs)


# 해충 이름의 끝 어미. 오답 보기를 같은 무리에서 뽑기 위한 기준이다.
# 긴 것부터 맞춰야 '밤나방'이 '나방'에 먼저 걸리지 않는다.
PEST_GROUPS = [
    "가루이", "거위벌레", "거품벌레", "굴파리", "깍지벌레", "나무이", "나무좀",
    "노린재", "대벌레", "땅강아지", "매미충", "매미", "면충", "명나방", "무당벌레",
    "바구미", "박각시", "방패벌레", "밤나방", "번데기", "불나방", "선녀벌레",
    "솜벌레", "쐐기나방", "여치", "응애", "잎벌레", "잎벌", "자나방", "재주나방",
    "잎말이나방", "진딧물", "총채벌레", "풍뎅이", "하늘소", "혹파리", "혹벌",
    "알락나방", "독나방", "나방",
]


def group_key(subject, question):
    """오답 보기를 같은 무리에서 뽑기 위한 묶음 키.

    - 해충: 이름 끝 어미 (나방 / 잎벌레 / 깍지벌레 / 진딧물 …)
    - 병해: 병명 끝 단어 (흰가루병 / 녹병 / 점무늬병 …)
    - 수목: 코스 (분류 순서대로 10종씩 묶여 있다)
    """
    name = (question.name or "").split(",")[0].strip()

    if subject == "pest":
        for suffix in PEST_GROUPS:
            if name.endswith(suffix):
                return suffix
        return None

    if subject == "disease":
        return name.split()[-1] if " " in name else name

    return f"course:{question.course_id}"


def build_questions(exam):
    """암기 데이터에서 무작위로 뽑아 시험 문제를 만든다.

    객관식 오답은 **같은 무리**에서 먼저 채운다. 나방 문제에는 나방을,
    깍지벌레 문제에는 깍지벌레를 붙여야 실제 시험처럼 변별이 된다.
    같은 무리가 모자라면 전체에서 채운다.
    """
    pool = source_pool(exam.subject)
    if not pool:
        return 0

    picked = random.sample(pool, min(exam.question_count, len(pool)))

    # 이름 목록과 무리별 이름 목록을 미리 만든다
    all_names, by_group = set(), {}
    for q in pool:
        name = q.name.split(",")[0].strip()
        if not name:
            continue
        all_names.add(name)
        key = group_key(exam.subject, q)
        if key:
            by_group.setdefault(key, set()).add(name)

    created = 0
    for i, src in enumerate(picked, 1):
        answer = src.name.split(",")[0].strip()
        choices = []

        if exam.answer_format == "choice":
            choices = _pick_choices(answer, group_key(exam.subject, src), by_group, all_names)

        ExamQuestion.objects.create(
            exam=exam,
            order=i,
            source_id=src.id,
            image_url=src.image.url,
            answer=answer,
            choices=choices,
        )
        created += 1

    return created


def _pick_choices(answer, key, by_group, all_names, count=4):
    """오답 4개를 고른다. 같은 무리를 우선하고 모자라면 전체에서 채운다."""
    same = [n for n in by_group.get(key, ()) if n != answer]
    random.shuffle(same)
    wrong = same[:count]

    if len(wrong) < count:
        rest = [n for n in all_names if n != answer and n not in wrong]
        random.shuffle(rest)
        wrong += rest[: count - len(wrong)]

    options = wrong + [answer]
    random.shuffle(options)
    return options
