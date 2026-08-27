from django.urls import path
from . import views
from . import pdf_views

app_name = 'practice'

urlpatterns = [
    path('', views.book_list, name='book_list'),
    path('<int:book_id>/', views.chapter_list, name='chapter_list'),
    path('chapter/<int:chapter_id>/', views.practice_questions, name='practice_questions'),
    path('chapter/<int:chapter_id>/detail/', views.chapter_detail, name='chapter_detail'),
    path('chapter/<int:chapter_id>/pdf/', pdf_views.chapter_pdf, name='chapter_pdf'),
    path('question/<int:question_id>/submit/', views.submit_answer, name='submit_answer'),
    path('upload/', views.upload_questions, name='upload_questions'),
    path('upload/chapters/', views.upload_chapters, name='upload_chapters'),
    path('content/create/', views.content_create, name='content_create'),
    path('content/<int:content_id>/edit/', views.content_update, name='content_update'),
    # BBS 게시글 연결 API
    path('chapter/<int:chapter_id>/api/search-posts/', views.api_search_bbs_posts, name='api_search_bbs_posts'),
    path('chapter/<int:chapter_id>/api/link-post/', views.api_link_post, name='api_link_post'),
    path('api/post/<int:post_id>/hit/', views.api_post_hit, name='api_post_hit'),
    path('chapter/<int:chapter_id>/api/unlink-post/', views.api_unlink_post, name='api_unlink_post'),
]

