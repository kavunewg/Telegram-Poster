/**
 * Страница очереди
 */
const QueuePage = {
    container: null,
    refreshInterval: null,
    
    init() {
        this.container = document.getElementById('queue-list');
        if (!this.container) return;
        
        this.load();
        this.startAutoRefresh();
    },
    
    getStatusLabel(status) {
        const labels = {
            'pending': '🟡 В очереди',
            'processing': '🔵 Отправляется',
            'retry': '🔴 Ошибка (повтор)',
            'success': '🟢 Отправлено',
            'failed': '🔴 Ошибка'
        };
        return labels[status] || status;
    },
    
    getStatusClass(status) {
        const classes = {
            'pending': 'status-pending',
            'processing': 'status-processing',
            'retry': 'status-retry',
            'success': 'status-success',
            'failed': 'status-failed'
        };
        return classes[status] || 'status-default';
    },
    
    async load() {
        try {
            const response = await fetch('/api/queue');
            const tasks = await response.json();
            
            if (!this.container) return;
            
            if (!tasks || tasks.length === 0) {
                this.container.innerHTML = '<div class="empty-queue">📭 Очередь пуста</div>';
                return;
            }
            
            this.container.innerHTML = tasks.map(task => `
                <div class="queue-card ${this.getStatusClass(task.status)}">
                    <div class="queue-header">
                        <span class="queue-status">${this.getStatusLabel(task.status)}</span>
                        <span class="queue-id">#${task.id}</span>
                    </div>
                    <div class="queue-body">
                        <div class="queue-channel">📢 ${this.truncate(task.channel || 'Неизвестно', 30)}</div>
                        <div class="queue-text">${this.truncate(task.text || task.post_text || '', 100)}</div>
                        <div class="queue-meta">
                            <span>🔄 Попыток: ${task.attempts || 0}</span>
                            <span>📅 ${this.formatDate(task.created_at)}</span>
                        </div>
                        ${task.error ? `<div class="queue-error">⚠️ ${this.truncate(task.error, 200)}</div>` : ''}
                    </div>
                    <div class="queue-actions">
                        ${task.status !== 'success' ? `
                            <button class="btn-retry" onclick="QueuePage.retry(${task.id})">🔄 Повторить</button>
                        ` : ''}
                        <button class="btn-delete" onclick="QueuePage.remove(${task.id})">🗑️ Удалить</button>
                    </div>
                </div>
            `).join('');
            
            const countEl = document.getElementById('queue-count');
            if (countEl) countEl.textContent = `Всего: ${tasks.length}`;
            
        } catch (error) {
            console.error('Failed to load queue:', error);
            if (this.container) {
                this.container.innerHTML = '<div class="error-message">❌ Ошибка загрузки очереди</div>';
            }
        }
    },
    
    truncate(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
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
    
    async retry(taskId) {
        if (!confirm('Повторить отправку этого поста?')) return;
        
        try {
            await API.retryTask(taskId);
            this.showMessage('Задача добавлена в очередь', 'success');
            await this.load();
        } catch (error) {
            this.showMessage('Ошибка при повторе', 'error');
        }
    },
    
    async remove(taskId) {
        if (!confirm('Удалить задачу из очереди?')) return;
        
        try {
            await API.deleteTask(taskId);
            this.showMessage('Задача удалена', 'success');
            await this.load();
        } catch (error) {
            this.showMessage('Ошибка при удалении', 'error');
        }
    },
    
    showMessage(message, type) {
        const container = document.getElementById('messageContainer');
        if (!container) return;
        
        const msgDiv = document.createElement('div');
        msgDiv.className = type === 'success' ? 'alert alert-success' : 'alert alert-error';
        msgDiv.innerHTML = (type === 'success' ? '✅ ' : '❌ ') + message;
        container.appendChild(msgDiv);
        
        setTimeout(() => msgDiv.remove(), 5000);
    },
    
    startAutoRefresh() {
        if (this.refreshInterval) clearInterval(this.refreshInterval);
        this.refreshInterval = setInterval(() => this.load(), 5000);
    },
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
};

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('queue-list')) {
        QueuePage.init();
    }
});

window.QueuePage = QueuePage;