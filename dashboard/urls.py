from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('print/', views.print_material, name='print_material'),
    path('api/chapters/', views.get_chapters, name='get_chapters'),
]
