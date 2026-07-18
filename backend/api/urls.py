from django.urls import path
from . import views

urlpatterns = [
    path('generate_roadmap', views.api_generate_roadmap, name='generate_roadmap'),
    path('compare_roles',    views.api_compare_roles,    name='compare_roles'),
]
