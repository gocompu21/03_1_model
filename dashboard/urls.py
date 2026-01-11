from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('print/', views.print_material, name='print_material'),
    path('print/exam/', views.exam_pdf, name='exam_pdf'),
    path('api/chapters/', views.get_chapters, name='get_chapters'),
    path('api/exam_questions/', views.get_exam_questions, name='get_exam_questions'),
]
