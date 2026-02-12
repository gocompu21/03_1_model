from django.contrib import admin
from .models import Book, Chapter, PracticeQuestion, PracticeAttempt, ChapterContent, ChapterPost


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'created_at']
    search_fields = ['name', 'subject']


class ChapterPostInline(admin.TabularInline):
    model = ChapterPost
    extra = 0
    autocomplete_fields = ['post']
    readonly_fields = ['linked_by', 'linked_at']


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'book', 'level', 'parent', 'order']
    list_filter = ['book', 'level']
    search_fields = ['code', 'title']
    ordering = ['book', 'order', 'code']
    inlines = [ChapterPostInline]


@admin.register(PracticeQuestion)
class PracticeQuestionAdmin(admin.ModelAdmin):
    list_display = ['chapter', 'number', 'content_short', 'answer']
    list_filter = ['chapter__book']
    search_fields = ['content', 'explanation']
    
    def content_short(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_short.short_description = '문제 내용'


@admin.register(PracticeAttempt)
class PracticeAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'selected_answer', 'is_correct', 'attempted_at']
    list_filter = ['is_correct', 'attempted_at']


@admin.register(ChapterContent)
class ChapterContentAdmin(admin.ModelAdmin):
    list_display = ['chapter', 'author', 'created_at', 'updated_at']
    list_filter = ['chapter__book', 'author']
    search_fields = ['chapter__code', 'chapter__title', 'content']


@admin.register(ChapterPost)
class ChapterPostAdmin(admin.ModelAdmin):
    list_display = ['chapter', 'post_title', 'post_type', 'linked_by', 'linked_at']
    list_filter = ['chapter__book', 'post__type', 'linked_at']
    search_fields = ['chapter__code', 'chapter__title', 'post__title']
    autocomplete_fields = ['chapter', 'post']
    readonly_fields = ['linked_at']

    def post_title(self, obj):
        return obj.post.title
    post_title.short_description = '게시글 제목'

    def post_type(self, obj):
        return obj.post.type.name if obj.post.type else '-'
    post_type.short_description = '게시글 유형'

