// Theme management
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 'system';
        this.init();
    }

    init() {
        this.applyTheme();
        this.setupThemeToggle();
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (this.theme === 'system') {
                this.applyTheme();
            }
        });
    }

    applyTheme() {
        const isDark = this.theme === 'dark' || 
            (this.theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
        
        document.documentElement.classList.toggle('dark', isDark);
    }

    toggleTheme() {
        const themes = ['light', 'dark', 'system'];
        const currentIndex = themes.indexOf(this.theme);
        const nextIndex = (currentIndex + 1) % themes.length;
        
        this.theme = themes[nextIndex];
        localStorage.setItem('theme', this.theme);
        this.applyTheme();
        
        console.log(`Theme changed to: ${this.theme}`);
    }

    setupThemeToggle() {
        const toggleButton = document.querySelector('.theme-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', () => this.toggleTheme());
        }
    }
}

// Chat Interface
class ChatInterface {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.messagesContainer = null;
        this.currentModel = 'qwen2.5:3b'; // Default model
        this.isLoading = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupAutoResize();
        this.setupMessagesContainer();
        this.loadAvailableModels();
    }

    setupMessagesContainer() {
        // Find the messages area and clear the welcome message
        const chatArea = document.querySelector('.flex-1.overflow-y-auto');
        if (chatArea) {
            // Create messages container
            this.messagesContainer = document.createElement('div');
            this.messagesContainer.className = 'max-w-4xl mx-auto space-y-4 p-4';
            this.messagesContainer.id = 'messages-container';
            
            // Clear existing content and add our container
            chatArea.innerHTML = '';
            chatArea.appendChild(this.messagesContainer);
        }
    }

    async loadAvailableModels() {
        try {
            const response = await fetch('/api/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Available models:', data.models);
                // Could add model selector UI here
            }
        } catch (error) {
            console.error('Failed to load models:', error);
        }
    }

    setupEventListeners() {
        // Send button click
        this.sendButton?.addEventListener('click', () => this.handleSend());

        // Enter key handling
        this.messageInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });

        // Input changes
        this.messageInput?.addEventListener('input', () => {
            this.updateSendButtonState();
        });
    }

    setupAutoResize() {
        if (!this.messageInput) return;

        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });
    }

    async handleSend() {
        const message = this.messageInput?.value.trim();
        if (!message || this.isLoading) return;

        console.log('Sending message:', message);
        
        // Display user message
        this.displayMessage('user', message);
        
        // Clear input
        if (this.messageInput) {
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
            this.updateSendButtonState();
        }

        // Set loading state
        this.isLoading = true;
        this.updateSendButtonState();
        
        // Show typing indicator
        const typingId = this.showTypingIndicator();

        try {
            // Send to Ollama via our API
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    model: this.currentModel
                })
            });

            const data = await response.json();
            
            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            if (response.ok) {
                // Display AI response
                this.displayMessage('assistant', data.response, data.model);
            } else {
                // Display error
                this.displayMessage('error', data.error || 'An error occurred');
            }

        } catch (error) {
            console.error('Chat error:', error);
            this.removeTypingIndicator(typingId);
            this.displayMessage('error', 'Failed to connect to the AI model. Please check your connection.');
        } finally {
            this.isLoading = false;
            this.updateSendButtonState();
        }
    }

    displayMessage(type, content, model = null) {
        if (!this.messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message animate-fade-in';
        
        let messageHtml = '';
        
        if (type === 'user') {
            messageHtml = `
                <div class="flex justify-end mb-4">
                    <div class="message-user max-w-2xl px-4 py-2 bg-blue-500 text-white rounded-2xl rounded-br-md">
                        <p class="text-sm">${this.escapeHtml(content)}</p>
                    </div>
                </div>
            `;
        } else if (type === 'assistant') {
            messageHtml = `
                <div class="flex justify-start mb-4">
                    <div class="flex space-x-3 max-w-2xl">
                        <img src="robobrain.svg" alt="AI" class="w-8 h-8 rounded-full flex-shrink-0 mt-1">
                        <div class="message-assistant bg-gray-100 dark:bg-gray-800 px-4 py-2 rounded-2xl rounded-bl-md">
                            <p class="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">${this.escapeHtml(content)}</p>
                            ${model ? `<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Model: ${model}</p>` : ''}
                        </div>
                    </div>
                </div>
            `;
        } else if (type === 'error') {
            messageHtml = `
                <div class="flex justify-center mb-4">
                    <div class="bg-red-100 dark:bg-red-900 border border-red-200 dark:border-red-800 px-4 py-2 rounded-lg">
                        <p class="text-sm text-red-700 dark:text-red-300">⚠️ ${this.escapeHtml(content)}</p>
                    </div>
                </div>
            `;
        }
        
        messageDiv.innerHTML = messageHtml;
        this.messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        this.scrollToBottom();
    }

    showTypingIndicator() {
        const typingId = 'typing-' + Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.id = typingId;
        typingDiv.className = 'message animate-fade-in';
        typingDiv.innerHTML = `
            <div class="flex justify-start mb-4">
                <div class="flex space-x-3 max-w-2xl">
                    <img src="robobrain.svg" alt="AI" class="w-8 h-8 rounded-full flex-shrink-0 mt-1">
                    <div class="bg-gray-100 dark:bg-gray-800 px-4 py-2 rounded-2xl rounded-bl-md">
                        <div class="typing-indicator flex space-x-1">
                            <div class="typing-dot animate-pulse"></div>
                            <div class="typing-dot animate-pulse" style="animation-delay: 0.2s"></div>
                            <div class="typing-dot animate-pulse" style="animation-delay: 0.4s"></div>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400">AI is thinking...</p>
                    </div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
        return typingId;
    }

    removeTypingIndicator(typingId) {
        const typingElement = document.getElementById(typingId);
        if (typingElement) {
            typingElement.remove();
        }
    }

    scrollToBottom() {
        const chatArea = this.messagesContainer?.parentElement;
        if (chatArea) {
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    updateSendButtonState() {
        const hasText = this.messageInput?.value.trim().length > 0;
        const canSend = hasText && !this.isLoading;
        
        if (this.sendButton) {
            this.sendButton.disabled = !canSend;
            this.sendButton.style.opacity = canSend ? '1' : '0.5';
            
            // Update button icon based on loading state
            const icon = this.sendButton.querySelector('svg');
            if (icon) {
                if (this.isLoading) {
                    icon.style.animation = 'spin 1s linear infinite';
                } else {
                    icon.style.animation = '';
                }
            }
        }
    }
}

// Navigation
class Navigation {
    constructor() {
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupMobileToggle();
    }

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                // Remove active class from all items
                navItems.forEach(nav => {
                    nav.classList.remove('bg-blue-50', 'dark:bg-blue-900/50', 'text-blue-600', 'dark:text-blue-400');
                    nav.classList.add('text-gray-700', 'dark:text-gray-300');
                });

                // Add active class to clicked item
                item.classList.add('bg-blue-50', 'dark:bg-blue-900/50', 'text-blue-600', 'dark:text-blue-400');
                item.classList.remove('text-gray-700', 'dark:text-gray-300');

                console.log('Navigation item clicked:', item.textContent.trim());
            });
        });
    }

    setupMobileToggle() {
        // TODO: Implement mobile sidebar toggle
        // This will be needed for responsive design
    }
}

// App initialization
class App {
    constructor() {
        this.themeManager = new ThemeManager();
        this.chatInterface = new ChatInterface();
        this.navigation = new Navigation();
        this.init();
    }

    init() {
        this.showSplashScreen();
        this.setupApp();
    }

    showSplashScreen() {
        const splash = document.getElementById('splash');
        const app = document.getElementById('app');

        // Hide splash and show app after loading
        setTimeout(() => {
            if (splash) splash.style.display = 'none';
            if (app) {
                app.classList.remove('hidden');
                app.classList.add('loaded');
            }
        }, 2000);
    }

    setupApp() {
        // Initialize any additional app functionality
        console.log('App initialized successfully');
        
        // Setup error handling
        window.addEventListener('error', (e) => {
            console.error('App error:', e.error);
        });

        // Setup performance monitoring
        if (window.performance) {
            window.addEventListener('load', () => {
                const loadTime = performance.now();
                console.log(`App loaded in ${Math.round(loadTime)}ms`);
            });
        }
    }
}

// Integration Functions (Placeholders for future implementation)
class IntegrationManager {
    constructor() {
        this.apiEndpoint = 'http://localhost:9090/api';
        this.wsEndpoint = 'ws://localhost:9090/ws';
        this.socket = null;
    }

    // Placeholder for API calls
    async makeRequest(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.apiEndpoint}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Placeholder for WebSocket connection
    connectWebSocket() {
        try {
            this.socket = new WebSocket(this.wsEndpoint);
            
            this.socket.onopen = () => {
                console.log('WebSocket connected');
            };

            this.socket.onmessage = (event) => {
                console.log('WebSocket message:', event.data);
            };

            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('WebSocket connection failed:', error);
        }
    }

    // Placeholder for agent interactions
    async sendToAgent(message, agentType = 'default') {
        return this.makeRequest('/agent/chat', {
            method: 'POST',
            body: JSON.stringify({
                message,
                agentType,
                timestamp: new Date().toISOString()
            })
        });
    }

    // Placeholder for file operations
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        return this.makeRequest('/files/upload', {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type for FormData
        });
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    window.integrationManager = new IntegrationManager();
    
    // Make integration manager available globally for future use
    console.log('Agentic UI loaded and ready');
});