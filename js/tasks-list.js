/**
 * Tasks List — renders all tasks across all opportunities.
 *
 * Displays inside #tasks-area (dedicated full-page panel).
 * Supports status filter pills and keyword search.
 */

const TASKS_LIST_STATUS_COLORS = {
    pending:     'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    completed:   'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
};

class TasksList {
    constructor() {
        this._items = [];
        this._filter = 'all';   // 'all' | 'pending' | 'in_progress' | 'completed'
        this._search = '';
        this._filtersWired = false;
        this._loading = false;
    }

    // -------------------------------------------------------------------------
    // Entry point called by navigateTo('tasks')
    // -------------------------------------------------------------------------

    show() {
        this._wireFilters();
        this._load();
    }

    // -------------------------------------------------------------------------
    // Filter / search wiring (once per page-load)
    // -------------------------------------------------------------------------

    _wireFilters() {
        if (this._filtersWired) return;
        this._filtersWired = true;

        // Status filter pills
        document.querySelectorAll('.tasks-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._filter = btn.dataset.statusFilter;
                document.querySelectorAll('.tasks-filter-btn').forEach(b => {
                    const active = b === btn;
                    b.classList.toggle('bg-blue-600', active);
                    b.classList.toggle('text-white', active);
                    b.classList.toggle('text-gray-600', !active);
                    b.classList.toggle('dark:text-gray-400', !active);
                    b.classList.toggle('hover:bg-gray-100', !active);
                    b.classList.toggle('dark:hover:bg-gray-700', !active);
                });
                this._render();
            });
        });

        // Keyword search
        const searchInput = document.getElementById('tasks-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                this._search = searchInput.value.trim();
                this._render();
            });
        }

        // Refresh button — forces a reload even if one is in progress
        const refreshBtn = document.getElementById('tasks-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this._loading = false;
                this._load();
            });
        }

        // Opportunity banner clicks — delegated on the cards container
        const container = document.getElementById('tasks-cards-container');
        if (container) {
            container.addEventListener('click', (e) => {
                const banner = e.target.closest('.tasks-opp-banner');
                if (!banner) return;
                const oppId  = banner.dataset.opportunityId;
                const taskId = banner.dataset.taskId;
                if (oppId) this._openOpportunity(oppId, taskId);
            });
        }
    }

    async _openOpportunity(opportunityId, taskId) {
        try {
            const res = await fetch(`/api/opportunities/${opportunityId}`);
            if (!res.ok) return;
            const data = await res.json();
            const opp = data.opportunity || data;
            if (!opp || !opp.id) return;
            if (window.app?.navigation) window.app.navigation.navigateTo('opportunities');
            if (window.app?.opportunitiesManager) window.app.opportunitiesManager.showOpportunityDetail(opp);
            // After navigation + async task load, scroll to and highlight the originating task row
            if (taskId) this._highlightOpportunityTask(taskId);
        } catch (err) {
            console.error('[TasksList] failed to open opportunity:', err);
        }
    }

    // Poll for the task row to appear in the opportunity detail table, then scroll+highlight.
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

    // Navigate to the Tasks panel and highlight a specific task card's opportunity banner.
    highlightTaskCard(taskId) {
        if (window.app?.navigation) window.app.navigation.navigateTo('tasks');
        // Tasks may still be loading; poll until the card renders.
        let attempts = 0;
        const poll = setInterval(() => {
            const banner = document.querySelector(`#tasks-cards-container .tasks-opp-banner[data-task-id="${taskId}"]`);
            if (banner || ++attempts >= 30) {
                clearInterval(poll);
                if (!banner) return;
                banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                this._highlight(banner);
            }
        }, 100);
    }

    // Briefly highlight an element with a yellow flash for 3 seconds.
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
            const res = await fetch('/api/all-tasks');
            if (!res.ok) {
                console.error(`[TasksList] /api/all-tasks returned HTTP ${res.status}`);
                this._renderError();
                return;
            }
            const data = await res.json();
            this._items = data.tasks || [];
            this._render();
        } catch (err) {
            console.error('[TasksList] load error:', err);
            this._renderError();
        } finally {
            this._loading = false;
        }
    }

    // -------------------------------------------------------------------------
    // Rendering
    // -------------------------------------------------------------------------

    _renderLoading() {
        const container = document.getElementById('tasks-cards-container');
        if (container) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12 text-gray-400 dark:text-gray-500">Loading tasks…</div>`;
        }
        this._updateStats(null, null, null, null);
    }

    _renderError() {
        const container = document.getElementById('tasks-cards-container');
        if (container) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12 text-red-500">Failed to load tasks.</div>`;
        }
    }

    _render() {
        const pending    = this._items.filter(t => t.status === 'pending').length;
        const inProgress = this._items.filter(t => t.status === 'in_progress').length;
        const completed  = this._items.filter(t => t.status === 'completed').length;
        this._updateStats(this._items.length, pending, inProgress, completed);

        const container = document.getElementById('tasks-cards-container');
        if (!container) return;

        const filtered = this._filtered();

        if (filtered.length === 0) {
            const msg = this._items.length === 0
                ? 'No tasks found. Tasks are created automatically when opportunities move through the pipeline.'
                : 'No tasks match the current filter.';
            container.innerHTML = `
                <div class="col-span-full text-center py-12 text-gray-400 dark:text-gray-500">${msg}</div>`;
            return;
        }

        container.innerHTML = filtered.map(t => this._card(t)).join('');
    }

    _filtered() {
        return this._items.filter(t => {
            if (this._filter !== 'all' && t.status !== this._filter) return false;
            if (this._search) {
                const q = this._search.toLowerCase();
                return (t.name || '').toLowerCase().includes(q) ||
                       (t.opportunity_name || t.opportunity_id || '').toLowerCase().includes(q) ||
                       (t.description || '').toLowerCase().includes(q) ||
                       (t.assigned_to || '').toLowerCase().includes(q);
            }
            return true;
        });
    }

    _updateStats(total, pending, inProgress, completed) {
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val === null ? '—' : val;
        };
        set('tasks-stat-total',       total);
        set('tasks-stat-pending',     pending);
        set('tasks-stat-in-progress', inProgress);
        set('tasks-stat-completed',   completed);
    }

    _card(t) {
        const statusClass = TASKS_LIST_STATUS_COLORS[t.status] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
        const statusLabel = (t.status || 'pending').replace('_', ' ');
        const progress    = t.progress || 0;
        const oppLabel    = this._esc(t.opportunity_name || t.opportunity_id || 'Unknown Opportunity');

        return `
        <div data-task-id="${this._esc(t.id)}" class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm overflow-hidden">
            <button data-opportunity-id="${this._esc(t.opportunity_id)}" data-task-id="${this._esc(t.id)}"
                    class="tasks-opp-banner w-full flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors text-left border-b border-blue-100 dark:border-blue-800">
                <svg class="w-3.5 h-3.5 text-blue-500 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                </svg>
                <span class="text-xs font-medium text-blue-700 dark:text-blue-300 truncate">${oppLabel}</span>
            </button>
            <div class="p-4">
            <div class="flex items-start justify-between gap-3 mb-2">
                <div class="flex-1 min-w-0">
                    <div class="font-semibold text-gray-900 dark:text-white">${this._esc(t.name)}</div>
                </div>
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${statusClass}">
                    ${this._esc(statusLabel)}
                </span>
            </div>

            ${t.description ? `<p class="text-sm text-gray-600 dark:text-gray-300 mb-3">${this._esc(t.description)}</p>` : ''}

            <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 text-xs">
                <div>
                    <div class="text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wide" style="font-size:10px">Start</div>
                    <div class="text-gray-700 dark:text-gray-300">${this._esc(t.start_date || '—')}</div>
                </div>
                <div>
                    <div class="text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wide" style="font-size:10px">Due</div>
                    <div class="text-gray-700 dark:text-gray-300">${this._esc(t.end_date || '—')}</div>
                </div>
                ${t.assigned_to ? `
                <div>
                    <div class="text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wide" style="font-size:10px">Assigned To</div>
                    <div class="text-gray-700 dark:text-gray-300">${this._esc(t.assigned_to)}</div>
                </div>` : ''}
            </div>

            ${progress > 0 ? `
            <div class="mt-3">
                <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                    <span>Progress</span><span>${progress}%</span>
                </div>
                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                    <div class="bg-blue-500 h-1.5 rounded-full" style="width:${progress}%"></div>
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

    // Called by old nav.js via _showTrackingPanel, which shows lists-interface-area
    // and hides tasks-area before calling this. Fix the area visibility here.
    openPanel() {
        document.getElementById('lists-interface-area')?.classList.add('hidden');
        document.getElementById('tasks-area')?.classList.remove('hidden');
        this.show();
    }
    closePanel() {}
}

window.tasksList = new TasksList();

// Auto-load whenever tasks-area becomes visible, regardless of how navigation triggers it
(function () {
    const area = document.getElementById('tasks-area');
    if (!area) return;
    const observer = new MutationObserver(() => {
        if (!area.classList.contains('hidden')) {
            window.tasksList.show();
        }
    });
    observer.observe(area, { attributes: true, attributeFilter: ['class'] });
}());
