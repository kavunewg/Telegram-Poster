/**
 * Утилиты - общие функции для всего приложения
 */

const Utils = {
    // Показ сообщений
    showMessage(message, type, containerId = 'messageContainer') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn('Container not found:', containerId);
            return;
        }
        
        const msgDiv = document.createElement('div');
        msgDiv.className = type === 'success' ? 'success-message' : 'error-message';
        msgDiv.innerHTML = (type === 'success' ? '✅ ' : '❌ ') + message;
        container.appendChild(msgDiv);
        
        setTimeout(() => msgDiv.remove(), 5000);
    },
    
    // Форматирование даты
    formatDate(dateString) {
        if (!dateString) return '—';
        try {
            const date = new Date(dateString);
            return date.toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateString;
        }
    },
    
    // Обрезка текста
    truncate(text, maxLength = 50) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
    // Получение параметров из URL
    getUrlParams() {
        const params = {};
        const urlParams = new URLSearchParams(window.location.search);
        for (const [key, value] of urlParams) {
            params[key] = value;
        }
        return params;
    },
    
    // Дебаунс
    debounce(func, delay = 300) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    },
    
    // Подтверждение действия
    confirm(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },
    
    // Копирование в буфер
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showMessage('Скопировано!', 'success');
            return true;
        } catch {
            this.showMessage('Не удалось скопировать', 'error');
            return false;
        }
    }
};

// Делаем глобальным
window.Utils = Utils;