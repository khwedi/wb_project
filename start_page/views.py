from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .forms import *
from .services import *
from .email_code_service import *
from .validators import *
from .models import PasswordResetRequest

User = get_user_model()

# ---------------- Хелперы ----------------
SCENARIO_PREFIXES = {
    "password_reset": "password_reset",
    "signup": "signup_email",
    "change_email": "change_email",
}

def _json_error(message: str, status: int = 400) -> JsonResponse:
    """Унифицированный формат ответа-ошибки."""
    return JsonResponse({"ok": False, "error": message}, status=status)


def _invalidate_flow_and_error(request, prefix: str, msg: str, status: int = 400) -> JsonResponse:
    """
    Чистим сессию по prefix и возвращаем JsonResponse с ошибкой.
    Удобно для "сессия восстановления недействительна", "сессия смены email недействительна" и т.п.
    """
    clear_email_flow(request, prefix)
    return _json_error(msg, status=status)


def _get_verified_email_or_invalid(request, prefix: str, invalid_msg: str):
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


def _validate_new_password_pair(password1: str, password2: str):
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


def _confirm_password_reset(request, prefix: str) -> JsonResponse:
    """
    Обработчик сценария 'password_reset' для confirm_code.
    """
    session_invalid_msg = "Сессия восстановления недействительна. Запросите код ещё раз."

    password1 = request.POST.get("password1", "") or ""
    password2 = request.POST.get("password2", "") or ""

    ok, err = _validate_new_password_pair(password1, password2)
    if not ok:
        return _json_error(err)

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


def _confirm_change_email(request, prefix: str) -> JsonResponse:
    """
    Обработчик сценария 'change_email' для confirm_code.
    """
    session_invalid_msg = "Сессия смены email недействительна. Запросите код ещё раз."

    if not request.user.is_authenticated:
        return _json_error("Требуется авторизация.", status=403)

    current_password = request.POST.get("current_password", "")
    if not current_password:
        return _json_error("Введите текущий пароль.")

    user = request.user
    if not user.check_password(current_password):
        return _json_error("Неверный текущий пароль.")

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

