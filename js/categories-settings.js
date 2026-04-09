/**
 * Categories Settings — manages the Categories tab in Settings.
 *
 * Loads task_statuses and workflow_stages from /api/settings/categories,
 * renders editable label fields, and saves changes back to the server.
 * "Apply at Runtime" re-renders the Tasks Kanban without a page reload.
 */

class CategoriesSettings {
    constructor() {
        this._data     = null;   // { task_statuses: [...], workflow_stages: [...] }
        this._loaded   = false;
        this._wired    = false;
    }

    // -------------------------------------------------------------------------
    // Called when the Categories tab becomes visible
    // -------------------------------------------------------------------------

    show() {
        this._wireButtons();
        if (!this._loaded) this._load();
    }

    // -------------------------------------------------------------------------
    // Event wiring (once)
    // -------------------------------------------------------------------------

    _wireButtons() {
        if (this._wired) return;
        this._wired = true;

        document.getElementById('categories-save-btn')?.addEventListener('click', () => this._save());
        document.getElementById('categories-apply-btn')?.addEventListener('click', () => this._apply());
    }

    // -------------------------------------------------------------------------
    // Data
    // -------------------------------------------------------------------------

    async _load() {
        try {
            const res = await fetch('/api/settings/categories');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this._data   = await res.json();
            this._loaded = true;
            this._render();
        } catch (err) {
            console.error('[CategoriesSettings] load error:', err);
            this._renderError();
        }
    }

    // -------------------------------------------------------------------------
    // Rendering
    // -------------------------------------------------------------------------

    _render() {
        this._renderTaskStatuses(this._data.task_statuses || []);
        this._renderWorkflowStages(this._data.workflow_stages || []);
    }

    _renderTaskStatuses(statuses) {
        const container = document.getElementById('categories-task-statuses');
        if (!container) return;

        const sorted = statuses.slice().sort((a, b) => a.order - b.order);
        container.innerHTML = sorted.map(s => `
            <div class="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div class="w-3 h-3 rounded-full flex-shrink-0 ${s.headerClass}"></div>
                <span class="text-xs font-mono text-gray-400 dark:text-gray-500 w-24 flex-shrink-0">${this._esc(s.slug)}</span>
                <input type="text"
                       data-category="task_statuses"
                       data-slug="${this._esc(s.slug)}"
                       value="${this._esc(s.label)}"
                       class="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white">
            </div>
        `).join('');
    }

    _renderWorkflowStages(stages) {
        const container = document.getElementById('categories-workflow-stages');
        if (!container) return;

        const sorted = stages.slice().sort((a, b) => a.order - b.order);
        container.innerHTML = sorted.map(s => `
            <div class="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div class="w-3 h-3 rounded-full flex-shrink-0 ${s.headerClass}"></div>
                <span class="text-xs font-mono text-gray-400 dark:text-gray-500 w-24 flex-shrink-0">${this._esc(s.slug)}</span>
                <input type="text"
                       data-category="workflow_stages"
                       data-slug="${this._esc(s.slug)}"
                       value="${this._esc(s.label)}"
                       class="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white">
            </div>
        `).join('');
    }

    _renderError() {
        ['categories-task-statuses', 'categories-workflow-stages'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = `<div class="text-center py-4 text-red-500 text-sm">Failed to load categories.</div>`;
        });
    }

    // -------------------------------------------------------------------------
    // Collect current form values into _data
    // -------------------------------------------------------------------------

    _collectForm() {
        if (!this._data) return;

        document.querySelectorAll('input[data-category]').forEach(input => {
            const category = input.dataset.category;   // 'task_statuses' | 'workflow_stages'
            const slug     = input.dataset.slug;
            const newLabel = input.value.trim();
            if (!newLabel) return;

            const list = this._data[category];
            if (!list) return;
            const item = list.find(i => i.slug === slug);
            if (item) item.label = newLabel;
        });
    }

    // -------------------------------------------------------------------------
    // Save
    // -------------------------------------------------------------------------

    async _save() {
        this._collectForm();
        const btn = document.getElementById('categories-save-btn');
        if (btn) { btn.textContent = 'Saving…'; btn.disabled = true; }
        try {
            const res = await fetch('/api/settings/categories', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this._data),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            if (btn) { btn.textContent = 'Saved!'; btn.disabled = false; }
            setTimeout(() => { if (btn) btn.textContent = 'Save'; }, 2000);
        } catch (err) {
            console.error('[CategoriesSettings] save error:', err);
            if (btn) { btn.textContent = 'Error — Retry'; btn.disabled = false; }
            setTimeout(() => { if (btn) btn.textContent = 'Save'; }, 3000);
        }
    }

    // -------------------------------------------------------------------------
    // Apply at runtime — saves first, then re-renders Tasks Kanban
    // -------------------------------------------------------------------------

    async _apply() {
        this._collectForm();
        const btn = document.getElementById('categories-apply-btn');
        if (btn) { btn.textContent = 'Applying…'; btn.disabled = true; }
        try {
            const res = await fetch('/api/settings/categories', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this._data),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            // Re-render the Tasks Kanban with the new column definitions
            if (window.tasksList) await window.tasksList.applyCategories();

            if (btn) { btn.textContent = 'Applied!'; btn.disabled = false; }
            setTimeout(() => { if (btn) btn.textContent = 'Apply at Runtime'; }, 2000);
        } catch (err) {
            console.error('[CategoriesSettings] apply error:', err);
            if (btn) { btn.textContent = 'Error — Retry'; btn.disabled = false; }
            setTimeout(() => { if (btn) btn.textContent = 'Apply at Runtime'; }, 3000);
        }
    }

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = String(text || '');
        return d.innerHTML;
    }
}

window.categoriesSettings = new CategoriesSettings();

document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('click', e => {
        const tab = e.target.closest('.settings-tab[data-tab="categories"]');
        if (tab) window.categoriesSettings.show();
    });
});
