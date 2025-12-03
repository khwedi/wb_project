import requests
from datetime import datetime

from start_page.messages import WB_API_CABINET


class WBCabinetError(Exception):
    """Ошибка при работе с API Wildberries."""
    pass


WILDBERRIES_API_URL_CABINET = "https://common-api.wildberries.ru/api/v1/seller-info"


def fetch_cabinet_info(api_key):
    """
    Запрашиваем у WB информацию о кабинете по API-ключу.

    Возвращает dict:
      {
        "cabinet_name": str,
        "cabinet_created_at": datetime | None
      }

    Если ключ невалиден или ответ странный — бросаем WBCabinetError.
    """
    headers = {
        "Authorization": api_key,
    }

    try:
        resp = requests.get(WILDBERRIES_API_URL_CABINET, headers=headers, timeout=10)
    except requests.RequestException:
        raise WBCabinetError(WB_API_CABINET["bad_connection"])

    if resp.status_code != 200:
        raise WBCabinetError(WB_API_CABINET["wb_error"])

    try:
        data = resp.json()
    except ValueError:
        raise WBCabinetError(WB_API_CABINET["wb_bad_answer"])

    cabinet_name = (
        data.get("cabinetName", "Без имени")
        or data.get("organizationName", "Без имени")
        or data.get("name", "Без имени")
    )

    created_raw = (
            data.get("createdAt", None)
            or data.get("createDate", None)
            or data.get("expired_at", None)
    )
    cabinet_created_at = None
    if created_raw:
        try:
            # если WB отдаёт ISO 8601 вида "2024-01-02T03:04:05Z"
            cabinet_created_at = datetime.fromisoformat(
                created_raw.replace("Z", "+00:00")
            )
        except Exception:
            cabinet_created_at = None

    return {
        "cabinet_name": cabinet_name,
        "cabinet_created_at": cabinet_created_at,
    }
