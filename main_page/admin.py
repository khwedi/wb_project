from django.contrib import admin
from .models import WBCabinet


@admin.register(WBCabinet)
class WBCabinetAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "api_key_name", "cabinet_name", "cabinet_created_at", "created_at")
    search_fields = ("api_key_name", "cabinet_name", "user__username", "user__email")
    list_filter = ("user",)
