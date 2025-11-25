(function () {
    function getCsrfToken() {
        const input = document.querySelector('#pr-email-form input[name="csrfmiddlewaretoken"]') ||
                      document.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : '';
    }

    const emailModal = document.getElementById('pr-modal-email');
    const codeModal = document.getElementById('pr-modal-code');
    const passwordModal = document.getElementById('pr-modal-password');

    const emailForm = document.getElementById('pr-email-form');
    const codeForm = document.getElementById('pr-code-form');
    const passwordForm = document.getElementById('pr-password-form');

    const emailInput = document.getElementById('pr-email-input');

    const emailError = document.getElementById('pr-email-error');
    const codeError = document.getElementById('pr-code-error');
    const passwordError = document.getElementById('pr-password-error');

    const emailCancel = document.getElementById('pr-email-cancel');
    const codeCancel = document.getElementById('pr-code-cancel');
    const passwordCancel = document.getElementById('pr-password-cancel');

    const resetBtn = document.getElementById('password-reset-btn');

    const codeResendBtn = document.getElementById('pr-code-resend');
    const codeTimer = document.getElementById('pr-code-timer');

    // Оверлей загрузки
    const loadingOverlay = document.getElementById('pr-loading-overlay');
    const loadingTextEl = document.getElementById('pr-loading-text');

    const codeInput = document.getElementById('pr-code-input');
    const password1Input = document.getElementById('pr-password1');
    const password2Input = document.getElementById('pr-password2');

    if (!resetBtn || !emailModal || !codeModal || !passwordModal) {
        return;
    }

    let savedEmail = '';
    let cooldownTimerId = null;
    let cooldownRemaining = 0;

    function openModal(modal) {
        modal.style.display = 'flex'; // flex, чтобы центрировать
    }

    function closeModal(modal) {
        modal.style.display = 'none';
    }

    function clearErrors() {
        emailError.textContent = '';
        codeError.textContent = '';
        passwordError.textContent = '';
    }

    function showLoading(text) {
        if (!loadingOverlay) return;
        if (loadingTextEl && text) {
            loadingTextEl.textContent = text;
        }
        loadingOverlay.style.display = 'flex';
    }

    function updateLoadingText(text) {
        if (loadingTextEl && text) {
            loadingTextEl.textContent = text;
        }
    }

    function hideLoading() {
        if (!loadingOverlay) return;
        loadingOverlay.style.display = 'none';
    }

    function formatTimeHMS(totalSeconds) {
        const s = Math.max(0, Math.floor(totalSeconds));
        const hours = Math.floor(s / 3600);
        const minutes = Math.floor((s % 3600) / 60);
        const seconds = s % 60;

        const pad = (n) => n.toString().padStart(2, '0');

        // всегда выводим hh:mm:ss, даже если часы 0
        return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    }

    function updateTimerText() {
        if (!codeTimer) return;
        if (cooldownRemaining > 0) {
            const formatted = formatTimeHMS(cooldownRemaining);
            codeTimer.textContent = `Повторный запрос кода будет доступен через ${formatted}.`;
        } else {
            codeTimer.textContent = '';
        }
    }

    function resetEmailStep() {
    if (emailForm) {
        emailForm.reset();
        }
        emailError.textContent = '';
    }

    function resetCodeStep() {
        if (codeForm) {
            codeForm.reset();
        }
        codeError.textContent = '';
    }

    function resetPasswordStep() {
        if (passwordForm) {
            passwordForm.reset();
        }
        passwordError.textContent = '';
    }

    function startCooldown(seconds) {
        if (!codeResendBtn || !codeTimer) return;

        if (cooldownTimerId) {
            clearInterval(cooldownTimerId);
            cooldownTimerId = null;
        }

        cooldownRemaining = seconds;
        if (cooldownRemaining <= 0) {
            codeResendBtn.disabled = false;
            codeTimer.textContent = '';
            return;
        }

        codeResendBtn.disabled = true;
        updateTimerText();

        cooldownTimerId = setInterval(function () {
            cooldownRemaining -= 1;
            if (cooldownRemaining <= 0) {
                clearInterval(cooldownTimerId);
                cooldownTimerId = null;
                codeResendBtn.disabled = false;
                codeTimer.textContent = '';
            } else {
                updateTimerText();
            }
        }, 1000);
    }

    // Открыть первый шаг
    resetBtn.addEventListener('click', function () {
        clearErrors();
        savedEmail = '';
        resetEmailStep();
        resetCodeStep();
        resetPasswordStep();
        openModal(emailModal);
    });

    // Отмена
    emailCancel.addEventListener('click', function () {
        resetEmailStep();
        savedEmail = '';
        closeModal(emailModal);
    });

    codeCancel.addEventListener('click', function () {
        resetCodeStep();
        closeModal(codeModal);
    });

    passwordCancel.addEventListener('click', function () {
        resetPasswordStep();
        closeModal(passwordModal);
    });

    // Шаг 1: отправка кода (первая попытка)
    emailForm.addEventListener('submit', function (evt) {
        evt.preventDefault();
        clearErrors();

        const formData = new FormData(emailForm);

        showLoading('Отправляем код...');
        fetch('/password-reset/send-code/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        })
            .then(resp => resp.json().then(data => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                if (!data.ok) {
                    hideLoading();
                    if (data.code === 'cooldown' && data.remaining_seconds) {
                        emailError.textContent = data.error || 'Слишком частые запросы.';
                    } else {
                        emailError.textContent = data.error || 'Произошла ошибка.';
                    }
                    return;
                }

                // успех
                savedEmail = (emailInput.value || '').trim();

                // показываем сообщение, что код отправлен
                updateLoadingText('Сообщение с кодом отправлено на вашу почту');
                const delay = 800; // чтобы пользователь успел увидеть

                setTimeout(function () {
                    hideLoading();
                    resetEmailStep();
                    closeModal(emailModal);
                    resetCodeStep();
                    openModal(codeModal);

                    if (codeResendBtn && typeof data.cooldown_seconds === 'number') {
                        startCooldown(data.cooldown_seconds);
                    }
                }, delay);
            })
            .catch(err => {
                hideLoading();
                emailError.textContent = 'Ошибка сети. Попробуйте ещё раз.';
            });
    });

    // Шаг 2: проверка кода
    codeForm.addEventListener('submit', function (evt) {
        evt.preventDefault();
        clearErrors();

        const formData = new FormData(codeForm);

        showLoading('Проверяем код...');
        fetch('/password-reset/verify-code/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        })
            .then(resp => resp.json().then(data => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                hideLoading();
                if (!data.ok) {
                    codeError.textContent = data.error || 'Произошла ошибка.';
                    return;
                }

                // очищаем код и ошибки
                resetCodeStep();
                closeModal(codeModal);

                // подготавливаем форму нового пароля
                resetPasswordStep();
                openModal(passwordModal);
            })
            .catch(err => {
                hideLoading();
                codeError.textContent = 'Ошибка сети. Попробуйте ещё раз.';
            });
    });

    // Кнопка "Запросить код повторно"
    if (codeResendBtn) {
        codeResendBtn.addEventListener('click', function () {
            if (codeResendBtn.disabled) return;
            clearErrors();

            if (!savedEmail) {
                codeError.textContent = 'Сначала введите email.';
                return;
            }

            const formData = new FormData();
            formData.append('email', savedEmail);

            showLoading('Отправляем код...');
            fetch('/password-reset/send-code/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                },
                body: formData,
            })
                .then(resp => resp.json().then(data => ({ status: resp.status, data })))
                .then(({ status, data }) => {
                    if (!data.ok) {
                        hideLoading();
                        if (data.code === 'cooldown' && data.remaining_seconds) {
                            codeError.textContent = data.error || 'Слишком частые запросы.';
                            startCooldown(data.remaining_seconds);
                        } else {
                            codeError.textContent = data.error || 'Произошла ошибка.';
                        }
                        return;
                    }

                    // успех повторной отправки
                    updateLoadingText('Новый код отправлен на вашу почту');
                    const delay = 800;
                    setTimeout(function () {
                        hideLoading();
                        if (typeof data.cooldown_seconds === 'number') {
                            startCooldown(data.cooldown_seconds);
                        }
                    }, delay);
                })
                .catch(err => {
                    hideLoading();
                    codeError.textContent = 'Ошибка сети. Попробуйте ещё раз.';
                });
        });
    }

    // Шаг 3: установка нового пароля
    passwordForm.addEventListener('submit', function (evt) {
        evt.preventDefault();
        clearErrors();

        const formData = new FormData(passwordForm);

        showLoading('Сохраняем новый пароль...');
        fetch('/password-reset/confirm/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        })
            .then(resp => resp.json().then(data => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                hideLoading();
                if (!data.ok) {
                    passwordError.textContent = data.error || 'Произошла ошибка.';
                    return;
                }
                resetPasswordStep();
                closeModal(passwordModal);
                alert('Пароль успешно изменён. Введите новый пароль в форму авторизации.');
            })
            .catch(err => {
                hideLoading();
                passwordError.textContent = 'Ошибка сети. Попробуйте ещё раз.';
            });
    });
})();
