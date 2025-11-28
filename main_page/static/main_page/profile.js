document.addEventListener('DOMContentLoaded', function () {
    function getCsrfToken() {
        const el = document.getElementById('csrf-token');
        return el ? el.value : '';
    }

    // ===== Показ/скрытие email =====
    const emailMasked = document.getElementById('email-masked');
    const emailFull = document.getElementById('email-full');
    const emailToggleBtn = document.getElementById('email-toggle-btn');

    if (emailMasked && emailFull && emailToggleBtn) {
        emailToggleBtn.addEventListener('click', function () {
            const isMaskedVisible = emailMasked.style.display !== 'none';

            if (isMaskedVisible) {
                emailMasked.style.display = 'none';
                emailFull.style.display = 'inline';
                emailToggleBtn.textContent = 'Скрыть';
            } else {
                emailMasked.style.display = 'inline';
                emailFull.style.display = 'none';
                emailToggleBtn.textContent = 'Показать';
            }
        });
    }

    // ===== Редактирование имени пользователя =====
    const usernameDisplay = document.getElementById('username-display');
    const usernameInput = document.getElementById('username-input');
    const usernameError = document.getElementById('username-error');

    const editBtn = document.getElementById('username-edit-btn');
    const saveBtn = document.getElementById('username-save-btn');
    const cancelBtn = document.getElementById('username-cancel-btn');

    if (usernameDisplay && usernameInput && usernameError && editBtn && saveBtn && cancelBtn) {
        function clearUsernameError() {
            usernameError.textContent = '';
        }

        function switchToEdit() {
            clearUsernameError();
            usernameInput.value = usernameDisplay.textContent.trim();
            usernameDisplay.style.display = 'none';
            usernameInput.style.display = 'inline-block';

            editBtn.style.display = 'none';
            saveBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'inline-block';

            usernameInput.focus();
            usernameInput.select();
        }

        function switchToView() {
            usernameInput.style.display = 'none';
            usernameDisplay.style.display = 'inline';

            editBtn.style.display = 'inline-block';
            saveBtn.style.display = 'none';
            cancelBtn.style.display = 'none';
        }

        editBtn.addEventListener('click', switchToEdit);

        cancelBtn.addEventListener('click', function () {
            clearUsernameError();
            usernameInput.value = usernameDisplay.textContent.trim();
            switchToView();
        });

        saveBtn.addEventListener('click', function () {
            clearUsernameError();
            const newUsername = usernameInput.value.trim();

            if (!newUsername) {
                usernameError.textContent = 'Имя пользователя не может быть пустым.';
                return;
            }

            const formData = new FormData();
            formData.append('username', newUsername);

            fetch('/main/profile/update-username/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                },
                body: formData,
            })
                .then(resp => resp.json().then(data => ({ status: resp.status, data })))
                .then(({ status, data }) => {
                    if (!data.ok) {
                        usernameError.textContent = data.error || 'Произошла ошибка при сохранении.';
                        return;
                    }

                    // успешно обновили на сервере — обновляем отображение
                    usernameDisplay.textContent = data.username;
                    switchToView();
                })
                .catch(() => {
                    usernameError.textContent = 'Ошибка сети. Попробуйте ещё раз.';
                });
        });
    }

    // ===== Смена пароля =====
    const passwordPlaceholder = document.getElementById('password-placeholder');
    const passwordEditBlock = document.getElementById('password-edit-block');
    const currentPasswordInput = document.getElementById('current-password-input');
    const newPassword1Input = document.getElementById('new-password1-input');
    const newPassword2Input = document.getElementById('new-password2-input');
    const passwordChangeError = document.getElementById('password-change-error');
    const passwordChangeSuccess = document.getElementById('password-change-success');

    const pwEditBtn = document.getElementById('password-edit-btn');
    const pwSaveBtn = document.getElementById('password-save-btn');
    const pwCancelBtn = document.getElementById('password-cancel-btn');

    if (
        passwordPlaceholder && passwordEditBlock &&
        currentPasswordInput && newPassword1Input && newPassword2Input &&
        passwordChangeError && passwordChangeSuccess &&
        pwEditBtn && pwSaveBtn && pwCancelBtn
    ) {
        function clearPasswordMessages() {
            passwordChangeError.textContent = '';
            passwordChangeSuccess.textContent = '';
        }

        function switchToPasswordEdit() {
            clearPasswordMessages();
            if (passwordPlaceholder) {
                passwordPlaceholder.style.display = 'none';
            }
            passwordEditBlock.style.display = 'flex';

            pwEditBtn.style.display = 'none';
            pwSaveBtn.style.display = 'inline-block';
            pwCancelBtn.style.display = 'inline-block';

            currentPasswordInput.value = '';
            newPassword1Input.value = '';
            newPassword2Input.value = '';
            currentPasswordInput.focus();
        }

        function switchToPasswordView() {
            clearPasswordMessages();
            passwordEditBlock.style.display = 'none';
            if (passwordPlaceholder) {
                passwordPlaceholder.style.display = 'inline';
            }

            pwEditBtn.style.display = 'inline-block';
            pwSaveBtn.style.display = 'none';
            pwCancelBtn.style.display = 'none';
        }

        pwEditBtn.addEventListener('click', switchToPasswordEdit);

        pwCancelBtn.addEventListener('click', function () {
            switchToPasswordView();
        });

        pwSaveBtn.addEventListener('click', function () {
            clearPasswordMessages();

            const currentPassword = currentPasswordInput.value.trim();
            const password1 = newPassword1Input.value.trim();
            const password2 = newPassword2Input.value.trim();

            if (!currentPassword || !password1 || !password2) {
                passwordChangeError.textContent = 'Заполните все поля.';
                return;
            }

            if (password1 !== password2) {
                passwordChangeError.textContent = 'Новые пароли не совпадают.';
                return;
            }

            const formData = new FormData();
            formData.append('current_password', currentPassword);
            formData.append('password1', password1);
            formData.append('password2', password2);

            fetch('/main/profile/change-password/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                },
                body: formData,
            })
                .then(resp => resp.json().then(data => ({ status: resp.status, data })))
                .then(({ status, data }) => {
                    if (!data.ok) {
                        passwordChangeError.textContent = data.error || 'Произошла ошибка при смене пароля.';
                        return;
                    }

                    switchToPasswordView();
                    passwordChangeSuccess.textContent = 'Пароль успешно изменён.';
                })
                .catch(() => {
                    passwordChangeError.textContent = 'Ошибка сети. Попробуйте ещё раз.';
                });
        });
    }
});
