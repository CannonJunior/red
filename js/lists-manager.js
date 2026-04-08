/**
 * Lists Manager
 *
 * Manages the Lists Interface: visibility toggles, CSV/JSON export,
 * delete, and add for all data collections in the app.
 *
 * Built-in lists (Opportunities, Career Analysis) are always present.
 * Custom lists are stored in localStorage under 'lists_registry'.
 */

class ListsManager {
    constructor() {
        // Built-in lists that always exist and map to known API endpoints
        this._builtins = [
            {
                id: 'opportunities',
                name: 'Opportunities',
                description: 'GovCon opportunity pipeline',
                type: 'builtin',
                apiEndpoint: '/api/opportunities',
                countKey: null,
            },
            {
                id: 'career-analysis',
                name: 'Career Analysis',
                description: 'Career-monster academic hiring analysis',
                type: 'builtin',
                apiEndpoint: '/api/career/list',
                countKey: 'results',
            },
            {
                id: 'proposals',
                name: 'Proposals',
                description: 'Active proposal submissions — auto-created when opportunity reaches 04-In Progress',
                type: 'builtin',
                apiEndpoint: '/api/proposal-items',
                countKey: 'items',
                viewable: true,
            },
            {
                id: 'bnb',
                name: 'Bid No-Bid',
                description: 'Bid/No-Bid decisions — auto-created when opportunity reaches 03-Bid Decision',
                type: 'builtin',
                apiEndpoint: '/api/bnb-items',
                countKey: 'items',
                viewable: true,
            },
            {
                id: 'hotwash',
                name: 'Hotwash',
                description: 'Post-action reviews — auto-created when opportunity reaches 06/07/08/09 stages',
                type: 'builtin',
                apiEndpoint: '/api/hotwash-items',
                countKey: 'items',
                viewable: true,
            },
            {
                id: 'tasks',
                name: 'Tasks',
                description: 'All tasks across all opportunities — auto-created from pipeline events',
                type: 'builtin',
                apiEndpoint: '/api/all-tasks',
                countKey: 'tasks',
                viewable: true,
            },
            {
                id: 'todos',
                name: 'TODO Lists',
                description: 'Task and checklist collections',
                type: 'builtin',
                apiEndpoint: '/api/todos',
                countKey: 'lists',
            },
        ];

        this._visibilityKey = 'lists_visibility';
        this._registryKey  = 'lists_registry';
        this._setupModalHandlers();
    }

    // -------------------------------------------------------------------------
    // Public entry point called by navigation
    // -------------------------------------------------------------------------

    async load() {
        this._render([]);  // show loading state immediately
        const lists = await this._getLists();
        this._render(lists);
    }

    // -------------------------------------------------------------------------
    // Data helpers
    // -------------------------------------------------------------------------

    /** Return merged list of builtins + custom registry entries. */
    _getLists() {
        const custom = JSON.parse(localStorage.getItem(this._registryKey) || '[]');
        return [...this._builtins, ...custom];
    }

    _visibility() {
        return JSON.parse(localStorage.getItem(this._visibilityKey) || '{}');
    }

    _setVisible(id, visible) {
        const v = this._visibility();
        v[id] = visible;
        localStorage.setItem(this._visibilityKey, JSON.stringify(v));
        this._applySidebarVisibility(id, visible);
    }

    /**
     * Sidebar element selectors keyed by list id.
     * Each entry is an array of CSS selectors whose elements are shown/hidden.
     */
    _sidebarSelectors() {
        return {
            'opportunities':  ['.sub-nav-item[data-list="opportunities"]', '#opportunities-list'],
            'career-analysis': ['.sub-nav-item[data-list="career-analysis"]'],
            'proposals':       ['.sub-nav-item[data-list="proposals"]'],
            'bnb':             ['.sub-nav-item[data-list="bnb"]'],
            'hotwash':         ['.sub-nav-item[data-list="hotwash"]'],
            'tasks':           ['.sub-nav-item[data-list="tasks"]'],
            'todos':           ['.sub-nav-item[data-list="todos"]',         '#todo-lists-dropdown'],
        };
    }

