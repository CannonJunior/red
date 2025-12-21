// Debug mode - set to true to enable verbose console logging
// Can be controlled via localStorage: localStorage.setItem('DEBUG_MODE', 'true')
const DEBUG_MODE = localStorage.getItem('DEBUG_MODE') === 'true';

function debugLog(...args) {
    if (DEBUG_MODE) {
        console.log(...args);
    }
}

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
        
        debugLog(`Theme changed to: ${this.theme}`);
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
        this.currentModel = null; // Will be set dynamically from available models
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
        this.setupAgentMentions();
    }

    setupAgentMentions() {
        // Initialize agent mention autocomplete
        if (typeof AgentMentionAutocomplete !== 'undefined') {
            this.agentMentionAutocomplete = new AgentMentionAutocomplete(this);
        }
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
                debugLog('Available models:', data.models);
                
                // Automatically select the first available model if we don't have one
                if (data.models && data.models.length > 0 && !this.currentModel) {
                    this.currentModel = data.models[0];
                    debugLog('Auto-selected model:', this.currentModel);
                }
            }
        } catch (error) {
            console.error('Failed to load models:', error);
            // Fallback to a default model if no model is selected
            if (!this.currentModel) {
                this.currentModel = 'qwen2.5:3b';
                debugLog('Using fallback model:', this.currentModel);
            }
        }
    }

    setupEventListeners() {
        // Send button click
        this.sendButton?.addEventListener('click', () => this.handleSend());

        // Enhanced key handling for Enter and arrow keys
        this.messageInput?.addEventListener('keydown', (e) => {
            // Check if Prompt autocomplete is visible
            if (this.isPromptAutocompleteVisible()) {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.navigatePromptAutocomplete(1);
                    return;
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.navigatePromptAutocomplete(-1);
                    return;
                } else if (e.key === 'Tab' || e.key === 'Enter') {
                    if (this.promptSelectedIndex >= 0) {
                        e.preventDefault();
                        this.selectCurrentPrompt();
                        return;
                    }
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    this.hidePromptAutocomplete();
                    return;
                }
            }

            // Check if MCP autocomplete is visible
            if (this.isMCPAutocompleteVisible()) {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.navigateMCPAutocomplete(1);
                    return;
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.navigateMCPAutocomplete(-1);
                    return;
                } else if (e.key === 'Tab' || e.key === 'Enter') {
                    if (this.mcpSelectedIndex >= 0) {
                        e.preventDefault();
                        this.selectCurrentMCPTool();
                        return;
                    }
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    this.hideMCPAutocomplete();
                    return;
                }
            }

            // Regular keyboard handling
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateHistory('up');
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateHistory('down');
            } else if (e.key === 'Escape') {
                this.handleEscapeKey();
            }
        });

        // Input changes
        this.messageInput?.addEventListener('input', (e) => {
            this.updateSendButtonState();
            this.handleMCPToolAutocomplete(e);
            this.handlePromptAutocomplete(e);
            // Handle agent mentions (@)
            if (this.agentMentionAutocomplete) {
                this.agentMentionAutocomplete.handleInput();
            }
        });
    }

    setupAutoResize() {
        if (!this.messageInput) return;

        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });
    }

    handleEscapeKey() {
        if (!this.isLoading) return; // Only handle ESC during loading

        if (this.escPressedOnce) {
            // Second ESC press - cancel the request
            debugLog('ESC pressed twice - cancelling request');
            this.cancelCurrentRequest();
            this.escPressedOnce = false;

            // Remove confirmation message
            const confirmMsg = document.getElementById('cancel-confirmation-message');
            if (confirmMsg) confirmMsg.remove();
        } else {
            // First ESC press - show confirmation
            debugLog('ESC pressed once - showing confirmation');
            this.escPressedOnce = true;
            this.showCancelConfirmation();

            // Reset after 3 seconds
            setTimeout(() => {
                this.escPressedOnce = false;
                const confirmMsg = document.getElementById('cancel-confirmation-message');
                if (confirmMsg) confirmMsg.remove();
            }, 3000);
        }
    }

    showCancelConfirmation() {
        // Remove existing confirmation if any
        const existing = document.getElementById('cancel-confirmation-message');
        if (existing) existing.remove();

        // Create confirmation message
        const confirmation = document.createElement('div');
        confirmation.id = 'cancel-confirmation-message';
        confirmation.className = 'fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2';
        confirmation.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>
            <span class="font-medium">Press ESC again to cancel the current request</span>
        `;

        document.body.appendChild(confirmation);
    }

    cancelCurrentRequest() {
        debugLog('Cancelling current request');

        // Set loading to false
        this.isLoading = false;
        this.updateSendButtonState();

        // Remove typing indicator
        const typingIndicators = document.querySelectorAll('.typing-indicator');
        typingIndicators.forEach(indicator => indicator.remove());

        // Display cancellation message
        this.displayMessage('system', 'Request cancelled by user');
    }

    async handleSend() {
        const message = this.messageInput?.value.trim();
        if (!message || this.isLoading) return;

        // Reset ESC press state
        this.escPressedOnce = false;

        debugLog('Sending message:', message);

        // Capture start time
        const startTime = Date.now();
        const startTimeFormatted = new Date(startTime).toLocaleTimeString();

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
            // Check for @ mention to invoke a specific agent
            if (message.startsWith('@')) {
                const atMentionMatch = message.match(/^@(\S+)\s+(.+)$/);
                if (atMentionMatch) {
                    const [, agentName, agentMessage] = atMentionMatch;
                    debugLog('Agent mention detected:', { agentName, agentMessage });

                    // Fetch agents to find the mentioned agent
                    const agentsResponse = await fetch('/api/ollama/agents');
                    if (agentsResponse.ok) {
                        const agentsData = await agentsResponse.json();
                        const agent = agentsData.agents?.find(a => a.name === agentName);

                        if (agent) {
                            debugLog('Found agent:', agent);

                            // Invoke the specific agent
                            const invokeResponse = await fetch(`/api/ollama/agents/${agent.agent_id}/invoke`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ message: agentMessage })
                            });

                            const invokeData = await invokeResponse.json();
                            this.removeTypingIndicator(typingId);

                            if (invokeResponse.ok && invokeData.status === 'success') {
                                // Calculate elapsed time
                                const endTime = Date.now();
                                const elapsedMs = endTime - startTime;
                                const elapsedSeconds = Math.floor(elapsedMs / 1000);
                                const elapsedMinutes = Math.floor(elapsedSeconds / 60);
                                const remainingSeconds = elapsedSeconds % 60;
                                const elapsedFormatted = elapsedMinutes > 0 ?
                                    `${elapsedMinutes}m ${remainingSeconds}s` :
                                    `${remainingSeconds}s`;

                                // Display agent response with metadata
                                const metadata = {
                                    model: invokeData.model,
                                    knowledgeBase: `Agent: ${agentName}`,
                                    ragEnabled: false,
                                    sourcesUsed: 0,
                                    startTime: startTimeFormatted,
                                    endTime: new Date(endTime).toLocaleTimeString(),
                                    elapsed: elapsedFormatted,
                                    cost: '$0.00'
                                };

                                this.displayMessage('assistant', invokeData.response, metadata);
                            } else {
                                this.displayMessage('error', invokeData.error || 'Agent invocation failed');
                            }

                            this.isLoading = false;
                            this.updateSendButtonState();
                            return;
                        } else {
                            // Agent not found
                            this.removeTypingIndicator(typingId);
                            this.displayMessage('error', `Agent '@${agentName}' not found. Available agents: ${agentsData.agents?.map(a => a.name).join(', ') || 'none'}`);
                            this.isLoading = false;
                            this.updateSendButtonState();
                            return;
                        }
                    }
                }
            }

            // Check knowledge mode
            const knowledgeMode = document.getElementById('knowledge-mode-selector')?.value || 'none';

            let apiEndpoint = '/api/chat';
            const requestBody = {
                message: message,
                model: this.currentModel,
                workspace: window.app.knowledgeManager?.currentKnowledgeBase || 'default'
            };

            // Route to CAG if CAG mode is selected
            if (knowledgeMode === 'cag') {
                apiEndpoint = '/api/cag/query';
                requestBody.query = message;
            }

            debugLog('Sending chat request:', { endpoint: apiEndpoint, body: requestBody, mode: knowledgeMode });

            // Send to appropriate API
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            debugLog('Received response:', {
                status: response.status,
                statusText: response.statusText,
                ok: response.ok,
                headers: Object.fromEntries(response.headers)
            });

            const data = await response.json();
            debugLog('Parsed response data:', data);

            // Capture end time and calculate elapsed
            const endTime = Date.now();
            const endTimeFormatted = new Date(endTime).toLocaleTimeString();
            const elapsedMs = endTime - startTime;
            const elapsedSeconds = Math.floor(elapsedMs / 1000);
            const elapsedMinutes = Math.floor(elapsedSeconds / 60);
            const remainingSeconds = elapsedSeconds % 60;
            const elapsedFormatted = elapsedMinutes > 0 ?
                `${elapsedMinutes}m ${remainingSeconds}s` :
                `${remainingSeconds}s`;

            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            if (response.ok) {
                // Debug RAG information
                debugLog('RAG Debug Info:', {
                    rag_enabled: data.rag_enabled,
                    sources_used: data.sources_used,
                    sources_used_type: typeof data.sources_used
                });

                // Prepare metadata
                const metadata = {
                    model: data.model,
                    knowledgeBase: knowledgeMode === 'none' ? 'None' :
                                   knowledgeMode === 'rag' ? 'RAG' : 'CAG',
                    ragEnabled: data.rag_enabled,
                    sourcesUsed: data.sources_used || 0,
                    startTime: startTimeFormatted,
                    endTime: endTimeFormatted,
                    elapsed: elapsedFormatted,
                    tokensUsed: data.tokens_used,
                    promptTokens: data.prompt_tokens,
                    completionTokens: data.completion_tokens
                };

                // Display AI response with complete metadata
                this.displayMessage('assistant', data.response, metadata);
            } else {
                // Display error
                this.displayMessage('error', data.error || 'An error occurred');
            }

        } catch (error) {
            console.error('Chat error details:', {
                error: error,
                message: error.message,
                stack: error.stack,
                currentModel: this.currentModel,
                workspace: window.app.knowledgeManager?.currentKnowledgeBase
            });
            this.removeTypingIndicator(typingId);
            
            // More specific error messages
            let errorMessage = 'Failed to connect to the AI model. Please check your connection.';
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = `Network error: Cannot connect to server. Please check if the server is running on port 9090.`;
            } else if (error.name === 'SyntaxError' && error.message.includes('JSON')) {
                errorMessage = `Server response error: Invalid JSON received from server.`;
            } else if (error.message) {
                errorMessage = `Connection error: ${error.message}`;
            }
            
            this.displayMessage('error', errorMessage);
        } finally {
            this.isLoading = false;
            this.updateSendButtonState();
        }
    }

    displayMessage(type, content, metadata = null) {
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
            // Build RAG/CAG indicator
            const knowledgeIndicator = metadata?.ragEnabled && metadata?.knowledgeBase !== 'None' ?
                `<div class="flex items-center text-xs text-blue-600 dark:text-blue-400 mb-2">
                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
                    </svg>
                    ${metadata.knowledgeBase} Enhanced${metadata.sourcesUsed > 0 ? ` • ${metadata.sourcesUsed} sources` : ''}
                </div>` : '';

            // Build metadata footer
            let metadataHtml = '';
            if (metadata) {
                const metadataParts = [];

                // Knowledge base used
                metadataParts.push(`<span class="inline-flex items-center">
                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/>
                    </svg>
                    KB: ${metadata.knowledgeBase}
                </span>`);

                // Model used
                if (metadata.model) {
                    metadataParts.push(`<span class="inline-flex items-center">
                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                        </svg>
                        ${metadata.model}
                    </span>`);
                }

                // Timing information
                metadataParts.push(`<span class="inline-flex items-center">
                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    ${metadata.elapsed}
                </span>`);

                // Token usage (if available)
                if (metadata.tokensUsed) {
                    metadataParts.push(`<span class="inline-flex items-center">
                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/>
                        </svg>
                        ${metadata.tokensUsed.toLocaleString()} tokens
                    </span>`);
                }

                // Detailed timing (collapsible)
                const timingDetails = `
                    <details class="mt-2 text-xs">
                        <summary class="cursor-pointer opacity-60 hover:opacity-100">Detailed Timing</summary>
                        <div class="mt-1 pl-4 space-y-1 opacity-70">
                            <div>• Prompt entered: ${metadata.startTime}</div>
                            <div>• Response returned: ${metadata.endTime}</div>
                            <div>• Elapsed: ${metadata.elapsed}</div>
                            ${metadata.promptTokens ? `<div>• Prompt tokens: ${metadata.promptTokens.toLocaleString()}</div>` : ''}
                            ${metadata.completionTokens ? `<div>• Completion tokens: ${metadata.completionTokens.toLocaleString()}</div>` : ''}
                        </div>
                    </details>
                `;

                metadataHtml = `
                    <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                        <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs opacity-70">
                            ${metadataParts.join('')}
                        </div>
                        ${timingDetails}
                    </div>
                `;
            }

            messageHtml = `
                <div class="flex justify-start mb-4">
                    <div class="flex space-x-3 max-w-2xl">
                        <img src="robobrain.svg" alt="AI" class="w-8 h-8 rounded-full flex-shrink-0 mt-1 opacity-80">
                        <div class="message-assistant px-4 py-3">
                            ${knowledgeIndicator}
                            <p class="text-sm whitespace-pre-wrap leading-relaxed">${this.escapeHtml(content)}</p>
                            ${metadataHtml}
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
        } else if (type === 'system') {
            messageHtml = `
                <div class="flex justify-center mb-4">
                    <div class="bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 px-4 py-2 rounded-lg">
                        <p class="text-sm text-gray-700 dark:text-gray-300">ℹ️ ${this.escapeHtml(content)}</p>
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

    // MCP Tool Autocomplete and Quick Reference
    async handleMCPToolAutocomplete(event) {
        const input = this.messageInput.value;
        const cursorPos = this.messageInput.selectionStart;

        // Find the last # character before cursor
        const textBeforeCursor = input.substring(0, cursorPos);
        const hashIndex = textBeforeCursor.lastIndexOf('#');

        if (hashIndex === -1) {
            this.hideMCPAutocomplete();
            return;
        }

        // Get the text after # up to cursor
        const searchTerm = textBeforeCursor.substring(hashIndex + 1);

        // Only show autocomplete if # is at start of word (after space or at start)
        const beforeHash = hashIndex > 0 ? textBeforeCursor[hashIndex - 1] : ' ';
        if (beforeHash !== ' ' && beforeHash !== '\n' && hashIndex !== 0) {
            this.hideMCPAutocomplete();
            return;
        }

        // Show autocomplete with filtered MCP tools
        await this.showMCPAutocomplete(searchTerm, hashIndex);
    }

    isMCPAutocompleteVisible() {
        const dropdown = document.getElementById('mcp-autocomplete');
        return dropdown && dropdown.style.display !== 'none';
    }

    navigateMCPAutocomplete(direction) {
        if (!this.filteredMCPTools || this.filteredMCPTools.length === 0) return;

        if (this.mcpSelectedIndex === -1 && direction === 1) {
            this.mcpSelectedIndex = 0;
        } else {
            this.mcpSelectedIndex += direction;
        }

        if (this.mcpSelectedIndex < 0) {
            this.mcpSelectedIndex = this.filteredMCPTools.length - 1;
        } else if (this.mcpSelectedIndex >= this.filteredMCPTools.length) {
            this.mcpSelectedIndex = 0;
        }

        // Update visual selection
        this.updateMCPAutocompleteSelection();
    }

    updateMCPAutocompleteSelection() {
        const dropdown = document.getElementById('mcp-autocomplete');
        if (!dropdown) return;

        const items = dropdown.querySelectorAll('.mcp-autocomplete-item');
        items.forEach((item, index) => {
            if (index === this.mcpSelectedIndex) {
                item.classList.add('bg-blue-50', 'dark:bg-blue-900/50');
                item.classList.remove('hover:bg-gray-100', 'dark:hover:bg-gray-700');
            } else {
                item.classList.remove('bg-blue-50', 'dark:bg-blue-900/50');
                item.classList.add('hover:bg-gray-100', 'dark:hover:bg-gray-700');
            }
        });
    }

    selectCurrentMCPTool() {
        if (this.mcpSelectedIndex >= 0 && this.filteredMCPTools && this.filteredMCPTools[this.mcpSelectedIndex]) {
            const tool = this.filteredMCPTools[this.mcpSelectedIndex];
            this.selectMCPTool(tool, this.mcpHashIndex);
        }
    }

    async showMCPAutocomplete(searchTerm, hashIndex) {
        try {
            // Load MCP tools if not already loaded
            if (!this.mcpTools) {
                const response = await fetch('/mcp-tools/project_tools_config.json');
                if (response.ok) {
                    const config = await response.json();
                    this.mcpTools = config.project_mcp_tools || [];
                } else {
                    this.mcpTools = [];
                }
            }

            // Filter tools based on search term
            const filteredTools = this.mcpTools.filter(tool =>
                tool.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                tool.id.toLowerCase().includes(searchTerm.toLowerCase())
            );

            if (filteredTools.length === 0) {
                this.hideMCPAutocomplete();
                return;
            }

            // Store for keyboard navigation
            this.filteredMCPTools = filteredTools;
            this.mcpHashIndex = hashIndex;
            this.mcpSelectedIndex = -1;

            // Create or update autocomplete dropdown
            let dropdown = document.getElementById('mcp-autocomplete');
            if (!dropdown) {
                dropdown = document.createElement('div');
                dropdown.id = 'mcp-autocomplete';
                dropdown.className = 'absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-64 overflow-y-auto z-20';
                this.messageInput.parentElement.insertBefore(dropdown, this.messageInput);
            }

            // Populate dropdown
            dropdown.innerHTML = `
                <div class="p-2 border-b border-gray-200 dark:border-gray-700">
                    <div class="text-xs font-medium text-gray-500 dark:text-gray-400 px-2">
                        MCP Tools (${filteredTools.length})
                    </div>
                </div>
                <div class="py-1">
                    ${filteredTools.map((tool, index) => `
                        <button type="button"
                                class="mcp-autocomplete-item w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-start"
                                data-index="${index}"
                                data-tool-id="${tool.id}"
                                data-tool-config='${JSON.stringify(tool)}'>
                            <svg class="w-5 h-5 text-blue-500 mr-2 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                            </svg>
                            <div class="flex-1">
                                <div class="text-sm font-medium text-gray-900 dark:text-white">#${tool.id}</div>
                                <div class="text-xs text-gray-500 dark:text-gray-400">${tool.description}</div>
                            </div>
                        </button>
                    `).join('')}
                </div>
            `;

            // Add click handlers
            dropdown.querySelectorAll('.mcp-autocomplete-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    const toolConfig = JSON.parse(item.dataset.toolConfig);
                    this.selectMCPTool(toolConfig, hashIndex);
                });
            });

            dropdown.style.display = 'block';

        } catch (error) {
            console.error('Failed to show MCP autocomplete:', error);
            this.hideMCPAutocomplete();
        }
    }

    hideMCPAutocomplete() {
        const dropdown = document.getElementById('mcp-autocomplete');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
    }

    async selectMCPTool(toolConfig, hashIndex) {
        // Hide autocomplete
        this.hideMCPAutocomplete();

        // Replace #search with #tool-id in the input
        const input = this.messageInput.value;
        const beforeHash = input.substring(0, hashIndex);
        const afterCursor = input.substring(this.messageInput.selectionStart);
        this.messageInput.value = `${beforeHash}#${toolConfig.id}${afterCursor}`;

        // Position cursor after the tool reference
        const newCursorPos = hashIndex + toolConfig.id.length + 1;
        this.messageInput.setSelectionRange(newCursorPos, newCursorPos);

        // Start sequential input collection
        await this.collectMCPToolInputs(toolConfig);
    }

    // Prompt Autocomplete and Quick Reference
    async handlePromptAutocomplete(event) {
        const input = this.messageInput.value;
        const cursorPos = this.messageInput.selectionStart;

        // Find the last / character before cursor
        const textBeforeCursor = input.substring(0, cursorPos);
        const slashIndex = textBeforeCursor.lastIndexOf('/');

        if (slashIndex === -1) {
            this.hidePromptAutocomplete();
            return;
        }

        // Get the text after / up to cursor
        const searchTerm = textBeforeCursor.substring(slashIndex + 1);

        // Only show autocomplete if / is at start of word (after space or at start)
        const beforeSlash = slashIndex > 0 ? textBeforeCursor[slashIndex - 1] : ' ';
        if (beforeSlash !== ' ' && beforeSlash !== '\n' && slashIndex !== 0) {
            this.hidePromptAutocomplete();
            return;
        }

        // Show autocomplete with filtered prompts
        await this.showPromptAutocomplete(searchTerm, slashIndex);
    }

    isPromptAutocompleteVisible() {
        const dropdown = document.getElementById('prompt-autocomplete');
        return dropdown && dropdown.style.display !== 'none';
    }

    navigatePromptAutocomplete(direction) {
        if (!this.filteredPrompts || this.filteredPrompts.length === 0) return;

        if (this.promptSelectedIndex === -1 && direction === 1) {
            this.promptSelectedIndex = 0;
        } else {
            this.promptSelectedIndex += direction;
        }

        if (this.promptSelectedIndex < 0) {
            this.promptSelectedIndex = this.filteredPrompts.length - 1;
        } else if (this.promptSelectedIndex >= this.filteredPrompts.length) {
            this.promptSelectedIndex = 0;
        }

        // Update visual selection
        this.updatePromptAutocompleteSelection();
    }

    updatePromptAutocompleteSelection() {
        const dropdown = document.getElementById('prompt-autocomplete');
        if (!dropdown) return;

        const items = dropdown.querySelectorAll('.prompt-autocomplete-item');
        items.forEach((item, index) => {
            if (index === this.promptSelectedIndex) {
                item.classList.add('bg-blue-50', 'dark:bg-blue-900/50');
                item.classList.remove('hover:bg-gray-100', 'dark:hover:bg-gray-700');
            } else {
                item.classList.remove('bg-blue-50', 'dark:bg-blue-900/50');
                item.classList.add('hover:bg-gray-100', 'dark:hover:bg-gray-700');
            }
        });
    }

    selectCurrentPrompt() {
        if (this.promptSelectedIndex >= 0 && this.filteredPrompts && this.filteredPrompts[this.promptSelectedIndex]) {
            const prompt = this.filteredPrompts[this.promptSelectedIndex];
            this.selectPrompt(prompt, this.promptSlashIndex);
        }
    }

    async showPromptAutocomplete(searchTerm, slashIndex) {
        try {
            // Load prompts if not already loaded
            if (!this.prompts) {
                const response = await fetch('/api/prompts');
                if (response.ok) {
                    const data = await response.json();
                    this.prompts = data.prompts || [];
                } else {
                    this.prompts = [];
                }
            }

            // Filter prompts based on search term
            const filteredPrompts = this.prompts.filter(prompt =>
                prompt.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (prompt.description && prompt.description.toLowerCase().includes(searchTerm.toLowerCase()))
            );

            if (filteredPrompts.length === 0) {
                this.hidePromptAutocomplete();
                return;
            }

            // Store for keyboard navigation
            this.filteredPrompts = filteredPrompts;
            this.promptSlashIndex = slashIndex;
            this.promptSelectedIndex = -1;

            // Create or update autocomplete dropdown
            let dropdown = document.getElementById('prompt-autocomplete');
            if (!dropdown) {
                dropdown = document.createElement('div');
                dropdown.id = 'prompt-autocomplete';
                dropdown.className = 'absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-64 overflow-y-auto z-20';
                this.messageInput.parentElement.insertBefore(dropdown, this.messageInput);
            }

            // Populate dropdown
            dropdown.innerHTML = `
                <div class="p-2 border-b border-gray-200 dark:border-gray-700">
                    <div class="text-xs font-medium text-gray-500 dark:text-gray-400 px-2">
                        Prompts (${filteredPrompts.length})
                    </div>
                </div>
                <div class="py-1">
                    ${filteredPrompts.map((prompt, index) => `
                        <button type="button"
                                class="prompt-autocomplete-item w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-start"
                                data-index="${index}"
                                data-prompt-id="${prompt.id}"
                                data-prompt-name="${prompt.name}">
                            <svg class="w-5 h-5 text-purple-500 mr-2 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                            </svg>
                            <div class="flex-1">
                                <div class="text-sm font-medium text-gray-900 dark:text-white">/${prompt.name}</div>
                                <div class="text-xs text-gray-500 dark:text-gray-400">${prompt.description || 'No description'}</div>
                                ${prompt.usage_count ? `<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Used ${prompt.usage_count} times</div>` : ''}
                            </div>
                        </button>
                    `).join('')}
                </div>
            `;

            // Add click handlers
            dropdown.querySelectorAll('.prompt-autocomplete-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    const index = parseInt(item.dataset.index);
                    const prompt = filteredPrompts[index];
                    this.selectPrompt(prompt, slashIndex);
                });
            });

            dropdown.style.display = 'block';

        } catch (error) {
            console.error('Failed to show prompt autocomplete:', error);
            this.hidePromptAutocomplete();
        }
    }

    hidePromptAutocomplete() {
        const dropdown = document.getElementById('prompt-autocomplete');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
    }

    async selectPrompt(prompt, slashIndex) {
        // Hide autocomplete
        this.hidePromptAutocomplete();

        // Replace /search with /prompt-name in the input
        const input = this.messageInput.value;
        const beforeSlash = input.substring(0, slashIndex);
        const afterCursor = input.substring(this.messageInput.selectionStart);

        // Insert the prompt content
        this.messageInput.value = `${beforeSlash}${prompt.content}${afterCursor}`;

        // Position cursor after the prompt content
        const newCursorPos = beforeSlash.length + prompt.content.length;
        this.messageInput.setSelectionRange(newCursorPos, newCursorPos);

        // Auto-resize textarea
        this.messageInput.dispatchEvent(new Event('input'));

        // Update usage count
        try {
            await fetch(`/api/prompts/use`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt_id: prompt.id })
            });
        } catch (error) {
            console.error('Failed to update prompt usage:', error);
        }
    }

    async collectMCPToolInputs(toolConfig) {
        debugLog('Starting MCP tool input collection for:', toolConfig.name);

        // Create input collection modal
        const modal = this.createMCPInputModal(toolConfig);
        document.body.appendChild(modal);

        // Setup form handlers
        this.setupMCPInputForm(modal, toolConfig);
    }

    createMCPInputModal(toolConfig) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.id = 'mcp-input-modal';

        const requiredInputs = toolConfig.required_inputs || [];
        const optionalInputs = toolConfig.optional_inputs || [];

        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
                <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">${toolConfig.name}</h3>
                <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">${toolConfig.description}</p>

                <form id="mcp-input-form">
                    <div class="space-y-4">
                        ${requiredInputs.map((input, idx) => this.createInputField(input, idx, true)).join('')}

                        ${optionalInputs.length > 0 ? `
                            <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                                <h4 class="text-md font-medium text-gray-900 dark:text-white mb-3">Optional Parameters</h4>
                                ${optionalInputs.map((input, idx) => this.createInputField(input, idx + requiredInputs.length, false)).join('')}
                            </div>
                        ` : ''}
                    </div>

                    <div class="flex gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                        <button type="submit" class="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors">
                            Run ${toolConfig.name}
                        </button>
                        <button type="button" id="mcp-input-cancel" class="bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 py-2 px-4 rounded-md hover:bg-gray-400 dark:hover:bg-gray-500 transition-colors">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        `;

        return modal;
    }

    createInputField(input, idx, required) {
        const fieldId = `mcp-input-${idx}`;

        if (input.type === 'file' || input.type === 'directory') {
            const isDirectory = input.type === 'directory';
            return `
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        ${input.label} ${required ? '*' : '(optional)'}
                    </label>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">${input.description}</p>
                    <div class="flex gap-2">
                        <input type="text"
                               id="${fieldId}"
                               placeholder="${isDirectory ? 'Enter directory path or browse' : 'Enter file path or browse'}"
                               ${required ? 'required' : ''}
                               class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white text-sm">
                        <input type="file"
                               id="${fieldId}-file"
                               accept="${input.accept || '*'}"
                               ${isDirectory ? 'webkitdirectory directory' : ''}
                               style="display: none;"
                               onchange="const f=this.files[0]; if(f) { document.getElementById('${fieldId}').value = f.name; document.getElementById('${fieldId}').fileObject = f; }">
                        <button type="button"
                                class="px-3 py-2 bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-500 text-sm whitespace-nowrap"
                                onclick="document.getElementById('${fieldId}-file').click()">
                            📁 Browse
                        </button>
                    </div>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        💡 Tip: Click Browse to upload ${isDirectory ? 'a directory' : 'a file'} from your computer
                    </p>
                </div>
            `;
        } else if (input.type === 'select') {
            return `
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        ${input.label} ${required ? '*' : '(optional)'}
                    </label>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">${input.description}</p>
                    <select id="${fieldId}"
                            ${required ? 'required' : ''}
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white">
                        ${(input.options || []).map(opt => `
                            <option value="${opt.value}" ${opt.value === input.default ? 'selected' : ''}>
                                ${opt.label}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `;
        } else if (input.type === 'number') {
            return `
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        ${input.label} ${required ? '*' : '(optional)'}
                    </label>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">${input.description}</p>
                    <input type="number"
                           id="${fieldId}"
                           min="${input.min || 0}"
                           max="${input.max || 9999}"
                           value="${input.default || ''}"
                           ${required ? 'required' : ''}
                           class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white">
                </div>
            `;
        } else {
            return `
                <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        ${input.label} ${required ? '*' : '(optional)'}
                    </label>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">${input.description}</p>
                    <input type="text"
                           id="${fieldId}"
                           placeholder="${input.placeholder || ''}"
                           ${required ? 'required' : ''}
                           class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white">
                </div>
            `;
        }
    }

    setupMCPInputForm(modal, toolConfig) {
        const form = modal.querySelector('#mcp-input-form');
        const cancelBtn = modal.querySelector('#mcp-input-cancel');

        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Collect form data
            const formData = {};
            const requiredInputs = toolConfig.required_inputs || [];
            const optionalInputs = toolConfig.optional_inputs || [];
            const allInputs = [...requiredInputs, ...optionalInputs];

            // Helper function to read file as base64
            const readFileAsBase64 = (file) => {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(',')[1]); // Remove data:...;base64, prefix
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });
            };

            // Collect all form values, reading files if necessary
            for (let idx = 0; idx < allInputs.length; idx++) {
                const input = allInputs[idx];
                const fieldId = `mcp-input-${idx}`;
                const field = document.getElementById(fieldId);

                if (field) {
                    // Check if this field has a File object attached
                    if (field.fileObject) {
                        // Read file content and send metadata
                        const fileContent = await readFileAsBase64(field.fileObject);
                        formData[input.name] = {
                            filename: field.fileObject.name,
                            content: fileContent,
                            size: field.fileObject.size,
                            type: field.fileObject.type,
                            lastModified: field.fileObject.lastModified
                        };
                    } else {
                        // Regular text value
                        formData[input.name] = field.value;
                    }
                }
            }

            debugLog('MCP Tool inputs collected:', formData);

            // Close modal
            document.body.removeChild(modal);

            // Execute MCP tool with collected inputs
            await this.executeMCPTool(toolConfig, formData);
        });
    }

    async executeMCPTool(toolConfig, inputs) {
        debugLog('Executing MCP Tool:', toolConfig.name, 'with inputs:', inputs);

        // Format the MCP tool call as a structured message
        const toolCallMessage = `#${toolConfig.id}\n\n${Object.entries(inputs)
            .filter(([k, v]) => v)  // Only include non-empty values
            .map(([k, v]) => `${k}: ${v}`)
            .join('\n')}`;

        // Display user's tool request in chat
        this.displayMessage('user', `🔧 ${toolConfig.name}\n\n${Object.entries(inputs)
            .filter(([k, v]) => v)
            .map(([k, v]) => `• ${k}: ${v}`)
            .join('\n')}`);

        // Set loading state
        this.isLoading = true;
        this.updateSendButtonState();

        // Show typing indicator
        const typingId = this.showTypingIndicator();

        try {
            // Prepare request to execute MCP tool
            const requestBody = {
                message: toolCallMessage,
                model: this.currentModel,
                workspace: window.app.knowledgeManager?.currentKnowledgeBase || 'default',
                mcp_tool_call: {
                    tool_id: toolConfig.id,
                    tool_name: toolConfig.name,
                    inputs: inputs
                }
            };

            debugLog('Sending MCP tool request:', requestBody);

            // Send to chat API (backend should handle MCP tool calls)
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            // Always try to parse the response body, even for errors
            const data = await response.json();
            debugLog('MCP tool response:', data);

            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            // Display the response or error
            if (!response.ok || data.error) {
                const errorMsg = data.error || `HTTP error! status: ${response.status}`;
                this.displayMessage('error', `❌ Error: ${errorMsg}`);
            } else {
                this.displayMessage('assistant', data.response || 'MCP tool executed successfully');
            }

        } catch (error) {
            console.error('MCP tool execution error:', error);
            this.removeTypingIndicator(typingId);
            this.displayMessage('error', `❌ Failed to execute MCP tool: ${error.message}`);
        } finally {
            // Reset loading state
            this.isLoading = false;
            this.updateSendButtonState();
        }
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

                // Handle expandable nav items (Lists)
                if (item.classList.contains('expandable-nav-item')) {
                    e.stopPropagation();
                    this.toggleExpandableNavItem(item, itemText);
                    return;
                }

                this.navigateTo(itemText);
                this.setActiveNavItem(item);

                // Show/hide knowledge base list when Knowledge is selected
                if (itemText === 'knowledge') {
                    this.toggleKnowledgeBaseList(true);
                } else {
                    this.toggleKnowledgeBaseList(false);
                }
            });
        });

        // Setup sub-nav items (Opportunities)
        const subNavItems = document.querySelectorAll('.sub-nav-item');
        subNavItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const listType = item.getAttribute('data-list');

                if (item.classList.contains('expandable-nav-item')) {
                    this.toggleExpandableNavItem(item, listType);
                    // Navigate to appropriate area based on list type
                    if (listType === 'todos') {
                        // Show TODO area
                        if (window.todoUI) {
                            window.todoUI.showTodoArea();
                        }
                    } else {
                        // Navigate to opportunities area for other expandable items
                        this.navigateTo('opportunities');
                        if (window.app?.opportunitiesManager) {
                            window.app.opportunitiesManager.loadOpportunities();
                        }
                    }
                }
            });
        });
    }

    toggleExpandableNavItem(item, itemName) {
        const expandIcon = item.querySelector('.expand-icon');
        let submenu = null;

        if (itemName === 'lists') {
            submenu = document.getElementById('lists-submenu');
        } else if (itemName === 'opportunities') {
            submenu = document.getElementById('opportunities-list');
        } else if (itemName === 'todos') {
            submenu = document.getElementById('todo-lists-dropdown');
        }

        if (submenu) {
            const isHidden = submenu.classList.contains('hidden');
            if (isHidden) {
                submenu.classList.remove('hidden');
                if (expandIcon) {
                    expandIcon.style.transform = 'rotate(180deg)';
                }
            } else {
                submenu.classList.add('hidden');
                if (expandIcon) {
                    expandIcon.style.transform = 'rotate(0deg)';
                }
            }
        }
    }

    navigateTo(page) {
        // Hide all areas
        document.getElementById('chat-area')?.classList.add('hidden');
        document.getElementById('models-area')?.classList.add('hidden');
        document.getElementById('settings-area')?.classList.add('hidden');
        document.getElementById('knowledge-area')?.classList.add('hidden');
        document.getElementById('cag-knowledge-area')?.classList.add('hidden');
        document.getElementById('visualizations-area')?.classList.add('hidden');
        document.getElementById('mcp-area')?.classList.add('hidden');
        document.getElementById('agents-area')?.classList.add('hidden');
        document.getElementById('prompts-area')?.classList.add('hidden');
        document.getElementById('opportunities-area')?.classList.add('hidden');
        document.getElementById('todos-area')?.classList.add('hidden');

        // Hide expandable submenu panels ONLY when navigating away from Lists-related pages
        // Don't hide them when navigating TO opportunities or todos pages
        if (page !== 'opportunities' && page !== 'todos') {
            document.getElementById('opportunities-list')?.classList.add('hidden');
            document.getElementById('todo-lists-dropdown')?.classList.add('hidden');
            document.getElementById('lists-submenu')?.classList.add('hidden');

            // Reset expand icons for all expandable nav items
            document.querySelectorAll('.expandable-nav-item .expand-icon').forEach(icon => {
                icon.style.transform = 'rotate(0deg)';
            });
        }

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
            case 'prompts':
                document.getElementById('prompts-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Prompts';
                this.currentPage = 'prompts';
                // Reload prompts when navigating to the page
                if (window.promptsManager) {
                    window.promptsManager.loadPrompts();
                }
                break;
            case 'visualizations':
                document.getElementById('visualizations-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Visualizations';
                this.currentPage = 'visualizations';
                this.loadVisualizationsPage();
                break;
            case 'settings':
                document.getElementById('settings-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Settings';
                this.currentPage = 'settings';
                this.loadSettingsPage();
                break;
            case 'rag knowledge':
            case 'knowledge':
                document.getElementById('knowledge-area')?.classList.remove('hidden');
                pageTitle.textContent = 'RAG Knowledge';
                this.currentPage = 'knowledge';
                this.loadKnowledgePage();
                break;
            case 'cag knowledge':
                document.getElementById('cag-knowledge-area')?.classList.remove('hidden');
                pageTitle.textContent = 'CAG Knowledge';
                this.currentPage = 'cag-knowledge';
                if (this.cagManager) {
                    this.cagManager.loadCAGStatus();
                }
                break;
            case 'mcp':
                document.getElementById('mcp-area')?.classList.remove('hidden');
                pageTitle.textContent = 'MCP';
                this.currentPage = 'mcp';
                this.setupMCPButtonHandlers();
                break;
            case 'agents':
                document.getElementById('agents-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Agents';
                this.currentPage = 'agents';
                this.setupAgentsButtonHandlers();
                break;
            case 'opportunities':
                document.getElementById('opportunities-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Opportunities';
                this.currentPage = 'opportunities';
                if (window.app?.opportunitiesManager) {
                    window.app.opportunitiesManager.loadOpportunities();
                }
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

    setupMCPButtonHandlers() {
        const addMCPServerBtn = document.getElementById('add-mcp-server-btn');
        if (addMCPServerBtn && !addMCPServerBtn.hasClickHandler) {
            addMCPServerBtn.hasClickHandler = true;
            addMCPServerBtn.addEventListener('click', () => {
                if (window.mcpAgentManager) {
                    window.mcpAgentManager.showAddMCPServerDialog();
                } else {
                    debugLog('MCP Agent Manager not available');
                }
            });
        }
    }

    setupAgentsButtonHandlers() {
        const createAgentBtn = document.getElementById('create-agent-btn');
        if (createAgentBtn && !createAgentBtn.hasClickHandler) {
            createAgentBtn.hasClickHandler = true;
            createAgentBtn.addEventListener('click', () => {
                if (window.mcpAgentManager) {
                    window.mcpAgentManager.showCreateAgentDialog();
                } else {
                    debugLog('MCP Agent Manager not available');
                }
            });
        }
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
            const isSelected = model === window.app?.chatInterface?.currentModel;

            modelCard.className = `model-card p-6 ${isRecommended ? 'model-recommended' : ''} ${isSelected ? 'model-selected' : ''}`;
            modelCard.setAttribute('data-model', model);

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
                    <div class="flex items-center space-x-2">
                        ${isSelected ? '<span class="px-2 py-1 text-xs font-medium text-white bg-blue-600 rounded-full">Selected</span>' : ''}
                        ${isRecommended ? '<span class="px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/50 rounded-full">Recommended</span>' : ''}
                    </div>
                </div>

                <div class="space-y-2 mb-4">
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        ${this.getModelDescription(model)}
                    </p>
                </div>

                <div class="flex space-x-2">
                    <button onclick="window.app.navigation.selectModel('${model}')" class="flex-1 px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/50 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/70 transition-colors">
                        ${isSelected ? 'Selected' : 'Select Model'}
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
            debugLog(`Selected model: ${modelName}`);

            // Update all model selectors
            document.querySelectorAll('#model-selector, #default-model-selector').forEach(selector => {
                selector.value = modelName;
            });

            // Update visual selection state for model cards
            document.querySelectorAll('.model-card').forEach(card => {
                const cardModel = card.getAttribute('data-model');
                const selectButton = card.querySelector('button');
                const selectLabel = card.querySelector('.flex.items-center.space-x-2');

                if (cardModel === modelName) {
                    // Add selected class and update UI
                    card.classList.add('model-selected');
                    if (selectButton) {
                        selectButton.textContent = 'Selected';
                    }
                    // Add selected badge if not already present
                    if (selectLabel && !selectLabel.innerHTML.includes('Selected')) {
                        selectLabel.innerHTML = `<span class="px-2 py-1 text-xs font-medium text-white bg-blue-600 rounded-full">Selected</span>${selectLabel.innerHTML}`;
                    }
                } else {
                    // Remove selected class and update UI
                    card.classList.remove('model-selected');
                    if (selectButton) {
                        selectButton.textContent = 'Select Model';
                    }
                    // Remove selected badge
                    if (selectLabel) {
                        selectLabel.innerHTML = selectLabel.innerHTML.replace(/<span class="px-2 py-1 text-xs font-medium text-white bg-blue-600 rounded-full">Selected<\/span>/, '');
                    }
                }
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

    loadVisualizationsPage() {
        // Initialize visualization manager if it doesn't exist
        if (!window.app.visualizationManager) {
            window.app.visualizationManager = new VisualizationManager();
        }

        // Load default visualization (knowledge graph)
        window.app.visualizationManager.renderVisualization('knowledge-graph');
    }

    loadKnowledgePage() {
        // Initialize knowledge manager if it doesn't exist
        if (!window.app.knowledgeManager) {
            window.app.knowledgeManager = new KnowledgeManager();
        }

        // Load knowledge data
        window.app.knowledgeManager.loadKnowledgeData();
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
        
        debugLog('Started new chat');
    }

    toggleKnowledgeBaseList(show) {
        const kbList = document.getElementById('knowledge-base-list');
        if (kbList) {
            if (show) {
                kbList.classList.remove('hidden');
                this.populateKnowledgeBaseList();
            } else {
                kbList.classList.add('hidden');
            }
        }
    }

    populateKnowledgeBaseList() {
        if (!window.app?.knowledgeManager) return;
        
        const kbList = document.getElementById('knowledge-base-list');
        if (!kbList) return;

        const knowledgeBases = window.app.knowledgeManager.knowledgeBases || ['default'];
        const currentKb = window.app.knowledgeManager.currentKnowledgeBase || 'default';

        kbList.innerHTML = '';
        
        knowledgeBases.forEach(kb => {
            const item = document.createElement('button');
            item.className = `w-full text-left px-3 py-1 rounded text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors ${
                kb === currentKb ? 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400' : ''
            }`;
            item.textContent = kb.charAt(0).toUpperCase() + kb.slice(1).replace(/-/g, ' ');
            
            item.addEventListener('click', () => {
                if (window.app.knowledgeManager) {
                    window.app.knowledgeManager.currentKnowledgeBase = kb;
                    window.app.knowledgeManager.loadKnowledgeData();
                    window.app.knowledgeManager.updateChatKnowledgeBaseIndicator();
                    this.populateKnowledgeBaseList(); // Refresh the list to show current selection
                }
            });
            
            kbList.appendChild(item);
        });
    }

    setupMobileToggle() {
        // TODO: Implement mobile sidebar toggle
        // This will be needed for responsive design
    }
}

// Knowledge Management
class KnowledgeManager {
    constructor() {
        this.currentKnowledgeBase = 'default';
        this.knowledgeBases = ['default'];
        this.documents = [];
        this.analytics = {
            totalDocuments: 0,
            totalVectorChunks: 0,
            totalQueries: 0
        };
        this.selectedFiles = []; // Store selected files for upload
        this.init();
    }

    init() {
        this.setupFileUpload();
        this.setupKnowledgeBaseSelector();
        this.setupDocumentSearch();
        this.setupActionButtons();
        this.loadKnowledgeBases();
        this.updateChatKnowledgeBaseIndicator();
    }

    async loadKnowledgeData() {
        try {
            debugLog('🔄 Starting knowledge data reload...');
            // Load documents from RAG system
            debugLog('📄 Loading documents...');
            await this.loadDocuments();
            debugLog('📊 Loading analytics...');
            // Load analytics
            await this.loadAnalytics();
            debugLog('🎨 Updating UI...');
            // Update UI
            this.updateKnowledgeUI();
            debugLog('✅ Knowledge data reload completed');
        } catch (error) {
            console.error('❌ Failed to load knowledge data:', error);
            this.showError('Failed to load knowledge base data');
        }
    }

    async loadDocuments() {
        try {
            const response = await fetch('/api/rag/documents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace: this.currentKnowledgeBase
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.documents = data.documents || [];
            } else {
                throw new Error('Failed to fetch documents');
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            this.documents = [];
        }
    }

    async loadAnalytics() {
        try {
            const response = await fetch('/api/rag/analytics', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.analytics = {
                    totalDocuments: data.document_count || 0,
                    totalVectorChunks: data.chunk_count || 0,
                    totalQueries: data.query_count || 0
                };
            }
        } catch (error) {
            console.error('Error loading analytics:', error);
            // Use default analytics on error
        }
    }

    updateKnowledgeUI() {
        // Update analytics cards
        this.updateAnalyticsCards();
        // Update documents table
        this.updateDocumentsTable();
        // Update knowledge base selector
        this.updateKnowledgeBaseSelector();
    }

    updateAnalyticsCards() {
        const docCount = document.getElementById('doc-count');
        const chunkCount = document.getElementById('chunk-count');
        const queryCount = document.getElementById('query-count');

        if (docCount) docCount.textContent = this.analytics.totalDocuments;
        if (chunkCount) chunkCount.textContent = this.analytics.totalVectorChunks.toLocaleString();
        if (queryCount) queryCount.textContent = this.analytics.totalQueries.toLocaleString();
    }

    updateDocumentsTable() {
        const tableBody = document.getElementById('documents-table-body');
        const emptyState = document.getElementById('documents-empty-state');

        if (!tableBody || !emptyState) return;

        if (this.documents.length === 0) {
            tableBody.classList.add('hidden');
            emptyState.classList.remove('hidden');
            return;
        }

        tableBody.classList.remove('hidden');
        emptyState.classList.add('hidden');

        tableBody.innerHTML = '';

        this.documents.forEach(doc => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 dark:hover:bg-gray-800/50';
            
            const formatFileSize = (bytes) => {
                if (!bytes) return 'Unknown';
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(1024));
                return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
            };

            const formatDate = (dateString) => {
                if (!dateString) return 'Unknown';
                return new Date(dateString).toLocaleDateString();
            };

            row.innerHTML = `
                <td class="px-6 py-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                            <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                            </svg>
                        </div>
                        <div>
                            <p class="text-sm font-medium text-gray-900 dark:text-white">${doc.name || 'Unknown Document'}</p>
                            <p class="text-sm text-gray-500 dark:text-gray-400">${doc.type || 'Unknown Type'}</p>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    ${formatFileSize(doc.size)}
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    ${doc.chunks || 0} chunks
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    ${formatDate(doc.uploadDate)}
                </td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${doc.status === 'processed' ? 'bg-green-100 text-green-800 dark:bg-gray-800 dark:text-green-400 dark:border dark:border-green-800' : 'bg-yellow-100 text-yellow-800 dark:bg-gray-800 dark:text-yellow-400 dark:border dark:border-yellow-800'}">
                        ${doc.status || 'processed'}
                    </span>
                </td>
                <td class="px-6 py-4 text-right text-sm font-medium">
                    <button onclick="window.app.knowledgeManager.deleteDocument('${doc.id}')" class="text-red-600 hover:text-red-900 dark:text-gray-400 dark:hover:text-red-400 transition-colors">
                        Delete
                    </button>
                </td>
            `;

            tableBody.appendChild(row);
        });
    }

    updateKnowledgeBaseSelector() {
        const selector = document.getElementById('knowledge-base-selector');
        if (!selector) return;

        // Populate with all available knowledge bases
        selector.innerHTML = '';
        this.knowledgeBases.forEach(kb => {
            const option = document.createElement('option');
            option.value = kb;
            option.textContent = kb.charAt(0).toUpperCase() + kb.slice(1).replace(/-/g, ' ') + ' Knowledge Base';
            selector.appendChild(option);
        });
        
        selector.value = this.currentKnowledgeBase;
    }

    setupActionButtons() {
        // Browse files button is handled in setupFileUpload()

        // Refresh documents button
        const refreshBtn = document.getElementById('refresh-documents');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                await this.loadKnowledgeData();
                this.showSuccess('Documents refreshed');
            });
        }

        // Search documents functionality is handled in setupDocumentSearch()

        // Add new knowledge base button
        const addKbBtn = document.getElementById('add-knowledge-base-btn');
        if (addKbBtn) {
            addKbBtn.addEventListener('click', () => {
                this.showAddKnowledgeBaseModal();
            });
        }
    }

    setupFileUpload() {
        const dropZone = document.getElementById('file-drop-zone');
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('upload-btn');
        const browseBtn = document.getElementById('browse-files-btn');

        if (!dropZone || !fileInput || !uploadBtn || !browseBtn) {
            console.error('Missing upload elements:', { dropZone: !!dropZone, fileInput: !!fileInput, uploadBtn: !!uploadBtn, browseBtn: !!browseBtn });
            return;
        }

        // Browse files button - opens file picker
        browseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            fileInput.click();
        });

        // Upload button - uploads selected files
        uploadBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (this.selectedFiles.length > 0) {
                await this.uploadSelectedFiles();
            } else {
                this.showError('Please select files to upload first');
            }
        });

        // File input change - store selected files
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.selectedFiles = Array.from(e.target.files);
                this.updateFileSelectionDisplay();
                debugLog(`Selected ${this.selectedFiles.length} files for upload`);
            }
        });

        // Drag and drop events
        dropZone.addEventListener('dragenter', (e) => {
            e.preventDefault();
            e.stopPropagation();
        });

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Only remove classes if we're leaving the dropzone entirely
            if (!dropZone.contains(e.relatedTarget)) {
                dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
            }
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
            
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.selectedFiles = files;
                this.updateFileSelectionDisplay();
                debugLog(`Dropped ${files.length} files for upload`);
            }
        });

        // Make the entire drop zone clickable to browse files
        // But exclude the Browse Files button to avoid duplicate triggers
        dropZone.addEventListener('click', (e) => {
            // Don't trigger if clicking the browse button or upload button
            if (e.target.closest('#browse-files-btn') || e.target.closest('#upload-btn')) {
                return;
            }
            // Only trigger on drop zone background clicks
            if (e.target === dropZone || e.target.closest('#file-drop-zone')) {
                fileInput.click();
            }
        });
    }

    updateFileSelectionDisplay() {
        const dropZone = document.getElementById('file-drop-zone');
        if (!dropZone) return;

        let displayText = 'Drag & drop files here or click "Browse Files" to select';
        
        if (this.selectedFiles.length > 0) {
            const fileNames = this.selectedFiles.map(file => file.name).join(', ');
            displayText = `Selected files: ${fileNames}`;
            
            // Update the drop zone text
            const textElement = dropZone.querySelector('p');
            if (textElement) {
                textElement.textContent = displayText;
                textElement.classList.add('text-blue-600', 'font-medium');
            }
        } else {
            // Reset to default text
            const textElement = dropZone.querySelector('p');
            if (textElement) {
                textElement.textContent = displayText;
                textElement.classList.remove('text-blue-600', 'font-medium');
            }
        }
    }

    async uploadSelectedFiles() {
        if (this.selectedFiles.length === 0) {
            this.showError('No files selected for upload');
            return;
        }

        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) {
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Uploading...';
        }

        let successCount = 0;
        let errorCount = 0;

        try {
            for (const file of this.selectedFiles) {
                try {
                    await this.uploadSingleFile(file);
                    successCount++;
                } catch (error) {
                    console.error(`Failed to upload ${file.name}:`, error);
                    errorCount++;
                }
            }
            
            // Clear selected files after upload attempt
            this.selectedFiles = [];
            this.updateFileSelectionDisplay();
            
            // Reset file input
            const fileInput = document.getElementById('file-input');
            if (fileInput) fileInput.value = '';
            
            // Refresh documents list - use full knowledge data reload
            await this.loadKnowledgeData();
            
            if (successCount > 0) {
                this.showSuccess(`Successfully uploaded ${successCount} file${successCount !== 1 ? 's' : ''}`);
            }
            if (errorCount > 0) {
                this.showError(`Failed to upload ${errorCount} file${errorCount !== 1 ? 's' : ''}`);
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showError(`Upload failed: ${error.message}`);
        } finally {
            if (uploadBtn) {
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Upload';
            }
        }
    }

    async uploadSingleFile(file) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('knowledge_base', this.currentKnowledgeBase);

            const xhr = new XMLHttpRequest();
            
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    debugLog(`Upload progress for ${file.name}: ${percentComplete.toFixed(1)}%`);
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.status === 'success') {
                            resolve(response);
                        } else {
                            reject(new Error(response.message || 'Upload failed'));
                        }
                    } catch (e) {
                        reject(new Error('Invalid server response'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            };

            xhr.onerror = () => {
                reject(new Error('Network error during upload'));
            };

            xhr.ontimeout = () => {
                reject(new Error('Upload timed out'));
            };

            xhr.timeout = 60000; // 60 second timeout
            xhr.open('POST', '/api/rag/ingest', true);
            xhr.send(formData);
        });
    }

    async handleFiles(files) {
        for (const file of files) {
            await this.uploadFile(file);
        }
        
        // Reload knowledge data after uploads
        debugLog('Reloading knowledge data after upload...');
        await this.loadKnowledgeData();
        debugLog('Knowledge data reloaded successfully');
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/rag/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                debugLog('File uploaded successfully:', data);
                this.showSuccess(`File "${file.name}" uploaded successfully`);
            } else {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
        } catch (error) {
            console.error('File upload error:', error);
            this.showError(`Failed to upload "${file.name}": ${error.message}`);
        }
    }

    async deleteDocument(documentId) {
        try {
            const response = await fetch(`/api/rag/documents/${documentId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workspace: this.currentKnowledgeBase
                })
            });

            if (response.ok) {
                debugLog(`Document ${documentId} deleted successfully`);
                this.showSuccess(`Document ${documentId} deleted successfully`);
                // Reload knowledge data
                debugLog('Reloading knowledge data after delete...');
                await this.loadKnowledgeData();
                debugLog('Knowledge data reloaded after delete');
            } else {
                throw new Error(`Delete failed: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Document delete error:', error);
            this.showError(`Failed to delete document: ${error.message}`);
        }
    }

    setupKnowledgeBaseSelector() {
        const selector = document.getElementById('knowledge-base-selector');
        if (!selector) return;

        selector.addEventListener('change', (e) => {
            this.currentKnowledgeBase = e.target.value;
            this.loadKnowledgeData();
            this.updateChatKnowledgeBaseIndicator();
        });
    }

    updateChatKnowledgeBaseIndicator() {
        const indicator = document.getElementById('currentKnowledgeBase');
        if (indicator) {
            indicator.textContent = this.currentKnowledgeBase;
        }
    }

    setupDocumentSearch() {
        const searchInput = document.getElementById('document-search');
        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            this.filterDocuments(e.target.value);
        });
    }

    filterDocuments(searchTerm) {
        const rows = document.querySelectorAll('#documents-table-body tr');
        const term = searchTerm.toLowerCase();

        rows.forEach(row => {
            const name = row.querySelector('td:first-child p').textContent.toLowerCase();
            const type = row.querySelector('td:first-child p:last-child').textContent.toLowerCase();
            
            if (name.includes(term) || type.includes(term)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    showSuccess(message) {
        // Simple success notification
        debugLog('Success:', message);
        // TODO: Implement proper toast notifications
    }

    showError(message) {
        // Simple error notification
        // Keep console.error for user-facing errors
        console.error('Error:', message);
        // TODO: Implement proper toast notifications
    }

    loadKnowledgeBases() {
        // Load knowledge bases from localStorage for now
        const stored = localStorage.getItem('robobrain_knowledge_bases');
        this.knowledgeBases = stored ? JSON.parse(stored) : ['default'];
        this.updateKnowledgeBaseSelector();
    }

    saveKnowledgeBases() {
        localStorage.setItem('robobrain_knowledge_bases', JSON.stringify(this.knowledgeBases));
    }

    showAddKnowledgeBaseModal() {
        const name = prompt('Enter the name for the new Knowledge Base:');
        if (name && name.trim()) {
            const kbName = name.trim().toLowerCase().replace(/\s+/g, '-');
            if (!this.knowledgeBases.includes(kbName)) {
                this.knowledgeBases.push(kbName);
                this.saveKnowledgeBases();
                this.updateKnowledgeBaseSelector();
                this.currentKnowledgeBase = kbName;
                this.loadKnowledgeData();
                this.updateChatKnowledgeBaseIndicator();
                this.showSuccess(`Knowledge Base "${name}" created successfully`);
                
                // Update sidebar list if Knowledge is currently selected
                if (window.app?.navigation) {
                    window.app.navigation.populateKnowledgeBaseList();
                }
            } else {
                this.showError('A Knowledge Base with that name already exists');
            }
        }
    }
}

// Visualization Management
class VisualizationManager {
    constructor() {
        this.currentVisualization = null;
        this.container = null;
        this.init();
    }

    init() {
        this.container = document.getElementById('visualization-container');
        this.setupControls();
    }

    setupControls() {
        const vizTypeSelect = document.getElementById('viz-type');
        const refreshBtn = document.getElementById('refresh-viz');

        if (vizTypeSelect) {
            vizTypeSelect.addEventListener('change', (e) => {
                this.renderVisualization(e.target.value);
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                const vizType = vizTypeSelect ? vizTypeSelect.value : 'knowledge-graph';
                this.renderVisualization(vizType);
            });
        }
    }

    async renderVisualization(type) {
        if (!this.container) return;

        try {
            switch (type) {
                case 'knowledge-graph':
                    await this.renderKnowledgeGraph();
                    break;
                case 'performance-dashboard':
                    await this.renderPerformanceDashboard();
                    break;
                case 'search-explorer':
                    await this.renderSearchExplorer();
                    break;
                default:
                    this.showError('Unknown visualization type');
            }
        } catch (error) {
            console.error('Visualization error:', error);
            this.showError(`Failed to render ${type}: ${error.message}`);
        }
    }

    async renderKnowledgeGraph() {
        const response = await fetch('/api/visualizations/knowledge-graph');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load knowledge graph data');
        }

        this.clearContainer();

        if (data.entities.length === 0) {
            this.showEmptyState('No documents in knowledge base', 'Upload documents to see knowledge relationships');
            return;
        }

        // Create D3.js visualization
        await this.createD3KnowledgeGraph(data);
        this.showDetails(`Knowledge graph with ${data.entities.length} entities and ${data.relationships.length} relationships from ${data.metadata.data_source}`);
    }

    async renderPerformanceDashboard() {
        const response = await fetch('/api/visualizations/performance');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load performance data');
        }

        this.clearContainer();

        const metrics = data.metrics;
        const html = `
            <div class="grid grid-cols-2 md:grid-cols-3 gap-4 h-full">
                <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">${metrics.total_documents}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Documents</div>
                </div>
                <div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold text-green-600 dark:text-green-400">${metrics.total_chunks}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Vector Chunks</div>
                </div>
                <div class="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg text-center">
                    <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">${metrics.avg_chunks_per_doc.toFixed(1)}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">Avg Chunks/Doc</div>
                </div>
                <div class="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg text-center col-span-2 md:col-span-3">
                    <div class="text-lg font-bold text-orange-600 dark:text-orange-400">${metrics.system_health.toUpperCase()}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">System Status • Data: ${metrics.data_source}</div>
                </div>
            </div>
        `;

        this.container.innerHTML = html;
        this.showDetails(`Performance dashboard showing real-time metrics from ${data.data_source}`);
    }

    async renderSearchExplorer() {
        const response = await fetch('/api/visualizations/search-results');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load search results');
        }

        this.clearContainer();

        if (data.search_results.length === 0) {
            this.showEmptyState('No search results available', 'Upload documents to enable search exploration');
            return;
        }

        const html = `
            <div class="h-full overflow-y-auto">
                <div class="mb-4 text-sm text-gray-600 dark:text-gray-400">
                    Query: "${data.query_info.query}" • ${data.search_results.length} results • ${data.query_info.execution_time}s
                </div>
                <div class="space-y-3">
                    ${data.search_results.map(result => `
                        <div class="p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                            <div class="flex items-start justify-between">
                                <div class="flex-1">
                                    <h4 class="font-medium text-gray-900 dark:text-white">${result.title}</h4>
                                    <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">${result.content}</p>
                                    <div class="text-xs text-gray-500 dark:text-gray-500 mt-2">
                                        Source: ${result.source} • Type: ${result.metadata.file_type}
                                    </div>
                                </div>
                                <div class="ml-4 text-right">
                                    <div class="text-sm font-medium text-blue-600 dark:text-blue-400">${(result.score * 100).toFixed(1)}%</div>
                                    <div class="text-xs text-gray-500 dark:text-gray-500">Relevance</div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        this.container.innerHTML = html;
        this.showDetails(`Search results explorer showing ${data.search_results.length} documents from ${data.data_source}`);
    }

    async createD3KnowledgeGraph(data) {
        // Ensure D3 is available
        if (typeof d3 === 'undefined') {
            await this.loadD3();
        }

        const width = 800;
        const height = 400;

        const svg = d3.select(this.container)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .style('border', '1px solid #e5e7eb')
            .style('border-radius', '8px')
            .style('background', 'white')
            .classed('dark:bg-gray-800 dark:border-gray-600', true);

        const nodes = data.entities;
        const links = data.relationships;

        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));

        // Create links
        const link = svg.append('g')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.sqrt(d.weight * 5));

        // Create nodes
        const node = svg.append('g')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (event, d) => this.dragstarted(event, d, simulation))
                .on('drag', this.dragged)
                .on('end', (event, d) => this.dragended(event, d, simulation)));

        // Add circles to nodes
        node.append('circle')
            .attr('r', d => 5 + (d.confidence * 15))
            .attr('fill', d => {
                const colors = {
                    'DOCUMENT': '#3b82f6',
                    'CATEGORY': '#10b981',
                    'CONCEPT': '#f59e0b'
                };
                return colors[d.type] || '#6b7280';
            })
            .attr('opacity', 0.8);

        // Add labels to nodes
        node.append('text')
            .text(d => d.name)
            .attr('dy', -20)
            .attr('text-anchor', 'middle')
            .style('font-family', 'Inter, sans-serif')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .attr('fill', 'currentColor');

        // Update positions on simulation tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    async loadD3() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://d3js.org/d3.v7.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    dragstarted(event, d, simulation) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d, simulation) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    clearContainer() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }

    showEmptyState(title, message) {
        const html = `
            <div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                <div class="text-center">
                    <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                    </svg>
                    <h3 class="text-lg font-medium mb-2">${title}</h3>
                    <p class="text-sm">${message}</p>
                </div>
            </div>
        `;
        this.container.innerHTML = html;
    }

    showDetails(text) {
        const detailsElement = document.getElementById('details-content');
        const detailsContainer = document.getElementById('visualization-details');

        if (detailsElement && detailsContainer) {
            detailsElement.textContent = text;
            detailsContainer.classList.remove('hidden');
        }
    }

    showError(message) {
        console.error('Visualization error:', message);
        this.showEmptyState('Visualization Error', message);
    }
}

