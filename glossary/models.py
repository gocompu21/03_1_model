from django.db import models


class Subject(models.Model):
    """과목 (수목병리학, 수목생리학 등)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="과목명")
    
    class Meta:
        verbose_name = "과목"
        verbose_name_plural = "과목"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Term(models.Model):
    """용어 정의"""
    word = models.CharField(max_length=200, unique=True, verbose_name="용어")
    content = models.TextField(verbose_name="설명")
    subjects = models.ManyToManyField(
        Subject, 
        blank=True, 
        related_name='terms',
        verbose_name="관련 과목"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "용어"
        verbose_name_plural = "용어"
        ordering = ['word']
    
    def __str__(self):
        return self.word


class TermReference(models.Model):
    """용어가 링크된 위치 추적"""
    SOURCE_TYPES = [
        ('chapter_content', 'ChapterContent'),
        ('question', 'Question'),
        ('practice_question', 'PracticeQuestion'),
    ]
    
    term = models.ForeignKey(
        Term, 
        on_delete=models.CASCADE, 
        related_name='references',
        verbose_name="용어"
    )
    source_type = models.CharField(
        max_length=50, 
        choices=SOURCE_TYPES,
        verbose_name="출처 유형"
    )
    source_id = models.IntegerField(verbose_name="출처 ID")
    source_title = models.CharField(max_length=300, blank=True, verbose_name="출처 제목")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        verbose_name = "용어 참조"
        verbose_name_plural = "용어 참조"
        unique_together = ['term', 'source_type', 'source_id']
    
    def __str__(self):
        return f"{self.term.word} - {self.source_type}:{self.source_id}"
