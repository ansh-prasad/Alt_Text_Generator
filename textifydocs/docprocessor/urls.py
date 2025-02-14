from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('results/<int:doc_id>/', views.results, name='results'),
]