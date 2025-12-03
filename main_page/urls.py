from django.urls import path
from . import views
from .profile_views import *
from .cabinet_views import *

app_name = "main_page"

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('profile/', views.profile, name='profile'),

    #------------- кнопки для изменения почты, имени или пароля -------------
    path('profile/update-username/', update_username, name='update_username'),
    path("profile/change-password/", change_password_profile, name="change_password_profile"),

    # --- Кабинеты ---
    path("cabinets/list/", cabinets_list, name="cabinets_list"),
    path("cabinets/add/", cabinets_add, name="cabinets_add"),
    path("cabinets/delete/", cabinets_delete, name="cabinets_delete"),
    path("cabinets/check/", cabinets_check, name="cabinets_check"),
    path("cabinets/update/", cabinets_update, name="cabinets_update"),
]