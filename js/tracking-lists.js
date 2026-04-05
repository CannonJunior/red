/**
 * Tracking Lists — inline item management for Proposals and Bid No-Bid lists.
 *
 * Renders inside #lists-items-panel within the Lists Interface area.
 * Uses a card-per-item layout so no horizontal scrolling is ever required.
 */

const CONTRACT_TYPES  = ['FFP', 'CPFF', 'CPAF', 'CPIF', 'T&M', 'LH', 'IDIQ', 'Other'];
const AGREEMENT_TYPES = ['Standalone', 'Task Order', 'IDIQ', 'BPA', 'GWAC', 'MATOC', 'Other'];
const BNB_DECISIONS   = ['pending', 'bid', 'no_bid', 'conditional'];

class TrackingLists {
    constructor() {
        this._current   = null;  // 'proposals' | 'bnb'
        this._items     = [];
        this._editingId = null;
    }

    // -------------------------------------------------------------------------
    // Panel open / close
    // -------------------------------------------------------------------------

    openPanel(listId, listName) {
        this._current   = listId;
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
        this._items   = [];
    }

    // -------------------------------------------------------------------------
    // Data
    // -------------------------------------------------------------------------

    async _load() {
        const endpoints = { proposals: '/api/proposal-items', bnb: '/api/bnb-items', hotwash: '/api/hotwash-items' };
        const endpoint = endpoints[this._current] || '/api/hotwash-items';
        const tbody = document.getElementById('tracking-items-tbody');
        if (tbody) tbody.innerHTML = '<tr><td class="px-4 py-6 text-center text-sm text-gray-400">Loading…</td></tr>';

        try {
            const res = await fetch(endpoint);
            const data = await res.json();
            this._items = data.items || [];
            this._renderItems();
        } catch {
            if (tbody) tbody.innerHTML = '<tr><td class="px-4 py-6 text-center text-sm text-red-500">Failed to load items</td></tr>';
        }
    }

