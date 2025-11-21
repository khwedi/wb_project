from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email

from .models import *
from .validators import *


class RegisterForm(forms.ModelForm):
    """
    Форма регистрации: имя пользователя, email, пароль.
    Здесь переопределяем save, который вызываем в views.signup. Пароль сохраняется в хешированном виде.
    """
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Введите ваше имя'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Введите ваш email'}),
            'password': forms.PasswordInput(attrs={'placeholder': 'Введите пароль'}),
        }


    def clean_username(self):
        """
        Проверка для поля имени пользователя: поле не пустое.
        """
        username = self.cleaned_data.get("username", "")
        return validate_username(username)


    def clean_email(self):
        """
        Вызов нашей общей функции validate_email_address.
        """
        email = self.cleaned_data.get("email")
        return validate_email_address(email)


    def clean_password(self):
        """
        Вызов нашей общей функции validate_password.
        """
        password = self.cleaned_data.get("password")
        return validate_password(password)


    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
