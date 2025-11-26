document.addEventListener('DOMContentLoaded', function () {
    const userMenu = document.getElementById('user-menu');
    const toggle = document.getElementById('user-menu-toggle');

    if (!userMenu || !toggle) return;

    toggle.addEventListener('click', function () {
        userMenu.classList.toggle('open');
    });

    document.addEventListener('click', function (e) {
        if (!userMenu.contains(e.target)) {
            userMenu.classList.remove('open');
        }
    });
});