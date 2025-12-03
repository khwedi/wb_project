from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

import datetime

from .models import WBCabinet
from .wb_api import fetch_cabinet_info, WBCabinetError

from start_page.messages import WB_API_CABINET
from start_page.code_confirm_views import json_error


# ---- Вспомогательные функции ----

def _short_api_key(api_key):
    """
    Сжимаем длинный ключ для отображения: первые 4 + ... + последние 4.
    Полный ключ на фронт не отдаём.
    """
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return api_key
    return f"{api_key[:4]}...{api_key[-4:]}"


def _serialize_cabinet(cabinet: WBCabinet):
    """
    Приводим объект WBCabinet к JSON-структуре для фронта.
    """
    created_at_str = ""
    created_date_str = ""
    if cabinet.cabinet_created_at:
        local_dt = timezone.localtime(cabinet.cabinet_created_at)
        created_at_str = local_dt.strftime("%Y-%m-%d %H:%M")
        created_date_str = local_dt.date().isoformat()

    return {
        "id": cabinet.id,
        "short_api_key": _short_api_key(cabinet.api_key),
        "api_key_name": cabinet.api_key_name or "",
        "cabinet_name": cabinet.cabinet_name or "",
        "cabinet_created_at": created_at_str,       # для отображения
        "cabinet_created_date": created_date_str,   # для <input type="date">
    }


def _get_cabinet_or_error(request):
    """
    Общая логика извлечения кабинета по id из POST и проверки,
    что он принадлежит текущему пользователю.

    Возвращает (cabinet, error_response):
      - если всё ок: (WBCabinet, None)
      - если ошибка: (None, JsonResponse)
    """
    cab_id = request.POST.get("id")
    if not cab_id:
        return None, json_error(WB_API_CABINET["without_id"])

    try:
        cab_id_int = int(cab_id)
    except ValueError:
        return None, json_error(WB_API_CABINET["incorrect_id"])

    cabinet = get_object_or_404(WBCabinet, id=cab_id_int, user=request.user)
    return cabinet, None


def _user_cabinets(user):
    """Удобный шорткат для queryset кабинетов текущего пользователя."""
    return WBCabinet.objects.filter(user=user)


def _is_api_key_name_taken(user, api_key_name, exclude_id=None):
    qs = _user_cabinets(user).filter(api_key_name__iexact=api_key_name)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()


def _is_api_key_taken(user, api_key, exclude_id=None):
    qs = _user_cabinets(user).filter(api_key=api_key)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()


def _fetch_info_or_error(api_key):
    """
    Обёртка над fetch_cabinet_info: возвращаем (info, error_text).
    """
    try:
        info = fetch_cabinet_info(api_key)
    except WBCabinetError as exc:
        return None, str(exc)
    return info, None


# ---- Вьюхи ----

@login_required
def cabinets_list(request):
    """
    Возвращает JSON со всеми кабинетами текущего пользователя.
    """
    cabinets = _user_cabinets(request.user).order_by("id")
    items = [_serialize_cabinet(c) for c in cabinets]
    return JsonResponse({"ok": True, "items": items})


@login_required
@require_POST
def cabinets_add(request):
    """
    Добавление нового кабинета:
      - проверяем, что поля заполнены
      - проверяем, что такого ключа/имени у пользователя ещё нет
      - валидируем ключ через WB
      - сохраняем в БД
    """
    api_key = (request.POST.get("api_key") or "").strip()
    api_key_name = (request.POST.get("api_key_name") or "").strip()
    user = request.user

    if not api_key or not api_key_name:
        return json_error(WB_API_CABINET["fill_api_field"])

    if _is_api_key_name_taken(user, api_key_name):
        return json_error(WB_API_CABINET["have_api_key_name"])

    if _is_api_key_taken(user, api_key):
        return json_error(WB_API_CABINET["have_api_key"])

    info, err = _fetch_info_or_error(api_key)
    if err:
        return json_error(err)

    cab = WBCabinet.objects.create(
        user=user,
        api_key=api_key,
        api_key_name=api_key_name,
        cabinet_name=info.get("cabinet_name") or "",
        cabinet_created_at=info.get("cabinet_created_at"),
    )

    return JsonResponse(
        {"ok": True, "item": _serialize_cabinet(cab)},
        status=201,
    )


