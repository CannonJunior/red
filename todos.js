/**
 * TODO List UI - Phase 5
 * Handles all TODO list interactions, rendering, and API calls
 */

class TodoUI {
    constructor() {
        this.currentUserId = '38024350-8533-4a8b-bbe1-bcd9b837cc01'; // Default user
        this.currentBucket = 'today';
        this.currentListId = null;
        this.todos = [];
        this.lists = [];
        this.stats = { total: 0, completed: 0, pending: 0, urgent: 0 };

        this.init();
    }

    /**
     * Initialize the TODO UI
     */
    init() {
        this.attachEventListeners();
        this.loadUserLists();
        this.loadTodos();
    }

    /**
     * Attach all event listeners
     */
    attachEventListeners() {
        // Bucket tabs
        const bucketTabs = document.querySelectorAll('[data-bucket]');
        bucketTabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchBucket(e.currentTarget.dataset.bucket));
        });

        // Quick add
        const quickAddBtn = document.getElementById('quick-add-btn');
        const quickAddInput = document.getElementById('quick-add-input');

        console.log('Quick add button found:', !!quickAddBtn);
        console.log('Quick add input found:', !!quickAddInput);

        if (quickAddBtn) {
            quickAddBtn.addEventListener('click', () => {
                console.log('Quick add button clicked');
                this.quickAddTodo();
            });
            console.log('Click listener attached to quick-add-btn');
        } else {
            console.error('quick-add-btn element not found during initialization');
        }

        if (quickAddInput) {
            quickAddInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    console.log('Enter key pressed in quick-add-input');
                    this.quickAddTodo();
                }
            });
        }

        // New list button
        const newListBtn = document.getElementById('new-list-btn');
        if (newListBtn) newListBtn.addEventListener('click', () => this.showCreateListModal());

        // Back to all lists button
        const backBtn = document.getElementById('back-to-all-lists-btn');
        if (backBtn) backBtn.addEventListener('click', () => this.showAllLists());

        // Modals
        this.attachModalListeners();

        // Sidebar TODO navigation
        const todoNavBtn = document.querySelector('[data-list="todos"]');
        if (todoNavBtn) {
            todoNavBtn.addEventListener('click', () => this.showTodoArea());
        }
    }

    /**
     * Attach modal event listeners
     */
    attachModalListeners() {
        // Todo detail modal
        const todoModal = document.getElementById('todo-modal');
        const todoModalClose = document.getElementById('close-todo-modal');
        const todoModalCancel = document.getElementById('cancel-todo-btn');
        const todoModalSave = document.getElementById('save-todo-btn');
        const todoModalDelete = document.getElementById('delete-todo-btn');

        if (todoModalClose) todoModalClose.addEventListener('click', () => this.closeTodoModal());
        if (todoModalCancel) todoModalCancel.addEventListener('click', () => this.closeTodoModal());
        if (todoModalSave) todoModalSave.addEventListener('click', (e) => {
            e.preventDefault();
            this.saveTodoModal();
        });
        if (todoModalDelete) todoModalDelete.addEventListener('click', () => this.deleteTodoFromModal());

        // Create list modal
        const listModal = document.getElementById('create-list-modal');
        const listModalClose = document.getElementById('close-create-list-modal');
        const listModalCancel = document.getElementById('cancel-create-list-btn');
        const listForm = document.getElementById('create-list-form');

        if (listModalClose) listModalClose.addEventListener('click', () => this.closeCreateListModal());
        if (listModalCancel) listModalCancel.addEventListener('click', () => this.closeCreateListModal());
        if (listForm) listForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.createList();
        });

        // Color picker buttons
        const colorButtons = document.querySelectorAll('.list-color-btn');
        colorButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const color = e.currentTarget.dataset.color;
                // Update hidden input
                const colorInput = document.getElementById('list-color');
                if (colorInput) colorInput.value = color;
                // Update visual selection
                colorButtons.forEach(b => {
                    b.classList.remove('border-blue-500', 'border-green-500', 'border-yellow-500', 'border-red-500', 'border-purple-500', 'border-pink-500');
                    b.classList.add('border-transparent');
                });
                e.currentTarget.classList.remove('border-transparent');
                // Apply color-specific border based on background
                const bgClass = e.currentTarget.className.match(/bg-(\w+)-500/);
                if (bgClass) {
                    e.currentTarget.classList.add(`border-${bgClass[1]}-500`);
                }
            });
        });
    }

    /**
     * Switch active bucket
     */
    switchBucket(bucket) {
        this.currentBucket = bucket;

        // Update tab UI
        document.querySelectorAll('[data-bucket]').forEach(tab => {
            tab.classList.remove('border-blue-500', 'text-blue-600', 'dark:text-blue-400');
            tab.classList.add('border-transparent', 'text-gray-500', 'dark:text-gray-400');
        });

        const activeTab = document.querySelector(`[data-bucket="${bucket}"]`);
        if (activeTab) {
            activeTab.classList.add('border-blue-500', 'text-blue-600', 'dark:text-blue-400');
            activeTab.classList.remove('border-transparent', 'text-gray-500', 'dark:text-gray-400');
        }

        this.renderTodos();
    }

    /**
     * Quick add todo with natural language
     */
    async quickAddTodo() {
        console.log('quickAddTodo called');
        const input = document.getElementById('quick-add-input');

        if (!input) {
            console.error('quick-add-input element not found');
            return;
        }

        const text = input.value.trim();
        console.log('Input text:', text);

        if (!text) {
            console.log('No text entered');
            return;
        }

        try {
            console.log('Sending request to create todo...');
            const response = await fetch('/api/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.currentUserId,
                    input: text,  // Natural language mode
                    list_id: this.currentListId
                })
            });

            const result = await response.json();
            console.log('Response:', result);

            if (result.status === 'success') {
                input.value = '';

                // Add the new todo to the array immediately
                if (result.todo) {
                    this.todos.unshift(result.todo); // Add to beginning of array
                    console.log('Added new todo to array:', result.todo);
                }

                // Update UI immediately
                this.updateStats();
                this.renderTodos();

                this.showNotification('Todo created successfully', 'success');
                console.log('Todo created successfully');
            } else {
                this.showNotification(result.message || 'Failed to create todo', 'error');
                console.error('Failed to create todo:', result);
            }
        } catch (error) {
            console.error('Error creating todo:', error);
            this.showNotification('Failed to create todo', 'error');
        }
    }

    /**
     * Load todos from API
     */
    async loadTodos() {
        try {
            const params = new URLSearchParams({
                user_id: this.currentUserId,
                bucket: this.currentBucket
            });

            if (this.currentListId) {
                params.append('list_id', this.currentListId);
            }

            const response = await fetch(`/api/todos?${params}`);
            const result = await response.json();

            if (result.status === 'success') {
                this.todos = result.todos || [];
                this.updateStats();
                this.renderTodos();
            }
        } catch (error) {
            console.error('Error loading todos:', error);
            this.showNotification('Failed to load todos', 'error');
        }
    }

    /**
     * Load user's todo lists
     */
    async loadUserLists() {
        try {
            const response = await fetch(`/api/todos/lists?user_id=${this.currentUserId}`);
            const result = await response.json();

            if (result.status === 'success') {
                this.lists = result.lists || [];
                this.renderListsDropdown();
            }
        } catch (error) {
            console.error('Error loading lists:', error);
        }
    }

    /**
     * Render lists dropdown in sidebar
     */
    renderListsDropdown() {
        const dropdown = document.getElementById('todo-lists-dropdown');
        if (!dropdown) return;

        if (this.lists.length === 0) {
            dropdown.innerHTML = '<p class="text-xs text-gray-500 dark:text-gray-400 px-3 py-2">No lists yet</p>';
            return;
        }

        dropdown.innerHTML = this.lists.map(list => `
            <button class="w-full text-left px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md flex items-center"
                    data-list-id="${list.id}">
                <span class="w-3 h-3 rounded-full mr-2" style="background-color: ${list.color || '#10B981'}"></span>
                ${this.escapeHtml(list.name)}
            </button>
        `).join('');

        // Attach list click handlers
        dropdown.querySelectorAll('[data-list-id]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const listId = e.currentTarget.dataset.listId;
                this.currentListId = listId;

                // Find the list name for display
                const list = this.lists.find(l => l.id === listId);
                const listName = list ? list.name : 'List';

                // Show TODO area with this list's context
                this.showTodoArea();
                this.loadTodos();

                // Update header to show we're viewing a specific list
                this.updateHeaderForList(listName);

                // Highlight the active list
                dropdown.querySelectorAll('[data-list-id]').forEach(b => {
                    b.classList.remove('bg-gray-200', 'dark:bg-gray-700');
                });
                e.currentTarget.classList.add('bg-gray-200', 'dark:bg-gray-700');
            });
        });
    }

    /**
     * Render todos in current bucket
     */
    renderTodos() {
        const container = document.getElementById('todos-container');
        if (!container) {
            console.warn('todos-container not found');
            return;
        }

        // Filter todos by current bucket
        const filteredTodos = this.todos.filter(todo => {
            if (this.currentBucket === 'all') return true;
            return todo.bucket === this.currentBucket;
        });

        console.log(`Rendering ${filteredTodos.length} todos (total: ${this.todos.length}, bucket: ${this.currentBucket})`);

        if (filteredTodos.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <svg class="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                    </svg>
                    <p class="text-gray-500 dark:text-gray-400 text-sm">No todos in "${this.currentBucket}"</p>
                    <p class="text-gray-400 dark:text-gray-500 text-xs mt-2">Add one using the input above or switch to "all" to see all todos</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filteredTodos.map(todo => this.renderTodoItem(todo)).join('');

        // Attach event listeners to todo items
        this.attachTodoItemListeners();
    }

    /**
     * Render a single todo item
     */
    renderTodoItem(todo) {
        const priorityColors = {
            low: 'text-gray-400',
            medium: 'text-blue-500',
            high: 'text-orange-500',
            urgent: 'text-red-500'
        };

        const priorityColor = priorityColors[todo.priority] || 'text-gray-400';
        const isCompleted = todo.status === 'completed';

        return `
            <div class="todo-item bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                 data-todo-id="${todo.id}">
                <div class="flex items-start space-x-3">
                    <!-- Checkbox -->
                    <button class="todo-checkbox mt-0.5 flex-shrink-0" data-todo-id="${todo.id}">
                        ${isCompleted
                            ? '<svg class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>'
                            : '<svg class="w-5 h-5 text-gray-400 hover:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-width="2"></circle></svg>'
                        }
                    </button>

                    <!-- Todo content -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between">
                            <h3 class="text-sm font-medium ${isCompleted ? 'line-through text-gray-400' : 'text-gray-900 dark:text-white'}">
                                ${this.escapeHtml(todo.title)}
                            </h3>
                            <span class="ml-2 ${priorityColor}">
                                ${'!'.repeat(todo.priority === 'urgent' ? 2 : todo.priority === 'high' ? 1 : 0)}
                            </span>
                        </div>

                        <!-- Meta info -->
                        <div class="mt-1 flex items-center space-x-3 text-xs text-gray-500 dark:text-gray-400">
                            ${todo.due_date ? `
                                <span class="flex items-center">
                                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                                    </svg>
                                    ${this.formatDate(todo.due_date)}${todo.due_time ? ' ' + todo.due_time : ''}
                                </span>
                            ` : ''}
                            ${todo.tags && todo.tags.length > 0 ? `
                                <span class="flex items-center space-x-1">
                                    ${todo.tags.map(tag => `<span class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">#${this.escapeHtml(tag)}</span>`).join('')}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners to todo items
     */
    attachTodoItemListeners() {
        // Checkbox handlers
        document.querySelectorAll('.todo-checkbox').forEach(checkbox => {
            checkbox.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleTodoComplete(e.currentTarget.dataset.todoId);
            });
        });

        // Todo item click to open detail modal
        document.querySelectorAll('.todo-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.todo-checkbox')) {
                    this.openTodoModal(item.dataset.todoId);
                }
            });
        });
    }

    /**
     * Toggle todo completion status
     */
    async toggleTodoComplete(todoId) {
        try {
            const response = await fetch(`/api/todos/${todoId}/complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.currentUserId })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.loadTodos(); // Reload to update UI
            }
        } catch (error) {
            console.error('Error toggling todo:', error);
        }
    }

    /**
     * Update stats counters
     */
    updateStats() {
        this.stats.total = this.todos.length;
        this.stats.completed = this.todos.filter(t => t.status === 'completed').length;
        this.stats.pending = this.todos.filter(t => t.status === 'pending' || t.status === 'in_progress').length;
        this.stats.urgent = this.todos.filter(t => t.priority === 'urgent').length;

        // Update UI
        const totalEl = document.getElementById('todos-total-count');
        const completedEl = document.getElementById('todos-completed-count');
        const pendingEl = document.getElementById('todos-pending-count');
        const urgentEl = document.getElementById('todos-urgent-count');

        if (totalEl) totalEl.textContent = this.stats.total;
        if (completedEl) completedEl.textContent = this.stats.completed;
        if (pendingEl) pendingEl.textContent = this.stats.pending;
        if (urgentEl) urgentEl.textContent = this.stats.urgent;
    }

    /**
     * Open todo detail modal
     */
    openTodoModal(todoId) {
        const todo = this.todos.find(t => t.id === todoId);
        if (!todo) return;

        // Populate modal fields
        document.getElementById('todo-id').value = todo.id;
        document.getElementById('todo-title').value = todo.title;
        document.getElementById('todo-description').value = todo.description || '';
        document.getElementById('todo-priority').value = todo.priority;
        document.getElementById('todo-status').value = todo.status;
        document.getElementById('todo-due-date').value = todo.due_date || '';
        document.getElementById('todo-due-time').value = todo.due_time || '';
        document.getElementById('todo-tags').value = todo.tags ? todo.tags.join(', ') : '';

        // Show modal
        document.getElementById('todo-modal').classList.remove('hidden');
    }

    /**
     * Close todo detail modal
     */
    closeTodoModal() {
        document.getElementById('todo-modal').classList.add('hidden');
    }

    /**
     * Save todo from modal
     */
    async saveTodoModal() {
        const todoId = document.getElementById('todo-id').value;
        const title = document.getElementById('todo-title').value.trim();
        const description = document.getElementById('todo-description').value.trim();
        const priority = document.getElementById('todo-priority').value;
        const status = document.getElementById('todo-status').value;
        const dueDate = document.getElementById('todo-due-date').value;
        const dueTime = document.getElementById('todo-due-time').value;
        const tagsText = document.getElementById('todo-tags').value;

        if (!title) {
            this.showNotification('Title is required', 'error');
            return;
        }

        const tags = tagsText.split(',').map(t => t.trim()).filter(t => t);

        try {
            const response = await fetch(`/api/todos/${todoId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.currentUserId,
                    title,
                    description,
                    priority,
                    status,
                    due_date: dueDate || null,
                    due_time: dueTime || null,
                    tags
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.closeTodoModal();
                this.loadTodos();
                this.showNotification('Todo updated successfully', 'success');
            } else {
                this.showNotification(result.message || 'Failed to update todo', 'error');
            }
        } catch (error) {
            console.error('Error updating todo:', error);
            this.showNotification('Failed to update todo', 'error');
        }
    }

    /**
     * Delete todo from modal
     */
    async deleteTodoFromModal() {
        const todoId = document.getElementById('todo-id').value;

        if (!confirm('Are you sure you want to delete this todo?')) return;

        try {
            const response = await fetch(`/api/todos/${todoId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.currentUserId })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.closeTodoModal();
                this.loadTodos();
                this.showNotification('Todo deleted successfully', 'success');
            } else {
                this.showNotification(result.message || 'Failed to delete todo', 'error');
            }
        } catch (error) {
            console.error('Error deleting todo:', error);
            this.showNotification('Failed to delete todo', 'error');
        }
    }

    /**
     * Show create list modal
     */
    showCreateListModal() {
        document.getElementById('create-list-modal').classList.remove('hidden');
    }

    /**
     * Close create list modal
     */
    closeCreateListModal() {
        document.getElementById('create-list-modal').classList.add('hidden');
        // Reset form
        document.getElementById('list-name').value = '';
        document.getElementById('list-description').value = '';
        document.getElementById('list-color').value = '#3B82F6';
    }

    /**
     * Create new list
     */
    async createList() {
        const name = document.getElementById('list-name').value.trim();
        const description = document.getElementById('list-description').value.trim();
        const color = document.getElementById('list-color').value;

        if (!name) {
            this.showNotification('List name is required', 'error');
            return;
        }

        try {
            const response = await fetch('/api/todos/lists', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.currentUserId,
                    name,
                    description,
                    color
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.closeCreateListModal();
                this.loadUserLists();
                // Ensure dropdown is visible
                const dropdown = document.getElementById('todo-lists-dropdown');
                if (dropdown && dropdown.classList.contains('hidden')) {
                    dropdown.classList.remove('hidden');
                    // Rotate the expand icon
                    const todoNavBtn = document.querySelector('[data-list="todos"]');
                    const expandIcon = todoNavBtn?.querySelector('.expand-icon');
                    if (expandIcon) {
                        expandIcon.style.transform = 'rotate(180deg)';
                    }
                }
                this.showNotification('List created successfully', 'success');
            } else {
                this.showNotification(result.message || 'Failed to create list', 'error');
            }
        } catch (error) {
            console.error('Error creating list:', error);
            this.showNotification('Failed to create list', 'error');
        }
    }

    /**
     * Show TODO area and hide others
     */
    showTodoArea() {
        // Hide all areas
        document.querySelectorAll('[id$="-area"]').forEach(area => {
            area.classList.add('hidden');
        });

        // Show todo area
        const todoArea = document.getElementById('todos-area');
        if (todoArea) {
            todoArea.classList.remove('hidden');
        }

        // Update active nav item
        document.querySelectorAll('.sub-nav-item').forEach(item => {
            item.classList.remove('bg-gray-200', 'dark:bg-gray-700');
        });

        const todoNav = document.querySelector('[data-list="todos"]');
        if (todoNav) {
            todoNav.classList.add('bg-gray-200', 'dark:bg-gray-700');
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Simple console notification for now
        // TODO: Implement toast notifications
        if (type === 'error') {
            console.error(message);
        } else {
            console.log(message);
        }
    }

    /**
     * Format date for display
     */
    formatDate(dateStr) {
        const date = new Date(dateStr);
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);

        if (date.toDateString() === today.toDateString()) return 'Today';
        if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow';

        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Update header to show we're viewing a specific list
     */
    updateHeaderForList(listName) {
        const titleEl = document.getElementById('todos-header-title');
        const subtitleEl = document.getElementById('todos-header-subtitle');
        const backBtn = document.getElementById('back-to-all-lists-btn');

        if (titleEl) titleEl.textContent = listName;
        if (subtitleEl) subtitleEl.textContent = 'Tasks in this list';
        if (backBtn) backBtn.classList.remove('hidden');

        // Hide bucket tabs when viewing a specific list
        const bucketTabsContainer = document.querySelector('.bucket-tab')?.parentElement;
        if (bucketTabsContainer) {
            bucketTabsContainer.style.display = 'none';
        }
    }

    /**
     * Show all lists view (reset to default)
     */
    showAllLists() {
        this.currentListId = null;

        const titleEl = document.getElementById('todos-header-title');
        const subtitleEl = document.getElementById('todos-header-subtitle');
        const backBtn = document.getElementById('back-to-all-lists-btn');

        if (titleEl) titleEl.textContent = 'TODO Lists';
        if (subtitleEl) subtitleEl.textContent = 'Manage your tasks with natural language input and smart organization';
        if (backBtn) backBtn.classList.add('hidden');

        // Show bucket tabs again
        const bucketTabsContainer = document.querySelector('.bucket-tab')?.parentElement;
        if (bucketTabsContainer) {
            bucketTabsContainer.style.display = 'flex';
        }

        // Clear list highlighting
        const dropdown = document.getElementById('todo-lists-dropdown');
        if (dropdown) {
            dropdown.querySelectorAll('[data-list-id]').forEach(b => {
                b.classList.remove('bg-gray-200', 'dark:bg-gray-700');
            });
        }

        // Reload todos without list filter
        this.loadTodos();
    }
}

// Initialize TODO UI when DOM is ready
// Handle both cases: if DOM is already loaded or if it's still loading
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('Initializing TodoUI via DOMContentLoaded event');
        window.todoUI = new TodoUI();
    });
} else {
    // DOM is already loaded (script is at bottom of page)
    console.log('Initializing TodoUI immediately (DOM already loaded)');
    window.todoUI = new TodoUI();
}
