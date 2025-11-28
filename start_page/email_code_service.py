import random
from typing import Tuple, Optional

from django.utils import timezone


EMAIL_CODE_MESSAGES = {
    "cooldown": "Слишком частые запросы кода. Попробуйте через {seconds} секунд.",
    "session_expired": "Сессия подтверждения истекла. Запросите код ещё раз.",
    "code_expired": "Срок действия кода истёк. Запросите новый код.",
    "code_mismatch": "Код не совпадает.",
}


def mask_email(email: str) -> str:
    """
    Маскирует email для отображения.
    Пример: diana.super@mail.ru -> dia******er@mail.ru
    """
    if not email or "@" not in email:
        return email

    local, domain = email.split("@", 1)
    if len(local) <= 4:
        visible_start = local[:1]
        visible_end = local[-1:] if len(local) > 1 else ""
    else:
        visible_start = local[:3]
        visible_end = local[-2:]

    stars_count = max(len(local) - len(visible_start) - len(visible_end), 1)
    masked_local = f"{visible_start}{'*' * stars_count}{visible_end}"
    return f"{masked_local}@{domain}"


def _generate_code() -> str:
    """Генерирует 6-значный код в виде строки."""
    return f"{random.randint(0, 999_999):06d}"


def _get_cooldown_seconds(attempts_so_far: int) -> int:
    """
    Логика задержек между отправками:
      0 -> первая отправка (без задержки)
      1 -> между 1 и 2 -> 30 секунд
      2 -> между 2 и 3 -> 5 минут
      >=3 -> 10 минут
    """
    if attempts_so_far == 0:
        return 0
    elif attempts_so_far == 1:
        return 30
    elif attempts_so_far == 2:
        return 300
    return 600


def start_email_code_flow(request, prefix: str, email: str) -> dict:
    """
    Общая логика "шаг 1": отправка кода на email.

    В сессии хранится:
      - {prefix}_attempts
      - {prefix}_last_attempt_ts
      - {prefix}_code
      - {prefix}_expires_ts
      - {prefix}_email
      - {prefix}_verified (False)

    Возврат:
      - ok=False, code="cooldown", error, remaining_seconds
      - ok=True, code_value, attempts, cooldown_seconds
    """
    now_ts = timezone.now().timestamp()

    attempts_key = f"{prefix}_attempts"
    last_ts_key = f"{prefix}_last_attempt_ts"
    code_key = f"{prefix}_code"
    expires_key = f"{prefix}_expires_ts"
    email_key = f"{prefix}_email"
    verified_key = f"{prefix}_verified"

    attempts = int(request.session.get(attempts_key, 0))
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


def verify_email_code_flow(request, prefix: str, code_input: str) -> dict:
    """
    Общая логика "шаг 2": проверка кода.
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


def get_verified_email(request, prefix: str) -> Tuple[bool, Optional[str]]:
    """Возвращает (verified, email) из сессии для данного prefix."""
    email_key = f"{prefix}_email"
    verified_key = f"{prefix}_verified"

    email = request.session.get(email_key)
    verified = bool(request.session.get(verified_key, False))
    return verified, email


def clear_email_flow(request, prefix: str) -> None:
    """Удаляет все ключи, связанные с email-flow для данного prefix."""
    for suffix in ("attempts", "last_attempt_ts", "code", "expires_ts", "email", "verified"):
        request.session.pop(f"{prefix}_{suffix}", None)
    request.session.modified = True