// Opportunities Manager
class OpportunitiesManager {
    constructor() {
        this.opportunities = [];
        this.currentOpportunity = null;
        this.calendarManager = null;
        this.ganttManager = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeVisualizations();
    }

    initializeVisualizations() {
        // Initialize Calendar Manager
        if (typeof SVGCalendarManager !== 'undefined') {
            this.calendarManager = new SVGCalendarManager('svg-calendar-container');
        }

        // Initialize Gantt Chart Manager
        if (typeof GanttChartManager !== 'undefined') {
            this.ganttManager = new GanttChartManager('gantt-chart-container');
        }
    }

    setupEventListeners() {
        // Add opportunity button
        const addBtn = document.getElementById('add-opportunity-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showCreateOpportunityModal());
        }

        // Modal close buttons
        const closeModal = document.getElementById('close-opportunity-modal');
        const cancelBtn = document.getElementById('cancel-opportunity-btn');
        if (closeModal) {
            closeModal.addEventListener('click', () => this.hideOpportunityModal());
        }
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hideOpportunityModal());
        }

        // Form submission
        const form = document.getElementById('opportunity-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveOpportunity();
            });
        }

        // Detail view buttons
        const closeDetailBtn = document.getElementById('close-opportunity-detail-btn');
        const editBtn = document.getElementById('edit-opportunity-btn');
        const deleteBtn = document.getElementById('delete-opportunity-btn');

        if (closeDetailBtn) {
            closeDetailBtn.addEventListener('click', () => this.closeOpportunityDetail());
        }
        if (editBtn) {
            editBtn.addEventListener('click', () => this.editCurrentOpportunity());
        }
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteCurrentOpportunity());
        }

        // Calendar and Tasks toggle buttons
        const toggleCalendarBtn = document.getElementById('toggle-calendar-view');
        const toggleTasksBtn = document.getElementById('toggle-tasks-view');
        const listViewBtn = document.getElementById('tasks-list-view-btn');

        if (toggleCalendarBtn) {
            toggleCalendarBtn.addEventListener('click', () => this.showCalendarView());
        }
        if (toggleTasksBtn) {
            toggleTasksBtn.addEventListener('click', () => this.showTasksView());
        }
        if (listViewBtn) {
            listViewBtn.addEventListener('click', () => this.showListView());
        }

        // Task management buttons
        const addTaskBtn = document.getElementById('add-task-btn');
        const closeTaskModal = document.getElementById('close-task-modal');
        const cancelTaskBtn = document.getElementById('cancel-task-btn');
        const taskForm = document.getElementById('task-form');

        if (addTaskBtn) {
            addTaskBtn.addEventListener('click', () => this.showCreateTaskModal());
        }
        if (closeTaskModal) {
            closeTaskModal.addEventListener('click', () => this.hideTaskModal());
        }
        if (cancelTaskBtn) {
            cancelTaskBtn.addEventListener('click', () => this.hideTaskModal());
        }
        if (taskForm) {
            taskForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveTask();
            });
        }
    }

    async loadOpportunities() {
        try {
            const response = await fetch('/api/opportunities', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.opportunities = data.opportunities || [];
                this.renderOpportunitiesList();
            }
        } catch (error) {
            console.error('Error loading opportunities:', error);
        }
    }

    renderOpportunitiesList() {
        const opportunitiesList = document.getElementById('opportunities-list');
        if (!opportunitiesList) return;

        opportunitiesList.innerHTML = '';

        if (this.opportunities.length === 0) {
            opportunitiesList.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400 px-3 py-2">No opportunities yet</p>';
            return;
        }

        this.opportunities.forEach(opp => {
            const wrapper = document.createElement('div');
            wrapper.className = 'flex items-center gap-1 group';

            const item = document.createElement('button');
            item.className = 'flex-1 text-left px-3 py-2 rounded text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors';
            item.textContent = opp.name;
            item.addEventListener('click', () => {
                // Show the opportunity detail first
                this.showOpportunityDetail(opp);

                // Navigate to opportunities page to make it visible
                if (window.app && window.app.currentPage !== 'opportunities') {
                    // Hide all areas
                    document.getElementById('chat-area')?.classList.add('hidden');
                    document.getElementById('models-area')?.classList.add('hidden');
                    document.getElementById('settings-area')?.classList.add('hidden');
                    document.getElementById('knowledge-area')?.classList.add('hidden');
                    document.getElementById('cag-knowledge-area')?.classList.add('hidden');
                    document.getElementById('visualizations-area')?.classList.add('hidden');
                    document.getElementById('mcp-area')?.classList.add('hidden');
                    document.getElementById('agents-area')?.classList.add('hidden');
                    document.getElementById('prompts-area')?.classList.add('hidden');
                    document.getElementById('todos-area')?.classList.add('hidden');

                    // Show opportunities area
                    document.getElementById('opportunities-area')?.classList.remove('hidden');
                    window.app.currentPage = 'opportunities';

                    // Update page title
                    const pageTitle = document.getElementById('page-title');
                    if (pageTitle) pageTitle.textContent = 'Opportunities';

                    // Set the Lists nav item as active
                    const navItems = document.querySelectorAll('.nav-item.expandable-nav-item');
                    navItems.forEach(nav => {
                        if (nav.textContent.trim().toLowerCase().includes('lists')) {
                            window.app.setActiveNavItem(nav);

                            // Ensure the Lists submenu is expanded
                            const expandIcon = nav.querySelector('.expand-icon');
                            if (expandIcon) {
                                expandIcon.style.transform = 'rotate(180deg)';
                            }
                        }
                    });

                    // Ensure the opportunities list and lists submenu stay visible
                    const listsSubmenu = document.getElementById('lists-submenu');
                    const opportunitiesList = document.getElementById('opportunities-list');
                    if (listsSubmenu) listsSubmenu.classList.remove('hidden');
                    if (opportunitiesList) opportunitiesList.classList.remove('hidden');

                    // Rotate the Opportunities expand icon
                    const oppSubNavItem = document.querySelector('.sub-nav-item[data-list="opportunities"]');
                    if (oppSubNavItem) {
                        const oppExpandIcon = oppSubNavItem.querySelector('.expand-icon');
                        if (oppExpandIcon) {
                            oppExpandIcon.style.transform = 'rotate(180deg)';
                        }
                    }
                }
            });

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'p-2 text-gray-400 hover:text-red-500 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity';
            deleteBtn.title = 'Delete opportunity';
            deleteBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
            `;
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteOpportunityFromList(opp.id, opp.name);
            });

            wrapper.appendChild(item);
            wrapper.appendChild(deleteBtn);
            opportunitiesList.appendChild(wrapper);
        });
    }

    showCreateOpportunityModal() {
        this.currentOpportunity = null;
        const modal = document.getElementById('opportunity-modal');
        const modalTitle = document.getElementById('opportunity-modal-title');
        const form = document.getElementById('opportunity-form');

        if (modalTitle) modalTitle.textContent = 'Create Opportunity';
        if (form) form.reset();
        if (modal) modal.classList.remove('hidden');
    }

    hideOpportunityModal() {
        const modal = document.getElementById('opportunity-modal');
        if (modal) modal.classList.add('hidden');
    }

    async saveOpportunity() {
        const name = document.getElementById('opportunity-name').value;
        const description = document.getElementById('opportunity-description').value;
        const status = document.getElementById('opportunity-status').value;
        const priority = document.getElementById('opportunity-priority').value;
        const value = parseFloat(document.getElementById('opportunity-value').value) || 0;
        const tagsInput = document.getElementById('opportunity-tags').value;
        const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];

        const opportunityData = {
            name,
            description,
            status,
            priority,
            value,
            tags
        };

        try {
            const url = this.currentOpportunity
                ? `/api/opportunities/${this.currentOpportunity.id}`
                : '/api/opportunities';

            const method = 'POST';

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(opportunityData)
            });

            if (response.ok) {
                const data = await response.json();
                debugLog(`Opportunity ${this.currentOpportunity ? 'updated' : 'created'} successfully`);
                this.hideOpportunityModal();
                this.loadOpportunities();

                // Show the newly created opportunity
                if (data.opportunity) {
                    this.showOpportunityDetail(data.opportunity);
                }
            } else {
                console.error('Failed to save opportunity');
            }
        } catch (error) {
            console.error('Error saving opportunity:', error);
        }
    }

    showOpportunityDetail(opportunity) {
        this.currentOpportunity = opportunity;

        const detailView = document.getElementById('opportunity-detail-view');
        const emptyState = document.getElementById('opportunities-empty-state');

        if (!detailView) {
            console.error('opportunity-detail-view element not found');
            return;
        }

        if (detailView) detailView.classList.remove('hidden');
        if (emptyState) emptyState.classList.add('hidden');

        // Populate detail fields
        const nameEl = document.getElementById('opportunity-detail-name');
        const statusEl = document.getElementById('opportunity-detail-status');
        const priorityEl = document.getElementById('opportunity-detail-priority');
        const valueEl = document.getElementById('opportunity-detail-value');
        const createdEl = document.getElementById('opportunity-detail-created');
        const descriptionEl = document.getElementById('opportunity-detail-description');

        if (nameEl) nameEl.textContent = opportunity.name;
        if (statusEl) statusEl.textContent = this.formatStatus(opportunity.status);
        if (priorityEl) priorityEl.textContent = this.formatPriority(opportunity.priority);
        if (valueEl) valueEl.textContent = `$${opportunity.value.toLocaleString()}`;
        if (createdEl) createdEl.textContent = new Date(opportunity.created_at).toLocaleDateString();
        if (descriptionEl) descriptionEl.textContent = opportunity.description || 'No description';

        // Render tags
        const tagsContainer = document.getElementById('opportunity-detail-tags');
        if (tagsContainer) {
            tagsContainer.innerHTML = '';
            if (opportunity.tags && opportunity.tags.length > 0) {
                opportunity.tags.forEach(tag => {
                    const tagEl = document.createElement('span');
                    tagEl.className = 'px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded';
                    tagEl.textContent = tag;
                    tagsContainer.appendChild(tagEl);
                });
            } else {
                tagsContainer.innerHTML = '<span class="text-gray-500 dark:text-gray-400">No tags</span>';
            }
        }

        // Load tasks for this opportunity
        this.loadTasks(opportunity.id);

        debugLog(`Showing opportunity detail: ${opportunity.name}`);
    }

    closeOpportunityDetail() {
        const detailView = document.getElementById('opportunity-detail-view');
        const emptyState = document.getElementById('opportunities-empty-state');

        if (detailView) detailView.classList.add('hidden');
        if (emptyState) emptyState.classList.remove('hidden');
    }

    editCurrentOpportunity() {
        if (!this.currentOpportunity) return;

        const modal = document.getElementById('opportunity-modal');
        const modalTitle = document.getElementById('opportunity-modal-title');

        if (modalTitle) modalTitle.textContent = 'Edit Opportunity';

        // Populate form
        document.getElementById('opportunity-id').value = this.currentOpportunity.id;
        document.getElementById('opportunity-name').value = this.currentOpportunity.name;
        document.getElementById('opportunity-description').value = this.currentOpportunity.description || '';
        document.getElementById('opportunity-status').value = this.currentOpportunity.status;
        document.getElementById('opportunity-priority').value = this.currentOpportunity.priority;
        document.getElementById('opportunity-value').value = this.currentOpportunity.value;
        document.getElementById('opportunity-tags').value = (this.currentOpportunity.tags || []).join(', ');

        if (modal) modal.classList.remove('hidden');
    }

    async deleteCurrentOpportunity() {
        if (!this.currentOpportunity) return;

        if (!confirm(`Are you sure you want to delete "${this.currentOpportunity.name}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/opportunities/${this.currentOpportunity.id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                debugLog('Opportunity deleted successfully');
                this.closeOpportunityDetail();
                this.loadOpportunities();
            } else {
                console.error('Failed to delete opportunity');
            }
        } catch (error) {
            console.error('Error deleting opportunity:', error);
        }
    }

    async deleteOpportunityFromList(opportunityId, opportunityName) {
        if (!confirm(`Are you sure you want to delete "${opportunityName}"? This will also delete all associated tasks.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/opportunities/${opportunityId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.status === 'success') {
                debugLog('Opportunity deleted from list successfully');
                this.loadOpportunities();
            } else {
                console.error('Failed to delete opportunity:', result.message);
            }
        } catch (error) {
            console.error('Error deleting opportunity:', error);
        }
    }

    showCalendarView() {
        const calendarContainer = document.getElementById('svg-calendar-container');
        const ganttContainer = document.getElementById('gantt-chart-container');

        if (calendarContainer && ganttContainer) {
            calendarContainer.classList.remove('hidden');
            ganttContainer.classList.add('hidden');

            // Load opportunities into calendar if manager exists
            if (this.calendarManager && this.currentOpportunity) {
                this.calendarManager.setOpportunities([this.currentOpportunity]);
                this.calendarManager.render();
            }
        }
    }

    showTasksView() {
        const calendarContainer = document.getElementById('svg-calendar-container');
        const ganttContainer = document.getElementById('gantt-chart-container');

        if (calendarContainer && ganttContainer) {
            calendarContainer.classList.add('hidden');
            ganttContainer.classList.remove('hidden');

            // Load tasks into gantt chart if manager exists
            if (this.ganttManager && this.currentOpportunity) {
                this.loadTasksForGantt(this.currentOpportunity.id);
            }
        }
    }

    async loadTasksForGantt(opportunityId) {
        try {
            const response = await fetch(`/api/opportunities/${opportunityId}/tasks`);
            if (response.ok) {
                const data = await response.json();
                if (this.ganttManager) {
                    this.ganttManager.setTasks(data.tasks || []);
                    this.ganttManager.render();
                }
            }
        } catch (error) {
            console.error('Error loading tasks for gantt:', error);
        }
    }

    showListView() {
        const listContainer = document.getElementById('tasks-list-container');
        const calendarContainer = document.getElementById('svg-calendar-container');
        const ganttContainer = document.getElementById('gantt-chart-container');

        if (listContainer && calendarContainer && ganttContainer) {
            listContainer.classList.remove('hidden');
            calendarContainer.classList.add('hidden');
            ganttContainer.classList.add('hidden');
        }
    }

    async loadTasks(opportunityId) {
        try {
            const response = await fetch(`/api/opportunities/${opportunityId}/tasks`);
            if (response.ok) {
                const data = await response.json();
                this.renderTasksList(data.tasks || []);
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
        }
    }

    renderTasksList(tasks) {
        const tbody = document.getElementById('tasks-table-body');
        const emptyState = document.getElementById('tasks-empty-state');

        if (!tbody) return;

        tbody.innerHTML = '';

        if (tasks.length === 0) {
            document.getElementById('tasks-table-wrapper')?.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }

        document.getElementById('tasks-table-wrapper')?.classList.remove('hidden');
        if (emptyState) emptyState.classList.add('hidden');

        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700';
            row.innerHTML = `
                <td class="px-3 py-2 text-gray-900 dark:text-white">${this.escapeHtml(task.name)}</td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.status}</td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.progress}%</td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.start_date}</td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.end_date}</td>
                <td class="px-3 py-2">
                    <button class="text-blue-600 hover:text-blue-800 mr-2" onclick="window.app.opportunitiesManager.editTask('${task.id}')">Edit</button>
                    <button class="text-red-600 hover:text-red-800" onclick="window.app.opportunitiesManager.deleteTask('${task.id}')">Delete</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    showCreateTaskModal() {
        if (!this.currentOpportunity) {
            alert('Please select an opportunity first');
            return;
        }

        const modal = document.getElementById('task-modal');
        const form = document.getElementById('task-form');

        if (form) form.reset();

        document.getElementById('task-id').value = '';
        document.getElementById('task-opportunity-id').value = this.currentOpportunity.id;
        document.getElementById('task-modal-title').textContent = 'Create Task';

        if (modal) modal.classList.remove('hidden');
    }

    hideTaskModal() {
        const modal = document.getElementById('task-modal');
        if (modal) modal.classList.add('hidden');
    }

    async saveTask() {
        const taskId = document.getElementById('task-id').value;
        const opportunityId = document.getElementById('task-opportunity-id').value;

        const taskData = {
            name: document.getElementById('task-name').value,
            description: document.getElementById('task-description').value,
            start_date: document.getElementById('task-start-date').value,
            end_date: document.getElementById('task-end-date').value,
            status: document.getElementById('task-status').value,
            progress: parseInt(document.getElementById('task-progress').value) || 0,
            assigned_to: document.getElementById('task-assigned-to').value
        };

        try {
            let response;
            if (taskId) {
                response = await fetch(`/api/tasks/${taskId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(taskData)
                });
            } else {
                response = await fetch(`/api/opportunities/${opportunityId}/tasks`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(taskData)
                });
            }

            if (response.ok) {
                this.hideTaskModal();
                this.loadTasks(opportunityId);
            }
        } catch (error) {
            console.error('Error saving task:', error);
        }
    }

    async editTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            if (response.ok) {
                const data = await response.json();
                const task = data.task;

                document.getElementById('task-id').value = task.id;
                document.getElementById('task-opportunity-id').value = task.opportunity_id;
                document.getElementById('task-name').value = task.name;
                document.getElementById('task-description').value = task.description || '';
                document.getElementById('task-start-date').value = task.start_date;
                document.getElementById('task-end-date').value = task.end_date;
                document.getElementById('task-status').value = task.status;
                document.getElementById('task-progress').value = task.progress;
                document.getElementById('task-assigned-to').value = task.assigned_to || '';

                document.getElementById('task-modal-title').textContent = 'Edit Task';
                document.getElementById('task-modal').classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error loading task:', error);
        }
    }

    async deleteTask(taskId) {
        if (!confirm('Are you sure you want to delete this task?')) return;

        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE'
            });

            if (response.ok && this.currentOpportunity) {
                this.loadTasks(this.currentOpportunity.id);
            }
        } catch (error) {
            console.error('Error deleting task:', error);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatStatus(status) {
        const statusMap = {
            'open': 'Open',
            'in_progress': 'In Progress',
            'won': 'Won',
            'lost': 'Lost'
        };
        return statusMap[status] || status;
    }

    formatPriority(priority) {
        return priority.charAt(0).toUpperCase() + priority.slice(1);
    }
}

// App initialization
class App {
    constructor() {
        this.themeManager = new ThemeManager();
        this.chatInterface = new ChatInterface();
        this.navigation = new Navigation();
        this.visualizationManager = new VisualizationManager();
        this.opportunitiesManager = new OpportunitiesManager();
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
        debugLog('App initialized successfully');
        
        // Setup error handling
        window.addEventListener('error', (e) => {
            console.error('App error:', e.error);
        });

        // Setup performance monitoring
        if (window.performance) {
            window.addEventListener('load', () => {
                const loadTime = performance.now();
                debugLog(`App loaded in ${Math.round(loadTime)}ms`);
            });
        }
    }
}

// Integration Functions (Placeholders for future implementation)
class IntegrationManager {
    constructor() {
        // Use dynamic URLs based on current window location for distributed deployment
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;
        const port = window.location.port || '9090';

        this.apiEndpoint = `${protocol}//${hostname}:${port}/api`;
        this.wsEndpoint = `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}:${port}/ws`;
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
                debugLog('WebSocket connected');
            };

            this.socket.onmessage = (event) => {
                debugLog('WebSocket message:', event.data);
            };

            this.socket.onclose = () => {
                debugLog('WebSocket disconnected');
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

    // Initialize CAG Manager
    if (typeof CAGManager !== 'undefined') {
        window.app.cagManager = new CAGManager();
        debugLog('✅ CAG Manager initialized');
    }

    // Initialize MCP Agent System integration
    initializeMCPAgentIntegration();

    // Make integration manager available globally for future use
    debugLog('Robobrain loaded and ready');
    debugLog('🤖 MCP Agent System integration initialized');
});

// MCP Agent System Integration
function initializeMCPAgentIntegration() {
    debugLog('🔗 Integrating MCP Agent System with main navigation...');

    // Add MCP and Agents sections to navigation if they don't exist
    // addMCPAgentNavigation(); // Disabled - using static navigation in index.html instead

    // Setup navigation event handlers
    setupMCPAgentNavHandlers();

    // Initialize dashboard widgets
    initializeMCPAgentDashboard();

    debugLog('✅ MCP Agent System integration completed');
}

function addMCPAgentNavigation() {
    // Find the main navigation container
    const navContainer = document.querySelector('nav') || document.querySelector('.sidebar');

    if (!navContainer) {
        console.warn('⚠️ Navigation container not found, creating agent navigation dynamically');
        return;
    }

    // Check if MCP/Agents navigation already exists
    if (document.getElementById('mcp-nav') || document.getElementById('agents-nav')) {
        debugLog('📋 MCP/Agents navigation already exists');
        return;
    }

    // Add MCP and Agents navigation items
    const mcpNavHtml = `
        <div id="mcp-nav" class="nav-section">
            <a href="#mcp" class="nav-item flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md">
                <svg class="mr-3 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
                </svg>
                MCP Servers
            </a>
        </div>

        <div id="agents-nav" class="nav-section">
            <a href="#agents" class="nav-item flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md">
                <svg class="mr-3 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
                </svg>
                Agents
            </a>
        </div>
    `;

    // Insert MCP/Agents navigation
    navContainer.insertAdjacentHTML('beforeend', mcpNavHtml);
}

function setupMCPAgentNavHandlers() {
    // Handle navigation clicks
    document.addEventListener('click', (e) => {
        if (e.target.matches('a[href="#mcp"], a[href="#mcp"] *')) {
            e.preventDefault();
            window.app.navigateTo('mcp');
        }

        if (e.target.matches('a[href="#agents"], a[href="#agents"] *')) {
            e.preventDefault();
            window.app.navigateTo('agents');
        }
    });

    // Handle browser back/forward
    window.addEventListener('popstate', (e) => {
        if (location.hash === '#mcp') {
            window.app.navigateTo('mcp');
        } else if (location.hash === '#agents') {
            window.app.navigateTo('agents');
        }
    });
}

function showMCPSection() {
    debugLog('📋 Showing MCP section');

    // Hide other sections
    hideAllSections();

    // Show or create MCP section
    let mcpSection = document.getElementById('mcp-section');
    if (!mcpSection) {
        mcpSection = createMCPSection();
        document.querySelector('main').appendChild(mcpSection);
    }

    mcpSection.style.display = 'block';

    // Update navigation state
    updateNavState('mcp');

    // Update URL
    history.pushState({section: 'mcp'}, 'MCP Servers', '#mcp');

    // Initialize MCP section if manager is available
    if (window.mcpAgentManager) {
        window.mcpAgentManager.updateMCPServersUI();
    }
}

function showAgentsSection() {
    debugLog('🤖 Showing Agents section');

    // Hide other sections
    hideAllSections();

    // Show or create Agents section
    let agentsSection = document.getElementById('agents-section');
    if (!agentsSection) {
        agentsSection = createAgentsSection();
        document.querySelector('main').appendChild(agentsSection);
    }

    agentsSection.style.display = 'block';

    // Update navigation state
    updateNavState('agents');

    // Update URL
    history.pushState({section: 'agents'}, 'Agents', '#agents');

    // Initialize Agents section if manager is available
    if (window.mcpAgentManager) {
        window.mcpAgentManager.updateAgentsUI();
    }
}

function createMCPSection() {
    const section = document.createElement('div');
    section.id = 'mcp-section';
    section.className = 'mcp-section p-6';
    section.style.display = 'none';

    section.innerHTML = `
        <div class="mb-6">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">MCP Servers</h2>
            <p class="text-gray-600 dark:text-gray-400 mt-1">Manage Model Context Protocol servers and tools</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- MCP Servers List -->
            <div class="lg:col-span-2">
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Server Status</h3>
                        <button class="refresh-mcp-servers px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
                            Refresh
                        </button>
                    </div>
                    <div id="mcp-servers-list" class="space-y-4">
                        <!-- MCP servers will be populated by JavaScript -->
                        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
                            Loading MCP servers...
                        </div>
                    </div>
                </div>
            </div>

            <!-- MCP Metrics -->
            <div class="space-y-6">
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Server Metrics</h3>
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Total Servers:</span>
                            <span class="text-sm font-medium text-gray-900 dark:text-white" id="total-mcp-servers">0</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Running:</span>
                            <span class="text-sm font-medium text-green-600" id="running-mcp-servers">0</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Avg Latency:</span>
                            <span class="text-sm font-medium text-gray-900 dark:text-white" id="mcp-avg-latency">< 10ms</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Cost:</span>
                            <span class="text-sm font-medium text-green-600">$0.00</span>
                        </div>
                    </div>
                </div>

                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Connection Status</h3>
                    <div class="flex items-center">
                        <div id="connection-status" class="w-2 h-2 bg-gray-500 rounded-full mr-2"></div>
                        <span class="text-sm text-gray-600 dark:text-gray-400">Real-time monitoring</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    return section;
}

function createAgentsSection() {
    const section = document.createElement('div');
    section.id = 'agents-section';
    section.className = 'agents-section p-6';
    section.style.display = 'none';

    section.innerHTML = `
        <div class="mb-6">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Agent System</h2>
            <p class="text-gray-600 dark:text-gray-400 mt-1">Manage AI agents and natural language task processing</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Natural Language Interface -->
            <div class="lg:col-span-2 space-y-6">
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Natural Language Task Input</h3>
                    <div class="space-y-4">
                        <textarea
                            id="nlp-task-input"
                            placeholder="Describe what you want to do... (e.g., 'Search for documents about machine learning', 'Review my Python code for security issues')"
                            class="w-full h-24 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        ></textarea>
                        <div class="flex justify-between items-center">
                            <div class="text-sm text-gray-500 dark:text-gray-400">
                                AI will analyze your request and recommend the best agent
                            </div>
                            <button
                                id="nlp-submit-button"
                                class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                            >
                                Parse Task
                            </button>
                        </div>
                    </div>

                    <!-- Analysis Result -->
                    <div id="nlp-analysis-result" style="display: none;"></div>
                </div>

                <!-- Agents List -->
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Active Agents</h3>
                        <div class="space-x-2">
                            <button class="create-agent px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">
                                Create Agent
                            </button>
                            <button class="refresh-agents px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
                                Refresh
                            </button>
                        </div>
                    </div>
                    <div id="agents-list" class="space-y-4">
                        <!-- Agents will be populated by JavaScript -->
                        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
                            Loading agents...
                        </div>
                    </div>
                </div>
            </div>

            <!-- Agent Metrics & Performance -->
            <div class="space-y-6">
                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Performance Metrics</h3>
                    <div id="ui-performance-metrics">
                        <!-- Performance metrics will be populated by JavaScript -->
                    </div>
                </div>

                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">System Status</h3>
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">NLP Parser:</span>
                            <span class="text-sm font-medium text-green-600">Active</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Mojo SIMD:</span>
                            <span class="text-sm font-medium text-green-600">35,000x</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Monitoring:</span>
                            <span class="text-sm font-medium text-green-600">< 10ms</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-sm text-gray-600 dark:text-gray-400">Total Cost:</span>
                            <span class="text-sm font-medium text-green-600">$0.00</span>
                        </div>
                    </div>
                </div>

                <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">RED Compliance</h3>
                    <div class="space-y-2">
                        <div class="flex items-center">
                            <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="text-sm text-gray-900 dark:text-white">COST-FIRST</span>
                        </div>
                        <div class="flex items-center">
                            <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="text-sm text-gray-900 dark:text-white">AGENT-NATIVE</span>
                        </div>
                        <div class="flex items-center">
                            <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="text-sm text-gray-900 dark:text-white">MOJO-OPTIMIZED</span>
                        </div>
                        <div class="flex items-center">
                            <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="text-sm text-gray-900 dark:text-white">LOCAL-FIRST</span>
                        </div>
                        <div class="flex items-center">
                            <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="text-sm text-gray-900 dark:text-white">SIMPLE-SCALE</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    return section;
}

function hideAllSections() {
    // Hide existing sections
    const sections = document.querySelectorAll('main > div, main > section, #mcp-section, #agents-section');
    sections.forEach(section => {
        section.style.display = 'none';
    });
}

function updateNavState(activeSection) {
    // Remove active state from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active', 'bg-gray-100', 'dark:bg-gray-700');
    });

    // Add active state to current section
    const activeNav = document.querySelector(`a[href="#${activeSection}"]`);
    if (activeNav) {
        activeNav.classList.add('active', 'bg-gray-100', 'dark:bg-gray-700');
    }
}

function initializeMCPAgentDashboard() {
    // Add quick stats to dashboard if it exists
    const dashboard = document.querySelector('.dashboard, #dashboard');
    if (dashboard) {
        const agentStatsHtml = `
            <div class="agent-dashboard-widget bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-4">
                <h4 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Agent System Status</h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div class="text-gray-600 dark:text-gray-400">MCP Servers</div>
                        <div class="font-semibold text-gray-900 dark:text-white">Ready</div>
                    </div>
                    <div>
                        <div class="text-gray-600 dark:text-gray-400">Agents</div>
                        <div class="font-semibold text-gray-900 dark:text-white">5 Active</div>
                    </div>
                    <div>
                        <div class="text-gray-600 dark:text-gray-400">Performance</div>
                        <div class="font-semibold text-green-600">35,000x</div>
                    </div>
                    <div>
                        <div class="text-gray-600 dark:text-gray-400">Cost</div>
                        <div class="font-semibold text-green-600">$0.00</div>
                    </div>
                </div>
            </div>
        `;

        dashboard.insertAdjacentHTML('afterbegin', agentStatsHtml);
    }
}
