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
        // Find the messages area inside #chat-area specifically.
        // The generic '.flex-1.overflow-y-auto' selector would also match the
        // sidebar <nav> element, which would wipe out all nav items.
        const chatArea = document.querySelector('#chat-area .flex-1.overflow-y-auto');
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

        // Input changes — updateSendButtonState fires immediately; autocomplete
        // calls are debounced at 150 ms to avoid hammering the DOM on fast typing.
        let _autocompleteTimer = null;
        this.messageInput?.addEventListener('input', (e) => {
            this.updateSendButtonState();
            clearTimeout(_autocompleteTimer);
            _autocompleteTimer = setTimeout(() => {
                this.handleMCPToolAutocomplete(e);
                this.handlePromptAutocomplete(e);
                if (this.agentMentionAutocomplete) {
                    this.agentMentionAutocomplete.handleInput();
                }
            }, 150);
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

                            // Invoke the specific agent via chat API (with tool calling support)
                            const invokeResponse = await fetch('/api/chat', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    message: agentMessage,
                                    agent: agent.agent_id,
                                    model: agent.model || 'qwen2.5:3b'
                                })
                            });

                            const invokeData = await invokeResponse.json();
                            this.removeTypingIndicator(typingId);

                            if (invokeResponse.ok && !invokeData.error) {
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
                                const toolCallsInfo = invokeData.tool_calls_made > 0 ?
                                    ` (${invokeData.tool_calls_made} tool calls)` : '';

                                const metadata = {
                                    model: invokeData.model,
                                    knowledgeBase: `Agent: ${agentName}${toolCallsInfo}`,
                                    ragEnabled: false,
                                    agentEnabled: true,
                                    toolCallsMade: invokeData.tool_calls_made || 0,
                                    iterations: invokeData.iterations || 1,
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

        // Add career-monster button if mentioned in assistant message
        if (type === 'assistant' && (content.toLowerCase().includes('career-monster') || content.toLowerCase().includes('career monster'))) {
            const buttonDiv = document.createElement('div');
            buttonDiv.className = 'mt-3';
            buttonDiv.innerHTML = `
                <button class="career-monster-btn px-4 py-2 bg-purple-600 dark:bg-purple-700 text-white rounded-lg hover:bg-purple-700 dark:hover:bg-purple-800 transition-colors flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                    </svg>
                    Open Career-Monster
                </button>
            `;
            const messageContent = messageDiv.querySelector('.message-assistant');
            if (messageContent) {
                messageContent.appendChild(buttonDiv);
            }

            // Add click handler for career-monster button
            const careerBtn = messageDiv.querySelector('.career-monster-btn');
            if (careerBtn) {
                careerBtn.addEventListener('click', () => {
                    if (window.app) {
                        window.app.showCareerMonster();
                    }
                });
            }
        }

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
