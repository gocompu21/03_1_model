from django.urls import path
from . import views

app_name = "exam"

urlpatterns = [
    path("", views.exam_list, name="index"),
    path("take/<int:exam_id>/", views.exam_take, name="take"),
    path("submit/<int:exam_id>/", views.exam_submit, name="submit"),
    path("result/<int:attempt_id>/", views.exam_result, name="result"),
    path("retry/<int:attempt_id>/", views.retry_exam, name="retry"),
    path("question/list/", views.question_list, name="question_list"),
    path("question/add/", views.question_create, name="question_create"),
    path("question/edit/<int:pk>/", views.question_update, name="question_update"),
    path("question/delete/<int:pk>/", views.question_delete, name="question_delete"),
]
