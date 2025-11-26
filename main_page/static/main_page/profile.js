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
});
