/**
 * Pipeline Tasks Settings — manages the configurable task template editor.
 *
 * Loads when the "Pipeline Tasks" settings tab is activated.
 * Reads from and writes to GET/PUT /api/settings/tracking-tasks.
 */

(function () {
    'use strict';

    const API_URL = '/api/settings/tracking-tasks';

    const TRIGGER_LABELS = {
        proposal: 'Proposal (04-In Progress)',
        bnb:      'Bid No-Bid (03-Bid Decision)',
        hotwash:  'Hotwash (06–09 Close stages)',
    };

    let _templates = [];
    let _loaded = false;

    // -------------------------------------------------------------------------
    // Load + render
    // -------------------------------------------------------------------------

    async function load() {
        if (_loaded) return;
        const container = document.getElementById('pipeline-tasks-content');
        if (!container) return;
        container.innerHTML = '<div class="text-center py-8 text-gray-400 text-sm">Loading…</div>';
        try {
            const res = await fetch(API_URL);
            const data = await res.json();
            _templates = data.templates || [];
            _loaded = true;
            render(container);
        } catch {
            container.innerHTML = '<p class="text-sm text-red-500">Failed to load templates.</p>';
        }
    }

    function render(container) {
        container.innerHTML = _templates.map((t, idx) => `
            <div class="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div class="flex items-center justify-between mb-3">
                    <div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">
                            ${_esc(TRIGGER_LABELS[t.trigger] || t.trigger)}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            Trigger: <code class="bg-gray-100 dark:bg-gray-800 px-1 rounded">${_esc(t.trigger)}</code>
                        </div>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" class="tmpl-enabled sr-only" data-idx="${idx}" ${t.enabled ? 'checked' : ''}>
                        <div class="tmpl-track w-10 h-5 rounded-full transition-colors ${t.enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}"></div>
                        <div class="tmpl-thumb absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${t.enabled ? 'translate-x-5' : ''}"></div>
                    </label>
                </div>
                <div class="space-y-2">
                    <div>
                        <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Task Name</label>
                        <input type="text" class="tmpl-name w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            data-idx="${idx}" value="${_esc(t.task_name)}">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Task Description</label>
                        <textarea class="tmpl-desc w-full px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                            data-idx="${idx}" rows="2">${_esc(t.task_description)}</textarea>
                    </div>
                </div>
            </div>
        `).join('');

        bindEvents(container);
    }

    // -------------------------------------------------------------------------
    // Event binding
    // -------------------------------------------------------------------------

    function bindEvents(container) {
        container.querySelectorAll('.tmpl-enabled').forEach(cb => {
            cb.addEventListener('change', e => {
                const idx = +e.target.dataset.idx;
                _templates[idx].enabled = e.target.checked;
                const label = e.target.closest('label');
                label.querySelector('.tmpl-track').classList.toggle('bg-blue-600', e.target.checked);
                label.querySelector('.tmpl-track').classList.toggle('bg-gray-300', !e.target.checked);
                label.querySelector('.tmpl-track').classList.toggle('dark:bg-gray-600', !e.target.checked);
                label.querySelector('.tmpl-thumb').classList.toggle('translate-x-5', e.target.checked);
            });
        });

        container.querySelectorAll('.tmpl-name').forEach(inp => {
            inp.addEventListener('input', e => {
                _templates[+e.target.dataset.idx].task_name = e.target.value;
            });
        });

        container.querySelectorAll('.tmpl-desc').forEach(ta => {
            ta.addEventListener('input', e => {
                _templates[+e.target.dataset.idx].task_description = e.target.value;
            });
        });
    }

    // -------------------------------------------------------------------------
    // Save
    // -------------------------------------------------------------------------

    async function save() {
        const btn = document.getElementById('pipeline-tasks-save-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
        try {
            const res = await fetch(API_URL, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ templates: _templates }),
            });
            const data = await res.json();
            if (btn) {
                btn.textContent = data.status === 'success' ? 'Saved!' : 'Error';
                setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 1800);
            }
        } catch {
            if (btn) { btn.textContent = 'Error'; setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 1800); }
        }
    }

    // -------------------------------------------------------------------------
    // Utility
    // -------------------------------------------------------------------------

    function _esc(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // -------------------------------------------------------------------------
    // Init
    // -------------------------------------------------------------------------

    document.addEventListener('DOMContentLoaded', () => {
        // Trigger load when Pipeline Tasks tab button is clicked
        document.addEventListener('click', e => {
            const tab = e.target.closest('.settings-tab[data-tab="pipeline-tasks"]');
            if (tab) load();
        });

        // Save button
        document.getElementById('pipeline-tasks-save-btn')?.addEventListener('click', save);
    });
})();
