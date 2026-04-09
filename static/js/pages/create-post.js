/**
 * Страница создания поста
 */

const CreatePost = {
    // Состояние
    selectedChannels: [],
    userBots: [],
    selectedButtonColor: 'success',
    isSubmitting: false,
    
    // DOM элементы
    elements: {},
    
    init() {
        this.cacheElements();
        this.bindEvents();
        this.loadUserBots();
        this.initColorOptions();
        this.initUploadArea();
        this.setDefaultDateTime();
        this.showUrlMessages();
        
        console.log('✅ Create post page initialized');
    },
    
    cacheElements() {
        this.elements = {
            channelsGrid: document.getElementById('channelsGrid'),
            selectedCount: document.getElementById('selectedCount'),
            channelsData: document.getElementById('channelsData'),
            postText: document.getElementById('postText'),
            buttonText: document.getElementById('buttonText'),
            buttonUrl: document.getElementById('buttonUrl'),
            buttonRequiredWarning: document.getElementById('buttonRequiredWarning'),
            buttonBadge: document.getElementById('buttonBadge'),
            mediaFile: document.getElementById('mediaFile'),
            mediaPreview: document.getElementById('mediaPreview'),
            mediaFileName: document.getElementById('mediaFileName'),
            previewCard: document.getElementById('previewCard'),
            previewText: document.getElementById('previewText'),
            previewChannelNames: document.getElementById('previewChannelNames'),
            previewButton: document.getElementById('previewButton'),
            submitBtn: document.getElementById('submitBtn'),
            postForm: document.getElementById('postForm'),
            scheduleModal: document.getElementById('scheduleModal'),
            regularModal: document.getElementById('regularModal'),
            scheduleDate: document.getElementById('scheduleDate'),
            scheduleTime: document.getElementById('scheduleTime'),
            regularStartDate: document.getElementById('regularStartDate'),
            regularStartTime: document.getElementById('regularStartTime'),
            regularInterval: document.getElementById('regularInterval'),
            regularEndDate: document.getElementById('regularEndDate'),
            regularEndTime: document.getElementById('regularEndTime')
        };
    },
    
    bindEvents() {
        // Выбор каналов
        document.querySelectorAll('.channel-card').forEach(card => {
            card.addEventListener('click', () => this.toggleChannel(card));
        });
        
        // Текст поста
        this.elements.postText.addEventListener('input', () => this.updatePreview());
        
        // Кнопка
        this.elements.buttonText.addEventListener('input', () => {
            this.updatePreview();
            this.validateButton();
        });
        this.elements.buttonUrl.addEventListener('input', () => {
            this.updatePreview();
            this.validateButton();
        });
        
        // Медиа
        this.elements.mediaFile.addEventListener('change', () => this.handleMediaSelect());
        
        // Форма
        this.elements.postForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Кнопки
        document.getElementById('scheduleBtn')?.addEventListener('click', () => this.openScheduleModal());
        document.getElementById('regularBtn')?.addEventListener('click', () => this.openRegularModal());
        document.getElementById('confirmScheduleBtn')?.addEventListener('click', () => this.sendScheduledPost(false));
        document.getElementById('confirmRegularBtn')?.addEventListener('click', () => this.sendScheduledPost(true));
        
        // Закрытие модалок по ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeScheduleModal();
                this.closeRegularModal();
            }
        });
        
        // Модалки не закрываются при клике на фон
        if (this.elements.scheduleModal) {
            this.elements.scheduleModal.addEventListener('click', (e) => {
                if (e.target === this.elements.scheduleModal) e.stopPropagation();
            });
        }
        if (this.elements.regularModal) {
            this.elements.regularModal.addEventListener('click', (e) => {
                if (e.target === this.elements.regularModal) e.stopPropagation();
            });
        }
    },
    
    async loadUserBots() {
        try {
            const data = await API.getBots();
            if (data.success && data.bots) {
                this.userBots = data.bots;
                
                document.querySelectorAll('.channel-card').forEach(card => {
                    const channelId = card.dataset.id;
                    const platform = card.dataset.platform;
                    
                    let botForChannel = null;
                    if (platform === 'telegram') {
                        botForChannel = this.userBots.find(b => b.platform === 'telegram');
                    } else if (platform === 'max') {
                        botForChannel = this.userBots.find(b => b.platform === 'max');
                    }
                    
                    if (botForChannel) {
                        card.dataset.botToken = botForChannel.token;
                        const botBadge = document.getElementById(`bot-status-${channelId}`);
                        if (botBadge) {
                            botBadge.style.display = 'inline-block';
                            botBadge.title = `Бот: ${botForChannel.name}`;
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Failed to load bots:', error);
        }
    },
    
    toggleChannel(card) {
        const id = card.dataset.id;
        const name = card.dataset.name;
        const channelId = card.dataset.channelId;
        const platform = card.dataset.platform;
        const botToken = card.dataset.botToken;
        
        if (card.classList.contains('selected')) {
            card.classList.remove('selected');
            this.selectedChannels = this.selectedChannels.filter(c => c.id !== id);
        } else {
            if (platform === 'telegram' && !botToken) {
                Utils.showMessage('Сначала добавьте Telegram бота на странице "Мои боты"', 'error');
                return;
            }
            
            card.classList.add('selected');
            this.selectedChannels.push({
                id: id,
                name: name,
                channel_id: channelId,
                platform: platform,
                bot_token: botToken
            });
        }
        
        this.elements.selectedCount.textContent = this.selectedChannels.length;
        this.elements.channelsData.value = JSON.stringify(this.selectedChannels);
        this.updatePreview();
    },
    
    initColorOptions() {
        document.querySelectorAll('.color-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('active'));
                option.classList.add('active');
                this.selectedButtonColor = option.dataset.color;
                this.updatePreview();
                this.validateButton();
            });
        });
        
        // По умолчанию зеленая
        const defaultOption = document.querySelector('.color-option[data-color="success"]');
        if (defaultOption) defaultOption.classList.add('active');
    },
    
    validateButton() {
        const buttonText = this.elements.buttonText.value.trim();
        const buttonUrl = this.elements.buttonUrl.value.trim();
        const isColorSelected = this.selectedButtonColor !== 'gray';
        
        if (isColorSelected && (!buttonText || !buttonUrl)) {
            this.elements.buttonRequiredWarning.style.display = 'block';
            if (this.elements.buttonBadge) this.elements.buttonBadge.innerHTML = '⚠️ required';
            return false;
        } else {
            this.elements.buttonRequiredWarning.style.display = 'none';
            if (this.elements.buttonBadge) this.elements.buttonBadge.innerHTML = 'опционально';
            return true;
        }
    },
    
    updatePreview() {
        const postText = this.elements.postText.value;
        const buttonText = this.elements.buttonText.value;
        const buttonUrl = this.elements.buttonUrl.value;
        
        if (postText || this.selectedChannels.length > 0) {
            this.elements.previewCard.style.display = 'block';
            this.elements.previewText.textContent = postText || 'Введите текст...';
            
            if (this.selectedChannels.length > 0) {
                this.elements.previewChannelNames.textContent = this.selectedChannels.map(c => c.name).join(', ');
            } else {
                this.elements.previewChannelNames.textContent = 'Выберите каналы';
            }
            
            if (buttonText && buttonUrl) {
                let bgColor = '#10b981';
                if (this.selectedButtonColor === 'danger') bgColor = '#ef4444';
                else if (this.selectedButtonColor === 'primary') bgColor = '#6366f1';
                else if (this.selectedButtonColor === 'gray') bgColor = '#6b7280';
                
                this.elements.previewButton.innerHTML = `<div class="preview-button" style="background: ${bgColor};">${this.escapeHtml(buttonText)}</div>`;
            } else {
                this.elements.previewButton.innerHTML = '';
            }
        } else {
            this.elements.previewCard.style.display = 'none';
        }
    },
    
    initUploadArea() {
        const uploadArea = document.getElementById('uploadArea');
        if (uploadArea) {
            uploadArea.addEventListener('click', () => this.elements.mediaFile.click());
        }
    },
    
    handleMediaSelect() {
        if (this.elements.mediaFile.files && this.elements.mediaFile.files[0]) {
            const file = this.elements.mediaFile.files[0];
            const fileSize = file.size / (1024 * 1024);
            const fileExt = file.name.split('.').pop().toLowerCase();
            
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileExt) && fileSize > 10) {
                Utils.showMessage('Фото слишком большое! Максимум 10 МБ', 'error');
                this.elements.mediaFile.value = '';
                return;
            }
            if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(fileExt) && fileSize > 50) {
                Utils.showMessage('Видео слишком большое! Максимум 50 МБ', 'error');
                this.elements.mediaFile.value = '';
                return;
            }
            
            this.elements.mediaFileName.textContent = file.name;
            this.elements.mediaPreview.style.display = 'flex';
        }
    },
    
    removeMedia() {
        this.elements.mediaFile.value = '';
        this.elements.mediaPreview.style.display = 'none';
    },
    
    getDefaultDateTime() {
        const now = new Date();
        now.setMinutes(now.getMinutes() + 5);
        
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        
        return {
            date: `${year}-${month}-${day}`,
            time: `${hours}:${minutes}`
        };
    },
    
    setDefaultDateTime() {
        const defaultTime = this.getDefaultDateTime();
        if (this.elements.scheduleDate) this.elements.scheduleDate.value = defaultTime.date;
        if (this.elements.scheduleTime) this.elements.scheduleTime.value = defaultTime.time;
        if (this.elements.regularStartDate) this.elements.regularStartDate.value = defaultTime.date;
        if (this.elements.regularStartTime) this.elements.regularStartTime.value = defaultTime.time;
    },
    
    openScheduleModal() {
        this.setDefaultDateTime();
        this.hideModalMessage('scheduleModalMessage');
        if (this.elements.scheduleModal) this.elements.scheduleModal.classList.add('active');
    },
    
    closeScheduleModal() {
        if (this.elements.scheduleModal) this.elements.scheduleModal.classList.remove('active');
    },
    
    openRegularModal() {
        this.setDefaultDateTime();
        this.hideModalMessage('regularModalMessage');
        if (this.elements.regularModal) this.elements.regularModal.classList.add('active');
    },
    
    closeRegularModal() {
        if (this.elements.regularModal) this.elements.regularModal.classList.remove('active');
    },
    
    showModalMessage(modalId, message, type) {
        const messageDiv = document.getElementById(modalId);
        if (!messageDiv) return;
        
        messageDiv.innerHTML = (type === 'success' ? '✅ ' : type === 'error' ? '❌ ' : 'ℹ️ ') + message;
        messageDiv.className = `modal-message ${type}`;
        messageDiv.style.display = 'block';
        
        setTimeout(() => {
            if (messageDiv) messageDiv.style.display = 'none';
        }, 5000);
    },
    
    hideModalMessage(modalId) {
        const messageDiv = document.getElementById(modalId);
        if (messageDiv) messageDiv.style.display = 'none';
    },
    
    async sendScheduledPost(isRegularPost = false) {
        if (!this.validateButton()) {
            const modalId = isRegularPost ? 'regularModalMessage' : 'scheduleModalMessage';
            this.showModalMessage(modalId, 'Заполните текст и ссылку кнопки', 'error');
            return;
        }
        
        let scheduleDate, scheduleTime;
        
        if (isRegularPost) {
            scheduleDate = this.elements.regularStartDate.value;
            scheduleTime = this.elements.regularStartTime.value;
        } else {
            scheduleDate = this.elements.scheduleDate.value;
            scheduleTime = this.elements.scheduleTime.value;
        }
        
        if (!scheduleDate || !scheduleTime) {
            const modalId = isRegularPost ? 'regularModalMessage' : 'scheduleModalMessage';
            this.showModalMessage(modalId, 'Выберите дату и время', 'error');
            return;
        }
        
        // Валидация времени
        const selectedDateTime = new Date(`${scheduleDate}T${scheduleTime}`);
        const minDateTime = new Date();
        minDateTime.setMinutes(minDateTime.getMinutes() + 5);
        
        if (selectedDateTime < minDateTime) {
            const modalId = isRegularPost ? 'regularModalMessage' : 'scheduleModalMessage';
            this.showModalMessage(modalId, 'Время должно быть не ранее чем через 5 минут от текущего момента', 'error');
            return;
        }
        
        if (this.selectedChannels.length === 0) {
            const modalId = isRegularPost ? 'regularModalMessage' : 'scheduleModalMessage';
            this.showModalMessage(modalId, 'Выберите хотя бы один канал', 'error');
            return;
        }
        
        const postText = this.elements.postText.value.trim();
        if (!postText) {
            const modalId = isRegularPost ? 'regularModalMessage' : 'scheduleModalMessage';
            this.showModalMessage(modalId, 'Введите текст поста', 'error');
            return;
        }
        
        this.isSubmitting = true;
        const modalId = isRegularPost ? 'regularModalMessage' : 'scheduleModalMessage';
        this.showModalMessage(modalId, 'Планирование поста...', 'info');
        
        const formData = new FormData();
        formData.append('channels_data', JSON.stringify(this.selectedChannels));
        formData.append('post_text', postText);
        formData.append('scheduled_date', scheduleDate);
        formData.append('scheduled_time', scheduleTime);
        
        // Кнопка
        const buttonText = this.elements.buttonText.value.trim();
        const buttonUrl = this.elements.buttonUrl.value.trim();
        
        if (buttonText && buttonUrl) {
            const buttonData = {
                text: buttonText,
                url: buttonUrl.startsWith('http') ? buttonUrl : 'https://' + buttonUrl
            };
            if (this.selectedButtonColor !== 'gray') {
                buttonData.style = this.selectedButtonColor;
            }
            formData.append('button_data', JSON.stringify(buttonData));
        }
        
        if (this.elements.mediaFile.files && this.elements.mediaFile.files[0]) {
            formData.append('media_file', this.elements.mediaFile.files[0]);
        }
        
        if (isRegularPost) {
            const interval = this.elements.regularInterval.value;
            const endDate = this.elements.regularEndDate.value;
            const endTime = this.elements.regularEndTime.value;
            formData.append('is_regular', '1');
            formData.append('regular_interval', interval);
            if (endDate) formData.append('regular_end_date', endDate);
            if (endTime) formData.append('regular_end_time', endTime);
        } else {
            formData.append('is_regular', '0');
        }
        
        try {
            const response = await fetch('/schedule_post', {
                method: 'POST',
                body: formData
            });
            
            if (response.redirected) {
                this.showModalMessage(modalId, 'Пост успешно запланирован!', 'success');
                setTimeout(() => {
                    window.location.href = response.url;
                }, 1500);
            } else {
                const result = await response.json();
                if (result.success) {
                    this.showModalMessage(modalId, 'Пост успешно запланирован!', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1500);
                } else {
                    this.showModalMessage(modalId, result.error || 'Ошибка планирования', 'error');
                    this.isSubmitting = false;
                }
            }
        } catch (error) {
            console.error('Schedule error:', error);
            this.showModalMessage(modalId, 'Ошибка сети: ' + error.message, 'error');
            this.isSubmitting = false;
        }
    },
    
    async handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateButton()) {
            Utils.showMessage('Заполните текст и ссылку кнопки', 'error');
            return;
        }
        
        if (this.isSubmitting) return;
        
        if (this.selectedChannels.length === 0) {
            Utils.showMessage('Выберите хотя бы один канал', 'error');
            return;
        }
        
        const postText = this.elements.postText.value.trim();
        if (!postText) {
            Utils.showMessage('Введите текст поста', 'error');
            return;
        }
        
        const telegramChannels = this.selectedChannels.filter(c => c.platform === 'telegram');
        const channelsWithoutBot = telegramChannels.filter(c => !c.bot_token);
        
        if (channelsWithoutBot.length > 0) {
            Utils.showMessage(`Каналы без бота: ${channelsWithoutBot.map(c => c.name).join(', ')}`, 'error');
            return;
        }
        
        this.isSubmitting = true;
        const originalText = this.elements.submitBtn.innerHTML;
        this.elements.submitBtn.innerHTML = '<span class="spinner"></span> Публикация...';
        this.elements.submitBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('channels_data', JSON.stringify(this.selectedChannels));
        formData.append('post_text', postText);
        
        const buttonText = this.elements.buttonText.value.trim();
        const buttonUrl = this.elements.buttonUrl.value.trim();
        
        if (buttonText && buttonUrl) {
            const buttonData = {
                text: buttonText,
                url: buttonUrl.startsWith('http') ? buttonUrl : 'https://' + buttonUrl
            };
            if (this.selectedButtonColor !== 'gray') {
                buttonData.style = this.selectedButtonColor;
            }
            formData.append('button_data', JSON.stringify(buttonData));
        }
        
        if (this.elements.mediaFile.files && this.elements.mediaFile.files[0]) {
            formData.append('media_file', this.elements.mediaFile.files[0]);
        }
        
        try {
            const response = await fetch('/publish_unified', {
                method: 'POST',
                body: formData
            });
            
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                const result = await response.json();
                if (result.success) {
                    Utils.showMessage('Пост успешно опубликован!', 'success');
                    setTimeout(() => window.location.href = `/publish_unified/${result.session_id}`, 1500);
                } else {
                    Utils.showMessage(result.error || 'Ошибка публикации', 'error');
                    this.elements.submitBtn.innerHTML = originalText;
                    this.elements.submitBtn.disabled = false;
                    this.isSubmitting = false;
                }
            }
        } catch (error) {
            console.error('Publish error:', error);
            Utils.showMessage('Ошибка сети: ' + error.message, 'error');
            this.elements.submitBtn.innerHTML = originalText;
            this.elements.submitBtn.disabled = false;
            this.isSubmitting = false;
        }
    },
    
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    },
    
    showUrlMessages() {
        const params = Utils.getUrlParams();
        if (params.success) Utils.showMessage(params.success, 'success');
        if (params.error) Utils.showMessage(params.error, 'error');
    }
};

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    CreatePost.init();
});

// Глобальные функции для HTML
window.removeMedia = () => CreatePost.removeMedia();
window.closeScheduleModal = () => CreatePost.closeScheduleModal();
window.closeRegularModal = () => CreatePost.closeRegularModal();