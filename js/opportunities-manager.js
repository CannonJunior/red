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
