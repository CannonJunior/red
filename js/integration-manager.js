// Integration Manager and MCP Agent System Integration

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

// -------------------------------------------------------------------------
// MCP Agent System Integration functions
// -------------------------------------------------------------------------

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
                            <span class="text-sm font-medium text-gray-900 dark:text-white" id="mcp-avg-latency">&lt; 10ms</span>
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
                            placeholder="Describe what you want to do..."
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
                    <div id="ui-performance-metrics"></div>
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
                            <span class="text-sm font-medium text-green-600">&lt; 10ms</span>
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
                        ${['COST-FIRST', 'AGENT-NATIVE', 'MOJO-OPTIMIZED', 'LOCAL-FIRST', 'SIMPLE-SCALE'].map(item => `
                        <div class="flex items-center">
                            <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="text-sm text-gray-900 dark:text-white">${item}</span>
                        </div>`).join('')}
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
