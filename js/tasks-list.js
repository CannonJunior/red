/**
 * Tasks List — renders all tasks across all opportunities as a Kanban board.
 *
 * Displays inside #tasks-area (dedicated full-page panel).
 * Columns driven by /api/settings/categories task_statuses config.
 * Cards are draggable between columns; dropping updates task status via the API.
 *
 * Search optimization (#10): _render() builds all cards once; search filtering
 * adds/removes the `hidden` class in _applySearch() without rebuilding innerHTML.
 * Debounce (#7): search input waits 150ms of inactivity before applying the filter.
 */

/** Simple debounce — delays fn by ms after the last call. */
function _taskListDebounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

class TasksList {
    constructor() {
        this._items    = [];
        this._columns  = [];   // loaded from /api/settings/categories
        this._search   = '';
        this._wired    = false;
        this._loading  = false;
        this._dragging = false;  // suppresses click-through during drag
    }

    // -------------------------------------------------------------------------
    // Entry point
    // -------------------------------------------------------------------------

    show() {
        this._wire();
        this._load();
    }

    // -------------------------------------------------------------------------
    // One-time event wiring (targets stable elements; survives board rebuilds)
    // -------------------------------------------------------------------------

    _wire() {
        if (this._wired) return;
        this._wired = true;

        // Keyword search — debounced, applies via CSS show/hide only (no DOM rebuild)
        const searchInput = document.getElementById('tasks-search-input');
        if (searchInput) {
            const debouncedSearch = _taskListDebounce(() => this._applySearch(), 150);
            searchInput.addEventListener('input', () => {
                this._search = searchInput.value.trim();
                debouncedSearch();
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('tasks-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this._loading = false;
                this._load();
            });
        }

        // Opportunity banner clicks — delegated on the board (survives board rebuilds)
        const board = document.getElementById('tasks-kanban-board');
        if (board) {
            board.addEventListener('click', (e) => {
                if (this._dragging) return;
                const banner = e.target.closest('.tasks-opp-banner');
                if (!banner) return;
                const oppId  = banner.dataset.opportunityId;
                const taskId = banner.dataset.taskId;
                if (oppId) this._openOpportunity(oppId, taskId);
            });
        }
    }

    // -------------------------------------------------------------------------
    // Drag-and-drop — wired after every _render() because innerHTML replaces DOM
    // -------------------------------------------------------------------------

    _wireDragAndDrop() {
        const board = document.getElementById('tasks-kanban-board');
        if (!board) return;

        board.querySelectorAll('.task-kanban-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                this._dragging = true;
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', card.dataset.taskId);
                card.classList.add('opacity-50', 'ring-2', 'ring-blue-400');
            });
            card.addEventListener('dragend', () => {
                this._dragging = false;
                card.classList.remove('opacity-50', 'ring-2', 'ring-blue-400');
            });
        });

        board.querySelectorAll('.tasks-col-body').forEach(col => {
            col.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                col.classList.add('ring-2', 'ring-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');
            });
            col.addEventListener('dragleave', (e) => {
                if (col.contains(e.relatedTarget)) return;
                col.classList.remove('ring-2', 'ring-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');
            });
            col.addEventListener('drop', (e) => {
                e.preventDefault();
                col.classList.remove('ring-2', 'ring-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20');
                const taskId    = e.dataTransfer.getData('text/plain');
                const newStatus = col.dataset.status;
                if (taskId && newStatus) this._moveTask(taskId, newStatus);
            });
        });
    }

    // -------------------------------------------------------------------------
    // Move task (optimistic update + API call; triggers full re-render)
    // -------------------------------------------------------------------------

    async _moveTask(taskId, newStatus) {
        const task = this._items.find(t => String(t.id) === String(taskId));
        if (!task || task.status === newStatus) return;

        const prevStatus = task.status;
        task.status      = newStatus;  // optimistic
        this._render();

        try {
            const res = await fetch(`/api/tasks/${taskId}`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ status: newStatus }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
        } catch (err) {
            console.error('[TasksList] failed to update task status:', err);
            task.status = prevStatus;  // revert
            this._render();
        }
    }

    // -------------------------------------------------------------------------
    // Navigation helpers
    // -------------------------------------------------------------------------

    async _openOpportunity(opportunityId, taskId) {
        try {
            const res = await fetch(`/api/opportunities/${opportunityId}`);
            if (!res.ok) return;
            const data = await res.json();
            const opp  = data.opportunity || data;
            if (!opp || !opp.id) return;
            if (window.app?.navigation) window.app.navigation.navigateTo('opportunities');
            if (window.app?.opportunitiesManager) window.app.opportunitiesManager.showOpportunityDetail(opp);
            if (taskId) this._highlightOpportunityTask(taskId);
        } catch (err) {
            console.error('[TasksList] failed to open opportunity:', err);
        }
    }

    _highlightOpportunityTask(taskId) {
        let attempts = 0;
        const poll = setInterval(() => {
            const row = document.querySelector(`#tasks-table-body tr[data-task-id="${taskId}"]`);
            if (row || ++attempts >= 25) {
                clearInterval(poll);
                if (!row) return;
                row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                this._highlight(row.querySelector('td'));
            }
        }, 100);
    }

    highlightTaskCard(taskId) {
        if (window.app?.navigation) window.app.navigation.navigateTo('tasks');
        let attempts = 0;
        const poll = setInterval(() => {
            const banner = document.querySelector(`#tasks-kanban-board .tasks-opp-banner[data-task-id="${taskId}"]`);
            if (banner || ++attempts >= 30) {
                clearInterval(poll);
                if (!banner) return;
                banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                this._highlight(banner);
            }
        }, 100);
    }

    _highlight(el) {
        if (!el) return;
        el.style.transition = 'background-color 0.4s ease';
        el.style.backgroundColor = '#fef08a';
        setTimeout(() => {
            el.style.transition = 'background-color 1s ease';
            el.style.backgroundColor = '';
        }, 3000);
    }

    // -------------------------------------------------------------------------
    // Data
    // -------------------------------------------------------------------------

    async _load() {
        if (this._loading) return;
        this._loading = true;
        this._renderLoading();
        try {
            const [tasksRes, catRes] = await Promise.all([
                fetch('/api/all-tasks'),
                fetch('/api/settings/categories'),
            ]);
            if (!tasksRes.ok) {
                console.error(`[TasksList] /api/all-tasks returned HTTP ${tasksRes.status}`);
                this._renderError();
                return;
            }
            const tasksData = await tasksRes.json();
            this._items = tasksData.tasks || [];

            if (catRes.ok) {
                const catData = await catRes.json();
                this._columns = (catData.task_statuses || []).slice().sort((a, b) => a.order - b.order);
            }
            if (!this._columns.length) {
                this._columns = [
                    { slug: 'not_started', label: 'Not Started', headerClass: 'bg-gray-400',   colorClass: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300' },
                    { slug: 'in_progress', label: 'In Progress', headerClass: 'bg-blue-500',   colorClass: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300' },
                    { slug: 'pending',     label: 'Pending',     headerClass: 'bg-yellow-500', colorClass: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300' },
                    { slug: 'completed',   label: 'Completed',   headerClass: 'bg-green-500',  colorClass: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' },
                ];
            }
            this._render();
        } catch (err) {
            console.error('[TasksList] load error:', err);
            this._renderError();
        } finally {
            this._loading = false;
        }
    }

    async applyCategories() {
        try {
            const res = await fetch('/api/settings/categories');
            if (res.ok) {
                const data = await res.json();
                this._columns = (data.task_statuses || []).slice().sort((a, b) => a.order - b.order);
            }
        } catch (_) { /* ignore */ }
        this._render();
    }

    // -------------------------------------------------------------------------
    // Rendering
    // -------------------------------------------------------------------------

    _renderLoading() {
        const board = document.getElementById('tasks-kanban-board');
        if (board) board.innerHTML = `<div class="flex items-center justify-center w-full h-32 text-gray-400 dark:text-gray-500">Loading tasks…</div>`;
        this._updateStats(null, null, null, null, null);
    }

    _renderError() {
        const board = document.getElementById('tasks-kanban-board');
        if (board) board.innerHTML = `<div class="flex items-center justify-center w-full h-32 text-red-500">Failed to load tasks.</div>`;
    }

    _render() {
        const notStarted = this._items.filter(t => t.status === 'not_started').length;
        const inProgress = this._items.filter(t => t.status === 'in_progress').length;
        const pending    = this._items.filter(t => t.status === 'pending').length;
        const completed  = this._items.filter(t => t.status === 'completed').length;
        this._updateStats(this._items.length, notStarted, inProgress, pending, completed);

        const board = document.getElementById('tasks-kanban-board');
        if (!board) return;

        // Render ALL items — search filtering is done by _applySearch() via CSS,
        // avoiding repeated DOM rebuilds on every keystroke.
        board.innerHTML = this._columns.map(col => this._buildColumn(col)).join('');

        this._wireDragAndDrop();
        this._applySearch();   // re-apply current search after rebuild
    }

    _buildColumn(col) {
        const cards = this._items.filter(t => t.status === col.slug);
        const hasCards = cards.length > 0;

        return `
        <div class="flex flex-col w-72 flex-shrink-0 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700" style="height: calc(100vh - 180px)">
            <div class="${col.headerClass} rounded-t-xl px-4 py-3 flex items-center justify-between">
                <span class="text-white text-sm font-semibold">${this._esc(col.label)}</span>
                <span class="tasks-col-count bg-white/20 text-white text-xs font-bold px-2 py-0.5 rounded-full">${cards.length}</span>
            </div>
            <div class="tasks-col-body flex-1 overflow-y-auto p-2 space-y-2 rounded-b-xl transition-colors"
                 data-status="${this._esc(col.slug)}">
                <div class="tasks-col-empty text-center py-8 text-gray-400 dark:text-gray-500 text-xs select-none ${hasCards ? 'hidden' : ''}">Drop tasks here</div>
                ${cards.map(t => this._card(t, col)).join('')}
            </div>
        </div>`;
    }

    /**
     * Apply the current search filter by toggling CSS visibility on existing cards.
     * Updating count badges and empty-state messages as needed.
     * No DOM rebuild — O(n) class toggle only.
     */
    _applySearch() {
        const q     = this._search.toLowerCase();
        const board = document.getElementById('tasks-kanban-board');
        if (!board) return;

        board.querySelectorAll('.tasks-col-body').forEach(colBody => {
            let visible = 0;

            colBody.querySelectorAll('.task-kanban-card').forEach(card => {
                const match = !q || card.dataset.search.toLowerCase().includes(q);
                card.classList.toggle('hidden', !match);
                if (match) visible++;
            });

            // Update count badge (in the sibling header div)
            const badge = colBody.previousElementSibling?.querySelector('.tasks-col-count');
            if (badge) badge.textContent = visible;

            // Show/hide empty state
            const empty = colBody.querySelector('.tasks-col-empty');
            if (empty) empty.classList.toggle('hidden', visible > 0);
        });
    }

    _updateStats(total, notStarted, inProgress, pending, completed) {
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val === null ? '—' : val;
        };
        set('tasks-stat-total',       total);
        set('tasks-stat-not-started', notStarted);
        set('tasks-stat-in-progress', inProgress);
        set('tasks-stat-pending',     pending);
        set('tasks-stat-completed',   completed);
    }

    _card(t, col) {
        const progress   = t.progress || 0;
        const oppLabel   = this._esc(t.opportunity_name || t.opportunity_id || 'Unknown Opportunity');
        // data-search holds all searchable text for CSS-free filtering in _applySearch()
        const searchText = this._esc(
            [t.name, t.opportunity_name, t.opportunity_id, t.description, t.assigned_to]
                .filter(Boolean).join(' ')
        );

        return `
        <div data-task-id="${this._esc(t.id)}"
             data-status="${this._esc(t.status)}"
             data-search="${searchText}"
             draggable="true"
             class="task-kanban-card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                    rounded-lg shadow-sm overflow-hidden cursor-grab active:cursor-grabbing
                    hover:shadow-md hover:border-blue-300 dark:hover:border-blue-600 transition-all select-none">

            <div class="flex items-stretch border-b border-blue-100 dark:border-blue-800">
                <div class="flex items-center px-1.5 text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-400 bg-blue-50 dark:bg-blue-900/30">
                    <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 10 16">
                        <circle cx="2" cy="2" r="1.5"/><circle cx="8" cy="2" r="1.5"/>
                        <circle cx="2" cy="8" r="1.5"/><circle cx="8" cy="8" r="1.5"/>
                        <circle cx="2" cy="14" r="1.5"/><circle cx="8" cy="14" r="1.5"/>
                    </svg>
                </div>
                <button data-opportunity-id="${this._esc(t.opportunity_id)}" data-task-id="${this._esc(t.id)}"
                        class="tasks-opp-banner flex-1 flex items-center gap-2 px-2 py-1.5
                               bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50
                               transition-colors text-left">
                    <svg class="w-3 h-3 text-blue-500 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                    </svg>
                    <span class="text-xs font-medium text-blue-700 dark:text-blue-300 truncate">${oppLabel}</span>
                </button>
            </div>

            <div class="p-3">
                <div class="font-semibold text-gray-900 dark:text-white text-sm mb-2">${this._esc(t.name)}</div>

                ${t.description ? `<p class="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2">${this._esc(t.description)}</p>` : ''}

                <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400 mb-2">
                    ${t.start_date  ? `<span>Start: ${this._esc(t.start_date)}</span>` : ''}
                    ${t.end_date    ? `<span>Due: ${this._esc(t.end_date)}</span>` : ''}
                    ${t.assigned_to ? `<span>→ ${this._esc(t.assigned_to)}</span>` : ''}
                </div>

                ${progress > 0 ? `
                <div>
                    <div class="flex items-center justify-between text-xs text-gray-400 mb-0.5">
                        <span>Progress</span><span>${progress}%</span>
                    </div>
                    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1">
                        <div class="bg-blue-500 h-1 rounded-full" style="width:${progress}%"></div>
                    </div>
                </div>` : ''}
            </div>
        </div>`;
    }

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = String(text || '');
        return d.innerHTML;
    }

    openPanel() {
        document.getElementById('lists-interface-area')?.classList.add('hidden');
        document.getElementById('tasks-area')?.classList.remove('hidden');
        this.show();
    }
    closePanel() {}
}

window.tasksList = new TasksList();

(function () {
    const area = document.getElementById('tasks-area');
    if (!area) return;
    const observer = new MutationObserver(() => {
        if (!area.classList.contains('hidden')) window.tasksList.show();
    });
    observer.observe(area, { attributes: true, attributeFilter: ['class'] });
}());
