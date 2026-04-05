/**
 * Tracking Lists — inline item management for Proposals and Bid No-Bid lists.
 *
 * Renders inside #lists-items-panel within the Lists Interface area.
 * Opened by listsManager when the user clicks "View" on a viewable list.
 */

const CONTRACT_TYPES  = ['FFP', 'CPFF', 'CPAF', 'CPIF', 'T&M', 'LH', 'IDIQ', 'Other'];
const AGREEMENT_TYPES = ['Standalone', 'Task Order', 'IDIQ', 'BPA', 'GWAC', 'MATOC', 'Other'];
const BNB_DECISIONS   = ['pending', 'bid', 'no_bid', 'conditional'];

class TrackingLists {
    constructor() {
        this._current = null;  // 'proposals' | 'bnb'
        this._items   = [];
        this._editingId = null;
    }

    // -------------------------------------------------------------------------
    // Panel open/close
    // -------------------------------------------------------------------------

    openPanel(listId, listName) {
        this._current = listId;
        this._editingId = null;

        const panel = document.getElementById('lists-items-panel');
        if (!panel) return;

        panel.classList.remove('hidden');
        panel.querySelector('#lists-items-panel-title').textContent = listName;
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

        this._load();
    }

    closePanel() {
        document.getElementById('lists-items-panel')?.classList.add('hidden');
        this._current = null;
        this._items = [];
    }

    // -------------------------------------------------------------------------
    // Data
    // -------------------------------------------------------------------------

    async _load() {
        const endpoint = this._current === 'proposals' ? '/api/proposal-items' : '/api/bnb-items';
        const tbody = document.getElementById('tracking-items-tbody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="px-4 py-6 text-center text-sm text-gray-400">Loading…</td></tr>';

        try {
            const res = await fetch(endpoint);
            const data = await res.json();
            this._items = data.items || [];
            this._renderItems();
        } catch {
            if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="px-4 py-6 text-center text-sm text-red-500">Failed to load items</td></tr>';
        }
    }

    async _save(id, fields) {
        const endpoint = this._current === 'proposals'
            ? `/api/proposal-items/${id}`
            : `/api/bnb-items/${id}`;
        const res = await fetch(endpoint, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(fields),
        });
        return res.json();
    }

    async _delete(id) {
        const endpoint = this._current === 'proposals'
            ? `/api/proposal-items/${id}`
            : `/api/bnb-items/${id}`;
        return fetch(endpoint, { method: 'DELETE' }).then(r => r.json());
    }

