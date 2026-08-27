from django.urls import path
from . import views

app_name = "study"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:round_number>/", views.detail, name="detail"),
    path("subject/<str:subject_name>/", views.subject_detail, name="subject_detail"),
    path("tts/", views.tts_generate, name="tts_generate"),
    path("api/question/<int:question_id>/", views.api_question, name="api_question"),
    path("api/question/<int:question_id>/terms/", views.api_question_terms, name="api_question_terms"),
    path("api/question/<int:question_id>/update/", views.question_update, name="question_update"),
    # 기출분석 URLs
    path("analysis/", views.analysis_index, name="analysis_index"),
    path("analysis/<int:round_number>/", views.analysis_detail, name="analysis_detail"),
    # 주제별 학습 URLs
    path("topic/<int:set_id>/", views.topic_solve, name="topic_solve"),
    path("topic/<int:set_id>/result/<int:attempt_id>/", views.topic_result, name="topic_result"),
    # 주제별 문제집 관리
    path("topic-sets/", views.topic_set_list, name="topic_set_list"),
    path("topic-sets/create/", views.topic_set_create, name="topic_set_create"),
    path("topic-sets/<int:set_id>/edit/", views.topic_set_edit, name="topic_set_edit"),
    path("topic-sets/<int:set_id>/delete/", views.delete_topic_set, name="delete_topic_set"),
    path("api/exam_questions/", views.api_exam_questions, name="api_exam_questions"),
    path("api/questions_by_term/", views.api_questions_by_term, name="api_questions_by_term"),
    path("api/save_topic_set/", views.api_save_topic_set, name="api_save_topic_set"),
    path("api/reorder_topic_set/", views.api_reorder_topic_set, name="api_reorder_topic_set"),
    # 기본서 학습문제 관리
    path("practice-manage/", views.practice_manage, name="practice_manage"),
    # 쪽집게 노트
    path("notes/<int:subject_id>/", views.study_notes, name="study_notes"),
    path("notes/<int:subject_id>/study/", views.notes_study, name="notes_study"),
]
