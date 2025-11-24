from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from start_page.services import create_or_update_user_session


@login_required
def main_page(request):
    """
    Основная страница.
    Проверку и продление UserSession делает middleware.
    Если сессия истекла, middleware разлогинит и отправит на start_page.
    """
    return render(request, "main_page/main_page.html")
