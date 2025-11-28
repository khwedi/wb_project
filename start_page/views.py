from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .forms import *
from .services import *
from .models import PasswordResetRequest
from .code_confirm_views import *

User = get_user_model()

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
        return json_error("Неизвестный сценарий отправки кода.")

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
            {"ok": False,
             "code": "email_error",
             "error": str(exc)},
            status=400,
        )

    # 2. Сценарная логика: кто, куда и можно ли вообще
    target_email, user_for_log, error_resp = resolve_target_email_and_user(
        request, scenario, email_normalized
    )
    if error_resp is not None:
        return error_resp

    if not target_email:
        return json_error("Не удалось определить email для отправки кода.")

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
    subject, message = build_email_subject_message(scenario, code)

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
        return json_error("Неизвестный сценарий подтверждения.")

    if scenario == "change_email" and not request.user.is_authenticated:
        json_error("Требуется авторизация.")

    prefix = SCENARIO_PREFIXES[scenario]
    code_input = request.POST.get("code", "").strip()

    result = verify_email_code_flow(request, prefix=prefix, code_input=code_input)
    if not result["ok"]:
        json_error(result["error"])

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
        return json_error("Неизвестный сценарий подтверждения.")

    prefix = SCENARIO_PREFIXES[scenario]

    if scenario == "password_reset":
        return confirm_password_reset(request, prefix)

    if scenario == "change_email":
        return confirm_change_email(request, prefix)

    # Для signup (и любых других сценариев, где confirm не нужен)
    return json_error("Для данного сценария отдельный confirm-шаг не требуется.")