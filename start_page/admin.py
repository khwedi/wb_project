from django.contrib import admin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'is_staff', 'is_active', 'date_joined','password')
    search_fields = ('email', 'username')
    ordering = ('-id',)
    readonly_fields = ('email', 'password')
    list_filter = ('email', 'is_active', 'is_staff', 'date_joined')
