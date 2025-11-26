import random
from django.utils import timezone

EMAIL_CODE_MESSAGES = {
    "cooldown": "Слишком частые запросы кода. Попробуйте через {seconds} секунд.",
    "session_expired": "Сессия подтверждения истекла. Запросите код ещё раз.",
    "code_expired": "Срок действия кода истёк. Запросите новый код.",
    "code_mismatch": "Код не совпадает.",
}


def _generate_code():
    return f"{random.randint(0, 999999):06d}"


def _get_cooldown_seconds(attempts_so_far):
    """
    0 → первая отправка (без задержки)
    1 → между 1 и 2 → 30 секунд
    2 → между 2 и 3 → 5 минут
    ≥3 → 10 минут
    """
    if attempts_so_far == 0:
        return 0
    elif attempts_so_far == 1:
        return 30
    elif attempts_so_far == 2:
        return 300
    else:
        return 600


def start_email_code_flow(request, prefix: str, email: str) -> dict:
    """
    Общая логика для стартового шага:
    - проверка cooldown по prefix (password_reset / signup_email / change_email)
    - генерация кода
    - сохранение кода и состояния в сессию
    Возвращает dict, который дальше можно отдать через JsonResponse.
    """
    now_ts = timezone.now().timestamp()

    attempts_key = f"{prefix}_attempts"
    last_ts_key = f"{prefix}_last_attempt_ts"
    code_key = f"{prefix}_code"
    expires_key = f"{prefix}_expires_ts"
    email_key = f"{prefix}_email"
    verified_key = f"{prefix}_verified"

    attempts = request.session.get(attempts_key, 0)
    last_ts = request.session.get(last_ts_key)

    if last_ts is not None:
        cooldown = _get_cooldown_seconds(attempts)
        elapsed = now_ts - float(last_ts)
        if cooldown > 0 and elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            msg = EMAIL_CODE_MESSAGES["cooldown"].format(seconds=remaining)
            return {
                "ok": False,
                "code": "cooldown",
                "error": msg,
                "remaining_seconds": remaining,
            }

    code = _generate_code()
    expires_ts = now_ts + 600  # 10 минут

    attempts += 1
    request.session[attempts_key] = attempts
    request.session[last_ts_key] = now_ts
    request.session[code_key] = code
    request.session[expires_key] = expires_ts
    request.session[email_key] = email
    request.session[verified_key] = False
    request.session.modified = True

    next_cooldown = _get_cooldown_seconds(attempts)
    return {
        "ok": True,
        "code_value": code,
        "attempts": attempts,
        "cooldown_seconds": next_cooldown,
    }


def verify_email_code_flow(request, prefix, code_input):
    """
    Общая логика шага проверки кода.
    Работает только с сессией, никакой привязки к конкретному сценарию.
    """
    code_key = f"{prefix}_code"
    expires_key = f"{prefix}_expires_ts"
    verified_key = f"{prefix}_verified"

    stored_code = request.session.get(code_key)
    expires_ts = request.session.get(expires_key)

    if not stored_code or expires_ts is None:
        return {
            "ok": False,
            "error": EMAIL_CODE_MESSAGES["session_expired"],
        }

    now_ts = timezone.now().timestamp()
    if now_ts > float(expires_ts):
        request.session[verified_key] = False
        request.session.modified = True
        return {
            "ok": False,
            "error": EMAIL_CODE_MESSAGES["code_expired"],
        }

    if stored_code != code_input:
        return {
            "ok": False,
            "error": EMAIL_CODE_MESSAGES["code_mismatch"],
        }

    request.session[verified_key] = True
    request.session.modified = True
    return {"ok": True}


def get_verified_email(request, prefix: str) -> tuple[bool, str | None]:
    """
    Достаём из сессии: подтверждён ли код и какая почта была подтверждена.
    """
    email_key = f"{prefix}_email"
    verified_key = f"{prefix}_verified"

    email = request.session.get(email_key)
    verified = bool(request.session.get(verified_key, False))
    return verified, email


def clear_email_flow(request, prefix: str) -> None:
    for suffix in ("attempts", "last_attempt_ts", "code", "expires_ts", "email", "verified"):
        request.session.pop(f"{prefix}_{suffix}", None)
    request.session.modified = True