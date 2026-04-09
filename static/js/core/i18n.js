// static/js/core/i18n.js
// Модуль интернационализации (i18n) - поддержка русского и английского языков

const I18n = {
    // Текущий язык
    currentLang: 'ru',
    
    // Объект с переводами
    translations: {},
    
    // Инициализация модуля
    async init() {
        // Получаем язык из localStorage или cookie
        this.currentLang = this.getStoredLanguage();
        
        // Загружаем переводы
        await this.loadTranslations();
        
        // Синхронизируем с сервером
        await this.syncWithServer();
        
        // Применяем переводы на странице
        this.applyTranslations();
        
        // Инициализируем кнопку переключения языка
        this.initLangButton();
        
        console.log(`🌐 I18n initialized, current language: ${this.currentLang}`);
    },
    
    // Получение сохранённого языка
    getStoredLanguage() {
        // Проверяем localStorage
        const savedLang = localStorage.getItem('language');
        if (savedLang && (savedLang === 'ru' || savedLang === 'en')) {
            return savedLang;
        }
        
        // Проверяем cookie
        const cookieLang = document.cookie
            .split('; ')
            .find(row => row.startsWith('language='));
        if (cookieLang) {
            const lang = cookieLang.split('=')[1];
            if (lang === 'ru' || lang === 'en') {
                return lang;
            }
        }
        
        // Проверяем HTML атрибут
        const htmlLang = document.documentElement.lang;
        if (htmlLang === 'ru' || htmlLang === 'en') {
            return htmlLang;
        }
        
        // По умолчанию русский
        return 'ru';
    },
    
    // Загрузка переводов с сервера
    async loadTranslations() {
        try {
            const response = await fetch('/api/translations');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            this.translations = await response.json();
            console.log('✅ Translations loaded');
        } catch (error) {
            console.error('Failed to load translations:', error);
            // Заглушка для переводов
            this.translations = {
                ru: {},
                en: {}
            };
        }
    },
    
    // Синхронизация с сервером
    async syncWithServer() {
        try {
            const response = await fetch('/api/language/get');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            
            if (data.success && data.language && (data.language === 'ru' || data.language === 'en')) {
                if (this.currentLang !== data.language) {
                    this.currentLang = data.language;
                    this.saveLanguage();
                }
            }
        } catch (error) {
            console.log('Could not sync language with server:', error);
        }
    },
    
    // Сохранение языка
    saveLanguage() {
        localStorage.setItem('language', this.currentLang);
        document.cookie = `language=${this.currentLang}; path=/; max-age=31536000`;
        document.documentElement.lang = this.currentLang;
    },
    
    // Получение перевода по ключу
    t(key, params = {}) {
        let text = this.translations[this.currentLang]?.[key] || key;
        
        // Замена параметров {name}
        Object.keys(params).forEach(param => {
            text = text.replace(new RegExp(`{${param}}`, 'g'), params[param]);
        });
        
        return text;
    },
    
    // Применение переводов на странице
    applyTranslations() {
        // Переводим элементы с data-i18n
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (!key) return;
            
            // Получаем параметры если есть
            const paramsAttr = el.getAttribute('data-i18n-params');
            let params = {};
            if (paramsAttr) {
                try {
                    params = JSON.parse(paramsAttr);
                } catch(e) {
                    console.error('Failed to parse i18n params:', e);
                }
            }
            
            const translatedText = this.t(key, params);
            
            // Для input/textarea меняем placeholder
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                if (el.placeholder !== undefined) {
                    el.placeholder = translatedText;
                }
            } else {
                el.textContent = translatedText;
            }
        });
        
        // Обновляем кнопку языка
        this.updateLangButtonText();
    },
    
    // Обновление текста кнопки языка
    updateLangButtonText() {
        const langBtn = document.getElementById('langToggleBtn');
        if (langBtn) {
            langBtn.innerHTML = this.currentLang === 'ru' ? '🌐 English' : '🌐 Русский';
        }
    },
    
    // Переключение языка
    async switchLanguage() {
        const newLang = this.currentLang === 'ru' ? 'en' : 'ru';
        
        try {
            // Отправляем запрос на сервер
            const response = await fetch('/api/language/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            if (data.success) {
                this.currentLang = data.language;
                this.saveLanguage();
                this.applyTranslations();
                
                // Отправляем событие о смене языка
                window.dispatchEvent(new CustomEvent('languageChanged', {
                    detail: { language: this.currentLang }
                }));
                
                console.log(`🌐 Language switched to: ${this.currentLang}`);
                this.showNotification(`Language switched to ${this.currentLang === 'ru' ? 'Russian' : 'English'}`, 'success');
            } else {
                throw new Error(data.error || 'Failed to switch language');
            }
        } catch (error) {
            console.error('Failed to switch language:', error);
            
            // Fallback: меняем локально
            this.currentLang = newLang;
            this.saveLanguage();
            this.applyTranslations();
            
            this.showNotification(`Language switched to ${this.currentLang === 'ru' ? 'Russian' : 'English'} (local only)`, 'warning');
        }
    },
    
    // Инициализация кнопки переключения языка
    initLangButton() {
        const langBtn = document.getElementById('langToggleBtn');
        if (!langBtn) {
            console.warn('Language toggle button not found');
            return;
        }
        
        // Удаляем старые обработчики
        const newBtn = langBtn.cloneNode(true);
        langBtn.parentNode?.replaceChild(newBtn, langBtn);
        
        // Добавляем новый обработчик
        newBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.switchLanguage();
        });
        
        this.updateLangButtonText();
    },
    
    // Показ уведомления
    showNotification(message, type = 'info') {
        const container = document.getElementById('alertContainer');
        if (!container) return;
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.innerHTML = (type === 'success' ? '✅ ' : type === 'error' ? '❌ ' : '⚠️ ') + message;
        container.appendChild(alertDiv);
        
        setTimeout(() => alertDiv.remove(), 3000);
    }
};

// Экспортируем для глобального использования
window.I18n = I18n;

// Автоматическая инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    I18n.init();
});