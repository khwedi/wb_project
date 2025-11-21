from django.shortcuts import render


def main_page(request):
    """
    Основная страница после регистрации/логина.
    Пока простая заглушка.
    """
    return render(request, "main_page/main_page.html")
