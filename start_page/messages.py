from django.utils.translation import gettext_lazy as _

# Ошибки по email (формат, домен, существование)
EMAIL_ERROR_MESSAGES = {
    "empty": _("Укажите email."),
    "invalid_format": _("Введите корректный email."),
    "domain_not_allowed": _("Используйте email с разрешённым доменом."),
    "not_found": _("Пользователь с таким email не найден."),
    "already_exists": _("Пользователь с таким email уже зарегистрирован."),
    "not_determine_email": _("Не удалось определить email для отправки кода."),
}

# Сообщения для flow с кодами на email
EMAIL_CODE_MESSAGES = {
    "session_code_expired": _("Сессия с кодом недействительна. Запросите код ещё раз."),
    "session_recovery_expired": _("Сессия восстановления недействительна. Запросите код ещё раз."),
    "session_email_expired": _("Сессия смены email недействительна. Запросите код ещё раз."),
    "session_confirm_expired": _("Сессия подтверждения истекла. Запросите код ещё раз."),

    "code_invalid": _("Неверный код."),
    "code_expired": _("Срок действия кода истёк. Запросите новый код."),
    "cooldown": _("Слишком частые запросы кода. Попробуйте позже."),
    "unknown_scenario_code": _("Неизвестный сценарий отправки кода."),
    "unknown_scenario_confirm": _("Неизвестный сценарий подтверждения."),
    "not_needed_confirm_step": _("Для данного сценария отдельный confirm-шаг не требуется."),

    "code_mismatch": _("Код не совпадает."),
    "cooldown_seconds": _("Слишком частые запросы кода. Попробуйте через {seconds} секунд."),
}

# Ошибки/успехи по паролю
PASSWORD_ERROR_MESSAGES = {
    "empty_password": _("Введите пароль."),
    "empty_fields": _("Заполните все поля."),
    "new_mismatch": _("Новые пароли не совпадают."),
    "mismatch": _("Пароли не совпадают."),
    "current_wrong": _("Неверный текущий пароль."),
    "enter_current_password": _("Введите текущий пароль."),
    "confirm_new_password": _("Введите и подтвердите новый пароль."),
    "user_not_found": _("Не удалось найти пользователя для восстановления пароля."),
}

PASSWORD_SUCCESS_MESSAGES = {
    "changed_profile": _("Пароль успешно изменён."),
    "changed_reset": _("Пароль успешно изменён. Введите новый пароль и авторизуйтесь."),
}

# Ошибки/успехи профиля
PROFILE_ERROR_MESSAGES = {
    "username_empty": _("Имя пользователя не может быть пустым."),
}

PROFILE_SUCCESS_MESSAGES = {
    "username_changed": _("Имя пользователя успешно изменено."),
    "email_changed": _("Email успешно изменён."),
}

# Ошибки авторизации
AUTH_MESSAGES = {
    "invalid_credentials": _("Неверный email или пароль."),
    "email_confirmation": _("Сначала подтвердите email через код."),
    "need_auth": _("Требуется авторизация."),
}

# Ошибки при создании супер юзера
SUPERUSER_MESSAGES = {
    "true_is_staff": _("У суперпользователя is_staff должен быть True"),
    "true_is_superuser": _("У суперпользователя is_superuser должен быть True"),
}