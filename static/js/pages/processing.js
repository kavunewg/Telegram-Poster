/**
 * Обработка публикации с анимацией
 */

const Processing = {
    overlay: null,
    
    show(steps = []) {
        // Удаляем существующий оверлей
        this.close();
        
        // Создаем оверлей
        this.overlay = document.createElement('div');
        this.overlay.className = 'processing-overlay';
        this.overlay.id = 'processing-overlay';
        
        const defaultSteps = [
            'Подготовка данных',
            'Отправка запроса',
            'Обработка ответа',
            'Завершение'
        ];
        
        const stepsList = steps.length ? steps : defaultSteps;
        
        this.overlay.innerHTML = `
            <div class="processing-card">
                <div class="processing-spinner"></div>
                <div class="processing-text" id="processing-text">Подготовка...</div>
                <div class="processing-progress">
                    <div class="processing-progress-bar" id="processing-progress-bar"></div>
                </div>
                <div class="processing-steps" id="processing-steps">
                    ${stepsList.map((step, index) => `
                        <div class="processing-step" data-step-index="${index}">
                            <span class="step-icon">○</span>
                            <span>${step}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(this.overlay);
        
        return {
            update: (stepIndex, progress, text) => this.update(stepIndex, progress, text),
            close: () => this.close()
        };
    },
    
    update(stepIndex, progress, text) {
        if (!this.overlay) return;
        
        // Обновляем прогресс-бар
        const progressBar = document.getElementById('processing-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        // Обновляем текст
        const textEl = document.getElementById('processing-text');
        if (textEl && text) {
            textEl.textContent = text;
        }
        
        // Обновляем шаги
        const steps = document.querySelectorAll('.processing-step');
        steps.forEach((step, idx) => {
            const icon = step.querySelector('.step-icon');
            if (idx < stepIndex) {
                icon.textContent = '✓';
                step.classList.add('done');
                step.classList.remove('active');
            } else if (idx === stepIndex) {
                icon.textContent = '●';
                step.classList.add('active');
                step.classList.remove('done');
            } else {
                icon.textContent = '○';
                step.classList.remove('active', 'done');
            }
        });
    },
    
    close() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
    },
    
    async publish(formData, steps = null) {
        const processing = this.show(steps || [
            'Подготовка поста',
            'Загрузка медиа',
            'Отправка в Telegram',
            'Завершение'
        ]);
        
        try {
            // Шаг 1
            processing.update(0, 10, 'Подготовка поста...');
            await this.delay(300);
            
            // Шаг 2
            processing.update(1, 40, 'Загрузка медиафайла...');
            await this.delay(500);
            
            // Шаг 3 - отправка
            processing.update(2, 70, 'Отправка в Telegram...');
            
            const response = await fetch('/publish_unified', {
                method: 'POST',
                body: formData
            });
            
            processing.update(3, 100, 'Публикация завершена!');
            await this.delay(500);
            
            processing.close();
            
            if (response.redirected) {
                window.location.href = response.url;
            }
            
            return true;
            
        } catch (error) {
            processing.update(3, 100, 'Ошибка!');
            await this.delay(500);
            processing.close();
            Utils.showMessage('Ошибка публикации: ' + error.message, 'error');
            return false;
        }
    },
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// Автоматическая инициализация форм
document.addEventListener('DOMContentLoaded', () => {
    // Форма публикации
    const publishForm = document.querySelector('form[action="/publish_unified"]');
    if (publishForm) {
        publishForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(publishForm);
            await Processing.publish(formData);
        });
    }
    
    // Кнопка "Далее"
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const href = nextBtn.getAttribute('href');
            
            const processing = Processing.show([
                'Сохранение данных',
                'Переход к следующему шагу',
                'Загрузка интерфейса'
            ]);
            
            processing.update(0, 30, 'Сохранение данных...');
            await Processing.delay(300);
            
            processing.update(1, 60, 'Переход к следующему шагу...');
            await Processing.delay(300);
            
            processing.update(2, 100, 'Загрузка...');
            await Processing.delay(300);
            
            processing.close();
            window.location.href = href;
        });
    }
});

window.Processing = Processing;