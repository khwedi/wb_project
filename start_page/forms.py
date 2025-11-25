from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email

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
        Вызов нашей общей функции validate_email_for_registration.
        """
        email = self.cleaned_data.get("email","")
        return validate_email(email, type='signup')


    def clean_password(self):
        """
        Вызов нашей общей функции validate_password.
        """
        password = self.cleaned_data.get("password","")
        return validate_password(password)


    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """
    Форма авторизации: email + пароль.
    Проверяем, что поля не пустые и что пара (email, пароль) корректна.
    """
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "Введите ваш email"}),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"placeholder": "Введите пароль"}),
    )

    # def clean_email(self):
    #     email = self.cleaned_data.get("email", "")
    #     return validate_email(email, type='login')
    #
    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        password = password.strip()
        if not password:
            raise ValidationError("Введите пароль.")
        return password

    def clean(self):
        """
        Общая проверка: email + пароль должны соответствовать существующему пользователю.
        """
        from django.contrib.auth import authenticate

        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        # если по полям уже есть ошибки — дальше не идём
        if self.errors:
            return cleaned_data

        user = authenticate(username=email, password=password)
        if user is None:
            raise ValidationError("Неверный email или пароль.")

        self.user = user
        return cleaned_data

    def get_user(self):
        return getattr(self, "user", None)