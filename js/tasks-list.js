/**
 * Tasks List — renders all tasks across all opportunities.
 *
 * Displays inside #lists-items-panel within the Lists Interface area.
 * Uses a card-per-item layout (no horizontal scrolling required).
 */

const TASK_STATUS_COLORS = {
    pending:     'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    completed:   'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
};

class TasksList {
    constructor() {
        this._items = [];
    }

    // -------------------------------------------------------------------------
    // Panel open / close
    // -------------------------------------------------------------------------

    openPanel(listId, listName) {
        const panel = document.getElementById('lists-items-panel');
        if (!panel) return;

        panel.classList.remove('hidden');
        const title = panel.querySelector('#lists-items-panel-title');
        if (title) title.textContent = listName;
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

        this._load();
    }

    closePanel() {
        document.getElementById('lists-items-panel')?.classList.add('hidden');
        this._items = [];
    }

    // -------------------------------------------------------------------------
    // Data
    // -------------------------------------------------------------------------

    async _load() {
        const tbody = document.getElementById('tracking-items-tbody');
        if (tbody) tbody.innerHTML = '<tr><td class="px-4 py-6 text-center text-sm text-gray-400">Loading…</td></tr>';

        try {
            const res = await fetch('/api/all-tasks');
            const data = await res.json();
            this._items = data.tasks || [];
            this._render();
        } catch {
            if (tbody) tbody.innerHTML = '<tr><td class="px-4 py-6 text-center text-sm text-red-500">Failed to load tasks.</td></tr>';
        }
    }

    // -------------------------------------------------------------------------
    // Render
    // -------------------------------------------------------------------------

    _render() {
        const tbody   = document.getElementById('tracking-items-tbody');
        const header  = document.getElementById('tracking-items-header');
        const addForm = document.getElementById('tracking-add-form-container');
        if (!tbody) return;

        // Tasks list is read-only — hide the add form and column header
        if (header)  header.classList.add('hidden');
        if (addForm) addForm.classList.add('hidden');

        if (this._items.length === 0) {
            tbody.innerHTML = `<tr><td class="px-4 py-10 text-center text-sm text-gray-400 dark:text-gray-500">No tasks found.</td></tr>`;
            return;
        }

        const cards = this._items.map(t => this._card(t)).join('');
        tbody.innerHTML = `<tr><td class="p-4"><div class="space-y-3">${cards}</div></td></tr>`;
    }

    _card(t) {
        const statusClass = TASK_STATUS_COLORS[t.status] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
        const statusLabel = (t.status || 'pending').replace('_', ' ');
        const progress = t.progress || 0;

        return `
        <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 shadow-sm">
            <div class="flex items-start justify-between gap-3 mb-2">
                <div class="flex-1 min-w-0">
                    <div class="font-semibold text-gray-900 dark:text-white">${this._esc(t.name)}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        ${this._esc(t.opportunity_name || t.opportunity_id || '')}
                    </div>
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
        </div>`;
    }

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = String(text || '');
        return d.innerHTML;
    }
}

window.tasksList = new TasksList();
