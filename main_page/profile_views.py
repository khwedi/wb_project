from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError

from start_page.validators import validate_username, validate_password
from start_page.code_confirm_views import json_error
from start_page.messages import *


@login_required
@require_POST
def update_username(request):
    """
    AJAX-обновление имени пользователя.
    Принимает POST 'username', валидирует и сохраняет.
    """
    new_username = request.POST.get("username", "").strip()

    try:
        validated = validate_username(new_username)
    except ValidationError as exc:
        return json_error(str(exc))

    user = request.user
    user.username = validated
    user.save(update_fields=["username"])

    return JsonResponse({"ok": True, "username": user.username})


@login_required
@require_POST
def change_password_profile(request):
    """
    Смена пароля из профиля:
    - проверяем текущий пароль
    - валидируем новый через validate_password
    - сохраняем
    - обновляем session auth hash, чтобы не разлогинивать пользователя
    """
    user = request.user

    current_password = request.POST.get("current_password", "") or ""
    password1 = request.POST.get("password1", "") or ""
    password2 = request.POST.get("password2", "") or ""

    if not current_password or not password1 or not password2:
        return json_error(PASSWORD_ERROR_MESSAGES["empty_fields"])

    if not user.check_password(current_password):
        return json_error(PASSWORD_ERROR_MESSAGES["current_wrong"])

    if password1 != password2:
        return json_error(PASSWORD_ERROR_MESSAGES["new_mismatch"])

    try:
        validate_password(password1)
    except ValidationError as exc:
        msg = "; ".join(exc.messages)
        json_error(msg)

    user.set_password(password1)
    user.save(update_fields=["password"])
    update_session_auth_hash(request, user)

    return JsonResponse({"ok": True})
