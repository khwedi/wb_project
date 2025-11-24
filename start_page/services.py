from datetime import timedelta

from django.utils import timezone

from .models import UserSession

SESSION_LIFETIME = timedelta(hours=24)


def _ensure_session_key(request):
    """
    Гарантируем, что у request.session есть session_key.
    """
    session = request.session
    if not session.session_key:
        session.create()
    return session.session_key


def create_or_update_user_session(request, user, *, create_if_missing: bool = True):
    """
    Общая функция работы с пользовательской сессией.

    - Деактивирует истёкшие активные сессии пользователя.
    - Если есть активная сессия (is_active=True, end_time > now),
      продлевает её: end_time = now + 24 часа, пересчитывает duration.
    - Если активной нет и create_if_missing=True — создаёт новую сессию.
    - Если активной нет и create_if_missing=False — ничего не создаёт, возвращает None.

    Использование:
    - signup/login → create_if_missing=True (создать/обновить сессию).
    - start_page/main_page → create_if_missing=False (если сессия истекла — не создавать новую).
    """
    now = timezone.now()
    session_key = _ensure_session_key(request)

    # деактивируем истёкшие активные сессии
    UserSession.objects.filter(
        user=user,
        is_active=True,
        end_time__lte=now,
    ).update(is_active=False)

    # ищем текущую активную
    active_session = UserSession.objects.filter(
        user=user,
        is_active=True,
        end_time__gt=now,
    ).order_by("-start_time").first()

    if active_session:
        # продлеваем
        new_end_time = now + SESSION_LIFETIME
        active_session.end_time = new_end_time
        active_session.duration = active_session.end_time - active_session.start_time
        active_session.session_key = session_key
        active_session.save(update_fields=["end_time", "duration", "session_key", "updated_at"])
        return active_session

    if not create_if_missing:
        return None

    # активной нет и разрешено создать новую
    start_time = now
    end_time = now + SESSION_LIFETIME
    session = UserSession.objects.create(
        user=user,
        session_key=session_key,
        start_time=start_time,
        end_time=end_time,
        duration=end_time - start_time,
        is_active=True,
    )
    return session


def end_user_sessions(user):
    """
    Прервать все активные сессии пользователя (logout):
    - end_time = сейчас
    - duration пересчитать
    - is_active=False
    """
    now = timezone.now()
    sessions = UserSession.objects.filter(user=user, is_active=True)

    for s in sessions:
        s.end_time = now
        s.duration = s.end_time - s.start_time
        s.is_active = False
        s.save(update_fields=["end_time", "duration", "is_active", "updated_at"])


