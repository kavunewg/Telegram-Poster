/**
 * Страница управления каналами
 */

const ChannelsPage = {
    init() {
        this.initModals();
        this.initForms();
        this.initMessages();
    },
    
    initModals() {
        // Блокируем закрытие при клике на фон
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    e.stopPropagation();
                }
            });
        });
        
        // Закрытие по ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAddModal();
                this.closeEditModal();
            }
        });
    },
    
    initForms() {
        const editForm = document.getElementById('editChannelForm');
        if (editForm) {
            editForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(editForm);
                
                try {
                    const response = await fetch('/update_channel', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.redirected) {
                        Utils.showMessage('Канал обновлён', 'success');
                        setTimeout(() => window.location.href = response.url, 1000);
                    }
                } catch (error) {
                    Utils.showMessage('Ошибка обновления', 'error');
                }
            });
        }
    },
    
    initMessages() {
        const params = Utils.getUrlParams();
        if (params.success) Utils.showMessage(params.success, 'success');
        if (params.error) Utils.showMessage(params.error, 'error');
    },
    
    openAddModal(platform) {
        const modal = document.getElementById('addModal');
        if (!modal) return;
        
        document.getElementById('addPlatform').value = platform;
        document.getElementById('channelName').value = '';
        document.getElementById('channelId').value = '';
        document.getElementById('channelUrl').value = '';
        document.getElementById('botSelect').value = '';
        
        modal.classList.add('active');
    },
    
    closeAddModal() {
        const modal = document.getElementById('addModal');
        if (modal) modal.classList.remove('active');
    },
    
    async openEditModal(channelId, platform) {
        try {
            const response = await fetch(`/get_channel/${channelId}`);
            if (!response.ok) throw new Error('Channel not found');
            
            const channel = await response.json();
            
            document.getElementById('editChannelId').value = channel.id;
            document.getElementById('editPlatform').value = platform;
            document.getElementById('editChannelName').value = channel.channel_name || '';
            document.getElementById('editChannelIdValue').value = channel.channel_id || '';
            document.getElementById('editChannelUrl').value = channel.channel_url || '';
            
            const botSelect = document.getElementById('editBotSelect');
            if (botSelect) botSelect.value = channel.bot_id || '';
            
            const modal = document.getElementById('editModal');
            if (modal) modal.classList.add('active');
            
        } catch (error) {
            console.error('Error loading channel:', error);
            Utils.showMessage('Ошибка загрузки данных канала', 'error');
        }
    },
    
    closeEditModal() {
        const modal = document.getElementById('editModal');
        if (modal) modal.classList.remove('active');
    }
};

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('addModal') || document.getElementById('editModal')) {
        ChannelsPage.init();
    }
});

// Глобальные функции для HTML onclick
window.openAddModal = (platform) => ChannelsPage.openAddModal(platform);
window.closeAddModal = () => ChannelsPage.closeAddModal();
window.openEditChannelModal = (id, platform) => ChannelsPage.openEditModal(id, platform);
window.closeEditModal = () => ChannelsPage.closeEditModal();