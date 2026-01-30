from django.urls import path
from . import views
from . import api_views

app_name = "exam"

urlpatterns = [
    # 웹 뷰 (기존)
    path("", views.exam_list, name="index"),
    path("take/<int:exam_id>/", views.exam_take, name="take"),
    path("submit/<int:exam_id>/", views.exam_submit, name="submit"),
    path("result/<int:attempt_id>/", views.exam_result, name="result"),
    path("retry/<int:attempt_id>/", views.retry_exam, name="retry"),
    path("question/list/", views.question_list, name="question_list"),
    path("question/add/", views.question_create, name="question_create"),
    path("question/edit/<int:pk>/", views.question_update, name="question_update"),
    path("question/delete/<int:pk>/", views.question_delete, name="question_delete"),

    # REST API (모바일 앱용)
    path("api/", api_views.exam_list, name="api_exam_list"),
    path("api/subjects/", api_views.subject_list, name="api_subject_list"),
    path("api/<int:exam_id>/", api_views.exam_detail, name="api_exam_detail"),
    path("api/<int:exam_id>/start/", api_views.exam_start, name="api_exam_start"),
    path("api/submit/<int:attempt_id>/", api_views.exam_submit, name="api_exam_submit"),
    path("api/result/<int:attempt_id>/", api_views.exam_result, name="api_exam_result"),
    path("api/my-attempts/", api_views.my_attempts, name="api_my_attempts"),
    path("api/topic-sets/", api_views.topic_set_list, name="api_topic_set_list"),
    path("api/topic-sets/<int:set_id>/", api_views.topic_set_detail, name="api_topic_set_detail"),
]
