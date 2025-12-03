document.addEventListener('DOMContentLoaded', function () {
    // ===== Выпадающее меню пользователя =====
    const userMenu = document.getElementById('user-menu');
    const toggle = document.getElementById('user-menu-toggle');

    if (userMenu && toggle) {
        toggle.addEventListener('click', function () {
            userMenu.classList.toggle('open');
        });

        document.addEventListener('click', function (e) {
            if (!userMenu.contains(e.target)) {
                userMenu.classList.remove('open');
            }
        });
    }

    // ===== Переключение разделов (Аналитика / Кабинеты) =====
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    const sections = {
        analytics: document.getElementById('section-analytics'),
        cabinets: document.getElementById('section-cabinets'),
    };

    function setActiveSection(name) {
        sidebarItems.forEach((btn) => {
            const sectionName = btn.getAttribute('data-section');
            btn.classList.toggle('active', sectionName === name);
        });

        Object.entries(sections).forEach(([key, el]) => {
            if (!el) return;
            el.classList.toggle('active', key === name);
        });
    }

    sidebarItems.forEach((btn) => {
        btn.addEventListener('click', function () {
            const sectionName = btn.getAttribute('data-section');
            if (!sectionName) return;
            setActiveSection(sectionName);
        });
    });

    // По умолчанию показываем Аналитику
    setActiveSection('analytics');
});

