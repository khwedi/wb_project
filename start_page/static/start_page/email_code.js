// Универсальная логика модалок для:
// - mode: "password_reset"  (сброс пароля)
// - mode: "signup"          (подтверждение email при регистрации)
// - mode: "change_email"    (смена email в профиле с подтверждением паролем)
(function () {
    const EC = window.EC_CONFIG || {};
    const mode = EC.mode || "password_reset";
    const triggerId = EC.triggerId || (mode === "password_reset" ? "password-reset-btn" : null);
    const emailSourceId = EC.emailInputId || null;
    const statusElementId = EC.statusElementId || null;
    const passwordResetSuccessEl = document.getElementById("password-reset-success");

    const ENDPOINTS = {
        password_reset: {
            sendUrl: "/email-code/send/password_reset/",
            verifyUrl: "/email-code/verify/password_reset/",
            confirmUrl: "/email-code/confirm/password_reset/",
        },
        signup: {
            sendUrl: "/email-code/send/signup/",
            verifyUrl: "/email-code/verify/signup/",
            confirmUrl: null,  // отдельного confirm-шаг нет
        },
        change_email: {
            sendUrl: "/email-code/send/change_email/",
            verifyUrl: "/email-code/verify/change_email/",
            confirmUrl: "/email-code/confirm/change_email/",
        },
    };

    const CURRENT = ENDPOINTS[mode] || ENDPOINTS.password_reset;

    const isPasswordReset = mode === "password_reset";
    const isSignup = mode === "signup";
    const isChangeEmail = mode === "change_email";
    const hasPasswordStep = isPasswordReset || isChangeEmail;

    function getCsrfToken() {
        const input = document.querySelector("input[name='csrfmiddlewaretoken']");
        return input ? input.value : "";
    }

    const emailModal = document.getElementById("pr-modal-email");
    const codeModal = document.getElementById("pr-modal-code");
    const passwordModal = document.getElementById("pr-modal-password");

    const emailForm = document.getElementById("pr-email-form");
    const codeForm = document.getElementById("pr-code-form");
    const passwordForm = document.getElementById("pr-password-form");

    const emailInput = document.getElementById("pr-email-input");
    const emailError = document.getElementById("pr-email-error");
    const codeError = document.getElementById("pr-code-error");
    const passwordError = document.getElementById("pr-password-error");

    const emailCancel = document.getElementById("pr-email-cancel");
    const codeCancel = document.getElementById("pr-code-cancel");
    const passwordCancel = document.getElementById("pr-password-cancel");

    const codeResendBtn = document.getElementById("pr-code-resend");
    const codeTimer = document.getElementById("pr-code-timer");

    const loadingOverlay = document.getElementById("pr-loading-overlay");
    const loadingTextEl = document.getElementById("pr-loading-text");

    const passwordTitle = document.getElementById("pr-password-title");
    const password1Input = document.getElementById("pr-password1");
    const password2Input = document.getElementById("pr-password2");

    const triggerBtn = triggerId ? document.getElementById(triggerId) : null;
    const emailSourceInput = emailSourceId ? document.getElementById(emailSourceId) : null;
    const statusEl = statusElementId ? document.getElementById(statusElementId) : null;

    if (!triggerBtn || !emailModal || !codeModal || !emailForm || !codeForm) {
        return;
    }
    if (hasPasswordStep && (!passwordModal || !passwordForm)) {
        return;
    }

    // адаптация 3-й модалки под смену email (ввод текущего пароля)
    if (isChangeEmail) {
        if (passwordTitle) {
            passwordTitle.textContent = "Подтверждение пароля";
        }
        if (password1Input) {
            password1Input.placeholder = "Текущий пароль";
        }
        if (password2Input) {
            password2Input.style.display = "none";
        }
    }

    let savedEmail = "";
    let cooldownTimerId = null;
    let cooldownRemaining = 0;

    function openModal(modal) {
        modal.style.display = "flex";
    }

    function closeModal(modal) {
        modal.style.display = "none";
    }

    function clearErrors() {
        if (emailError) emailError.textContent = "";
        if (codeError) codeError.textContent = "";
        if (passwordError) passwordError.textContent = "";
    }

    function resetEmailStep() {
        if (emailForm) emailForm.reset();
        if (emailError) emailError.textContent = "";
    }

    function resetCodeStep() {
        if (codeForm) codeForm.reset();
        if (codeError) codeError.textContent = "";
    }

    function resetPasswordStep() {
        if (passwordForm) passwordForm.reset();
        if (passwordError) passwordError.textContent = "";
    }

    function showLoading(text) {
        if (!loadingOverlay) return;
        if (loadingTextEl && text) {
            loadingTextEl.textContent = text;
        }
        loadingOverlay.style.display = "flex";
    }

    function updateLoadingText(text) {
        if (loadingTextEl && text) {
            loadingTextEl.textContent = text;
        }
    }

    function hideLoading() {
        if (!loadingOverlay) return;
        loadingOverlay.style.display = "none";
    }

    function formatTimeHMS(totalSeconds) {
        const s = Math.max(0, Math.floor(totalSeconds));
        const hours = Math.floor(s / 3600);
        const minutes = Math.floor((s % 3600) / 60);
        const seconds = s % 60;
        const pad = (n) => n.toString().padStart(2, "0");
        return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    }

    function updateTimerText() {
        if (!codeTimer) return;
        if (cooldownRemaining > 0) {
            const formatted = formatTimeHMS(cooldownRemaining);
            codeTimer.textContent = `Повторный запрос кода будет доступен через ${formatted}.`;
        } else {
            codeTimer.textContent = "";
        }
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
            codeTimer.textContent = "";
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
                codeTimer.textContent = "";
            } else {
                updateTimerText();
            }
        }, 1000);
    }

    // Открытие цепочки модалок по кнопке на странице
    triggerBtn.addEventListener("click", function () {
        clearErrors();
        resetEmailStep();
        resetCodeStep();
        if (hasPasswordStep) {
            resetPasswordStep();
        }

        if (passwordResetSuccessEl && isPasswordReset) {
            passwordResetSuccessEl.textContent = '';
        }

        if (emailSourceInput && emailInput) {
            emailInput.value = (emailSourceInput.value || "").trim();
        }

        openModal(emailModal);
    });

    // Отмена в модалках
    if (emailCancel) {
        emailCancel.addEventListener("click", function () {
            resetEmailStep();
            closeModal(emailModal);
        });
    }

    if (codeCancel) {
        codeCancel.addEventListener("click", function () {
            resetCodeStep();
            closeModal(codeModal);
        });
    }

    if (hasPasswordStep && passwordCancel) {
        passwordCancel.addEventListener("click", function () {
            resetPasswordStep();
            closeModal(passwordModal);
        });
    }

    // Шаг 1: отправка кода
    emailForm.addEventListener("submit", function (evt) {
        evt.preventDefault();
        clearErrors();

        const formData = new FormData(emailForm);

        // для signup — берём email из внешнего поля формы
        if (emailSourceInput) {
            const v = (emailSourceInput.value || "").trim();
            formData.set("email", v);
        }

        showLoading("Отправляем код...");
        fetch(CURRENT.sendUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
            },
            body: formData,
        })
            .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                if (!data.ok) {
                    hideLoading();
                    if (data.code === "cooldown" && data.remaining_seconds) {
                        if (emailError) emailError.textContent = data.error || "Слишком частые запросы кода.";
                        startCooldown(data.remaining_seconds);
                    } else {
                        if (emailError) emailError.textContent = data.error || "Произошла ошибка.";
                    }
                    return;
                }

                if (emailInput) {
                    savedEmail = (emailInput.value || "").trim();
                }

                updateLoadingText("Сообщение с кодом отправлено на вашу почту");
                setTimeout(function () {
                    hideLoading();
                    closeModal(emailModal);
                    resetCodeStep();
                    openModal(codeModal);

                    if (codeResendBtn && typeof data.cooldown_seconds === "number") {
                        startCooldown(data.cooldown_seconds);
                    }

                    if (statusEl && isSignup) {
                        statusEl.textContent = "Код отправлен на вашу почту.";
                    }
                }, 800);
            })
            .catch(() => {
                hideLoading();
                if (emailError) emailError.textContent = "Ошибка сети. Попробуйте ещё раз.";
            });
    });

    // Шаг 2: проверка кода
    codeForm.addEventListener("submit", function (evt) {
        evt.preventDefault();
        clearErrors();

        const formData = new FormData(codeForm);

        showLoading("Проверяем код...");
        fetch(CURRENT.verifyUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
            },
            body: formData,
        })
            .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                hideLoading();
                if (!data.ok) {
                    if (codeError) codeError.textContent = data.error || "Произошла ошибка.";
                    return;
                }

                if (isPasswordReset || isChangeEmail) {
                    closeModal(codeModal);
                    resetPasswordStep();
                    openModal(passwordModal);
                } else if (isSignup) {
                    closeModal(codeModal);
                    if (statusEl) {
                        statusEl.textContent = "Email подтверждён ✔";
                    }
                    alert("Email успешно подтверждён.");
                } else {
                    closeModal(codeModal);
                }
            })
            .catch(() => {
                hideLoading();
                if (codeError) codeError.textContent = "Ошибка сети. Попробуйте ещё раз.";
            });
    });

    // Повторная отправка кода
    if (codeResendBtn) {
        codeResendBtn.addEventListener("click", function () {
            if (codeResendBtn.disabled) return;
            clearErrors();

            const emailToUse =
                savedEmail || (emailInput ? (emailInput.value || "").trim() : "");

            if (!emailToUse) {
                if (codeError) codeError.textContent = "Сначала введите email.";
                return;
            }

            const formData = new FormData();
            formData.append("email", emailToUse);

            showLoading("Отправляем код...");
            fetch(CURRENT.sendUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                },
                body: formData,
            })
                .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
                .then(({ status, data }) => {
                    if (!data.ok) {
                        hideLoading();
                        if (data.code === "cooldown" && data.remaining_seconds) {
                            if (codeError) codeError.textContent = data.error || "Слишком частые запросы кода.";
                            startCooldown(data.remaining_seconds);
                        } else {
                            if (codeError) codeError.textContent = data.error || "Произошла ошибка.";
                        }
                        return;
                    }

                    updateLoadingText("Новый код отправлен на вашу почту");
                    setTimeout(function () {
                        hideLoading();
                        if (typeof data.cooldown_seconds === "number") {
                            startCooldown(data.cooldown_seconds);
                        }
                        if (statusEl && isSignup) {
                            statusEl.textContent = "Новый код отправлен на вашу почту.";
                        }
                    }, 800);
                })
                .catch(() => {
                    hideLoading();
                    if (codeError) codeError.textContent = "Ошибка сети. Попробуйте ещё раз.";
                });
        });
    }

    // Шаг 3: обработка пароля / текущего пароля
    if (hasPasswordStep && passwordForm) {
        passwordForm.addEventListener("submit", function (evt) {
            evt.preventDefault();
            clearErrors();

            const pwd1 = password1Input ? password1Input.value : "";
            const pwd2 = password2Input ? password2Input.value : "";

            if (isPasswordReset) {
                const formData = new FormData(passwordForm);

                showLoading("Сохраняем новый пароль...");
                if (!CURRENT.confirmUrl) {
                    hideLoading();
                    if (passwordError) passwordError.textContent = "Не настроен URL смены пароля.";
                    return;
                }

                fetch(CURRENT.confirmUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: formData,
                })
                    .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
                    .then(({ status, data }) => {
                        hideLoading();
                        if (!data.ok) {
                            if (passwordError) passwordError.textContent = data.error || "Произошла ошибка.";
                            return;
                        }
                        resetPasswordStep();
                        closeModal(passwordModal);

                        if (passwordResetSuccessEl) {
                        passwordResetSuccessEl.textContent = "Пароль успешно изменён. Введите новый пароль и авторизуйтесь.";
                        }
                    })
                    .catch(() => {
                        hideLoading();
                        if (passwordError) passwordError.textContent = "Ошибка сети. Попробуйте ещё раз.";
                    });
            } else if (isChangeEmail) {
                if (!pwd1) {
                    if (passwordError) passwordError.textContent = "Введите текущий пароль.";
                    return;
                }

                if (!CURRENT.confirmUrl) {
                    if (passwordError) passwordError.textContent = "Не настроен URL смены email.";
                    return;
                }

                const formData = new FormData();
                formData.append("current_password", pwd1);

                showLoading("Сохраняем новый email...");
                fetch(CURRENT.confirmUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: formData,
                })
                    .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
                    .then(({ status, data }) => {
                        hideLoading();
                        if (!data.ok) {
                            if (passwordError) passwordError.textContent = data.error || "Произошла ошибка.";
                            return;
                        }

                        const emailMaskedEl = document.getElementById("email-masked");
                        const emailFullEl = document.getElementById("email-full");

                        if (emailMaskedEl) {
                            emailMaskedEl.textContent = data.masked_email || "";
                            emailMaskedEl.style.display = "inline";
                        }
                        if (emailFullEl) {
                            emailFullEl.textContent = data.email || "";
                            emailFullEl.style.display = "none";
                        }

                        resetPasswordStep();
                        closeModal(passwordModal);
                        alert("Email успешно изменён.");
                    })
                    .catch(() => {
                        hideLoading();
                        if (passwordError) passwordError.textContent = "Ошибка сети. Попробуйте ещё раз.";
                    });
            }
        });
    }
})();
