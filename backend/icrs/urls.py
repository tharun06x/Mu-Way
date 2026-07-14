from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
]

# Fallback for React router
if (settings.BASE_DIR.parent / 'frontend' / 'dist').exists():
    urlpatterns += [
        re_path(r'^.*', TemplateView.as_view(template_name='index.html')),
    ]
