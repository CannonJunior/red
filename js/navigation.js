// Navigation Manager
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
        // Top-level nav items identified by data-page attribute
        const navItems = document.querySelectorAll('.nav-item[data-page]');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const page = item.dataset.page;

                if (item.classList.contains('expandable-nav-item')) {
                    e.stopPropagation();
                    this.toggleExpandableNavItem(item, page);
                    // Skills also navigates to the management page
                    if (page === 'skills') {
                        this.navigateTo('skills-interface');
                        this.setActiveNavItem(item);
                    }
                    // Knowledge and Lists: expand only, no area navigation
                    return;
                }

                this.navigateTo(page);
                this.setActiveNavItem(item);
            });
        });

        // Sub-nav items (data-list, data-skill, data-nav)
        const subNavItems = document.querySelectorAll('.sub-nav-item');
        subNavItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const listType  = item.getAttribute('data-list');
                const skillType = item.getAttribute('data-skill');
                const navType   = item.getAttribute('data-nav');

                // Knowledge sub-items: CAG Knowledge / RAG Knowledge
                if (navType) {
                    this.navigateTo(navType);
                    return;
                }

                // Skills sub-items: career-monster, etc.
                if (skillType) {
                    if (skillType === 'career-monster') {
                        this.showCareerMonster();
                    }
                    return;
                }

                // Lists sub-items
                if (listType === 'career-analysis') {
                    if (window.careerList) {
                        window.careerList.showCareerAnalysisList();
                    }
                    return;
                }

                if (item.classList.contains('expandable-nav-item')) {
                    this.toggleExpandableNavItem(item, listType);
                    if (listType === 'todos') {
                        if (window.todoUI) {
                            window.todoUI.showTodoArea();
                        }
                    } else {
                        this.navigateTo('opportunities');
                        if (window.app?.opportunitiesManager) {
                            window.app.opportunitiesManager.loadOpportunities();
                        }
                    }
                }
            });
        });

        // Settings button (bottom of sidebar)
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.navigateTo('settings');
            });
        }
    }

    showCareerMonster() {
        this.navigateTo('career-monster');
        const careerArea = document.getElementById('career-monster-area');
        if (careerArea) {
            careerArea.classList.remove('hidden');
        }
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = 'Career-Monster';
        }
    }

    loadSkillsManagementPage() {
        const STORAGE_KEY = 'skills_enabled_state';
        const savedState = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');

        fetch(`${this.baseUrl || ''}/api/ollama/skills`)
            .then(r => r.json())
            .then(data => {
                const skills = data.skills || [];
                const pluginSkills = skills.filter(s => s.source === 'plugin');
                const customSkills = skills.filter(s => s.source === 'local');

                this._renderSkillsManagementList('plugin-skills-list', pluginSkills, savedState, STORAGE_KEY);
                this._renderSkillsManagementList('custom-skills-list', customSkills, savedState, STORAGE_KEY);
                this.refreshSkillsSubmenu(skills, savedState);
            })
            .catch(() => {
                // Fallback: show only the built-in Career Monster skill
                const builtinSkills = [{ name: 'career-monster', description: 'Academic hiring pattern analysis', source: 'local', hasInterface: true }];
                this._renderSkillsManagementList('plugin-skills-list', [], savedState, STORAGE_KEY);
                this._renderSkillsManagementList('custom-skills-list', builtinSkills, savedState, STORAGE_KEY);
                this.refreshSkillsSubmenu(builtinSkills, savedState);
            });
    }

    _renderSkillsManagementList(containerId, skills, savedState, storageKey) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (skills.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-400 dark:text-gray-500">No skills available</p>';
            return;
        }

        container.innerHTML = skills.map(skill => {
            const enabled = savedState[skill.name] !== false; // default enabled
            return `
                <div class="flex items-start justify-between p-3 border border-gray-200 dark:border-gray-600 rounded-lg">
                    <div class="flex-1 min-w-0 mr-4">
                        <div class="text-sm font-medium text-gray-900 dark:text-white">${skill.name}</div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${skill.description || ''}</div>
                        ${skill.hasInterface ? '<span class="inline-block mt-1 text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded">Has sub-tab interface</span>' : ''}
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer flex-shrink-0">
                        <input type="checkbox" class="skill-toggle sr-only" data-skill="${skill.name}" ${enabled ? 'checked' : ''}>
                        <div class="skill-toggle-track w-11 h-6 bg-gray-200 dark:bg-gray-600 rounded-full transition-colors ${enabled ? '!bg-blue-600' : ''}"></div>
                        <div class="skill-toggle-thumb absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${enabled ? 'translate-x-5' : ''}"></div>
                    </label>
                </div>
            `;
        }).join('');

        // Bind toggle events
        container.querySelectorAll('.skill-toggle').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const skillName = e.target.dataset.skill;
                const isEnabled = e.target.checked;
                const state = JSON.parse(localStorage.getItem(storageKey) || '{}');
                state[skillName] = isEnabled;
                localStorage.setItem(storageKey, JSON.stringify(state));

                // Update visual track/thumb
                const label = e.target.closest('label');
                const track = label.querySelector('.skill-toggle-track');
                const thumb = label.querySelector('.skill-toggle-thumb');
                if (isEnabled) {
                    track.classList.add('!bg-blue-600');
                    thumb.classList.add('translate-x-5');
                } else {
                    track.classList.remove('!bg-blue-600');
                    thumb.classList.remove('translate-x-5');
                }

                // Refresh the sidebar submenu
                fetch(`${this.baseUrl || ''}/api/ollama/skills`)
                    .then(r => r.json())
                    .then(data => this.refreshSkillsSubmenu(data.skills || [], state))
                    .catch(() => {});
            });
        });
    }

    refreshSkillsSubmenu(skills, savedState) {
        const submenu = document.getElementById('skills-submenu');
        if (!submenu) return;

        // Keep only skills with a UI interface that are enabled
        const interfaceSkills = skills.filter(s => s.hasInterface && savedState[s.name] !== false);
        // Always include career-monster if enabled
        const cmEnabled = savedState['career-monster'] !== false;

        let html = '';

        // Career Monster (built-in interface skill)
        if (cmEnabled) {
            html += `
                <button class="sub-nav-item w-full text-left px-3 py-2 rounded-md text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700" data-skill="career-monster">
                    <span class="flex items-center">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                        </svg>
                        Career-Monster
                    </span>
                </button>`;
        }

        // Other interface skills from the API
        interfaceSkills.filter(s => s.name !== 'career-monster').forEach(skill => {
            html += `
                <button class="sub-nav-item w-full text-left px-3 py-2 rounded-md text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700" data-skill="${skill.name}">
                    <span class="flex items-center">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path>
                        </svg>
                        ${skill.name}
                    </span>
                </button>`;
        });

        submenu.innerHTML = html;

        // Re-bind sub-nav click events for newly created buttons
        submenu.querySelectorAll('.sub-nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const skillType = item.getAttribute('data-skill');
                if (skillType === 'career-monster') {
                    this.showCareerMonster();
                }
            });
        });
    }

    loadOllamaAgentCreatePage() {
        // Load skills into the full-screen form
        fetch(`${this.baseUrl || ''}/api/ollama/skills`)
            .then(r => r.json())
            .then(data => {
                const skills = data.skills || [];
                this._renderAgentSkillsGrid('fs-plugin-skills-grid', skills.filter(s => s.source === 'plugin'));
                this._renderAgentSkillsGrid('fs-custom-skills-grid', skills.filter(s => s.source === 'local'));
            })
            .catch(() => {
                document.getElementById('fs-plugin-skills-grid').innerHTML = '<p class="text-sm text-gray-400 col-span-2">No plugin skills available</p>';
                document.getElementById('fs-custom-skills-grid').innerHTML = '<p class="text-sm text-gray-400 col-span-2">No custom skills available</p>';
            });

        // Tab switching
        const fsSkillTabs = document.querySelectorAll('.fs-skill-tab');
        const fsSkillContents = document.querySelectorAll('.fs-skill-tab-content');
        fsSkillTabs.forEach(tab => {
            tab.onclick = (e) => {
                e.preventDefault();
                const target = tab.dataset.tab;
                fsSkillTabs.forEach(t => {
                    if (t.dataset.tab === target) {
                        t.classList.remove('border-transparent', 'text-gray-500', 'dark:text-gray-400');
                        t.classList.add('border-blue-600', 'text-blue-600', 'dark:border-blue-400', 'dark:text-blue-400');
                    } else {
                        t.classList.remove('border-blue-600', 'text-blue-600', 'dark:border-blue-400', 'dark:text-blue-400');
                        t.classList.add('border-transparent', 'text-gray-500', 'dark:text-gray-400');
                    }
                });
                fsSkillContents.forEach(c => {
                    c.dataset.tabContent === target ? c.classList.remove('hidden') : c.classList.add('hidden');
                });
            };
        });

        // Back/Cancel buttons
        const backBtn = document.getElementById('back-to-agents-btn');
        const cancelBtn = document.getElementById('cancel-agent-fullscreen');
        const goBack = () => {
            this.navigateTo('agents');
            const agentsNavItem = document.querySelector('.nav-item[data-page="agents"]') ||
                Array.from(document.querySelectorAll('.nav-item')).find(el => el.textContent.trim().toLowerCase() === 'agents');
            if (agentsNavItem) this.setActiveNavItem(agentsNavItem);
        };
        if (backBtn) backBtn.onclick = goBack;
        if (cancelBtn) cancelBtn.onclick = goBack;

        // Form submission
        const form = document.getElementById('create-agent-fullscreen-form');
        if (form) {
            form.onsubmit = async (e) => {
                e.preventDefault();
                const name = document.getElementById('fs-agent-name').value;
                const description = document.getElementById('fs-agent-description').value;
                const model = document.getElementById('fs-agent-model').value;
                const capabilities = Array.from(document.querySelectorAll('.fs-capability:checked')).map(c => c.value);
                const skills = Array.from(document.querySelectorAll('.fs-agent-skill:checked')).map(c => c.value);

                try {
                    if (window.mcpAgentManager) {
                        await window.mcpAgentManager.createAgent({ name, description, model, capabilities, skills });
                    }
                    goBack();
                } catch (err) {
                    console.error('Failed to create agent:', err);
                    alert('Failed to create agent: ' + err.message);
                }
            };
        }
    }

    _renderAgentSkillsGrid(containerId, skills) {
        const container = document.getElementById(containerId);
        if (!container) return;
        if (skills.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-400 col-span-2">No skills available</p>';
            return;
        }
        container.innerHTML = skills.map(skill => `
            <label class="flex items-start p-3 border border-gray-200 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700">
                <input type="checkbox" class="fs-agent-skill mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500" value="${skill.name}">
                <div class="ml-2">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${skill.name}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">${skill.description || ''}</div>
                </div>
            </label>
        `).join('');
    }

    toggleExpandableNavItem(item, itemName) {
        const expandIcon = item.querySelector('.expand-icon');
        let submenu = null;

        switch (itemName) {
            case 'lists':
                submenu = document.getElementById('lists-submenu'); break;
            case 'knowledge':
                submenu = document.getElementById('knowledge-submenu'); break;
            case 'skills':
            case 'skills interface': // legacy fallback
                submenu = document.getElementById('skills-submenu'); break;
            case 'opportunities':
                submenu = document.getElementById('opportunities-list'); break;
            case 'todos':
                submenu = document.getElementById('todo-lists-dropdown'); break;
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
        document.getElementById('career-monster-area')?.classList.add('hidden');
        document.getElementById('career-analysis-area')?.classList.add('hidden');
        document.getElementById('skills-interface-area')?.classList.add('hidden');
        document.getElementById('ollama-agent-create-area')?.classList.add('hidden');
        document.getElementById('workflows-area')?.classList.add('hidden');

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
                pageTitle.textContent = 'Ollama';
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
            case 'rag-knowledge':
            case 'rag knowledge':
            case 'knowledge':
                document.getElementById('knowledge-area')?.classList.remove('hidden');
                pageTitle.textContent = 'RAG Knowledge';
                this.currentPage = 'knowledge';
                this.loadKnowledgePage();
                break;
            case 'cag-knowledge':
            case 'cag knowledge':
                document.getElementById('cag-knowledge-area')?.classList.remove('hidden');
                pageTitle.textContent = 'CAG Knowledge';
                this.currentPage = 'cag-knowledge';
                if (this.cagManager) {
                    this.cagManager.loadCAGStatus();
                }
                break;
            case 'workflows':
                document.getElementById('workflows-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Workflows';
                this.currentPage = 'workflows';
                if (window.workflowsManager) {
                    window.workflowsManager.load();
                }
                // Wire refresh button each time we navigate here
                const refreshBtn = document.getElementById('refresh-workflows-btn');
                if (refreshBtn && !refreshBtn._wired) {
                    refreshBtn._wired = true;
                    refreshBtn.addEventListener('click', () => {
                        if (window.workflowsManager) window.workflowsManager.load();
                    });
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
            case 'skills-interface':
                document.getElementById('skills-interface-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Skills Interface';
                this.currentPage = 'skills-interface';
                this.loadSkillsManagementPage();
                break;
            case 'ollama-agent-create':
                document.getElementById('ollama-agent-create-area')?.classList.remove('hidden');
                pageTitle.textContent = 'Create New Ollama Agent';
                this.currentPage = 'ollama-agent-create';
                this.loadOllamaAgentCreatePage();
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
                    card.classList.add('model-selected');
                    if (selectButton) {
                        selectButton.textContent = 'Selected';
                    }
                    if (selectLabel && !selectLabel.innerHTML.includes('Selected')) {
                        selectLabel.innerHTML = `<span class="px-2 py-1 text-xs font-medium text-white bg-blue-600 rounded-full">Selected</span>${selectLabel.innerHTML}`;
                    }
                } else {
                    card.classList.remove('model-selected');
                    if (selectButton) {
                        selectButton.textContent = 'Select Model';
                    }
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

    async loadSettingsPage() {
        const themeSelector = document.getElementById('theme-selector');
        const defaultModelSelector = document.getElementById('default-model-selector');

        if (themeSelector && window.app?.themeManager) {
            themeSelector.value = window.app.themeManager.theme;
            themeSelector.addEventListener('change', (e) => {
                window.app.themeManager.setTheme(e.target.value);
            });
        }

        if (defaultModelSelector) {
            // Fetch available models from API instead of hardcoding
            try {
                const response = await fetch('/api/models', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (response.ok) {
                    const data = await response.json();
                    this.populateModelSelector(data.models || [], defaultModelSelector);
                } else {
                    console.warn('Failed to fetch models, using defaults');
                    this.populateModelSelector(['qwen2.5:3b'], defaultModelSelector);
                }
            } catch (error) {
                console.error('Error fetching models:', error);
                this.populateModelSelector(['qwen2.5:3b'], defaultModelSelector);
            }
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
