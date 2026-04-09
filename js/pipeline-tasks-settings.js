/**
 * Pipeline Tasks Settings — manages the configurable task template editor.
 *
 * Each template defines:
 *   - trigger      : which tracking List type creates the item (proposal / bnb / hotwash)
 *   - trigger_stages: pipeline_stage values (from KANBAN_STAGES) that fire the trigger
 *   - enabled      : whether the template is active
 *   - task_name    : auto-created task name
 *   - task_description: auto-created task description
 *
 * Templates are stored at /api/settings/tracking-tasks (GET/PUT).
 */

(function () {
    'use strict';

    const API_URL = '/api/settings/tracking-tasks';

    // Available tracking list types (backed by ensure_*_item() in the server).
    const TRIGGER_TYPES = [
        { value: 'proposal', label: 'Proposal' },
        { value: 'bnb',      label: 'Bid No-Bid' },
        { value: 'hotwash',  label: 'Hotwash' },
    ];

    let _templates = [];
    let _loaded    = false;

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    /** Escape text for safe HTML insertion. */
    function _esc(text) {
        return String(text || '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /**
     * Return all KANBAN pipeline stages available on the page.
     * Falls back to a minimal hard-coded list if workflows.js hasn't loaded.
     *
     * @returns {Array<{code: string, localStages: string[]}>}
     */
    function _getPipelineStages() {
        if (typeof KANBAN_STAGES !== 'undefined') return KANBAN_STAGES;
        // Fallback — covers the three most-used stages
        return [
            { code: '01-Qualification', localStages: ['identified', 'qualifying'] },
            { code: '03-Bid Decision',  localStages: ['bid_decision'] },
            { code: '04-In Progress',   localStages: ['active'] },
            { code: '05-Waiting/Review',localStages: ['submitted'] },
            { code: '06-In Negotiation',localStages: ['negotiating'] },
            { code: '07-Closed Won',    localStages: ['awarded'] },
            { code: '08-Closed Lost',   localStages: ['lost'] },
            { code: '09-Closed No Bid', localStages: ['no_bid'] },
        ];
    }

    // -------------------------------------------------------------------------
    // Load
    // -------------------------------------------------------------------------

    async function load() {
        if (_loaded) return;
        const container = document.getElementById('pipeline-tasks-content');
        if (!container) return;
        container.innerHTML = '<div class="text-center py-8 text-gray-400 text-sm">Loading…</div>';
        try {
            const res  = await fetch(API_URL);
            const data = await res.json();
            _templates = data.templates || [];
            _loaded    = true;
            render(container);
        } catch {
            container.innerHTML = '<p class="text-sm text-red-500">Failed to load templates.</p>';
        }
    }

    // -------------------------------------------------------------------------
    // Render
    // -------------------------------------------------------------------------

    function render(container) {
        const cards = _templates.map((t, idx) => _cardHtml(t, idx)).join('');
        container.innerHTML = `
            ${cards}
            <div class="pt-2">
                <button id="pipeline-tasks-add-btn"
                    class="w-full py-2 border-2 border-dashed border-gray-300 dark:border-gray-600
                           text-sm text-gray-500 dark:text-gray-400 rounded-lg
                           hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    + Add Template
                </button>
            </div>`;
        bindEvents(container);
    }

    function _cardHtml(t, idx) {
        const stages       = _getPipelineStages();
        const activeStages = new Set(t.trigger_stages || []);

        // Build trigger type <select>
        const triggerOptions = TRIGGER_TYPES.map(tt =>
            `<option value="${tt.value}" ${t.trigger === tt.value ? 'selected' : ''}>${_esc(tt.label)}</option>`
        ).join('');

        // Build stage checkboxes — one per KANBAN_STAGES entry
        const stageCheckboxes = stages.map(s => {
            const checked = s.localStages.some(ls => activeStages.has(ls));
            const stageKey = s.localStages.join(',');   // stored as data attr for toggle logic
            return `
            <label class="flex items-center gap-2 cursor-pointer select-none">
                <input type="checkbox" class="tmpl-stage-chk w-3.5 h-3.5 rounded text-blue-600"
                       data-idx="${idx}" data-local-stages="${_esc(stageKey)}"
                       ${checked ? 'checked' : ''}>
                <span class="text-xs text-gray-700 dark:text-gray-300">${_esc(s.code)}</span>
            </label>`;
        }).join('');

        return `
        <div class="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3"
             data-tmpl-idx="${idx}">

            <!-- Header: item type + enable toggle + remove -->
            <div class="flex items-center gap-3">
                <div class="flex-1">
                    <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        List Item Type
                    </label>
                    <select class="tmpl-trigger w-full px-2 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600
                                   bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                                   focus:outline-none focus:ring-2 focus:ring-blue-500"
                            data-idx="${idx}">
                        ${triggerOptions}
                    </select>
                </div>

                <!-- Enable toggle -->
                <div class="flex flex-col items-center gap-1 flex-shrink-0">
                    <span class="text-xs text-gray-500 dark:text-gray-400">Enabled</span>
                    <label class="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" class="tmpl-enabled sr-only" data-idx="${idx}" ${t.enabled ? 'checked' : ''}>
                        <div class="tmpl-track w-10 h-5 rounded-full transition-colors ${t.enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}"></div>
                        <div class="tmpl-thumb absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${t.enabled ? 'translate-x-5' : ''}"></div>
                    </label>
                </div>

                <!-- Remove -->
                <button class="tmpl-remove flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors" data-idx="${idx}" title="Remove template">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>

            <!-- Trigger stages -->
            <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                    Trigger on Stage Entry
                </label>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1.5 p-3
                            bg-white dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700">
                    ${stageCheckboxes}
                </div>
            </div>

            <!-- Task name -->
            <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Task Name</label>
                <input type="text" class="tmpl-name w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600
                                          bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                                          focus:outline-none focus:ring-2 focus:ring-blue-500"
                       data-idx="${idx}" value="${_esc(t.task_name)}">
            </div>

            <!-- Task description -->
            <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Task Description</label>
                <textarea class="tmpl-desc w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600
                                 bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                                 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                          data-idx="${idx}" rows="2">${_esc(t.task_description)}</textarea>
            </div>
        </div>`;
    }

    // -------------------------------------------------------------------------
    // Event binding
    // -------------------------------------------------------------------------

    function bindEvents(container) {
        // Trigger type (list item type)
        container.querySelectorAll('.tmpl-trigger').forEach(sel => {
            sel.addEventListener('change', e => {
                _templates[+e.target.dataset.idx].trigger = e.target.value;
            });
        });

        // Enable toggle
        container.querySelectorAll('.tmpl-enabled').forEach(cb => {
            cb.addEventListener('change', e => {
                const idx = +e.target.dataset.idx;
                _templates[idx].enabled = e.target.checked;
                const label = e.target.closest('label');
                label.querySelector('.tmpl-track').classList.toggle('bg-blue-600',         e.target.checked);
                label.querySelector('.tmpl-track').classList.toggle('bg-gray-300',        !e.target.checked);
                label.querySelector('.tmpl-track').classList.toggle('dark:bg-gray-600',   !e.target.checked);
                label.querySelector('.tmpl-thumb').classList.toggle('translate-x-5',       e.target.checked);
            });
        });

        // Stage checkboxes
        container.querySelectorAll('.tmpl-stage-chk').forEach(cb => {
            cb.addEventListener('change', e => {
                const idx         = +e.target.dataset.idx;
                const localStages = e.target.dataset.localStages.split(',').filter(Boolean);
                let current       = new Set(_templates[idx].trigger_stages || []);
                if (e.target.checked) {
                    localStages.forEach(s => current.add(s));
                } else {
                    localStages.forEach(s => current.delete(s));
                }
                _templates[idx].trigger_stages = [...current];
            });
        });

        // Task name
        container.querySelectorAll('.tmpl-name').forEach(inp => {
            inp.addEventListener('input', e => {
                _templates[+e.target.dataset.idx].task_name = e.target.value;
            });
        });

        // Task description
        container.querySelectorAll('.tmpl-desc').forEach(ta => {
            ta.addEventListener('input', e => {
                _templates[+e.target.dataset.idx].task_description = e.target.value;
            });
        });

        // Remove template
        container.querySelectorAll('.tmpl-remove').forEach(btn => {
            btn.addEventListener('click', e => {
                const idx = +e.target.closest('.tmpl-remove').dataset.idx;
                _templates.splice(idx, 1);
                render(container);
            });
        });

        // Add template
        document.getElementById('pipeline-tasks-add-btn')?.addEventListener('click', () => {
            _templates.push({
                trigger:       TRIGGER_TYPES[0].value,
                trigger_stages: [],
                enabled:       true,
                task_name:     '',
                task_description: '',
            });
            render(container);
        });
    }

    // -------------------------------------------------------------------------
    // Save
    // -------------------------------------------------------------------------

    async function save() {
        const btn = document.getElementById('pipeline-tasks-save-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
        try {
            const res  = await fetch(API_URL, {
                method:  'PUT',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ templates: _templates }),
            });
            const data = await res.json();
            if (btn) {
                btn.textContent = data.status === 'success' ? 'Saved!' : 'Error';
                setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 1800);
            }
        } catch {
            if (btn) {
                btn.textContent = 'Error';
                setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 1800);
            }
        }
    }

    // -------------------------------------------------------------------------
    // Init
    // -------------------------------------------------------------------------

    document.addEventListener('DOMContentLoaded', () => {
        document.addEventListener('click', e => {
            const tab = e.target.closest('.settings-tab[data-tab="pipeline-tasks"]');
            if (tab) load();
        });
        document.getElementById('pipeline-tasks-save-btn')?.addEventListener('click', save);
    });
})();
