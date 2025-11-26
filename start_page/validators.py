from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.conf import settings

from .models import CustomUser

import re


def _normalize_email(email):
    """
    Общая нормализация email: обрезать пробелы, привести к нижнему регистру,
    проверить формат.
    """
    if not email:
        raise ValidationError("Укажите email.")

    email_normalized = email.strip().lower()
    try:
        django_validate_email(email_normalized)
    except ValidationError:
        raise ValidationError("Введите корректный email.")
    return email_normalized


def _check_allowed_domain(email_normalized):
    allowed_domains = getattr(settings, "ALLOWED_EMAIL_DOMAINS", [])
    if allowed_domains:
        domain = email_normalized.split("@")[-1]
        if domain not in allowed_domains:
            raise ValidationError("Регистрация/вход с этого домена email недоступны.")


def validate_username(username):
    """
    Проверяем, что поле с именем пользователя не пустое
    """
    username = username.strip()
    if not username:
        raise ValidationError("Укажите имя пользователя.")
    return username


def validate_email(email, type):
    """
    Универсальная проверка email.

    Общая часть:
    - не пустой
    - корректный формат
    - домен из ALLOWED_EMAIL_DOMAINS (если задан)

    В зависимости от type также проверяем наличие в базе:

      type == 'signup':
          email НЕ должен существовать
          -> иначе: "Пользователь с таким email уже зарегистрирован."

      type in ('login', 'password_reset'):
          email ДОЛЖЕН существовать
          -> иначе: "Пользователь с таким email не найден."

      type is None:
          только формат + домен, без проверки в базе
    """
    email_normalized = _normalize_email(email)
    _check_allowed_domain(email_normalized)

    if type is None:
        return email_normalized

    exists = CustomUser.objects.filter(email__iexact=email_normalized).exists()

    if type in ("login", "password_reset"):
        if not exists:
            raise ValidationError("Пользователь с таким email не найден.")
    elif type == "signup":
        if exists:
            raise ValidationError("Пользователь с таким email уже зарегистрирован.")

    return email_normalized


def validate_password(password):
    """
    Проверка пароля по правилам:
    - не пустой
    - длина не менее PASSWORD_MIN_LENGTH
    - хотя бы одна буква (латиница или кириллица)
    - хотя бы одна цифра
    - хотя бы один спецсимвол из SPECIAL_CHARS

    Если пароль не проходит проверки — выбрасывает ValidationError
    (сразу со всеми текстами ошибок).
    Если всё ок — возвращает нормализованный пароль (обрезанные пробелы).
    """
    password_min_length = 6
    special_chars = r"!@#$%^&*(),.?\":{}|<>"
    errors = []

    if password is None:
        raise ValidationError("Введите пароль.")

    # убираем пробелы по краям
    password = password.strip()

    # 1. длина
    if len(password) < password_min_length:
        errors.append(f"Длина пароля не менее {password_min_length} символов.")

    # 2. хотя бы одна буква (латиница или кириллица)
    if not re.search(r"[A-Za-zА-Яа-я]", password):
        errors.append("Пароль должен содержать хотя бы одну букву.")

    # 3. хотя бы одна цифра
    if not re.search(r"\d", password):
        errors.append("Пароль должен содержать хотя бы одну цифру.")

    # 4. хотя бы один спецсимвол
    if not re.search(rf"[{re.escape(special_chars)}]", password):
        errors.append(
            "Пароль должен содержать хотя бы один специальный символ."
        )

    if errors:
        raise ValidationError(errors)

    return password