@login_required
@require_POST
def cabinets_delete(request):
    cabinet, error_response = _get_cabinet_or_error(request)
    if error_response is not None:
        return error_response

    cabinet.delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def cabinets_check(request):
    """
    Проверка API-ключа:
      - sync=0: только проверяем, при расхождении данных — предлагаем синхронизацию
      - sync=1: проверяем и сразу синхронизируем cabinet_name / cabinet_created_at
    """
    cabinet, error_response = _get_cabinet_or_error(request)
    if error_response is not None:
        return error_response

    sync_flag = request.POST.get("sync") in ("1", "true", "yes")

    info, err = _fetch_info_or_error(cabinet.api_key)
    if err:
        return json_error(err)

    new_name = info.get("cabinet_name") or ""
    new_dt = info.get("cabinet_created_at")

    changed_name = bool(new_name and new_name != cabinet.cabinet_name)
    changed_dt = bool(new_dt and new_dt != cabinet.cabinet_created_at)
    has_changes = changed_name or changed_dt

    if not has_changes:
        return JsonResponse(
            {
                "ok": True,
                "message": WB_API_CABINET["api_active"],
                "has_changes": False,
                "item": _serialize_cabinet(cabinet),
            }
        )

    # Есть изменения, но sync_flag = False -> только сообщаем, фронт решает
    if not sync_flag:
        return JsonResponse(
            {
                "ok": True,
                "message": WB_API_CABINET["api_active_with_changes"],
                "has_changes": True,
                "new_cabinet_name": new_name,
                "new_cabinet_created_at": (
                    new_dt.strftime("%Y-%m-%d %H:%M") if new_dt else ""
                ),
                "item": _serialize_cabinet(cabinet),
            }
        )

    # sync_flag = True -> реально обновляем запись
    updated_fields = []
    if changed_name:
        cabinet.cabinet_name = new_name
        updated_fields.append("cabinet_name")
    if changed_dt:
        cabinet.cabinet_created_at = new_dt
        updated_fields.append("cabinet_created_at")

    if updated_fields:
        cabinet.save(update_fields=updated_fields)

    return JsonResponse(
        {
            "ok": True,
            "message": WB_API_CABINET["synced"],
            "has_changes": False,
            "item": _serialize_cabinet(cabinet),
        }
    )


@login_required
@require_POST
def cabinets_update(request):
    """
    Редактирование кабинета:
      - можно изменить:
        * api_key (с проверкой на WB + уникальность),
        * api_key_name (уникальность среди кабинетов юзера),
        * cabinet_name,
        * cabinet_created_at (через дату).
    """
    cabinet, error_response = _get_cabinet_or_error(request)
    if error_response is not None:
        return error_response

    user = request.user

    api_key_raw = (request.POST.get("api_key") or "").strip()
    api_key_name = (request.POST.get("api_key_name") or "").strip()
    cabinet_name = (request.POST.get("cabinet_name") or "").strip()
    cabinet_created_date = (request.POST.get("cabinet_created_date") or "").strip()

    errors = []

    # --- 1. api_key: если пусто — не меняем, если не пусто — валидируем и обновляем через WB ---
    api_key_changed = bool(api_key_raw)

    if api_key_changed:
        if _is_api_key_taken(user, api_key_raw, exclude_id=cabinet.id):
            errors.append(WB_API_CABINET["api_key_duplicate"])
        else:
            info, err = _fetch_info_or_error(api_key_raw)
            if err:
                errors.append(err)
            else:
                cabinet.api_key = api_key_raw

                new_name = info.get("cabinet_name") or ""
                new_created_at = info.get("cabinet_created_at")

                if new_name:
                    cabinet.cabinet_name = new_name
                if new_created_at:
                    cabinet.cabinet_created_at = new_created_at

    # --- 2. api_key_name: обязательно, уникально для пользователя ---
    if not api_key_name:
        errors.append(WB_API_CABINET["api_key_name_required"])
    else:
        if _is_api_key_name_taken(user, api_key_name, exclude_id=cabinet.id):
            errors.append(WB_API_CABINET["have_api_key_name"])
        else:
            cabinet.api_key_name = api_key_name

    # --- 3. cabinet_name / cabinet_created_date ---
    # Если ключ менялся — имя/дату уже обновили из WB.
    # Если ключ НЕ менялся — даём редактировать эти поля вручную и НЕ связываем их друг с другом.
    if not api_key_changed:
        # 3.1. Имя кабинета: обновляем, только если оно реально изменилось
        if cabinet_name != cabinet.cabinet_name:
            if not cabinet_name:
                errors.append(WB_API_CABINET["cabinet_name_required"])
            else:
                cabinet.cabinet_name = cabinet_name

        # 3.2. Дата: обновляем, только если она реально изменилась
        current_date_str = ""
        if cabinet.cabinet_created_at:
            current_date_str = timezone.localtime(
                cabinet.cabinet_created_at
            ).date().isoformat()

        if cabinet_created_date != current_date_str:
            if not cabinet_created_date:
                # пользователь попытался "очистить" дату
                errors.append(WB_API_CABINET["cabinet_date_required"])
            else:
                try:
                    d = datetime.date.fromisoformat(cabinet_created_date)
                except ValueError:
                    errors.append(WB_API_CABINET["cabinet_date_invalid"])
                else:
                    dt_naive = datetime.datetime.combine(d, datetime.time(0, 0))
                    dt_aware = timezone.make_aware(
                        dt_naive,
                        timezone.get_default_timezone(),
                    )
                    cabinet.cabinet_created_at = dt_aware

    if errors:
        return JsonResponse(
            {
                "ok": False,
                "errors": errors,
            },
            status=400,
        )

    cabinet.save()

    return JsonResponse(
        {
            "ok": True,
            "message": WB_API_CABINET["update_ok"],
            "item": _serialize_cabinet(cabinet),
        }
    )
