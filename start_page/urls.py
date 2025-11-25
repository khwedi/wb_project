from django.urls import path, include
from . import views
from .password_reset_views import *

app_name = 'start_page'

urlpatterns = [
    path('', views.start_page, name='start_page'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_auth, name='login_auth'),
    path('logout/', views.logout_auth, name='logout_auth'),

    # password reset API
    path('password-reset/send-code/', password_reset_send_code, name='password_reset_send_code'),
    path('password-reset/verify-code/', password_reset_verify_code, name='password_reset_verify_code'),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
]