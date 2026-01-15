from django.contrib import admin
from .models import Subject, Term, TermReference


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class TermReferenceInline(admin.TabularInline):
    model = TermReference
    extra = 0
    readonly_fields = ['source_type', 'source_id', 'source_title', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ['word', 'canonical_term', 'get_synonyms_count', 'get_subjects', 'updated_at']
    list_filter = ['subjects', ('canonical_term', admin.EmptyFieldListFilter)]
    search_fields = ['word', 'content']
    filter_horizontal = ['subjects']
    autocomplete_fields = ['canonical_term']
    inlines = [TermReferenceInline]
    
    fieldsets = (
        (None, {
            'fields': ('word', 'content')
        }),
        ('유사어 설정', {
            'fields': ('canonical_term',),
            'description': '이 용어가 다른 용어의 유사어인 경우, 대표 용어를 선택하세요.'
        }),
        ('분류', {
            'fields': ('subjects',)
        }),
    )
    
    def get_subjects(self, obj):
        return ", ".join([s.name for s in obj.subjects.all()])
    get_subjects.short_description = "관련 과목"
    
    def get_synonyms_count(self, obj):
        count = obj.synonyms.count()
        if count > 0:
            return f"📌 {count}개"
        return "-"
    get_synonyms_count.short_description = "유사어"


@admin.register(TermReference)
class TermReferenceAdmin(admin.ModelAdmin):
    list_display = ['term', 'source_type', 'source_id', 'source_title', 'created_at']
    list_filter = ['source_type']
    search_fields = ['term__word', 'source_title']
    readonly_fields = ['term', 'source_type', 'source_id', 'source_title', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
