from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/predict/', views.api_predict, name='api_predict'),
    path('history/', views.history_view, name='history'),
]
