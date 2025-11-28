from django.contrib.auth import login, logout, authenticate, get_user_model
from django.http import JsonResponse
from django.core.exceptions import ValidationError


from .email_code_service import *
from .validators import *

User = get_user_model()

# ---------------- Хелперы ----------------
SCENARIO_PREFIXES = {
    "password_reset": "password_reset",
    "signup": "signup_email",
    "change_email": "change_email",
}

def json_error(message, status=400) -> JsonResponse:
    """Унифицированный формат ответа-ошибки."""
    return JsonResponse({"ok": False, "error": message}, status=status)


def _invalidate_flow_and_error(request, prefix, msg, status=400) -> JsonResponse:
    """
    Чистим сессию по prefix и возвращаем JsonResponse с ошибкой.
    Удобно для "сессия восстановления недействительна", "сессия смены email недействительна" и т.п.
    """
    clear_email_flow(request, prefix)
    return json_error(msg, status=status)


def _get_verified_email_or_invalid(request, prefix, invalid_msg):
    """
    Достаём email из сессии для prefix и проверяем, что код был подтверждён.
    Если что-то не так — сразу чистим flow и отдаём JsonResponse с invalid_msg.

    Возвращает кортеж:
      (email: str | None, error_response: JsonResponse | None)
    """
    verified, email = get_verified_email(request, prefix)
    if not verified or not email:
        return None, _invalidate_flow_and_error(request, prefix, invalid_msg)
    return email, None


def _validate_new_password_pair(password1, password2):
    """
    Общая валидация пары паролей для reset:
      - заполнены оба поля
      - совпадают
      - проходят наш кастомный validate_password

    Возвращает (ok: bool, error_message: str | None).
    """
    if not password1 or not password2:
        return False, "Введите и подтвердите новый пароль."

    if password1 != password2:
        return False, "Пароли не совпадают."

    try:
        validate_password(password1)
    except ValidationError as exc:
        msg = "; ".join(exc.messages)
        return False, msg

    return True, None


def confirm_password_reset(request, prefix) -> JsonResponse:
    """
    Обработчик сценария 'password_reset' для confirm_code.
    """
    session_invalid_msg = "Сессия восстановления недействительна. Запросите код ещё раз."

    password1 = request.POST.get("password1", "") or ""
    password2 = request.POST.get("password2", "") or ""

    ok, err = _validate_new_password_pair(password1, password2)
    if not ok:
        return json_error(err)

    # проверяем, что email и код в сессии валидны
    email, error_resp = _get_verified_email_or_invalid(request, prefix, session_invalid_msg)
    if error_resp:
        return error_resp

    # достаём пользователя по email
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        # между шагами пользователь мог исчезнуть/сменить email
        return _invalidate_flow_and_error(request, prefix, session_invalid_msg)

    # меняем пароль
    user.set_password(password1)
    user.save(update_fields=["password"])

    # чистим flow
    clear_email_flow(request, prefix)

    return JsonResponse({"ok": True})


def confirm_change_email(request, prefix) -> JsonResponse:
    """
    Обработчик сценария 'change_email' для confirm_code.
    """
    session_invalid_msg = "Сессия смены email недействительна. Запросите код ещё раз."

    if not request.user.is_authenticated:
        return json_error("Требуется авторизация.", status=403)

    current_password = request.POST.get("current_password", "")
    if not current_password:
        return json_error("Введите текущий пароль.")

    user = request.user
    if not user.check_password(current_password):
        return json_error("Неверный текущий пароль.")

    # Проверяем, что в сессии есть подтверждённый новый email
    new_email, error_resp = _get_verified_email_or_invalid(request, prefix, session_invalid_msg)
    if error_resp:
        return error_resp

    # Проверяем, что этот email всё ещё не занят другим пользователем
    email_taken = (
        User.objects
        .filter(email__iexact=new_email)
        .exclude(id=user.id)
        .exists()
    )
    if email_taken:
        return _invalidate_flow_and_error(request, prefix, session_invalid_msg)

    # Обновляем email
    user.email = new_email
    user.save(update_fields=["email"])

    clear_email_flow(request, prefix)

    return JsonResponse(
        {
            "ok": True,
            "email": user.email,
            "masked_email": mask_email(user.email),
        }
    )

def resolve_target_email_and_user(request, scenario, email_normalized):
    """
    Возвращает (target_email, user_for_log, error_response) или (None, None, JsonResponse).

    validate_email уже сделал:
      - формат + домен
      - для signup: убедился, что email НЕ существует
      - для password_reset: убедился, что email существует
      - для change_email: только формат+домен (без проверки в базе)
    """
    target_email = None
    user_for_log = None

    if scenario == "password_reset":
        # Здесь validate_email(type="password_reset") уже гарантировал,
        # что такой email есть в базе, поэтому .first() "на всякий случай".
        user = User.objects.filter(email__iexact=email_normalized).first()
        if not user:
            # Теоретически не должно происходить, но пусть будет аккуратный ответ.
            return None, None, json_error(
                "Не удалось найти пользователя для восстановления пароля.", status=400
            )
        target_email = user.email
        user_for_log = user

    elif scenario == "signup":
        # validate_email(type="signup") уже проверил, что email свободен.
        target_email = email_normalized

    elif scenario == "change_email":
        # Здесь validate_email(type=None) проверил только формат + домен.
        # Дальше проверяем авторизацию и уникальность email относительно текущего пользователя.
        if not request.user.is_authenticated:
            return None, None, json_error("Требуется авторизация.", status=403)

        email_taken = (
            User.objects
            .filter(email__iexact=email_normalized)
            .exclude(id=request.user.id)
            .exists()
        )
        if email_taken:
            return None, None, JsonResponse(
                {
                    "ok": False,
                    "code": "email_exists",
                    "error": "Этот email уже используется другим пользователем.",
                },
                status=400,
            )

        target_email = email_normalized

    else:
        # На всякий случай защита, сюда не должны попасть, т.к. scenario уже проверяли выше
        return None, None, json_error("Неизвестный сценарий отправки кода.", status=400)

    return target_email, user_for_log, None


def build_email_subject_message(scenario, code):
    """
    Возвращает (subject, message) для письма в зависимости от сценария.
    """
    if scenario == "password_reset":
        subject = "Код для восстановления пароля"
        message = f"Ваш код для восстановления пароля: {code}\nКод действителен 10 минут."
    elif scenario == "signup":
        subject = "Код подтверждения регистрации"
        message = f"Ваш код подтверждения email: {code}\nКод действителен 10 минут."
    elif scenario == "change_email":
        subject = "Код подтверждения смены почты"
        message = f"Ваш код для смены email: {code}\nКод действителен 10 минут."
    else:
        subject = "Код подтверждения"
        message = f"Ваш код: {code}"
    return subject, message


