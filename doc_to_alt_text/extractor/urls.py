from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_docx, name='upload_docx'),
    path('results/', views.view_results, name='view_results'),
]
