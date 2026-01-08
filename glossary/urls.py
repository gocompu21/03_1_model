from django.urls import path
from . import views

app_name = 'glossary'

urlpatterns = [
    path('', views.term_list, name='term_list'),
    path('create/', views.term_create, name='term_create'),
    path('term/<int:pk>/', views.term_detail, name='term_detail'),
    path('term/<int:pk>/edit/', views.term_edit, name='term_edit'),
    path('term/<str:word>/', views.term_by_word, name='term_by_word'),
    path('subject/<int:pk>/', views.subject_terms, name='subject_terms'),
]
