from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def _mask_email(email):
    """
    Маскируем email: показываем первые 3 символа и последние 2,
    остальное заменяем звёздочками.
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


@login_required
def main_page(request):
    """
    Основная страница.
    Проверку и продление UserSession делает middleware.
    Если сессия истекла, middleware разлогинит и отправит на стартовую страницу.
    """
    return render(request, "main_page/main_page.html")


@login_required
def profile(request):
    """
    Страница профиля.
    Секции: имя пользователя, почта (маскированная), пароль.
    Пока только отображение, без сохранения изменений.
    """
    user = request.user
    full_email = user.email or ""
    masked_email = _mask_email(full_email)

    context = {
        "user": user,
        "full_email": full_email,
        "masked_email": masked_email,
    }
    return render(request, "main_page/profile.html", context)