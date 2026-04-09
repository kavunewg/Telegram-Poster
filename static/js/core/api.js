/**
 * API запросы
 */
const API = {
    baseUrl: '',
    
    async request(endpoint, options = {}) {
        const url = this.baseUrl + endpoint;
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                const error = await response.text();
                throw new Error(`HTTP ${response.status}: ${error}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    },
    
    get(endpoint) {
        return this.request(endpoint);
    },
    
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },
    
    postForm(endpoint, formData) {
        return fetch(endpoint, { method: 'POST', body: formData });
    },
    
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },
    
    // Специфичные методы
    getQueue() {
        return this.get('/api/queue');
    },
    
    retryTask(taskId) {
        return this.post(`/api/queue/retry/${taskId}`, {});
    },
    
    deleteTask(taskId) {
        return this.delete(`/api/queue/${taskId}`);
    },
    
    getBots() {
        return this.get('/api/bots');
    },
    
    getChannels() {
        return this.get('/api/channels');
    },
    
    getStats() {
        return this.get('/api/stats');
    }
};

window.API = API;