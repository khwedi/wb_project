from django.conf import settings
from django.db import models


class WBCabinet(models.Model):
    """
    Кабинет Wildberries, привязанный к пользователю.
    Храним: API-ключ, его название, название кабинета и дату его создания.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wb_cabinets",
    )
    api_key = models.CharField(max_length=255)
    api_key_name = models.CharField(max_length=100)
    cabinet_name = models.CharField(max_length=255, blank=True)
    cabinet_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "api_key")
        verbose_name = "Кабинет WB"
        verbose_name_plural = "Кабинеты WB"

    def __str__(self):
        return f"{self.api_key_name} ({self.user})"