from django.urls import path, include
from . import views

app_name = 'start_page'

urlpatterns = [
    path('', views.start_page, name='start_page'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_auth, name='login_auth'),
    path('logout/', views.logout_auth, name='logout_auth'),
]