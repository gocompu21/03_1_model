from django.contrib import admin
from django.utils.html import format_html
from .models import Post, PostType, Comment


@admin.register(PostType)
class PostTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['author', 'created_at']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'type', 'author', 'hits', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['title', 'content', 'author__username']
    list_editable = ['type']
    readonly_fields = ['hits', 'created_at', 'updated_at']
    inlines = [CommentInline]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('type', 'title', 'author')
        }),
        ('내용', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('통계', {
            'fields': ('hits', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username', 'post__title']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '내용 미리보기'
