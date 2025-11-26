from django.urls import path, include
from . import views

app_name = 'start_page'

urlpatterns = [
    path('', views.start_page, name='start_page'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_auth, name='login_auth'),
    path('logout/', views.logout_auth, name='logout_auth'),

    # Универсальные эндпоинты email-кода:
    path("email-code/send/<str:scenario>/", views.send_code, name="send_code"),
    path("email-code/verify/<str:scenario>/", views.verify_code, name="verify_code"),
    path("email-code/confirm/<str:scenario>/", views.confirm_code, name="confirm_code"),
]