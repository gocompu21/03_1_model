from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('print/', views.print_material, name='print_material'),
    path('print/exam/', views.exam_pdf, name='exam_pdf'),
    path('api/chapters/', views.get_chapters, name='get_chapters'),
    path('api/exam_questions/', views.get_exam_questions, name='get_exam_questions'),
    path('api/save_topic_set/', views.save_topic_set, name='save_topic_set'),
    path('topic-sets/', views.topic_set_list, name='topic_set_list'),
    path('topic-sets/<int:set_id>/', views.topic_set_solve, name='topic_set_solve'),
    path('topic-sets/result/<int:attempt_id>/', views.topic_set_result, name='topic_set_result'),
]