    async _save(id, fields) {
        const map = { proposals: 'proposal-items', bnb: 'bnb-items', hotwash: 'hotwash-items' };
        const endpoint = `/api/${map[this._current] || 'hotwash-items'}/${id}`;
        const res = await fetch(endpoint, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(fields),
        });
        return res.json();
    }

    async _delete(id) {
        const map = { proposals: 'proposal-items', bnb: 'bnb-items', hotwash: 'hotwash-items' };
        const endpoint = `/api/${map[this._current] || 'hotwash-items'}/${id}`;
        return fetch(endpoint, { method: 'DELETE' }).then(r => r.json());
    }

    async _create(fields) {
        const map = { proposals: 'proposal-items', bnb: 'bnb-items', hotwash: 'hotwash-items' };
        const endpoint = `/api/${map[this._current] || 'hotwash-items'}`;
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(fields),
        });
        return res.json();
    }

    // -------------------------------------------------------------------------
    // Render dispatcher
    // -------------------------------------------------------------------------

    _renderItems() {
        // Cards go into a single-cell tbody row so the panel table structure is preserved
        const tbody   = document.getElementById('tracking-items-tbody');
        const header  = document.getElementById('tracking-items-header');
        const addForm = document.getElementById('tracking-add-form-container');
        if (!tbody) return;

        // Clear the header — cards carry their own labels
        if (header) header.innerHTML = '';

        if (this._current === 'proposals') {
            this._renderProposalCards(tbody);
            if (addForm) this._renderProposalAddForm(addForm);
        } else if (this._current === 'hotwash') {
            this._renderHotwashCards(tbody);
            if (addForm) this._renderHotwashAddForm(addForm);
        } else {
            this._renderBnbCards(tbody);
            if (addForm) this._renderBnbAddForm(addForm);
        }

        this._bindItemEvents();
    }

    // -------------------------------------------------------------------------
    // Proposals — card layout
    // -------------------------------------------------------------------------

    _renderProposalCards(tbody) {
        if (this._items.length === 0) {
            tbody.innerHTML = `<tr><td class="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                No proposals yet — move an opportunity to <strong>04-In Progress</strong> to auto-create one.
            </td></tr>`;
            return;
        }

        const cardsHtml = this._items.map(item =>
            this._editingId === item.id
                ? this._proposalEditCard(item)
                : this._proposalViewCard(item)
        ).join('');

        tbody.innerHTML = `<tr><td class="p-4"><div class="space-y-3">${cardsHtml}</div></td></tr>`;
    }

    _proposalViewCard(item) {
        const price = item.proposal_price != null
            ? '$' + Number(item.proposal_price).toLocaleString()
            : '—';
        const submittedBadge = item.submitted
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300">&#10003; Submitted</span>'
            : '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">Not submitted</span>';

        return `
            <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4" data-item-id="${item.id}">
                <div class="flex items-start justify-between gap-2 mb-3">
                    <div class="font-medium text-gray-900 dark:text-white text-sm">${this._esc(item.opportunity_name)}</div>
                    <div class="flex gap-2 flex-shrink-0">
                        ${submittedBadge}
                        <button class="item-edit-btn text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium" data-id="${item.id}">Edit</button>
                        <button class="item-delete-btn text-xs text-red-500 hover:text-red-700 font-medium" data-id="${item.id}" data-name="${this._esc(item.opportunity_name)}">Delete</button>
                    </div>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Created</span><span class="text-gray-700 dark:text-gray-300">${item.created_date || '—'}</span></div>
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Goldenrod</span><span class="${item.goldenrod_date ? 'text-yellow-600 dark:text-yellow-400 font-medium' : 'text-gray-400'}">${item.goldenrod_date || '—'}</span></div>
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Submission</span><span class="text-gray-700 dark:text-gray-300">${item.submission_date || '—'}</span></div>
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Price</span><span class="text-gray-700 dark:text-gray-300 font-medium">${price}</span></div>
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Contract Type</span><span class="text-gray-700 dark:text-gray-300">${this._esc(item.contract_type) || '—'}</span></div>
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Agreement Type</span><span class="text-gray-700 dark:text-gray-300">${this._esc(item.agreement_type) || '—'}</span></div>
                    ${item.notes ? `<div class="col-span-2 sm:col-span-3"><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Notes</span><span class="text-gray-600 dark:text-gray-400">${this._esc(item.notes)}</span></div>` : ''}
                </div>
            </div>`;
    }

    _proposalEditCard(item) {
        const ctOpts = CONTRACT_TYPES.map(t =>
            `<option ${item.contract_type === t ? 'selected' : ''}>${t}</option>`).join('');
        const agOpts = AGREEMENT_TYPES.map(t =>
            `<option ${item.agreement_type === t ? 'selected' : ''}>${t}</option>`).join('');

        return `
            <div class="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-700 rounded-lg p-4" data-item-id="${item.id}">
                <div class="font-medium text-gray-800 dark:text-white text-sm mb-3">${this._esc(item.opportunity_name)}</div>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
                    <div><label class="block text-xs text-gray-500 mb-1">Created</label>
                        <input type="date" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="created_date" value="${item.created_date || ''}"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Goldenrod</label>
                        <input type="date" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="goldenrod_date" value="${item.goldenrod_date || ''}"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Submission</label>
                        <input type="date" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="submission_date" value="${item.submission_date || ''}"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Proposal Price</label>
                        <input type="number" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="proposal_price" value="${item.proposal_price ?? ''}"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Contract Type</label>
                        <select class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="contract_type">${ctOpts}</select></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Agreement Type</label>
                        <select class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="agreement_type">${agOpts}</select></div>
                    <div class="col-span-2 sm:col-span-3"><label class="block text-xs text-gray-500 mb-1">Notes</label>
                        <input type="text" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="notes" value="${this._esc(item.notes || '')}"></div>
                </div>
                <div class="flex items-center gap-3">
                    <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                        <input type="checkbox" class="edit-field" data-field="submitted" ${item.submitted ? 'checked' : ''}> Submitted
                    </label>
                    <button class="item-save-btn text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded font-medium" data-id="${item.id}">Save</button>
                    <button class="item-cancel-btn text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" data-id="${item.id}">Cancel</button>
                </div>
            </div>`;
    }

    _renderProposalAddForm(container) {
        const ctOpts = CONTRACT_TYPES.map(t => `<option>${t}</option>`).join('');
        const agOpts = AGREEMENT_TYPES.map(t => `<option>${t}</option>`).join('');
        container.innerHTML = `
            <div class="mt-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h5 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Add Proposal Manually</h5>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
                    <div class="col-span-2 sm:col-span-3"><label class="block text-xs text-gray-500 mb-1">Opportunity Name *</label>
                        <input id="add-opp-name" type="text" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white" placeholder="Opportunity name"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Goldenrod Date</label>
                        <input id="add-goldenrod" type="date" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Submission Date</label>
                        <input id="add-submission" type="date" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Proposal Price</label>
                        <input id="add-price" type="number" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white" placeholder="0.00"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Contract Type</label>
                        <select id="add-contract" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white">${ctOpts}</select></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Agreement Type</label>
                        <select id="add-agreement" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white">${agOpts}</select></div>
                </div>
                <button id="add-tracking-item-btn" class="px-4 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded font-medium">Add Proposal</button>
            </div>`;
    }

    // -------------------------------------------------------------------------
    // BNB — card layout
    // -------------------------------------------------------------------------

    _renderBnbCards(tbody) {
        if (this._items.length === 0) {
            tbody.innerHTML = `<tr><td class="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                No BNB entries yet — move an opportunity to <strong>03-Bid Decision</strong> to auto-create one.
            </td></tr>`;
            return;
        }

        const cardsHtml = this._items.map(item =>
            this._editingId === item.id
                ? this._bnbEditCard(item)
                : this._bnbViewCard(item)
        ).join('');

        tbody.innerHTML = `<tr><td class="p-4"><div class="space-y-3">${cardsHtml}</div></td></tr>`;
    }

    _bnbDecisionBadge(decision) {
        const map = {
            bid:         'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
            no_bid:      'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
            conditional: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
            pending:     'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
        };
        const cls = map[decision] || map.pending;
        return `<span class="inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cls}">${decision.replace('_', ' ')}</span>`;
    }

    _bnbViewCard(item) {
        return `
            <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4" data-item-id="${item.id}">
                <div class="flex items-start justify-between gap-2 mb-3">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-medium text-gray-900 dark:text-white text-sm">${this._esc(item.opportunity_name)}</span>
                        ${this._bnbDecisionBadge(item.decision)}
                    </div>
                    <div class="flex gap-2 flex-shrink-0">
                        <button class="item-edit-btn text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium" data-id="${item.id}">Edit</button>
                        <button class="item-delete-btn text-xs text-red-500 hover:text-red-700 font-medium" data-id="${item.id}" data-name="${this._esc(item.opportunity_name)}">Delete</button>
                    </div>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Score</span><span class="text-gray-700 dark:text-gray-300">${item.score != null ? item.score : '—'}</span></div>
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Decision Date</span><span class="text-gray-700 dark:text-gray-300">${item.decision_date || '—'}</span></div>
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Created</span><span class="text-gray-400 dark:text-gray-500 text-xs">${item.created_at?.slice(0, 10) || ''}</span></div>
                    ${item.rationale ? `<div class="col-span-2 sm:col-span-3"><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Rationale</span><span class="text-gray-600 dark:text-gray-400">${this._esc(item.rationale)}</span></div>` : ''}
                </div>
            </div>`;
    }

    _bnbEditCard(item) {
        const decOpts = BNB_DECISIONS.map(d =>
            `<option value="${d}" ${item.decision === d ? 'selected' : ''}>${d.replace('_', ' ')}</option>`).join('');

        return `
            <div class="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-700 rounded-lg p-4" data-item-id="${item.id}">
                <div class="font-medium text-gray-800 dark:text-white text-sm mb-3">${this._esc(item.opportunity_name)}</div>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
                    <div><label class="block text-xs text-gray-500 mb-1">Decision</label>
                        <select class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="decision">${decOpts}</select></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Score (0–100)</label>
                        <input type="number" step="0.1" min="0" max="100" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="score" value="${item.score ?? ''}"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Decision Date</label>
                        <input type="date" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="decision_date" value="${item.decision_date || ''}"></div>
                    <div class="col-span-2 sm:col-span-3"><label class="block text-xs text-gray-500 mb-1">Rationale</label>
                        <input type="text" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="rationale" value="${this._esc(item.rationale || '')}"></div>
                </div>
                <div class="flex items-center gap-3">
                    <button class="item-save-btn text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded font-medium" data-id="${item.id}">Save</button>
                    <button class="item-cancel-btn text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" data-id="${item.id}">Cancel</button>
                </div>
            </div>`;
    }

    _renderBnbAddForm(container) {
        const decOpts = BNB_DECISIONS.map(d => `<option value="${d}">${d.replace('_', ' ')}</option>`).join('');
        container.innerHTML = `
            <div class="mt-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h5 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Add BNB Entry Manually</h5>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
                    <div class="col-span-2 sm:col-span-3"><label class="block text-xs text-gray-500 mb-1">Opportunity Name *</label>
                        <input id="add-opp-name" type="text" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white" placeholder="Opportunity name"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Decision</label>
                        <select id="add-decision" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white">${decOpts}</select></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Score (0–100)</label>
                        <input id="add-score" type="number" step="0.1" min="0" max="100" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Decision Date</label>
                        <input id="add-decision-date" type="date" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white"></div>
                    <div class="col-span-2 sm:col-span-3"><label class="block text-xs text-gray-500 mb-1">Rationale</label>
                        <input id="add-rationale" type="text" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white" placeholder="Brief rationale"></div>
                </div>
                <button id="add-tracking-item-btn" class="px-4 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded font-medium">Add BNB Entry</button>
            </div>`;
    }

    // -------------------------------------------------------------------------
    // Hotwash — card layout
    // -------------------------------------------------------------------------

    _renderHotwashCards(tbody) {
        if (this._items.length === 0) {
            tbody.innerHTML = `<tr><td class="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                No hotwash entries yet — move an opportunity to 06, 07, 08, or 09 to auto-create one.
            </td></tr>`;
            return;
        }
        const cardsHtml = this._items.map(item =>
            this._editingId === item.id
                ? this._hotwashEditCard(item)
                : this._hotwashViewCard(item)
        ).join('');
        tbody.innerHTML = `<tr><td class="p-4"><div class="space-y-3">${cardsHtml}</div></td></tr>`;
    }

    _hotwashViewCard(item) {
        const stageBadge = item.trigger_stage
            ? `<span class="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">${this._esc(item.trigger_stage)}</span>`
            : '';
        return `
            <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4" data-item-id="${item.id}">
                <div class="flex items-start justify-between gap-2 mb-3">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-medium text-gray-900 dark:text-white text-sm">${this._esc(item.opportunity_name)}</span>
                        ${stageBadge}
                    </div>
                    <div class="flex gap-2 flex-shrink-0">
                        <button class="item-edit-btn text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium" data-id="${item.id}">Edit</button>
                        <button class="item-delete-btn text-xs text-red-500 hover:text-red-700 font-medium" data-id="${item.id}" data-name="${this._esc(item.opportunity_name)}">Delete</button>
                    </div>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
                    <div><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Conducted</span><span class="text-gray-700 dark:text-gray-300">${item.conducted_date || '—'}</span></div>
                    <div class="col-span-1 sm:col-span-2"><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Participants</span><span class="text-gray-700 dark:text-gray-300">${this._esc(item.participants) || '—'}</span></div>
                    ${item.outcome_summary ? `<div class="col-span-2 sm:col-span-3"><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Outcome Summary</span><span class="text-gray-600 dark:text-gray-400">${this._esc(item.outcome_summary)}</span></div>` : ''}
                    ${item.lessons_learned ? `<div class="col-span-2 sm:col-span-3"><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Lessons Learned</span><span class="text-gray-600 dark:text-gray-400">${this._esc(item.lessons_learned)}</span></div>` : ''}
                    ${item.action_items ? `<div class="col-span-2 sm:col-span-3"><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Action Items</span><span class="text-gray-600 dark:text-gray-400">${this._esc(item.action_items)}</span></div>` : ''}
                    ${item.notes ? `<div class="col-span-2 sm:col-span-3"><span class="text-xs text-gray-400 dark:text-gray-500 uppercase tracking-wide block mb-0.5">Notes</span><span class="text-gray-600 dark:text-gray-400">${this._esc(item.notes)}</span></div>` : ''}
                </div>
            </div>`;
    }

    _hotwashEditCard(item) {
        return `
            <div class="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-700 rounded-lg p-4" data-item-id="${item.id}">
                <div class="font-medium text-gray-800 dark:text-white text-sm mb-3">${this._esc(item.opportunity_name)}</div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                    <div><label class="block text-xs text-gray-500 mb-1">Conducted Date</label>
                        <input type="date" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="conducted_date" value="${item.conducted_date || ''}"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Participants</label>
                        <input type="text" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="participants" value="${this._esc(item.participants || '')}"></div>
                    <div class="sm:col-span-2"><label class="block text-xs text-gray-500 mb-1">Outcome Summary</label>
                        <input type="text" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="outcome_summary" value="${this._esc(item.outcome_summary || '')}"></div>
                    <div class="sm:col-span-2"><label class="block text-xs text-gray-500 mb-1">Lessons Learned</label>
                        <input type="text" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="lessons_learned" value="${this._esc(item.lessons_learned || '')}"></div>
                    <div class="sm:col-span-2"><label class="block text-xs text-gray-500 mb-1">Action Items</label>
                        <input type="text" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="action_items" value="${this._esc(item.action_items || '')}"></div>
                    <div class="sm:col-span-2"><label class="block text-xs text-gray-500 mb-1">Notes</label>
                        <input type="text" class="edit-field w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 dark:bg-gray-700 dark:text-white" data-field="notes" value="${this._esc(item.notes || '')}"></div>
                </div>
                <div class="flex items-center gap-3">
                    <button class="item-save-btn text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded font-medium" data-id="${item.id}">Save</button>
                    <button class="item-cancel-btn text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" data-id="${item.id}">Cancel</button>
                </div>
            </div>`;
    }

    _renderHotwashAddForm(container) {
        container.innerHTML = `
            <div class="mt-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                <h5 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Add Hotwash Entry Manually</h5>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                    <div class="sm:col-span-2"><label class="block text-xs text-gray-500 mb-1">Opportunity Name *</label>
                        <input id="add-opp-name" type="text" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white" placeholder="Opportunity name"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Conducted Date</label>
                        <input id="add-conducted-date" type="date" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white"></div>
                    <div><label class="block text-xs text-gray-500 mb-1">Participants</label>
                        <input id="add-participants" type="text" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white" placeholder="Names or roles"></div>
                    <div class="sm:col-span-2"><label class="block text-xs text-gray-500 mb-1">Outcome Summary</label>
                        <input id="add-outcome" type="text" class="w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 dark:bg-gray-700 dark:text-white" placeholder="Brief outcome"></div>
                </div>
                <button id="add-tracking-item-btn" class="px-4 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded font-medium">Add Hotwash</button>
            </div>`;
    }

    // -------------------------------------------------------------------------
    // Event binding
    // -------------------------------------------------------------------------

    _bindItemEvents() {
        document.querySelectorAll('.item-edit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._editingId = btn.dataset.id;
                this._renderItems();
            });
        });

        document.querySelectorAll('.item-cancel-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._editingId = null;
                this._renderItems();
            });
        });

        document.querySelectorAll('.item-save-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const card = btn.closest('[data-item-id]');
                const fields = {};
                card.querySelectorAll('.edit-field').forEach(el => {
                    if (el.type === 'checkbox') fields[el.dataset.field] = el.checked;
                    else if (el.value !== '') fields[el.dataset.field] = el.type === 'number' ? Number(el.value) : el.value;
                });
                await this._save(btn.dataset.id, fields);
                this._editingId = null;
                this._load();
            });
        });

        document.querySelectorAll('.item-delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm(`Delete entry for "${btn.dataset.name}"?`)) return;
                await this._delete(btn.dataset.id);
                this._load();
            });
        });

        document.getElementById('add-tracking-item-btn')?.addEventListener('click', async () => {
            const name = document.getElementById('add-opp-name')?.value.trim();
            if (!name) return;

            const fields = { opportunity_name: name };
            if (this._current === 'proposals') {
                fields.goldenrod_date  = document.getElementById('add-goldenrod')?.value || '';
                fields.submission_date = document.getElementById('add-submission')?.value || '';
                const price = document.getElementById('add-price')?.value;
                if (price) fields.proposal_price = Number(price);
                fields.contract_type   = document.getElementById('add-contract')?.value || '';
                fields.agreement_type  = document.getElementById('add-agreement')?.value || '';
            } else if (this._current === 'hotwash') {
                fields.conducted_date  = document.getElementById('add-conducted-date')?.value || '';
                fields.participants    = document.getElementById('add-participants')?.value || '';
                fields.outcome_summary = document.getElementById('add-outcome')?.value || '';
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
