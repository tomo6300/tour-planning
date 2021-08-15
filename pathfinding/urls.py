from django.urls import path
from . import views

app_name = 'pathfinding'
urlpatterns = [
    path('', views.index, name='index'),
]