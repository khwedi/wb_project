from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError

from start_page.validators import validate_username


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
        return JsonResponse(
            {"ok": False, "error": str(exc)},
            status=400,
        )

    user = request.user
    user.username = validated
    user.save(update_fields=["username"])

    return JsonResponse({"ok": True, "username": user.username})