    _applySidebarVisibility(id, visible) {
        const map = this._sidebarSelectors();
        const selectors = map[id];
        if (!selectors) return;
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                el.style.display = visible ? '' : 'none';
            });
        });
    }

    /** Apply stored visibility to all known sidebar items on load. */
    _syncSidebarVisibility() {
        const vis = this._visibility();
        const map = this._sidebarSelectors();
        Object.entries(map).forEach(([id, selectors]) => {
            const visible = vis[id] !== false; // default visible
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => {
                    el.style.display = visible ? '' : 'none';
                });
            });
        });
    }

    /** Fetch item count for a list. Returns null on failure. */
    async _fetchCount(list) {
        try {
            const res = await fetch(list.apiEndpoint);
            if (!res.ok) return null;
            const data = await res.json();
            if (list.countKey) {
                return Array.isArray(data[list.countKey]) ? data[list.countKey].length : null;
            }
            // Top-level array or object with 'opportunities' key
            if (Array.isArray(data)) return data.length;
            if (data.opportunities) return data.opportunities.length;
            if (data.results) return data.results.length;
            return null;
        } catch {
            return null;
        }
    }

    /** Fetch full data for a list (for export). */
    async _fetchData(list) {
        const res = await fetch(list.apiEndpoint);
        const data = await res.json();
        if (list.countKey && Array.isArray(data[list.countKey])) return data[list.countKey];
        if (Array.isArray(data)) return data;
        if (data.opportunities) return data.opportunities;
        if (data.results) return data.results;
        return data;
    }

    // -------------------------------------------------------------------------
    // Rendering
    // -------------------------------------------------------------------------

    _render(lists) {
        const tbody = document.getElementById('lists-table-body');
        if (!tbody) return;

        if (lists.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-5 py-10 text-center text-sm text-gray-400 dark:text-gray-500">
                        No lists found. Click <strong>Add List</strong> to create one.
                    </td>
                </tr>`;
            return;
        }

        const vis = this._visibility();

        tbody.innerHTML = lists.map(list => {
            const isVisible = vis[list.id] !== false;  // default visible
            return `
                <tr class="border-b border-gray-100 dark:border-gray-700 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                    <td class="px-5 py-4">
                        <div class="font-medium text-gray-900 dark:text-white">${this._esc(list.name)}</div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${this._esc(list.description || '')}</div>
                    </td>
                    <td class="px-5 py-4">
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                            ${list.type === 'builtin'
                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                                : 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'}">
                            ${list.type === 'builtin' ? 'Built-in' : 'Custom'}
                        </span>
                    </td>
                    <td class="px-5 py-4 text-right text-gray-600 dark:text-gray-400 tabular-nums" id="count-${list.id}">
                        <span class="text-gray-300 dark:text-gray-600">—</span>
                    </td>
                    <td class="px-5 py-4">
                        <div class="flex justify-center">
                            <label class="relative inline-flex items-center cursor-pointer">
                                <input type="checkbox" class="list-visibility-toggle sr-only"
                                    data-list-id="${list.id}" ${isVisible ? 'checked' : ''}>
                                <div class="list-vis-track w-10 h-5 rounded-full transition-colors ${isVisible ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}"></div>
                                <div class="list-vis-thumb absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${isVisible ? 'translate-x-5' : ''}"></div>
                            </label>
                        </div>
                    </td>
                    <td class="px-5 py-4">
                        <div class="flex items-center justify-end gap-2">
                            ${list.viewable ? `
                            <button class="list-view-btn text-xs px-2.5 py-1 rounded border border-indigo-300 dark:border-indigo-700
                                text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors font-medium"
                                data-list-id="${list.id}" data-list-name="${this._esc(list.name)}">View</button>
                            ` : ''}
                            <button class="list-export-csv text-xs px-2.5 py-1 rounded border border-gray-300 dark:border-gray-600
                                text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                data-list-id="${list.id}" title="Export as CSV">CSV</button>
                            <button class="list-export-json text-xs px-2.5 py-1 rounded border border-gray-300 dark:border-gray-600
                                text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                data-list-id="${list.id}" title="Export as JSON">JSON</button>
                            ${list.type !== 'builtin' ? `
                            <button class="list-delete-btn text-xs px-2.5 py-1 rounded border border-red-200 dark:border-red-800/50
                                text-red-500 hover:border-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                                data-list-id="${list.id}" data-list-name="${this._esc(list.name)}">Delete</button>
                            ` : ''}
                        </div>
                    </td>
                </tr>`;
        }).join('');

        this._bindTableEvents(lists);
        this._syncSidebarVisibility();

        // Async-load counts after rows are in DOM
        lists.forEach(async list => {
            if (!list.apiEndpoint) return;
            const count = await this._fetchCount(list);
            const cell = document.getElementById(`count-${list.id}`);
            if (cell) {
                cell.textContent = count !== null ? count.toLocaleString() : '—';
            }
        });
    }

    _bindTableEvents(lists) {
        // Visibility toggles
        document.querySelectorAll('.list-visibility-toggle').forEach(toggle => {
            toggle.addEventListener('change', e => {
                const id = e.target.dataset.listId;
                const on = e.target.checked;
                this._setVisible(id, on);
                const label = e.target.closest('label');
                label.querySelector('.list-vis-track').classList.toggle('bg-blue-600', on);
                label.querySelector('.list-vis-track').classList.toggle('bg-gray-300', !on);
                label.querySelector('.list-vis-track').classList.toggle('dark:bg-gray-600', !on);
                label.querySelector('.list-vis-thumb').classList.toggle('translate-x-5', on);
            });
        });

        // CSV export
        document.querySelectorAll('.list-export-csv').forEach(btn => {
            btn.addEventListener('click', async () => {
                const list = lists.find(l => l.id === btn.dataset.listId);
                if (!list?.apiEndpoint) return this._notify('No data source for this list', 'error');
                btn.textContent = '…';
                try {
                    const data = await this._fetchData(list);
                    this._downloadCSV(data, list.name);
                } catch {
                    this._notify('Export failed', 'error');
                } finally {
                    btn.textContent = 'CSV';
                }
            });
        });

        // JSON export
        document.querySelectorAll('.list-export-json').forEach(btn => {
            btn.addEventListener('click', async () => {
                const list = lists.find(l => l.id === btn.dataset.listId);
                if (!list?.apiEndpoint) return this._notify('No data source for this list', 'error');
                btn.textContent = '…';
                try {
                    const data = await this._fetchData(list);
                    this._downloadJSON(data, list.name);
                } catch {
                    this._notify('Export failed', 'error');
                } finally {
                    btn.textContent = 'JSON';
                }
            });
        });

        // View items panel (proposals, bnb, hotwash, tasks)
        document.querySelectorAll('.list-view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.dataset.listId;
                const name = btn.dataset.listName;
                if (id === 'tasks') {
                    // Navigate to the dedicated tasks area
                    if (window.app?.navigation) window.app.navigation.navigateTo('tasks');
                } else {
                    if (window.trackingLists) window.trackingLists.openPanel(id, name);
                }
            });
        });

        // Delete (custom lists only)
        document.querySelectorAll('.list-delete-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.dataset.listId;
                const name = btn.dataset.listName;
                if (!confirm(`Delete list "${name}"? This cannot be undone.`)) return;
                this._deleteCustomList(id);
                this.load();
                this._notify(`"${name}" deleted`, 'success');
            });
        });
    }

    // -------------------------------------------------------------------------
    // Modal: Add List
    // -------------------------------------------------------------------------

    _setupModalHandlers() {
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('add-list-btn')?.addEventListener('click', () => this._openModal());
            document.getElementById('close-add-list-modal')?.addEventListener('click', () => this._closeModal());
            document.getElementById('cancel-add-list-btn')?.addEventListener('click', () => this._closeModal());
            document.getElementById('add-list-modal')?.addEventListener('click', e => {
                if (e.target === document.getElementById('add-list-modal')) this._closeModal();
            });
            document.getElementById('add-list-form')?.addEventListener('submit', e => {
                e.preventDefault();
                this._saveNewList();
            });
        });
    }

    _openModal() {
        document.getElementById('add-list-form')?.reset();
        document.getElementById('add-list-modal')?.classList.remove('hidden');
    }

    _closeModal() {
        document.getElementById('add-list-modal')?.classList.add('hidden');
    }

    _saveNewList() {
        const name = document.getElementById('new-list-name')?.value.trim();
        const description = document.getElementById('new-list-description')?.value.trim();
        const type = document.getElementById('new-list-type')?.value || 'custom';

        if (!name) return;

        const registry = JSON.parse(localStorage.getItem(this._registryKey) || '[]');
        const id = 'list-' + Date.now();
        registry.push({ id, name, description: description || '', type });
        localStorage.setItem(this._registryKey, JSON.stringify(registry));

        this._closeModal();
        this.load();
        this._notify(`"${name}" added`, 'success');
    }

    _deleteCustomList(id) {
        const registry = JSON.parse(localStorage.getItem(this._registryKey) || '[]');
        localStorage.setItem(this._registryKey, JSON.stringify(registry.filter(l => l.id !== id)));
        // Clean up visibility entry too
        const vis = this._visibility();
        delete vis[id];
        localStorage.setItem(this._visibilityKey, JSON.stringify(vis));
    }

    // -------------------------------------------------------------------------
    // Export helpers
    // -------------------------------------------------------------------------

    _downloadCSV(data, name) {
        const rows = Array.isArray(data) ? data : [data];
        if (rows.length === 0) return this._notify('No data to export', 'error');

        const headers = Object.keys(rows[0]);
        const lines = [
            headers.map(h => `"${h}"`).join(','),
            ...rows.map(row =>
                headers.map(h => {
                    const v = row[h];
                    const str = v === null || v === undefined ? '' : String(v);
                    return `"${str.replace(/"/g, '""')}"`;
                }).join(',')
            ),
        ];

        this._triggerDownload(lines.join('\n'), `${name.replace(/\s+/g, '_')}.csv`, 'text/csv');
    }

    _downloadJSON(data, name) {
        this._triggerDownload(
            JSON.stringify(data, null, 2),
            `${name.replace(/\s+/g, '_')}.json`,
            'application/json'
        );
    }

    _triggerDownload(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url  = URL.createObjectURL(blob);
        const a    = Object.assign(document.createElement('a'), { href: url, download: filename });
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = String(text || '');
        return d.innerHTML;
    }

    _notify(message, type = 'info') {
        const toast = Object.assign(document.createElement('div'), {
            className: `fixed bottom-4 right-4 px-5 py-3 rounded-lg shadow-lg text-white text-sm z-50 transition-opacity duration-300 ${
                type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600'
            }`,
            textContent: message,
        });
        document.body.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 2800);
    }
}

// Global instance
window.listsManager = new ListsManager();
