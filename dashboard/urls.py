from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('print/', views.print_material, name='print_material'),
    path('print/exam/', views.exam_pdf, name='exam_pdf'),
    path('api/chapters/', views.get_chapters, name='get_chapters'),
    path('api/exam_questions/', views.get_exam_questions, name='get_exam_questions'),
    
    # 기본서 내용 생성 및 연습문제 자동 출제
    path('textbook/', views.textbook_generator, name='textbook_generator'),
    path('api/textbook/content/', views.api_get_textbook_content, name='api_get_textbook_content'),
    path('api/textbook/quiz/', views.api_generate_quiz, name='api_generate_quiz'),
    path('api/textbook/save-content/', views.api_save_content, name='api_save_content'),
    path('api/textbook/load-content/', views.api_load_content, name='api_load_content'),
    path('api/textbook/save-quiz/', views.api_save_quiz, name='api_save_quiz'),
    path('api/textbook/image/', views.api_generate_textbook_image, name='api_generate_textbook_image'),
    path('api/textbook/format-content/', views.api_format_textbook_content, name='api_format_textbook_content'),
    
    # 이미지 생성 연구소 (Image Lab)
    path('image-lab/', views.image_generator, name='image_generator'),
    path('api/image-lab/generate/', views.api_generate_image_variations, name='api_generate_image_variations'),
    path('api/image-lab/text-to-image/', views.api_generate_image_from_text, name='api_generate_image_from_text'),
]

