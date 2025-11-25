from django.contrib import admin
from django.utils import timezone

from .models import *


class SessionStatusFilter(admin.SimpleListFilter):
    """
    Фильтр по статусу сессии относительно текущего времени:
    - Активные (end_time > сейчас)
    - Истёкшие (end_time <= сейчас)
    """
    title = "Статус по времени"
    parameter_name = "time_status"

    def lookups(self, request, model_admin):
        return (
            ("active", "Активные (end_time > сейчас)"),
            ("expired", "Истёкшие (end_time ≤ сейчас)"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "active":
            return queryset.filter(end_time__gt=timezone.now())
        if value == "expired":
            return queryset.filter(end_time__lte=timezone.now())
        return queryset


class UserSessionInline(admin.TabularInline):
    """
    Показывает сессии конкретного пользователя прямо в его карточке.
    Только для чтения, без создания/удаления.
    """
    model = UserSession
    extra = 0
    can_delete = False
    readonly_fields = (
        "session_key",
        "start_time",
        "end_time",
        "duration",
        "is_active",
        "created_at",
        "updated_at",
    )
    fields = (
        "session_key",
        "start_time",
        "end_time",
        "duration",
        "is_active",
        "created_at",
        "updated_at",
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "session_key",
        "start_time",
        "end_time",
        "duration",
        "is_active",
    )
    list_filter = (
        "is_active",
        SessionStatusFilter,
        "user",
    )
    search_fields = ("user__email", "user__username", "session_key")
    readonly_fields = (
        "user",
        "session_key",
        "start_time",
        "end_time",
        "duration",
        "is_active",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "start_time"


class PasswordResetRequestInline(admin.TabularInline):
    model = PasswordResetRequest
    extra = 0
    can_delete = False
    readonly_fields = ("code", "created_at", "expires_at", "is_used")
    fields = ("code", "created_at", "expires_at", "is_used")


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'is_staff', 'is_active', 'date_joined','password')
    search_fields = ('email', 'username')
    ordering = ('-id',)
    readonly_fields = ('email', 'password')
    list_filter = ('email', 'is_active', 'is_staff', 'date_joined')

    inlines = [UserSessionInline, PasswordResetRequestInline]


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "expires_at", "is_used")
    list_filter = ("is_used", "created_at", "expires_at", "user")
    search_fields = ("user__email", "user__username", "code")
    readonly_fields = ("user", "code", "created_at", "expires_at", "is_used")

    date_hierarchy = "created_at"




