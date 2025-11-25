from django.contrib.auth import logout
from django.shortcuts import redirect

from .services import create_or_update_user_session


class UserSessionMiddleware:
    """
    Проверяет пользовательскую сессию (UserSession) на КАЖДОМ запросе.

    Логика:
    - если пользователь не авторизован — ничего не делаем;
    - если авторизован:
        - пробуем продлить его сессию (create_if_missing=False);
        - если сессия истекла → logout и редирект на стартовую страницу.
    - некоторые пути пропускаем (login, signup, logout, admin), чтобы не ловить странные кейсы.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # проверяем только для авторизованных
        if request.user.is_authenticated:
            path = request.path

            # пути, для которых мы не трогаем сессию
            skip_prefixes = (
                "/admin/",
                "/static/",
                "/media/",
            )
            skip_exact = (
                "/login/",
                "/signup/",
                "/logout/",
            )

            if not any(path.startswith(p) for p in skip_prefixes) and path not in skip_exact:
                session_obj = create_or_update_user_session(
                    request,
                    request.user,
                    create_if_missing=False,
                )
                if session_obj is None:
                    logout(request)
                    return redirect("start_page:start_page")

        response = self.get_response(request)
        return response