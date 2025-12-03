document.addEventListener('DOMContentLoaded', function () {
    // ===== Helpers =====
    function getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';').map(c => c.trim());
        for (const c of cookies) {
            if (c.startsWith(name + '=')) {
                return decodeURIComponent(c.substring(name.length + 1));
            }
        }
        return '';
    }

    // ===== Элементы кабинетов =====
    const cabinetSelect = document.getElementById('cabinet-select');
    const cabinetAddBtn = document.getElementById('cabinet-add-btn');
    const cabinetShowBtn = document.getElementById('cabinet-show-btn');
    const cabinetsTableWrapper = document.getElementById('cabinets-table-wrapper');
    const cabinetsTableBody = document.getElementById('cabinets-table-body');

    const cabinetsGlobalError = document.getElementById('cabinets-global-error');
    const cabinetsGlobalStatus = document.getElementById('cabinets-global-status');

    // Модалка добавления кабинета
    const cabinetModal = document.getElementById('cabinet-modal');
    const cabinetApiKeyInput = document.getElementById('cabinet-api-key-input');
    const cabinetApiKeyNameInput = document.getElementById('cabinet-api-key-name-input');
    const cabinetModalError = document.getElementById('cabinet-modal-error');
    const cabinetModalSaveBtn = document.getElementById('cabinet-modal-save-btn');
    const cabinetModalCancelBtn = document.getElementById('cabinet-modal-cancel-btn');

    // Модалка синхронизации
    const cabinetSyncModal = document.getElementById('cabinet-sync-modal');
    const cabinetSyncMessage = document.getElementById('cabinet-sync-message');
    const cabinetSyncConfirmBtn = document.getElementById('cabinet-sync-confirm-btn');
    const cabinetSyncCancelBtn = document.getElementById('cabinet-sync-cancel-btn');

    // Модалка удаления
    const cabinetDeleteModal = document.getElementById('cabinet-delete-modal');
    const cabinetDeleteMessage = document.getElementById('cabinet-delete-message');
    const cabinetDeleteConfirmBtn = document.getElementById('cabinet-delete-confirm-btn');
    const cabinetDeleteCancelBtn = document.getElementById('cabinet-delete-cancel-btn');

    // Мини-редактор
    const inlineEditor = document.getElementById('cabinet-inline-editor');
    const inlineEditorTextarea = document.getElementById('cabinet-inline-editor-text');
    const inlineEditorSaveBtn = document.getElementById('cabinet-inline-editor-save');
    const inlineEditorCancelBtn = document.getElementById('cabinet-inline-editor-cancel');

    let inlineEditorTarget = null;


    let CABINETS_DATA = [];
    let pendingSyncCabinetId = null;
    let pendingDeleteCabinetId = null;
    const rowMessageTimeouts = {};
    let editingCabinetId = null;

    function clearCabinetsMessages() {
        if (cabinetsGlobalError) cabinetsGlobalError.textContent = '';
        if (cabinetsGlobalStatus) cabinetsGlobalStatus.textContent = '';
    }

    function setCabinetsError(msg) {
        clearCabinetsMessages();
        if (cabinetsGlobalError) {
            cabinetsGlobalError.textContent = msg || '';
        }
    }

    function setCabinetsStatus(msg) {
        clearCabinetsMessages();
        if (cabinetsGlobalStatus) {
            cabinetsGlobalStatus.textContent = msg || '';
        }
    }

    // ===== Сообщения под конкретной строкой =====
    function clearRowMessage(cabinetId) {
        if (!cabinetsTableBody) return;
        const row = cabinetsTableBody.querySelector(
            '.cabinet-message-row[data-cabinet-id="' + cabinetId + '"]'
        );
        if (!row) return;
        const cell = row.querySelector('.cabinet-row-message');
        if (cell) {
            cell.textContent = '';
            cell.classList.remove('cabinet-row-message-success', 'cabinet-row-message-error');
        }
        row.style.display = 'none';

        if (rowMessageTimeouts[cabinetId]) {
            clearTimeout(rowMessageTimeouts[cabinetId]);
            delete rowMessageTimeouts[cabinetId];
        }
    }

    function setRowMessage(cabinetId, message, type) {
        if (!cabinetsTableBody) return;
        const row = cabinetsTableBody.querySelector(
            '.cabinet-message-row[data-cabinet-id="' + cabinetId + '"]'
        );
        if (!row) return;
        const cell = row.querySelector('.cabinet-row-message');
        if (!cell) return;

        cell.textContent = message || '';
        cell.classList.remove('cabinet-row-message-success', 'cabinet-row-message-error');

        if (type === 'success') {
            cell.classList.add('cabinet-row-message-success');
        } else if (type === 'error') {
            cell.classList.add('cabinet-row-message-error');
        }

        row.style.display = message ? 'table-row' : 'none';

        if (rowMessageTimeouts[cabinetId]) {
            clearTimeout(rowMessageTimeouts[cabinetId]);
        }
        rowMessageTimeouts[cabinetId] = setTimeout(function () {
            clearRowMessage(cabinetId);
        }, 3000);
    }

    // ===== Select и таблица =====
    function fillCabinetSelect() {
        if (!cabinetSelect) return;

        cabinetSelect.innerHTML = '';

        if (CABINETS_DATA.length === 0) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'API ключи не добавлены';
            cabinetSelect.appendChild(opt);
            cabinetSelect.disabled = true;
            return;
        }

        cabinetSelect.disabled = false;

        if (CABINETS_DATA.length > 1) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'Выберите API ключ';
            cabinetSelect.appendChild(opt);
        }

        CABINETS_DATA.forEach((item) => {
            const opt = document.createElement('option');
            opt.value = String(item.id);
            opt.textContent = item.api_key_name;
            cabinetSelect.appendChild(opt);
        });

        if (CABINETS_DATA.length === 1) {
            cabinetSelect.value = String(CABINETS_DATA[0].id);
        }
    }

    function renderCabinetsTable(selectedId) {
        if (!cabinetsTableBody) return;

        cabinetsTableBody.innerHTML = '';

        if (CABINETS_DATA.length === 0) {
            cabinetsTableWrapper.style.display = 'none';
            return;
        }

        const filtered = selectedId
            ? CABINETS_DATA.filter((item) => String(item.id) === String(selectedId))
            : CABINETS_DATA;

        filtered.forEach((item) => {
            const isEditing = String(item.id) === String(editingCabinetId);

            const tr = document.createElement('tr');
            tr.dataset.cabinetId = String(item.id);

            if (!isEditing) {
                // ----- Обычный режим просмотра -----
                const tdKey = document.createElement('td');
                tdKey.textContent = item.short_api_key || '';
                tr.appendChild(tdKey);

                const tdName = document.createElement('td');
                tdName.textContent = item.api_key_name || '';
                tr.appendChild(tdName);

                const tdCabinetName = document.createElement('td');
                tdCabinetName.textContent = item.cabinet_name || '';
                tr.appendChild(tdCabinetName);

                const tdCreated = document.createElement('td');
                tdCreated.textContent = item.cabinet_created_at || '';
                tr.appendChild(tdCreated);

                const tdMenu = document.createElement('td');
                const menuWrapper = document.createElement('div');
                menuWrapper.className = 'cabinet-row-menu';
                menuWrapper.dataset.cabinetId = String(item.id);

                const menuBtn = document.createElement('button');
                menuBtn.type = 'button';
                menuBtn.className = 'cabinet-menu-btn';
                menuBtn.textContent = '⋯';

                const menuDropdown = document.createElement('div');
                menuDropdown.className = 'cabinet-menu-dropdown';

                const editBtn = document.createElement('button');
                editBtn.type = 'button';
                editBtn.dataset.action = 'edit';
                editBtn.textContent = 'Редактировать';

                const deleteBtn = document.createElement('button');
                deleteBtn.type = 'button';
                deleteBtn.dataset.action = 'delete';
                deleteBtn.textContent = 'Удалить';

                const checkBtn = document.createElement('button');
                checkBtn.type = 'button';
                checkBtn.dataset.action = 'check';
                checkBtn.textContent = 'Проверить';

                menuDropdown.appendChild(editBtn);
                menuDropdown.appendChild(deleteBtn);
                menuDropdown.appendChild(checkBtn);

                menuWrapper.appendChild(menuBtn);
                menuWrapper.appendChild(menuDropdown);

                tdMenu.appendChild(menuWrapper);
                tr.appendChild(tdMenu);
            } else {
                // ----- Режим редактирования -----
                // 1) API ключ (новый)
                const tdKey = document.createElement('td');
                const apiKeyInput = document.createElement('input');
                apiKeyInput.type = 'text';
                apiKeyInput.className = 'cabinet-input cabinet-edit-api-key';
                apiKeyInput.placeholder = 'Новый API ключ (оставьте пустым, чтобы не менять)';
                tdKey.appendChild(apiKeyInput);
                tr.appendChild(tdKey);

                // 2) Наименование API ключа
                const tdName = document.createElement('td');
                const nameInput = document.createElement('input');
                nameInput.type = 'text';
                nameInput.className = 'cabinet-input cabinet-edit-api-key-name';
                nameInput.value = item.api_key_name || '';
                tdName.appendChild(nameInput);
                tr.appendChild(tdName);

                // 3) Наименование кабинета
                const tdCabinetName = document.createElement('td');
                const cabNameInput = document.createElement('input');
                cabNameInput.type = 'text';
                cabNameInput.className = 'cabinet-input cabinet-edit-cabinet-name';
                cabNameInput.value = item.cabinet_name || '';
                tdCabinetName.appendChild(cabNameInput);
                tr.appendChild(tdCabinetName);

                // 4) Дата создания кабинета
                const tdCreated = document.createElement('td');
                const dateInput = document.createElement('input');
                dateInput.type = 'date';
                dateInput.className = 'cabinet-input cabinet-edit-cabinet-date';
                if (item.cabinet_created_date) {
                    dateInput.value = item.cabinet_created_date;
                }
                tdCreated.appendChild(dateInput);
                tr.appendChild(tdCreated);

                // 5) Кнопки "Сохранить" / "Отмена"
                const tdActions = document.createElement('td');

                const saveBtn = document.createElement('button');
                saveBtn.type = 'button';
                saveBtn.className = 'btn cabinet-edit-save-btn';
                saveBtn.textContent = 'Сохранить';

                const cancelBtn = document.createElement('button');
                cancelBtn.type = 'button';
                cancelBtn.className = 'btn cabinet-edit-cancel-btn';
                cancelBtn.textContent = 'Отмена';

                tdActions.appendChild(saveBtn);
                tdActions.appendChild(cancelBtn);
                tr.appendChild(tdActions);
            }

            cabinetsTableBody.appendChild(tr);

            // Строка для сообщения под записью
            const msgTr = document.createElement('tr');
            msgTr.className = 'cabinet-message-row';
            msgTr.dataset.cabinetId = String(item.id);

            const msgTd = document.createElement('td');
            msgTd.colSpan = 5;
            msgTd.className = 'cabinet-row-message';
            msgTr.appendChild(msgTd);

            cabinetsTableBody.appendChild(msgTr);
        });

        cabinetsTableWrapper.style.display = filtered.length > 0 ? 'block' : 'none';
    }


    function updateCabinetInData(item) {
        const idx = CABINETS_DATA.findIndex(
            (it) => String(it.id) === String(item.id)
        );
        if (idx !== -1) {
            CABINETS_DATA[idx] = item;
        }
    }

    function removeCabinetFromData(cabinetId) {
        CABINETS_DATA = CABINETS_DATA.filter(
            (item) => String(item.id) !== String(cabinetId)
        );
        if (rowMessageTimeouts[cabinetId]) {
            clearTimeout(rowMessageTimeouts[cabinetId]);
            delete rowMessageTimeouts[cabinetId];
        }

        fillCabinetSelect();

        const selectedId = cabinetSelect ? cabinetSelect.value : '';
        const idToShow = selectedId || null;
        renderCabinetsTable(idToShow);
    }

    function fetchCabinets() {
        clearCabinetsMessages();

        fetch('/main/cabinets/list/')
            .then((resp) => resp.json())
            .then((data) => {
                if (!data.ok) {
                    setCabinetsError(data.error || 'Ошибка загрузки кабинетов.');
                    return;
                }
                CABINETS_DATA = data.items || [];
                fillCabinetSelect();
            })
            .catch((err) => {
                console.error('Ошибка сети при загрузке кабинетов:', err);
                setCabinetsError('Ошибка сети при загрузке кабинетов.');
            });
    }

    function handleEditCabinet(cabinetId) {
        editingCabinetId = cabinetId;
        const selectedId = cabinetSelect ? cabinetSelect.value : '';
        const idToShow = selectedId || null;
        renderCabinetsTable(idToShow);
    }

    function openInlineEditorForInput(inputEl) {
        if (!inlineEditor || !inlineEditorTextarea) return;

        inlineEditorTarget = inputEl;
        inlineEditorTextarea.value = inputEl.value || '';

        const rect = inputEl.getBoundingClientRect();
        const docLeft = window.scrollX || document.documentElement.scrollLeft;
        const docTop = window.scrollY || document.documentElement.scrollTop;

        // позиционируем справа от инпута, чуть с отступом
        inlineEditor.style.left = (rect.right + 8 + docLeft) + 'px';
        inlineEditor.style.top = (rect.top + docTop) + 'px';

        inlineEditor.classList.remove('hidden');
        inlineEditorTextarea.focus();
        inlineEditorTextarea.select();
    }

    function closeInlineEditor() {
        if (!inlineEditor) return;
        inlineEditor.classList.add('hidden');
        inlineEditorTarget = null;
    }

    if (inlineEditorSaveBtn && inlineEditorCancelBtn && inlineEditorTextarea) {
        inlineEditorSaveBtn.addEventListener('click', function () {
            if (inlineEditorTarget) {
                inlineEditorTarget.value = inlineEditorTextarea.value;
                inlineEditorTarget.dispatchEvent(new Event('input', { bubbles: true }));
            }
            closeInlineEditor();
        });

        inlineEditorCancelBtn.addEventListener('click', function () {
            closeInlineEditor();
        });

        // закрытие по клику вне редактора
        document.addEventListener('click', function (e) {
            if (!inlineEditor) return;
            if (inlineEditor.classList.contains('hidden')) return;

            if (inlineEditor.contains(e.target)) {
                return;
            }
            if (inlineEditorTarget && e.target === inlineEditorTarget) {
                return;
            }
            closeInlineEditor();
        });
    }

    function handleSaveCabinetEdits(cabinetId, row) {
        clearCabinetsMessages();
        clearRowMessage(cabinetId);

        const apiKeyInput = row.querySelector('.cabinet-edit-api-key');
        const nameInput = row.querySelector('.cabinet-edit-api-key-name');
        const cabNameInput = row.querySelector('.cabinet-edit-cabinet-name');
        const dateInput = row.querySelector('.cabinet-edit-cabinet-date');

        const formData = new FormData();
        formData.append('id', cabinetId);

        if (apiKeyInput && apiKeyInput.value.trim()) {
            formData.append('api_key', apiKeyInput.value.trim());
        }
        if (nameInput) {
            formData.append('api_key_name', nameInput.value.trim());
        }
        if (cabNameInput) {
            formData.append('cabinet_name', cabNameInput.value.trim());
        }
        if (dateInput && dateInput.value) {
            formData.append('cabinet_created_date', dateInput.value);
        }

        fetch('/main/cabinets/update/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        })
            .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                if (!data.ok) {
                    const msg =
                        data.error ||
                        (data.errors && data.errors.join(' ')) ||
                        'Не удалось сохранить изменения.';
                    setRowMessage(cabinetId, msg, 'error');
                    return;
                }

                if (data.item) {
                    updateCabinetInData(data.item);
                }

                editingCabinetId = null;
                const selectedId = cabinetSelect ? cabinetSelect.value : '';
                const idToShow = selectedId || null;
                renderCabinetsTable(idToShow);

                setRowMessage(
                    cabinetId,
                    data.message || 'Изменения сохранены.',
                    'success'
                );
            })
            .catch(() => {
                setRowMessage(
                    cabinetId,
                    'Ошибка сети. Попробуйте ещё раз.',
                    'error'
                );
            });
    }

    function handleCancelCabinetEdits() {
        editingCabinetId = null;
        const selectedId = cabinetSelect ? cabinetSelect.value : '';
        const idToShow = selectedId || null;
        renderCabinetsTable(idToShow);
    }

    // ===== Модалка добавления кабинета =====
    function openCabinetModal() {
        if (!cabinetModal) return;
        cabinetApiKeyInput.value = '';
        cabinetApiKeyNameInput.value = '';
        cabinetModalError.textContent = '';
        cabinetModal.classList.remove('hidden');
        cabinetApiKeyInput.focus();
    }

    function closeCabinetModal() {
        if (!cabinetModal) return;
        cabinetModal.classList.add('hidden');
    }

    if (cabinetAddBtn && cabinetModalSaveBtn && cabinetModalCancelBtn) {
        cabinetAddBtn.addEventListener('click', openCabinetModal);

        cabinetModalCancelBtn.addEventListener('click', function () {
            closeCabinetModal();
        });

        if (cabinetModal) {
            cabinetModal.addEventListener('click', function (e) {
                if (
                    e.target === cabinetModal ||
                    e.target === cabinetModal.querySelector('.cabinet-modal-backdrop')
                ) {
                    closeCabinetModal();
                }
            });
        }

        cabinetModalSaveBtn.addEventListener('click', function () {
            cabinetModalError.textContent = '';

            const apiKey = cabinetApiKeyInput.value.trim();
            const apiKeyName = cabinetApiKeyNameInput.value.trim();

            if (!apiKey || !apiKeyName) {
                cabinetModalError.textContent = 'Заполните API ключ и его наименование.';
                return;
            }

            const formData = new FormData();
            formData.append('api_key', apiKey);
            formData.append('api_key_name', apiKeyName);

            fetch('/main/cabinets/add/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                },
                body: formData,
            })
                .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
                .then(({ status, data }) => {
                    if (!data.ok) {
                        cabinetModalError.textContent = data.error || 'Произошла ошибка при сохранении.';
                        return;
                    }

                    if (data.item) {
                        CABINETS_DATA.push(data.item);
                        fillCabinetSelect();
                    }

                    closeCabinetModal();
                })
                .catch(() => {
                    cabinetModalError.textContent = 'Ошибка сети. Попробуйте ещё раз.';
                });
        });
    }

    // ===== Модалка синхронизации =====
    function openSyncModal(cabinetId, message) {
        pendingSyncCabinetId = cabinetId;
        if (cabinetSyncMessage && message) {
            cabinetSyncMessage.textContent = message;
        }
        if (cabinetSyncModal) {
            cabinetSyncModal.classList.remove('hidden');
        }
    }

    function closeSyncModal() {
        pendingSyncCabinetId = null;
        if (cabinetSyncModal) {
            cabinetSyncModal.classList.add('hidden');
        }
    }

    if (cabinetSyncConfirmBtn && cabinetSyncCancelBtn) {
        cabinetSyncConfirmBtn.addEventListener('click', function () {
            if (!pendingSyncCabinetId) {
                closeSyncModal();
                return;
            }
            const id = pendingSyncCabinetId;
            closeSyncModal();
            handleSyncCabinet(id);
        });

        cabinetSyncCancelBtn.addEventListener('click', function () {
            // просто сообщение внизу строки
            if (pendingSyncCabinetId) {
                setRowMessage(
                    pendingSyncCabinetId,
                    'API активен. Изменения не были синхронизированы.',
                    'success'
                );
            }
            closeSyncModal();
        });

        if (cabinetSyncModal) {
            cabinetSyncModal.addEventListener('click', function (e) {
                if (
                    e.target === cabinetSyncModal ||
                    e.target === cabinetSyncModal.querySelector('.cabinet-modal-backdrop')
                ) {
                    closeSyncModal();
                }
            });
        }
    }

    // ===== Модалка удаления =====
    function openDeleteModal(cabinetId, message) {
        pendingDeleteCabinetId = cabinetId;
        if (cabinetDeleteMessage && message) {
            cabinetDeleteMessage.textContent = message;
        }
        if (cabinetDeleteModal) {
            cabinetDeleteModal.classList.remove('hidden');
        }
    }

    function closeDeleteModal() {
        pendingDeleteCabinetId = null;
        if (cabinetDeleteModal) {
            cabinetDeleteModal.classList.add('hidden');
        }
    }

    if (cabinetDeleteConfirmBtn && cabinetDeleteCancelBtn) {
        cabinetDeleteConfirmBtn.addEventListener('click', function () {
            if (!pendingDeleteCabinetId) {
                closeDeleteModal();
                return;
            }
            const id = pendingDeleteCabinetId;
            closeDeleteModal();
            performDeleteCabinet(id);
        });

        cabinetDeleteCancelBtn.addEventListener('click', function () {
            closeDeleteModal();
        });

        if (cabinetDeleteModal) {
            cabinetDeleteModal.addEventListener('click', function (e) {
                if (
                    e.target === cabinetDeleteModal ||
                    e.target === cabinetDeleteModal.querySelector('.cabinet-modal-backdrop')
                ) {
                    closeDeleteModal();
                }
            });
        }
    }

    // ===== Удаление / Проверка / Синхронизация =====
    function performDeleteCabinet(cabinetId) {
        clearCabinetsMessages();

        const formData = new FormData();
        formData.append('id', cabinetId);

        fetch('/main/cabinets/delete/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        })
            .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                if (!data.ok) {
                    // ошибка удаления глобально, так как строки уже может не быть
                    setCabinetsError(data.error || 'Не удалось удалить API ключ.');
                    return;
                }
                removeCabinetFromData(cabinetId);
            })
            .catch(() => {
                setCabinetsError('Ошибка сети. Попробуйте ещё раз.');
            });
    }

    function handleDeleteCabinet(cabinetId) {
        const msg = 'Вы действительно хотите удалить API ключ?';
        openDeleteModal(cabinetId, msg);
    }

    function handleSyncCabinet(cabinetId) {
        clearCabinetsMessages();

        const formData = new FormData();
        formData.append('id', cabinetId);
        formData.append('sync', '1');

        fetch('/main/cabinets/check/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        })
            .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                if (!data.ok) {
                    setRowMessage(
                        cabinetId,
                        data.error || 'Не удалось синхронизировать данные кабинета.',
                        'error'
                    );
                    return;
                }

                if (data.item) {
                    updateCabinetInData(data.item);
                    const selectedId = cabinetSelect ? cabinetSelect.value : '';
                    const idToShow = selectedId || null;
                    renderCabinetsTable(idToShow);
                }

                setRowMessage(
                    cabinetId,
                    data.message || 'Данные кабинета синхронизированы.',
                    'success'
                );
            })
            .catch(() => {
                setRowMessage(
                    cabinetId,
                    'Ошибка сети. Попробуйте ещё раз.',
                    'error'
                );
            });
    }

    function handleCheckCabinet(cabinetId) {
        clearCabinetsMessages();

        const formData = new FormData();
        formData.append('id', cabinetId);
        formData.append('sync', '0');  // сначала только проверяем

        fetch('/main/cabinets/check/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            body: formData,
        })
            .then((resp) => resp.json().then((data) => ({ status: resp.status, data })))
            .then(({ status, data }) => {
                if (!data.ok) {
                    setRowMessage(
                        cabinetId,
                        data.error || 'Не удалось проверить API ключ.',
                        'error'
                    );
                    return;
                }

                if (data.item) {
                    updateCabinetInData(data.item);
                    const selectedId = cabinetSelect ? cabinetSelect.value : '';
                    const idToShow = selectedId || null;
                    renderCabinetsTable(idToShow);
                }

                if (!data.has_changes) {
                    setRowMessage(
                        cabinetId,
                        data.message || 'API активен. Данные актуальны.',
                        'success'
                    );
                    return;
                }

                // есть изменения -> показываем модальное подтверждение
                const confirmText =
                    'При проверке обнаружено изменение наименования кабинета или даты создания кабинета. ' +
                    'Хотите синхронизировать данные?';

                setRowMessage(
                    cabinetId,
                    data.message || 'API активен, но данные кабинета отличаются от сохранённых.',
                    'success'
                );
                openSyncModal(cabinetId, confirmText);
            })
            .catch(() => {
                setRowMessage(
                    cabinetId,
                    'Ошибка сети. Попробуйте ещё раз.',
                    'error'
                );
            });
    }

    // ===== Показ таблицы =====
    if (cabinetShowBtn) {
        cabinetShowBtn.addEventListener('click', function () {
            const selectedId = cabinetSelect ? cabinetSelect.value : '';
            const idToShow = selectedId || null;
            renderCabinetsTable(idToShow);
        });
    }

    // ===== Обработка кликов по трём точкам =====
    // if (cabinetsTableBody) {
    //     cabinetsTableBody.addEventListener('dblclick', function (e) {
    //         const input = e.target.closest(
    //             '.cabinet-edit-api-key, ' +
    //             '.cabinet-edit-api-key-name, ' +
    //             '.cabinet-edit-cabinet-name'
    //         );
    //         if (!input) return;
    //         openInlineEditorForInput(input);
    //     });
    // }

    if (cabinetsTableBody) {
        cabinetsTableBody.addEventListener('click', function (e) {
            // Сначала проверяем кнопки сохранения / отмены в режиме редактирования
            const saveEditBtn = e.target.closest('.cabinet-edit-save-btn');
            const cancelEditBtn = e.target.closest('.cabinet-edit-cancel-btn');

            if (saveEditBtn) {
                const row = saveEditBtn.closest('tr');
                const cabinetId = row ? row.dataset.cabinetId : null;
                if (cabinetId) {
                    handleSaveCabinetEdits(cabinetId, row);
                }
                return;
            }

            if (cancelEditBtn) {
                handleCancelCabinetEdits();
                return;
            }
            // 2) Клик по полю в режиме редактирования -> мини-редактор
            const input = e.target.closest(
                '.cabinet-edit-api-key, ' +
                '.cabinet-edit-api-key-name, ' +
                '.cabinet-edit-cabinet-name'
            );
            if (input) {
                openInlineEditorForInput(input);
                return;
            }
            // Дальше — логика трёх точек
            const menuBtn = e.target.closest('.cabinet-menu-btn');
            const actionBtn = e.target.closest('.cabinet-menu-dropdown button');

            if (menuBtn) {
                const wrapper = menuBtn.closest('.cabinet-row-menu');
                const isOpen = wrapper.classList.contains('open');
                document.querySelectorAll('.cabinet-row-menu.open').forEach((w) => {
                    w.classList.remove('open');
                });
                if (!isOpen) {
                    wrapper.classList.add('open');
                }
                return;
            }

            if (actionBtn) {
                const action = actionBtn.dataset.action;
                const wrapper = actionBtn.closest('.cabinet-row-menu');
                const cabinetId = wrapper.dataset.cabinetId;
                wrapper.classList.remove('open');

                if (action === 'delete') {
                    handleDeleteCabinet(cabinetId);
                } else if (action === 'edit') {
                    handleEditCabinet(cabinetId);
                } else if (action === 'check') {
                    handleCheckCabinet(cabinetId);
                }
                return;
            }
        });

        document.addEventListener('click', function (e) {
            if (!e.target.closest('.cabinet-row-menu')) {
                document.querySelectorAll('.cabinet-row-menu.open').forEach((w) => {
                    w.classList.remove('open');
                });
            }
        });
    }

    // начальная загрузка кабинетов
    fetchCabinets();
});
