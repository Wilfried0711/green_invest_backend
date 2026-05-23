from django.urls import path
from . import views
urlpatterns = [
    path('status/', views.status),
    path('ndvi/', views.ndvi),
    path('ndvi/all/', views.ndvi_all),
    path('humidity/', views.humidity),
]
