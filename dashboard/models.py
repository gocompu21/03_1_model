from django.db import models


class SiteSettings(models.Model):
    """사이트 전역 설정 (싱글톤 패턴)"""

    # Gemini 모델 선택지
    GEMINI_MODEL_CHOICES = [
        ('gemini-3-pro-preview', 'Gemini 3 Pro Preview ($2/$12 per 1M)'),
        ('gemini-3-flash-preview', 'Gemini 3 Flash Preview ($0.5/$3 per 1M)'),
        ('gemini-2.5-flash', 'Gemini 2.5 Flash ($0.15/$0.60 per 1M)'),
        ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash Exp (Legacy)'),
    ]

    # 나무주치의 (Chat) API 모델
    chat_model = models.CharField(
        max_length=50,
        choices=GEMINI_MODEL_CHOICES,
        default='gemini-3-pro-preview',
        verbose_name='나무주치의 모델'
    )

    # 기본서 (Mypage) API 모델
    textbook_model = models.CharField(
        max_length=50,
        choices=GEMINI_MODEL_CHOICES,
        default='gemini-3-flash-preview',
        verbose_name='기본서 모델'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '사이트 설정'
        verbose_name_plural = '사이트 설정'

    def __str__(self):
        return '사이트 설정'

    def save(self, *args, **kwargs):
        # 싱글톤: pk를 항상 1로 고정
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """설정 인스턴스 반환 (없으면 생성)"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def get_chat_model(cls):
        """나무주치의 모델명 반환"""
        return cls.get_settings().chat_model

    @classmethod
    def get_textbook_model(cls):
        """기본서 모델명 반환"""
        return cls.get_settings().textbook_model
