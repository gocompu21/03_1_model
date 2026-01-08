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
    list_display = ['word', 'get_subjects', 'updated_at']
    list_filter = ['subjects']
    search_fields = ['word', 'content']
    filter_horizontal = ['subjects']
    inlines = [TermReferenceInline]
    
    def get_subjects(self, obj):
        return ", ".join([s.name for s in obj.subjects.all()])
    get_subjects.short_description = "관련 과목"


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
