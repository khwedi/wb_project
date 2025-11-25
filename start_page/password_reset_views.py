import random
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.utils import timezone

from .models import CustomUser, PasswordResetRequest
from .validators import validate_email, validate_password


PASSWORD_RESET_MESSAGES = {
    "cooldown": "Слишком частые запросы кода. Попробуйте через {seconds} секунд.",
    "session_expired": "Сессия восстановления пароля истекла. Попробуйте ещё раз.",
    "code_invalid": "Код недействителен. Запросите новый код.",
    "code_expired": "Срок действия кода истёк. Запросите новый код.",
    "code_mismatch": "Код не совпадает.",
    "passwords_mismatch": "Пароли не совпадают.",
}


def _generate_reset_code():
    """
    Генерируем шестизначный код.
    """
    return f"{random.randint(0, 999999):06d}"


def _get_cooldown_seconds(attempts_so_far):
    """
    Attempts_so_far — сколько попыток уже было УСПЕШНО сделано.
    0 → первая попытка (без задержки)
    1 → между 1 и 2 → 30 секунд
    2 → между 2 и 3 → 5 минут
    >=3 → 10 минут
    """
    if attempts_so_far == 0:
        return 0
    elif attempts_so_far == 1:
        return 30
    elif attempts_so_far == 2:
        return 300
    else:
        return 600


@require_POST
def password_reset_send_code(request):
    """
    Шаг 1: пользователь вводит email.
    - Валидируем email (формат + домен + что пользователь существует).
    - Создаём или обновляем PasswordResetRequest.
    - Отправляем код на почту.
    - В сессии сохраняем id пользователя, чтобы дальше не передавать email туда-сюда.

    Лимиты попыток:
    - первая попытка — сразу;
    - между 1 и 2 -> 30 секунд;
    - между 2 и 3 -> 5 минут;
    - 4-я и далее -> каждая через 10 минут.

    Счётчик и время последней попытки лежат в request.session.
    """
    email = request.POST.get("email", "")

    # --- проверяем лимиты попыток ---
    now = timezone.now()
    attempts = request.session.get("password_reset_attempts", 0)
    last_at_str = request.session.get("password_reset_last_attempt_at")

    if last_at_str:
        try:
            last_at = timezone.datetime.fromisoformat(last_at_str)
        except ValueError:
            last_at = None
    else:
        last_at = None

    if last_at is not None:
        cooldown = _get_cooldown_seconds(attempts_so_far=attempts)
        if cooldown > 0:
            elapsed = (now - last_at).total_seconds()
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                msg = PASSWORD_RESET_MESSAGES["cooldown"].format(seconds=remaining)
                return JsonResponse(
                    {
                        "ok": False,
                        "code": "cooldown",
                        "error": msg,
                        "remaining_seconds": remaining,
                    },
                    status=429,
                )

    try:
        email_normalized = validate_email(email, type='login')
    except ValidationError as exc:
        return JsonResponse({"ok": False, "code": "email_error", "error": str(exc)}, status=400)

    user = CustomUser.objects.get(email__iexact=email_normalized)

    # инвалидируем старые запросы
    PasswordResetRequest.objects.filter(
        user=user,
        is_used=False,
    ).update(is_used=True)

    code = _generate_reset_code()
    expires_at = now + timedelta(minutes=10)  # код действует 10 минут

    reset_req = PasswordResetRequest.objects.create(
        user=user,
        code=code,
        expires_at=expires_at,
    )

    # обновляем данные попыток в сессии
    attempts += 1
    request.session["password_reset_attempts"] = attempts
    request.session["password_reset_last_attempt_at"] = now.isoformat()

    # сохраняем в сессии, что этот пользователь сейчас проходит процедуру сброса
    request.session["password_reset_user_id"] = user.id
    request.session["password_reset_request_id"] = reset_req.id
    request.session["password_reset_verified"] = False

    # отправляем письмо
    send_mail(
        subject="Код для восстановления пароля",
        message=f"Ваш код для восстановления пароля: {code}\nКод действителен 10 минут.",
        from_email=None,  # возьмётся DEFAULT_FROM_EMAIL из settings
        recipient_list=[user.email],
    )

    # на фронт отдадим, сколько секунд ждать до следующей попытки
    next_cooldown = _get_cooldown_seconds(attempts_so_far=attempts)
    return JsonResponse({"ok": True, "cooldown_seconds": next_cooldown, "attempts": attempts})


@require_POST
def password_reset_verify_code(request):
    """
    Шаг 2: пользователь вводит код из письма.
    - Берём user_id и request_id из сессии.
    - Проверяем, что код совпадает, не истёк, не использован.
    - Если всё ок — ставим флаг password_reset_verified=True в сессии.
    """
    user_id = request.session.get("password_reset_user_id")
    req_id = request.session.get("password_reset_request_id")
    code_input = request.POST.get("code", "").strip()

    if not user_id or not req_id:
        return JsonResponse(
            {"ok": False, "error": PASSWORD_RESET_MESSAGES["session_expired"]},
            status=400,
        )

    try:
        reset_req = PasswordResetRequest.objects.select_related("user").get(
            id=req_id,
            user_id=user_id,
            is_used=False,
        )
    except PasswordResetRequest.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": PASSWORD_RESET_MESSAGES["code_invalid"]},
            status=400,
        )

    if reset_req.is_expired:
        reset_req.is_used = True
        reset_req.save(update_fields=["is_used"])
        return JsonResponse(
            {"ok": False, "error": PASSWORD_RESET_MESSAGES["code_expired"]},
            status=400,
        )

    if reset_req.code != code_input:
        return JsonResponse(
            {"ok": False, "error": PASSWORD_RESET_MESSAGES["code_mismatch"]},
            status=400,
        )

    request.session["password_reset_verified"] = True
    return JsonResponse({"ok": True})


@require_POST
def password_reset_confirm(request):
    """
    Шаг 3: пользователь вводит новый пароль дважды.
    - Проверяем, что есть user_id + verified=True в сессии.
    - Валидируем пароль (через validate_password).
    - Проверяем совпадение двух паролей.
    - Обновляем пароль пользователя.
    - Помечаем запрос как использованный.
    - Чистим данные восстановления из сессии.
    """
    user_id = request.session.get("password_reset_user_id")
    req_id = request.session.get("password_reset_request_id")
    verified = request.session.get("password_reset_verified", False)

    if not user_id or not req_id or not verified:
        return JsonResponse(
            {"ok": False, "error": PASSWORD_RESET_MESSAGES["session_expired"]},
            status=400,
        )

    password1 = request.POST.get("password1", "")
    password2 = request.POST.get("password2", "")

    if password1.strip() != password2.strip():
        return JsonResponse(
            {"ok": False, "error": PASSWORD_RESET_MESSAGES["passwords_mismatch"]},
            status=400,
        )

    try:
        validate_password(password1)
    except ValidationError as exc:
        error_text = "; ".join(exc.messages)
        return JsonResponse({"ok": False, "error": error_text}, status=400)

    user = CustomUser.objects.get(id=user_id)
    user.set_password(password1)
    user.save(update_fields=["password"])

    PasswordResetRequest.objects.filter(id=req_id).update(is_used=True)

    # чистим данные восстановления
    for key in [
        "password_reset_user_id",
        "password_reset_request_id",
        "password_reset_verified",
        "password_reset_attempts",
        "password_reset_last_attempt_at",
    ]:
        request.session.pop(key, None)

    return JsonResponse({"ok": True})