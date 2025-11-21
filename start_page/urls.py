from django.urls import path, include
from . import views

app_name = 'start_page'

urlpatterns = [
    path('', views.start_page, name='start_page'),
    path('signup/', views.signup, name='signup'),
]