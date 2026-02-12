from django.db import models
from django.contrib.auth.models import User
import re
import base64
import uuid
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class Book(models.Model):
    """교재 정보"""
    name = models.CharField(max_length=200, verbose_name="교재명")
    subject = models.CharField(max_length=100, verbose_name="과목")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "교재"
        verbose_name_plural = "교재"
    
    def __str__(self):
        return f"{self.subject} - {self.name}"


class Chapter(models.Model):
    """계층적 목차 (대제목 > 중제목 > 소제목 > 부제목)"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters', verbose_name="교재")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children', verbose_name="상위 목차")
    code = models.CharField(max_length=50, verbose_name="목차 번호")  # "1.1.1"
    title = models.CharField(max_length=200, verbose_name="제목")
    level = models.IntegerField(default=1, verbose_name="단계")  # 1=대제목, 2=중제목, 3=소제목, 4=부제목
    order = models.IntegerField(default=0, verbose_name="순서")
    
    class Meta:
        verbose_name = "목차"
        verbose_name_plural = "목차"
        ordering = ['book', 'order', 'code']
    
    def __str__(self):
        return f"{self.code} {self.title}"
    
    def get_full_path(self):
        """목차 전체 경로 반환 (예: '1. 개요 > 1.1 정의')"""
        path = [self.title]
        parent = self.parent
        while parent:
            path.insert(0, parent.title)
            parent = parent.parent
        return " > ".join(path)
    
    def get_ancestors(self):
        """부모 목차들을 리스트로 반환 (최상위부터 순서대로, 자기 자신 제외)"""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.insert(0, parent)
            parent = parent.parent
        return ancestors
    
    def has_content(self):
        """챕터에 컨텐츠가 있는지 확인"""
        return hasattr(self, 'content') and self.content is not None


class PracticeQuestion(models.Model):
    """5지선다형 연습문제"""
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='questions', verbose_name="목차")
    number = models.IntegerField(default=1, verbose_name="문제 번호")
    content = models.TextField(verbose_name="문제 내용")
    choice1 = models.CharField(max_length=500, verbose_name="선지 1")
    choice2 = models.CharField(max_length=500, verbose_name="선지 2")
    choice3 = models.CharField(max_length=500, verbose_name="선지 3")
    choice4 = models.CharField(max_length=500, verbose_name="선지 4")
    choice5 = models.CharField(max_length=500, verbose_name="선지 5")
    answer = models.IntegerField(verbose_name="정답")  # 1-5
    explanation = models.TextField(blank=True, verbose_name="해설")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "연습문제"
        verbose_name_plural = "연습문제"
        ordering = ['chapter', 'number']
    
    def __str__(self):
        return f"{self.chapter.code} - 문제 {self.number}"


class PracticeAttempt(models.Model):
    """사용자 문제 풀이 기록"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practice_attempts')
    question = models.ForeignKey(PracticeQuestion, on_delete=models.CASCADE, related_name='attempts')
    selected_answer = models.IntegerField(verbose_name="선택한 답")
    is_correct = models.BooleanField(default=False, verbose_name="정답 여부")
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "풀이 기록"
        verbose_name_plural = "풀이 기록"
        ordering = ['-attempted_at']


class ChapterContent(models.Model):
    """목차별 학습 컨텐츠"""
    chapter = models.OneToOneField(
        Chapter, 
        on_delete=models.CASCADE, 
        related_name='content',
        verbose_name="목차"
    )
    content = models.TextField(verbose_name="내용")
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name="작성자",
        related_name='practice_contents'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    def save(self, *args, **kwargs):
        """저장 시 Base64 이미지를 파일로 자동 추출"""
        if self.content:
            self._extract_images()
        super().save(*args, **kwargs)

    def _extract_images(self):
        """본문 내 Base64 이미지를 추출하여 Media 파일로 저장"""
        pattern = re.compile(r'src="data:image/(?P<ext>png|jpeg|jpg|gif|webp);base64,(?P<data>[^"]+)"')
        
        replacement_count = 0
        
        def replace_match(match):
            nonlocal replacement_count
            ext = match.group('ext')
            data_str = match.group('data')
            
            # 파일명 생성
            filename = f"chapter_{self.chapter.id}_{uuid.uuid4().hex[:8]}.{ext}"
            upload_path = f"uploads/content_images/{filename}"
            
            try:
                img_data = base64.b64decode(data_str)
                saved_path = default_storage.save(upload_path, ContentFile(img_data))
                url = default_storage.url(saved_path)
                replacement_count += 1
                return f'src="{url}"'
            except Exception as e:
                # 에러 시 원본 유지
                return match.group(0)

        new_content, count = pattern.subn(replace_match, self.content)
        
        if count > 0:
            self.content = new_content
            
    class Meta:
        verbose_name = "학습 컨텐츠"
        verbose_name_plural = "학습 컨텐츠"
    
    def __str__(self):
        return f"{self.chapter.code} {self.chapter.title} - 컨텐츠"


class ChapterPost(models.Model):
    """목차와 BBS 게시글 연결"""
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='linked_posts',
        verbose_name="목차"
    )
    post = models.ForeignKey(
        'bbs.Post',
        on_delete=models.CASCADE,
        related_name='linked_chapters',
        verbose_name="게시글"
    )
    linked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="연결한 사람"
    )
    linked_at = models.DateTimeField(auto_now_add=True, verbose_name="연결일시")

    class Meta:
        verbose_name = "목차-게시글 연결"
        verbose_name_plural = "목차-게시글 연결"
        unique_together = ('chapter', 'post')
        ordering = ['-linked_at']

    def __str__(self):
        return f"{self.chapter.code} - {self.post.title}"