    async _create(fields) {
        const endpoint = this._current === 'proposals' ? '/api/proposal-items' : '/api/bnb-items';
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(fields),
        });
        return res.json();
    }

    // -------------------------------------------------------------------------
    // Render
    // -------------------------------------------------------------------------

    _renderItems() {
        const tbody = document.getElementById('tracking-items-tbody');
        const header = document.getElementById('tracking-items-header');
        const addForm = document.getElementById('tracking-add-form-container');
        if (!tbody || !header) return;

        if (this._current === 'proposals') {
            this._renderProposalHeader(header);
            this._renderProposalRows(tbody);
            if (addForm) this._renderProposalAddForm(addForm);
        } else {
            this._renderBnbHeader(header);
            this._renderBnbRows(tbody);
            if (addForm) this._renderBnbAddForm(addForm);
        }

        this._bindItemEvents();
    }

    // ---- Proposals -----------------------------------------------------------

    _renderProposalHeader(header) {
        header.innerHTML = `
            <tr class="bg-gray-50 dark:bg-gray-900/50 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <th class="px-4 py-2 text-left">Opportunity</th>
                <th class="px-4 py-2 text-left">Created</th>
                <th class="px-4 py-2 text-left">Goldenrod</th>
                <th class="px-4 py-2 text-left">Submission</th>
                <th class="px-4 py-2 text-right">Price ($)</th>
                <th class="px-4 py-2 text-left">Contract</th>
                <th class="px-4 py-2 text-left">Agreement</th>
                <th class="px-4 py-2 text-center">Submitted</th>
                <th class="px-4 py-2 text-left">Notes</th>
                <th class="px-4 py-2"></th>
            </tr>`;
    }

    _renderProposalRows(tbody) {
        if (this._items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                No proposals yet — move an opportunity to <strong>04-In Progress</strong> to auto-create one.
            </td></tr>`;
            return;
        }

        tbody.innerHTML = this._items.map(item => {
            if (this._editingId === item.id) return this._proposalEditRow(item);
            return `
                <tr class="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/20 text-sm" data-item-id="${item.id}">
                    <td class="px-4 py-3 font-medium text-gray-900 dark:text-white max-w-[160px] truncate" title="${this._esc(item.opportunity_name)}">${this._esc(item.opportunity_name)}</td>
                    <td class="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">${item.created_date || '—'}</td>
                    <td class="px-4 py-3 ${item.goldenrod_date ? 'text-yellow-600 dark:text-yellow-400 font-medium' : 'text-gray-400'} whitespace-nowrap">${item.goldenrod_date || '—'}</td>
                    <td class="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">${item.submission_date || '—'}</td>
                    <td class="px-4 py-3 text-right text-gray-600 dark:text-gray-400">${item.proposal_price != null ? '$' + Number(item.proposal_price).toLocaleString() : '—'}</td>
                    <td class="px-4 py-3 text-gray-600 dark:text-gray-400">${this._esc(item.contract_type) || '—'}</td>
                    <td class="px-4 py-3 text-gray-600 dark:text-gray-400">${this._esc(item.agreement_type) || '—'}</td>
                    <td class="px-4 py-3 text-center">${item.submitted
                        ? '<span class="inline-block w-4 h-4 rounded-full bg-green-500" title="Submitted"></span>'
                        : '<span class="inline-block w-4 h-4 rounded-full bg-gray-300 dark:bg-gray-600" title="Not submitted"></span>'}</td>
                    <td class="px-4 py-3 text-gray-500 dark:text-gray-400 max-w-[140px] truncate" title="${this._esc(item.notes)}">${this._esc(item.notes) || ''}</td>
                    <td class="px-4 py-3 text-right whitespace-nowrap">
                        <button class="item-edit-btn text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 mr-2" data-id="${item.id}">Edit</button>
                        <button class="item-delete-btn text-xs text-red-500 hover:text-red-700" data-id="${item.id}" data-name="${this._esc(item.opportunity_name)}">Delete</button>
                    </td>
                </tr>`;
        }).join('');
    }

    _proposalEditRow(item) {
        const ctOpts = CONTRACT_TYPES.map(t => `<option ${item.contract_type === t ? 'selected' : ''}>${t}</option>`).join('');
        const agOpts = AGREEMENT_TYPES.map(t => `<option ${item.agreement_type === t ? 'selected' : ''}>${t}</option>`).join('');
        return `
            <tr class="border-b border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/10 text-sm" data-item-id="${item.id}">
                <td class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300 text-xs">${this._esc(item.opportunity_name)}</td>
                <td class="px-4 py-2"><input type="date" class="edit-field w-full text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="created_date" value="${item.created_date || ''}"></td>
                <td class="px-4 py-2"><input type="date" class="edit-field w-full text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="goldenrod_date" value="${item.goldenrod_date || ''}"></td>
                <td class="px-4 py-2"><input type="date" class="edit-field w-full text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="submission_date" value="${item.submission_date || ''}"></td>
                <td class="px-4 py-2"><input type="number" class="edit-field w-full text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="proposal_price" value="${item.proposal_price ?? ''}"></td>
                <td class="px-4 py-2"><select class="edit-field text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="contract_type">${ctOpts}</select></td>
                <td class="px-4 py-2"><select class="edit-field text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="agreement_type">${agOpts}</select></td>
                <td class="px-4 py-2 text-center"><input type="checkbox" class="edit-field" data-field="submitted" ${item.submitted ? 'checked' : ''}></td>
                <td class="px-4 py-2"><input type="text" class="edit-field w-full text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="notes" value="${this._esc(item.notes || '')}"></td>
                <td class="px-4 py-2 text-right whitespace-nowrap">
                    <button class="item-save-btn text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded mr-1" data-id="${item.id}">Save</button>
                    <button class="item-cancel-btn text-xs text-gray-500 hover:text-gray-700" data-id="${item.id}">Cancel</button>
                </td>
            </tr>`;
    }

    _renderProposalAddForm(container) {
        const ctOpts = CONTRACT_TYPES.map(t => `<option>${t}</option>`).join('');
        const agOpts = AGREEMENT_TYPES.map(t => `<option>${t}</option>`).join('');
        container.innerHTML = `
            <div class="mt-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h5 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Add Proposal Manually</h5>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div><label class="block text-xs text-gray-500 mb-1">Opportunity Name *</label>
                        <input id="add-opp-name" type="text" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" placeholder="Opportunity name"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Goldenrod Date</label>
                        <input id="add-goldenrod" type="date" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Submission Date</label>
                        <input id="add-submission" type="date" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Proposal Price</label>
                        <input id="add-price" type="number" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" placeholder="0.00"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Contract Type</label>
                        <select id="add-contract" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white">${ctOpts}</select></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Agreement Type</label>
                        <select id="add-agreement" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white">${agOpts}</select></div>
                </div>
                <button id="add-tracking-item-btn" class="mt-3 px-4 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded font-medium">Add Proposal</button>
            </div>`;
    }

    // ---- BNB -----------------------------------------------------------------

    _renderBnbHeader(header) {
        header.innerHTML = `
            <tr class="bg-gray-50 dark:bg-gray-900/50 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <th class="px-4 py-2 text-left">Opportunity</th>
                <th class="px-4 py-2 text-left">Decision</th>
                <th class="px-4 py-2 text-right">Score</th>
                <th class="px-4 py-2 text-left">Decision Date</th>
                <th class="px-4 py-2 text-left">Rationale</th>
                <th class="px-4 py-2 text-left">Created</th>
                <th class="px-4 py-2"></th>
            </tr>`;
    }

    _bnbDecisionBadge(decision) {
        const map = {
            bid: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
            no_bid: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
            conditional: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
            pending: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
        };
        const cls = map[decision] || map.pending;
        return `<span class="inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cls}">${decision.replace('_', ' ')}</span>`;
    }

    _renderBnbRows(tbody) {
        if (this._items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                No BNB entries yet — move an opportunity to <strong>03-Bid Decision</strong> to auto-create one.
            </td></tr>`;
            return;
        }

        tbody.innerHTML = this._items.map(item => {
            if (this._editingId === item.id) return this._bnbEditRow(item);
            return `
                <tr class="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/20 text-sm" data-item-id="${item.id}">
                    <td class="px-4 py-3 font-medium text-gray-900 dark:text-white max-w-[200px] truncate" title="${this._esc(item.opportunity_name)}">${this._esc(item.opportunity_name)}</td>
                    <td class="px-4 py-3">${this._bnbDecisionBadge(item.decision)}</td>
                    <td class="px-4 py-3 text-right text-gray-600 dark:text-gray-400">${item.score != null ? item.score : '—'}</td>
                    <td class="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">${item.decision_date || '—'}</td>
                    <td class="px-4 py-3 text-gray-500 dark:text-gray-400 max-w-[240px] truncate" title="${this._esc(item.rationale)}">${this._esc(item.rationale) || ''}</td>
                    <td class="px-4 py-3 text-gray-400 dark:text-gray-500 whitespace-nowrap text-xs">${item.created_at?.slice(0,10) || ''}</td>
                    <td class="px-4 py-3 text-right whitespace-nowrap">
                        <button class="item-edit-btn text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 mr-2" data-id="${item.id}">Edit</button>
                        <button class="item-delete-btn text-xs text-red-500 hover:text-red-700" data-id="${item.id}" data-name="${this._esc(item.opportunity_name)}">Delete</button>
                    </td>
                </tr>`;
        }).join('');
    }

    _bnbEditRow(item) {
        const decOpts = BNB_DECISIONS.map(d => `<option value="${d}" ${item.decision === d ? 'selected' : ''}>${d.replace('_', ' ')}</option>`).join('');
        return `
            <tr class="border-b border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/10 text-sm" data-item-id="${item.id}">
                <td class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300 text-xs">${this._esc(item.opportunity_name)}</td>
                <td class="px-4 py-2"><select class="edit-field text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="decision">${decOpts}</select></td>
                <td class="px-4 py-2"><input type="number" step="0.1" min="0" max="100" class="edit-field w-20 text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="score" value="${item.score ?? ''}"></td>
                <td class="px-4 py-2"><input type="date" class="edit-field text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="decision_date" value="${item.decision_date || ''}"></td>
                <td class="px-4 py-2" colspan="1"><input type="text" class="edit-field w-full text-xs border rounded px-1 py-0.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white" data-field="rationale" value="${this._esc(item.rationale || '')}"></td>
                <td class="px-4 py-2"></td>
                <td class="px-4 py-2 text-right whitespace-nowrap">
                    <button class="item-save-btn text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded mr-1" data-id="${item.id}">Save</button>
                    <button class="item-cancel-btn text-xs text-gray-500 hover:text-gray-700" data-id="${item.id}">Cancel</button>
                </td>
            </tr>`;
    }

    _renderBnbAddForm(container) {
        const decOpts = BNB_DECISIONS.map(d => `<option value="${d}">${d.replace('_', ' ')}</option>`).join('');
        container.innerHTML = `
            <div class="mt-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h5 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Add BNB Entry Manually</h5>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div><label class="block text-xs text-gray-500 mb-1">Opportunity Name *</label>
                        <input id="add-opp-name" type="text" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" placeholder="Opportunity name"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Decision</label>
                        <select id="add-decision" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white">${decOpts}</select></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Score (0–100)</label>
                        <input id="add-score" type="number" step="0.1" min="0" max="100" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Decision Date</label>
                        <input id="add-decision-date" type="date" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white"></div>
                    <div class="md:col-span-2"><label class="block text-xs text-gray-500 mb-1">Rationale</label>
                        <input id="add-rationale" type="text" class="w-full text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" placeholder="Brief rationale"></div>
                </div>
                <button id="add-tracking-item-btn" class="mt-3 px-4 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded font-medium">Add BNB Entry</button>
            </div>`;
    }

    // -------------------------------------------------------------------------
    // Event binding
    // -------------------------------------------------------------------------

    _bindItemEvents() {
        // Edit buttons
        document.querySelectorAll('.item-edit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._editingId = btn.dataset.id;
                this._renderItems();
            });
        });

        // Cancel edit
        document.querySelectorAll('.item-cancel-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._editingId = null;
                this._renderItems();
            });
        });

        // Save edit
        document.querySelectorAll('.item-save-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const row = btn.closest('tr');
                const fields = {};
                row.querySelectorAll('.edit-field').forEach(el => {
                    if (el.type === 'checkbox') fields[el.dataset.field] = el.checked;
                    else if (el.value !== '') fields[el.dataset.field] = el.type === 'number' ? Number(el.value) : el.value;
                });
                await this._save(btn.dataset.id, fields);
                this._editingId = null;
                this._load();
            });
        });

        // Delete buttons
        document.querySelectorAll('.item-delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm(`Delete entry for "${btn.dataset.name}"?`)) return;
                await this._delete(btn.dataset.id);
                this._load();
            });
        });

        // Add form submit
        document.getElementById('add-tracking-item-btn')?.addEventListener('click', async () => {
            const name = document.getElementById('add-opp-name')?.value.trim();
            if (!name) return;

            let fields = { opportunity_name: name };
            if (this._current === 'proposals') {
                fields.goldenrod_date   = document.getElementById('add-goldenrod')?.value || '';
                fields.submission_date  = document.getElementById('add-submission')?.value || '';
                const price = document.getElementById('add-price')?.value;
                if (price) fields.proposal_price = Number(price);
                fields.contract_type    = document.getElementById('add-contract')?.value || '';
                fields.agreement_type   = document.getElementById('add-agreement')?.value || '';
            } else {
                fields.decision      = document.getElementById('add-decision')?.value || 'pending';
                const score = document.getElementById('add-score')?.value;
                if (score) fields.score = Number(score);
                fields.decision_date = document.getElementById('add-decision-date')?.value || '';
                fields.rationale     = document.getElementById('add-rationale')?.value || '';
            }

            const result = await this._create(fields);
            if (result.status === 'success') this._load();
        });
    }

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = String(text || '');
        return d.innerHTML;
    }
}

window.trackingLists = new TrackingLists();
