from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, update_session_auth_hash, login, logout
from django.http import JsonResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import json
import string

from .forms import *


def start_page(request):
    """
    Стартовая страница с двумя кнопками: Sign up и Log in.
    """
    return render(request, 'start_page/start_page.html')


def signup(request):
    """
    Страница регистрации.
    - GET: показываем пустую форму
    - POST: проверяем форму, при успехе создаём пользователя и редиректим
    """
    allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', [])

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('main_page:main_page')
    else:
        form = RegisterForm()

    return render(request,'start_page/signup.html',
        {
            'form': form,
            'allowed_domains': allowed_domains,
        },
    )


def login_auth(request):
    """
    Авторизация:
     - GET: показать форму
    - POST: проверить данные, залогинить и отправить на main_page
    """
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("main_page:main_page")
    else:
        form = LoginForm()

    return render(request, "start_page/login.html", {"form": form})

