/**
 * Agent Mention Autocomplete System
 * Allows users to mention agents in chat using @ symbol
 */

class AgentMentionAutocomplete {
    constructor(chatInterface) {
        this.chatInterface = chatInterface;
        this.messageInput = document.getElementById('messageInput');
        this.agents = [];
        this.autocompleteContainer = null;
        this.selectedIndex = -1;
        this.init();
    }

    init() {
        this.createAutocompleteContainer();
        this.loadAgents();
        this.setupEventListeners();
    }

    createAutocompleteContainer() {
        // Create autocomplete dropdown
        this.autocompleteContainer = document.createElement('div');
        this.autocompleteContainer.id = 'agent-mention-autocomplete';
        this.autocompleteContainer.className = 'hidden absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-64 overflow-y-auto z-10';

        const inputContainer = this.messageInput.parentElement;
        inputContainer.insertBefore(this.autocompleteContainer, this.messageInput);
    }

    async loadAgents() {
        try {
            // Load Ollama agents
            const response = await fetch('/api/ollama/agents');
            if (response.ok) {
                const data = await response.json();
                this.agents = data.agents || [];
                console.log(`✅ Loaded ${this.agents.length} agents for mention autocomplete`);
            }
        } catch (error) {
            console.error('Failed to load agents for autocomplete:', error);
            this.agents = [];
        }
    }

    setupEventListeners() {
        // Handle keyboard navigation in autocomplete
        this.messageInput.addEventListener('keydown', (e) => {
            if (!this.isAutocompleteVisible()) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateAutocomplete(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateAutocomplete(-1);
            } else if (e.key === 'Enter' || e.key === 'Tab') {
                if (this.selectedIndex >= 0) {
                    e.preventDefault();
                    this.selectAgent(this.selectedIndex);
                }
            } else if (e.key === 'Escape') {
                this.hideAutocomplete();
            }
        });
    }

    handleInput() {
        const input = this.messageInput.value;
        const cursorPos = this.messageInput.selectionStart;

        // Find the last @ character before cursor
        const textBeforeCursor = input.substring(0, cursorPos);
        const atIndex = textBeforeCursor.lastIndexOf('@');

        if (atIndex === -1) {
            this.hideAutocomplete();
            return;
        }

        // Get the text after @ up to cursor
        const searchTerm = textBeforeCursor.substring(atIndex + 1);

        // Only show autocomplete if @ is at start of word (after space or at start)
        const beforeAt = atIndex > 0 ? textBeforeCursor[atIndex - 1] : ' ';
        if (beforeAt !== ' ' && beforeAt !== '\n' && atIndex !== 0) {
            this.hideAutocomplete();
            return;
        }

        // Don't show if there's a space after @
        if (searchTerm.includes(' ')) {
            this.hideAutocomplete();
            return;
        }

        // Show autocomplete with filtered agents
        this.showAutocomplete(searchTerm, atIndex);
    }

    showAutocomplete(searchTerm, atIndex) {
        // Filter agents based on search term
        const filteredAgents = this.agents.filter(agent =>
            agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (agent.description && agent.description.toLowerCase().includes(searchTerm.toLowerCase()))
        );

        if (filteredAgents.length === 0) {
            this.hideAutocomplete();
            return;
        }

        // Build autocomplete HTML
        let html = '<div class="py-2">';
        html += '<div class="px-3 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Mention Agent</div>';

        filteredAgents.forEach((agent, index) => {
            const isSelected = index === this.selectedIndex;
            const bgClass = isSelected ? 'bg-blue-50 dark:bg-blue-900/50' : 'hover:bg-gray-50 dark:hover:bg-gray-700';

            html += `
                <div class="agent-mention-option ${bgClass} px-3 py-2 cursor-pointer flex items-start justify-between"
                     data-index="${index}"
                     data-agent-id="${agent.agent_id}"
                     data-agent-name="${agent.name}">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center">
                            <span class="font-medium text-gray-900 dark:text-white">@${agent.name}</span>
                            ${agent.status === 'active' ? '<span class="ml-2 w-2 h-2 bg-green-500 rounded-full"></span>' : ''}
                        </div>
                        <p class="text-xs text-gray-600 dark:text-gray-400 truncate mt-0.5">${agent.description || 'No description'}</p>
                        ${agent.skills && agent.skills.length > 0 ? `
                            <div class="flex flex-wrap gap-1 mt-1">
                                ${agent.skills.slice(0, 3).map(skill =>
                                    `<span class="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100 rounded">${skill}</span>`
                                ).join('')}
                                ${agent.skills.length > 3 ? `<span class="text-xs text-gray-500">+${agent.skills.length - 3}</span>` : ''}
                            </div>
                        ` : ''}
                    </div>
                    <div class="ml-2 text-xs text-gray-500 dark:text-gray-400 shrink-0">${agent.model || 'ollama'}</div>
                </div>
            `;
        });

        html += '</div>';

        this.autocompleteContainer.innerHTML = html;
        this.autocompleteContainer.classList.remove('hidden');

        // Add click handlers to options
        this.autocompleteContainer.querySelectorAll('.agent-mention-option').forEach(option => {
            option.addEventListener('click', () => {
                const index = parseInt(option.dataset.index);
                this.selectAgent(index, atIndex, searchTerm);
            });
        });

        // Store filtered agents for selection
        this.filteredAgents = filteredAgents;
        this.atIndex = atIndex;
        this.searchTerm = searchTerm;
        this.selectedIndex = -1;
    }

    navigateAutocomplete(direction) {
        if (!this.filteredAgents || this.filteredAgents.length === 0) return;

        this.selectedIndex += direction;

        if (this.selectedIndex < -1) {
            this.selectedIndex = this.filteredAgents.length - 1;
        } else if (this.selectedIndex >= this.filteredAgents.length) {
            this.selectedIndex = -1;
        }

        // Update visual selection
        this.showAutocomplete(this.searchTerm, this.atIndex);
    }

    selectAgent(index, atIndexOverride = null, searchTermOverride = null) {
        const atIndex = atIndexOverride !== null ? atIndexOverride : this.atIndex;
        const searchTerm = searchTermOverride !== null ? searchTermOverride : this.searchTerm;

        if (!this.filteredAgents || index < 0 || index >= this.filteredAgents.length) return;

        const agent = this.filteredAgents[index];
        const input = this.messageInput.value;

        // Replace @searchTerm with @agentname
        const before = input.substring(0, atIndex);
        const after = input.substring(atIndex + 1 + searchTerm.length);
        const newValue = before + `@${agent.name} ` + after;

        this.messageInput.value = newValue;

        // Position cursor after the mention
        const newCursorPos = before.length + agent.name.length + 2; // +2 for @ and space
        this.messageInput.setSelectionRange(newCursorPos, newCursorPos);

        // Trigger input event to resize textarea
        this.messageInput.dispatchEvent(new Event('input'));

        this.hideAutocomplete();
    }

    hideAutocomplete() {
        this.autocompleteContainer.classList.add('hidden');
        this.selectedIndex = -1;
        this.filteredAgents = null;
    }

    isAutocompleteVisible() {
        return !this.autocompleteContainer.classList.contains('hidden');
    }
}

// Export for use in app.js
window.AgentMentionAutocomplete = AgentMentionAutocomplete;