def _resolve_target_email_and_user(request, scenario, email_normalized):
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
            return None, None, _json_error(
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
            return None, None, _json_error("Требуется авторизация.", status=403)

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
        return None, None, _json_error("Неизвестный сценарий отправки кода.", status=400)

    return target_email, user_for_log, None


def _build_email_subject_message(scenario: str, code: str):
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


# ---------------- Базовые страницы ----------------
def start_page(request):
    """
    Стартовая страница.
    Проверку/продление сессий делает middleware,
    поэтому тут достаточно просто отрендерить шаблон.
    """
    return render(request, "start_page/start_page.html")


def signup(request):
    """
    Страница регистрации.
    - GET: показываем пустую форму
    - POST: проверяем форму, при успехе создаём пользователя и редиректим
    Пользователь создаётся ТОЛЬКО если email предварительно подтверждён через код (prefix="signup_email").
    """
    allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', [])
    prefix = SCENARIO_PREFIXES["signup"]

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            email_from_form = form.cleaned_data.get("email", "").strip().lower()

            verified, verified_email = get_verified_email(request, prefix)
            if not verified or not verified_email or verified_email.lower() != email_from_form:
                form.add_error("email", "Сначала подтвердите email через код.")
            else:
                user = form.save()
                clear_email_flow(request, prefix)
                login(request, user)
                create_or_update_user_session(request, user, create_if_missing=True)
                return redirect("main_page:main_page")
    else:
        form = RegisterForm()

    verified, _ = get_verified_email(request, prefix)
    context = {
        "form": form,
        "email_verified": verified,
        'allowed_domains': allowed_domains
    }
    return render(request, "start_page/signup.html", context)


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
            create_or_update_user_session(request, user, create_if_missing=True)
            return redirect("main_page:main_page")
    else:
        form = LoginForm()

    return render(request, "start_page/login.html", {"form": form})


def logout_auth(request):
    """
    Logout:
    - завершаем все активные сессии пользователя
    - вылогиниваем через Django
    - возвращаем на стартовую страницу
    """
    if request.user.is_authenticated:
        end_user_sessions(request.user)
        logout(request)

    return redirect("start_page:start_page")


# ---------------- Универсальный шаг 1: отправка кода ----------------
@require_POST
def send_code(request, scenario):
    """
    Универсальная отправка кода для сценариев:
      - password_reset
      - signup
      - change_email

    Отличия по сценариям:
      - password_reset: email ДОЛЖЕН существовать.
      - signup: email НЕ должен быть занят.
      - change_email: требуется авторизация, email НЕ должен быть занят другим пользователем.
    """
    if scenario not in SCENARIO_PREFIXES:
        return _json_error("Неизвестный сценарий отправки кода.")

    prefix = SCENARIO_PREFIXES[scenario]
    email_raw = request.POST.get("email", "")

    # 1. Базовая валидация email + проверка в базе в зависимости от сценария
    #    signup         -> email НЕ должен существовать
    #    password_reset -> email ДОЛЖЕН существовать
    #    change_email   -> только формат+домен (проверку уникальности делаем отдельно)
    if scenario == "signup":
        validate_type = "signup"
    elif scenario == "password_reset":
        validate_type = "password_reset"
    else:
        validate_type = None

    try:
        email_normalized = validate_email(email_raw, type=validate_type)
    except ValidationError as exc:
        return JsonResponse(
            {"ok": False, "code": "email_error", "error": str(exc)},
            status=400,
        )

    # 2. Сценарная логика: кто, куда и можно ли вообще
    target_email, user_for_log, error_resp = _resolve_target_email_and_user(
        request, scenario, email_normalized
    )
    if error_resp is not None:
        return error_resp

    if not target_email:
        return _json_error("Не удалось определить email для отправки кода.")

    # 3. Общий сервис: cooldown + генерация кода
    result = start_email_code_flow(request, prefix=prefix, email=target_email)
    if not result["ok"]:
        status = 429 if result.get("code") == "cooldown" else 400
        return JsonResponse(result, status=status)

    code = result["code_value"]

    # 4. Логируем только password_reset
    if scenario == "password_reset" and user_for_log is not None:
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        PasswordResetRequest.objects.create(
            user=user_for_log,
            code=code,
            expires_at=expires_at,
        )

    # 5. Письмо по сценарию
    subject, message = _build_email_subject_message(scenario, code)

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[target_email],
    )

    return JsonResponse(
        {
            "ok": True,
            "cooldown_seconds": result["cooldown_seconds"],
            "attempts": result["attempts"],
        }
    )


# ---------------- Универсальный шаг 2: проверка кода ----------------
@require_POST
def verify_code(request, scenario: str):
    """
    Универсальная проверка кода (шаг 2) для:
      - password_reset -> prefix="password_reset"
      - signup        -> prefix="signup_email"
      - change_email  -> prefix="change_email"
    """
    if scenario not in SCENARIO_PREFIXES:
        return JsonResponse(
            {"ok": False, "error": "Неизвестный сценарий подтверждения."},
            status=400,
        )

    if scenario == "change_email" and not request.user.is_authenticated:
        return JsonResponse(
            {"ok": False, "error": "Требуется авторизация."},
            status=403,
        )

    prefix = SCENARIO_PREFIXES[scenario]
    code_input = request.POST.get("code", "").strip()

    result = verify_email_code_flow(request, prefix=prefix, code_input=code_input)
    if not result["ok"]:
        return JsonResponse({"ok": False, "error": result["error"]}, status=400)

    return JsonResponse({"ok": True})


# ---------------- Универсальный шаг 3: финальное действие ----------------
@require_POST
def confirm_code(request, scenario: str):
    """
    Универсальный шаг 3:

      - password_reset:
            ввод нового пароля (password1, password2),
            меняем пароль пользователю, чей email лежит в сессии (prefix="password_reset").

      - change_email:
            ввод текущего пароля (current_password),
            меняем email текущему пользователю на email из сессии (prefix="change_email").

      - signup:
            отдельного confirm-шаг не имеет — достаточно verify_code.
    """
    if scenario not in SCENARIO_PREFIXES:
        return _json_error("Неизвестный сценарий подтверждения.")

    prefix = SCENARIO_PREFIXES[scenario]

    if scenario == "password_reset":
        return _confirm_password_reset(request, prefix)

    if scenario == "change_email":
        return _confirm_change_email(request, prefix)

    # Для signup (и любых других сценариев, где confirm не нужен)
    return _json_error("Для данного сценария отдельный confirm-шаг не требуется.")