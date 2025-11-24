from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Не указан email")
        if not username:
            raise ValueError("Не указано имя пользователя")

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            username=username,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("У суперпользователя is_staff должен быть True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("У суперпользователя is_superuser должен быть True")

        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Кастомная модель пользователя сайта.

    Логиним по email (USERNAME_FIELD = 'email').
    В регистрации используем поля: username, email, password.
    """
    email = models.EmailField("Email", unique=True)
    username = models.CharField("Имя пользователя", max_length=150)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class UserSession(models.Model):
    """
    Лог сессий пользователя:
    - user: к какому пользователю относится
    - session_key: ключ сессии Django
    - start_time: когда сессия началась
    - end_time: когда должна закончиться
    - duration: длительность (end_time - start_time)
    - is_active: флаг "активна ли сессия сейчас"
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    session_key = models.CharField(max_length=40, db_index=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.DurationField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"Session {self.session_key} for {self.user.email}"