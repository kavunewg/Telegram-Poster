/**
 * Главный файл приложения
 * Загружает все модули и инициализирует приложение
 */

// Ждем загрузки всех скриптов
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Application initialized');
    
    // Инициализация темы (есть на всех страницах)
    if (window.Theme) Theme.init();
    
    // Инициализация переводов (есть на всех страницах)
    if (window.I18n) I18n.init();
    
    // Блокировка закрытия модалок на всех страницах
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                e.stopPropagation();
            }
        });
    });
    
    // Закрытие модалок по ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                modal.classList.remove('active');
            });
        }
    });
});