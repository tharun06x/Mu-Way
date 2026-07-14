from django.urls import path
from . import views

urlpatterns = [
    path('generate_roadmap', views.api_generate_roadmap, name='generate_roadmap'),
]
