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
        
        // Update theme toggle icons
        this.updateThemeIcons(isDark);
        
        // Update favicon for dark mode
        this.updateFavicon(isDark);
    }

    updateThemeIcons(isDark) {
        const lightIcon = document.querySelector('.theme-icon-light');
        const darkIcon = document.querySelector('.theme-icon-dark');
        
        if (lightIcon && darkIcon) {
            if (isDark) {
                // In dark mode, show sun icon (to switch to light)
                lightIcon.classList.remove('hidden');
                lightIcon.classList.add('block');
                darkIcon.classList.remove('block');
                darkIcon.classList.add('hidden');
            } else {
                // In light mode, show moon icon (to switch to dark)
                lightIcon.classList.remove('block');
                lightIcon.classList.add('hidden');
                darkIcon.classList.remove('hidden');
                darkIcon.classList.add('block');
            }
        }
    }

    toggleTheme() {
        // Simple toggle between light and dark (skip system for direct toggle)
        if (this.theme === 'dark') {
            this.setTheme('light');
        } else {
            this.setTheme('dark');
        }
    }

    setTheme(newTheme) {
        this.theme = newTheme;
        localStorage.setItem('theme', this.theme);
        this.applyTheme();
        this.updateThemeSelectors();
        
        console.log(`Theme changed to: ${this.theme}`);
    }

    updateFavicon(isDark) {
        const favicon = document.querySelector('link[rel="icon"]');
        const appleTouchIcon = document.querySelector('link[rel="apple-touch-icon"]');
        
        if (isDark) {
            // In dark mode, use the dark variant
            if (favicon) favicon.href = 'robobrain-dark.svg';
            if (appleTouchIcon) appleTouchIcon.href = 'robobrain-dark.svg';
        } else {
            // In light mode, use the original
            if (favicon) favicon.href = 'robobrain.svg';
            if (appleTouchIcon) appleTouchIcon.href = 'robobrain.svg';
        }
    }

    updateThemeSelectors() {
        // Update theme selector in settings if it exists
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = this.theme;
        }
    }

    setupThemeToggle() {
        const toggleButton = document.querySelector('.theme-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleTheme();
            });
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
        
        // Chat history system - terminal-style command history
        this.chatId = 'default'; // Default chat session
        this.inputHistory = [];
        this.historyIndex = -1; // -1 means current input, 0+ are history entries
        this.currentDraft = ''; // Stores current input when navigating history
        this.maxHistorySize = 50; // Limit history to last 50 commands
        
        this.loadChatHistory();
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

        // Enhanced key handling for Enter and arrow keys
        this.messageInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateHistory('up');
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateHistory('down');
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
        
        // Add message to history before sending
        this.addToHistory(message);
        
        // Display user message
        this.displayMessage('user', message);
        
        // Clear input and reset history navigation
        if (this.messageInput) {
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
            this.updateSendButtonState();
            this.resetHistoryNavigation();
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
                // Display AI response with RAG information
                this.displayMessage('assistant', data.response, data.model, data.rag_enabled, data.sources_used);
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

    displayMessage(type, content, model = null, ragEnabled = false, sourcesUsed = 0) {
        if (!this.messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message animate-fade-in';
        
        let messageHtml = '';
        
        if (type === 'user') {
            messageHtml = `
                <div class="flex justify-end mb-4">
                    <div class="message-user max-w-2xl px-4 py-3">
                        <p class="text-sm font-medium">${this.escapeHtml(content)}</p>
                    </div>
                </div>
            `;
        } else if (type === 'assistant') {
            const ragIndicator = ragEnabled ? 
                `<div class="flex items-center text-xs text-blue-600 dark:text-blue-400 mb-2">
                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
                    </svg>
                    RAG Enhanced${sourcesUsed > 0 ? ` • ${sourcesUsed} sources` : ''}
                </div>` : '';
                
            messageHtml = `
                <div class="flex justify-start mb-4">
                    <div class="flex space-x-3 max-w-2xl">
                        <img src="robobrain.svg" alt="AI" class="w-8 h-8 rounded-full flex-shrink-0 mt-1 opacity-80">
                        <div class="message-assistant px-4 py-3">
                            ${ragIndicator}
                            <p class="text-sm whitespace-pre-wrap leading-relaxed">${this.escapeHtml(content)}</p>
                            ${model ? `<p class="text-xs opacity-70 mt-2">Model: ${model}</p>` : ''}
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

    // Chat History Management System - Terminal-style command history
    loadChatHistory() {
        try {
            const historyKey = `robobrain_chat_history_${this.chatId}`;
            const stored = localStorage.getItem(historyKey);
            if (stored) {
                this.inputHistory = JSON.parse(stored);
            }
        } catch (error) {
            console.warn('Failed to load chat history:', error);
            this.inputHistory = [];
        }
    }

    saveChatHistory() {
        try {
            const historyKey = `robobrain_chat_history_${this.chatId}`;
            localStorage.setItem(historyKey, JSON.stringify(this.inputHistory));
        } catch (error) {
            console.warn('Failed to save chat history:', error);
        }
    }

    addToHistory(message) {
        // Don't add empty messages or duplicates
        if (!message.trim() || this.inputHistory[this.inputHistory.length - 1] === message) {
            return;
        }

        // Add to history
        this.inputHistory.push(message);

        // Limit history size
        if (this.inputHistory.length > this.maxHistorySize) {
            this.inputHistory.shift(); // Remove oldest entry
        }

        // Save to localStorage
        this.saveChatHistory();
    }

    navigateHistory(direction) {
        if (!this.messageInput) return;

        const historyLength = this.inputHistory.length;
        if (historyLength === 0) return;

        // Save current input as draft when starting to navigate
        if (this.historyIndex === -1) {
            this.currentDraft = this.messageInput.value;
        }

        if (direction === 'up') {
            // Go backwards through history (older messages)
            if (this.historyIndex < historyLength - 1) {
                this.historyIndex++;
            }
        } else if (direction === 'down') {
            // Go forwards through history (newer messages)
            if (this.historyIndex > -1) {
                this.historyIndex--;
            }
        }

        // Update input field
        if (this.historyIndex === -1) {
            // Back to current draft
            this.messageInput.value = this.currentDraft;
        } else {
            // Show history entry (newest first, so reverse the index)
            const historyEntry = this.inputHistory[historyLength - 1 - this.historyIndex];
            this.messageInput.value = historyEntry || '';
        }

        // Trigger auto-resize
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        
        // Update send button state
        this.updateSendButtonState();

        // Place cursor at end
        this.messageInput.setSelectionRange(this.messageInput.value.length, this.messageInput.value.length);
    }

    resetHistoryNavigation() {
        this.historyIndex = -1;
        this.currentDraft = '';
    }

    // Method to change chat sessions (for future multi-chat support)
    switchChat(newChatId) {
        this.chatId = newChatId;
        this.loadChatHistory();
        this.resetHistoryNavigation();
    }
}

// Navigation
class Navigation {
    constructor() {
        this.currentPage = 'chat';
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupMobileToggle();
        this.setupNewChatButton();
    }

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const itemText = item.textContent.trim().toLowerCase();
                this.navigateTo(itemText);
                this.setActiveNavItem(item);
            });
        });
    }

    navigateTo(page) {
        // Hide all areas
        document.getElementById('chat-area')?.classList.add('hidden');
        document.getElementById('models-area')?.classList.add('hidden');
        document.getElementById('settings-area')?.classList.add('hidden');

        // Show the selected area
        const pageTitle = document.getElementById('page-title');
        
        switch(page) {
            case 'chat':
                document.getElementById('chat-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Chat';
                this.currentPage = 'chat';
                break;
            case 'models':
                document.getElementById('models-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Models';
                this.currentPage = 'models';
                this.loadModelsPage();
                break;
            case 'settings':
                document.getElementById('settings-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Settings';
                this.currentPage = 'settings';
                this.loadSettingsPage();
                break;
        }
    }

    setActiveNavItem(activeItem) {
        const navItems = document.querySelectorAll('.nav-item');
        
        // Remove active class from all items
        navItems.forEach(nav => {
            nav.classList.remove('bg-blue-50', 'dark:bg-blue-900/50', 'text-blue-600', 'dark:text-blue-400');
            nav.classList.add('text-gray-700', 'dark:text-gray-300', 'hover:bg-gray-100', 'dark:hover:bg-gray-700');
        });

        // Add active class to clicked item
        activeItem.classList.add('bg-blue-50', 'dark:bg-blue-900/50', 'text-blue-600', 'dark:text-blue-400');
        activeItem.classList.remove('text-gray-700', 'dark:text-gray-300', 'hover:bg-gray-100', 'dark:hover:bg-gray-700');
    }

    async loadModelsPage() {
        const modelsGrid = document.getElementById('models-grid');
        const modelSelector = document.getElementById('model-selector');
        
        if (!modelsGrid || !modelSelector) return;

        try {
            // Fetch available models
            const response = await fetch('/api/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.populateModelsGrid(data.models);
                this.populateModelSelector(data.models, modelSelector);
            } else {
                modelsGrid.innerHTML = '<p class="text-red-500 dark:text-red-400">Failed to load models</p>';
            }
        } catch (error) {
            console.error('Error loading models:', error);
            modelsGrid.innerHTML = '<p class="text-red-500 dark:text-red-400">Error connecting to model service</p>';
        }
    }

    populateModelsGrid(models) {
        const modelsGrid = document.getElementById('models-grid');
        if (!modelsGrid) return;

        modelsGrid.innerHTML = '';

        models.forEach(model => {
            const modelCard = document.createElement('div');
            const isRecommended = model === 'qwen2.5:3b';
            modelCard.className = `model-card p-6 ${isRecommended ? 'model-recommended' : ''}`;
            
            const modelSize = this.getModelSize(model);
            
            modelCard.innerHTML = `
                <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                            <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                            </svg>
                        </div>
                        <div>
                            <h4 class="font-medium text-gray-900 dark:text-white">${model}</h4>
                            <p class="text-sm text-gray-500 dark:text-gray-400">${modelSize}</p>
                        </div>
                    </div>
                    ${isRecommended ? '<span class="px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/50 rounded-full">Recommended</span>' : ''}
                </div>
                
                <div class="space-y-2 mb-4">
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        ${this.getModelDescription(model)}
                    </p>
                </div>
                
                <div class="flex space-x-2">
                    <button onclick="window.app.navigation.selectModel('${model}')" class="flex-1 px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/50 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/70 transition-colors">
                        Select Model
                    </button>
                </div>
            `;
            
            modelsGrid.appendChild(modelCard);
        });
    }

    populateModelSelector(models, selector) {
        selector.innerHTML = '';
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model + (model === 'qwen2.5:3b' ? ' (Recommended)' : '');
            if (model === window.app?.chatInterface?.currentModel) {
                option.selected = true;
            }
            selector.appendChild(option);
        });

        // Handle model selection changes
        selector.addEventListener('change', (e) => {
            this.selectModel(e.target.value);
        });
    }

    selectModel(modelName) {
        if (window.app?.chatInterface) {
            window.app.chatInterface.currentModel = modelName;
            console.log(`Selected model: ${modelName}`);
            
            // Update all model selectors
            document.querySelectorAll('#model-selector, #default-model-selector').forEach(selector => {
                selector.value = modelName;
            });
        }
    }

    getModelSize(model) {
        if (model.includes('3b')) return '3B Parameters';
        if (model.includes('7b') || model.includes('8b')) return '~8B Parameters';
        if (model.includes('13b')) return '13B Parameters';
        return 'Unknown Size';
    }

    getModelDescription(model) {
        if (model === 'qwen2.5:3b') {
            return 'Fast and efficient model, perfect for quick responses and general conversation. Recommended for most use cases.';
        }
        if (model.includes('llama3.1-claude')) {
            return 'Advanced model with enhanced reasoning capabilities. Better for complex tasks but slower responses.';
        }
        return 'AI language model with general conversation capabilities.';
    }

    loadSettingsPage() {
        const themeSelector = document.getElementById('theme-selector');
        const defaultModelSelector = document.getElementById('default-model-selector');
        
        if (themeSelector && window.app?.themeManager) {
            themeSelector.value = window.app.themeManager.theme;
            themeSelector.addEventListener('change', (e) => {
                window.app.themeManager.setTheme(e.target.value);
            });
        }

        if (defaultModelSelector) {
            this.populateModelSelector(['qwen2.5:3b', 'incept5/llama3.1-claude:latest'], defaultModelSelector);
        }
    }

    setupNewChatButton() {
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                this.startNewChat();
            });
        }
    }

    startNewChat() {
        // Clear chat messages
        if (window.app?.chatInterface?.messagesContainer) {
            window.app.chatInterface.messagesContainer.innerHTML = '';
        }
        
        // Navigate to chat if not already there
        if (this.currentPage !== 'chat') {
            this.navigateTo('chat');
            // Set chat nav item as active
            const chatNavItem = document.querySelector('.nav-item');
            if (chatNavItem) {
                this.setActiveNavItem(chatNavItem);
            }
        }
        
        console.log('Started new chat');
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
    console.log('Robobrain loaded and ready');
});
