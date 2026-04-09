// Тема
const themeBtn = document.getElementById('themeToggleBtn');
if(themeBtn) {
    themeBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark');
        localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
        themeBtn.textContent = document.body.classList.contains('dark') ? '☀️ Светлая' : '🌙 Тёмная';
    });
    if(localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark');
        themeBtn.textContent = '☀️ Светлая';
    } else {
        themeBtn.textContent = '🌙 Тёмная';
    }
}