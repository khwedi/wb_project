from django.urls import path
from . import views
from .profile_views import *

app_name = "main_page"

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('profile/', views.profile, name='profile'),
    path('profile/update-username/', update_username, name='update_username'),
]