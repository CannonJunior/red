/**
 * Shipley Capture Intelligence Panel — Core (Win Strategy + Customer Contacts)
 *
 * Renders a 5-tab panel for each selected opportunity. Competitors, Activities,
 * and PTW tab methods live in capture-intel.js, which extends this prototype.
 *
 * Listens for custom DOM events:
 *   opportunitySelected  { detail: { id } }
 *   opportunityDeselected
 */

const SHIPLEY_GATES = [
    { num: 0, name: 'Opportunity Identification',  desc: 'Pipeline entry, initial customer intel, Go/No-Go criteria check' },
    { num: 1, name: 'Opportunity Qualification',   desc: 'Customer need confirmed, 3+ contacts, budget identified, capture plan started' },
    { num: 2, name: 'Bid Decision (Go/No-Go)',     desc: 'B/NB assessment done, win strategy drafted, PTW target set, teaming decided' },
    { num: 3, name: 'Strategy Review (Pink Team)', desc: 'Win themes finalized, discriminators documented, ghosting strategies defined' },
    { num: 4, name: 'Proposal Review (Red Team)',  desc: 'Draft complete, compliance matrix verified, color team reviews conducted' },
    { num: 5, name: 'Pre-Submission (Gold Team)',  desc: 'Exec summary approved, pricing within PTW, final compliance check passed' },
];

const ROLE_COLORS = {
    'Decision Maker':     'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300',
    'KO':                 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300',
    'PM':                 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300',
    'Technical Evaluator':'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300',
    'Influencer':         'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300',
    'User':               'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
};

// Shared CSS for form inputs (referenced from both capture.js and capture-intel.js)
const CAPTURE_INPUT_CLS = 'border border-gray-300 dark:border-gray-500 rounded px-2 py-1 bg-white dark:bg-gray-800 text-gray-900 dark:text-white';

class CapturePanel {
    constructor() {
        this.oppId = null;
        this.activeTab = 'win-strategy';
        this._panel = document.getElementById('capture-panel');
        this._content = document.getElementById('capture-tab-content');
        this._setupTabs();
        document.addEventListener('opportunitySelected', e => this.load(e.detail.id));
        document.addEventListener('opportunityDeselected', () => this.hide());
    }

    load(oppId) {
        this.oppId = oppId;
        if (this._panel) this._panel.classList.remove('hidden');
        this._renderTab(this.activeTab);
    }

    hide() {
        this.oppId = null;
        if (this._panel) this._panel.classList.add('hidden');
    }

    _setupTabs() {
        document.querySelectorAll('.capture-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.capture-tab').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.activeTab = btn.dataset.tab;
                if (this.oppId) this._renderTab(this.activeTab);
            });
        });
    }

    _renderTab(tab) {
        const map = {
            'win-strategy': () => this._renderWinStrategy(),
            'contacts':     () => this._renderContacts(),
            'competitors':  () => this._renderCompetitors(),
            'activities':   () => this._renderActivities(),
            'ptw':          () => this._renderPTW(),
        };
        if (map[tab]) map[tab](); else this._setError(`Unknown tab: ${tab}`);
    }

    // ---- Win Strategy -------------------------------------------------------

    async _renderWinStrategy() {
        this._setLoading();
        try {
            const res = await fetch(`/api/opportunities/${this.oppId}/win-strategy`);
            const data = await res.json();
            const ws = data.win_strategy || {};
            const pwin = Math.round((ws.pwin_score || 0) * 100);
            const gateRows = SHIPLEY_GATES.map(g => {
                const done = ws[`gate_${g.num}_complete`];
                const dt = ws[`gate_${g.num}_date`] || '';
                const bg = done ? 'bg-green-50 dark:bg-green-950' : 'bg-gray-50 dark:bg-gray-700';
                const numCls = done ? 'text-green-700 dark:text-green-300' : 'text-gray-500';
                const dateFld = done
                    ? `<input type="date" class="gate-date mt-1 text-xs border border-gray-300 dark:border-gray-600 rounded px-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300" data-gate="${g.num}" value="${dt}">`
                    : '';
                return `<div class="flex items-start gap-3 p-2 rounded ${bg}">
                    <input type="checkbox" class="gate-check mt-1 cursor-pointer" data-gate="${g.num}" ${done ? 'checked' : ''}>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-xs font-bold ${numCls}">Gate ${g.num}</span>
                            <span class="text-sm font-medium text-gray-900 dark:text-white">${g.name}</span>
                            ${done ? '<span class="text-xs text-green-600 dark:text-green-400">✓ Complete</span>' : ''}
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${g.desc}</p>${dateFld}
                    </div></div>`;
            }).join('');
            this._content.innerHTML = `<div class="space-y-4">
                <div class="flex items-center gap-4">
                    <div class="flex-1">
                        <label class="text-sm font-medium text-gray-700 dark:text-gray-300">pWin Score</label>
                        <div class="flex items-center gap-3 mt-1">
                            <input type="range" id="ws-pwin" min="0" max="100" value="${pwin}" class="flex-1 h-2 rounded-lg">
                            <span id="ws-pwin-label" class="text-lg font-bold w-14 text-center ${pwin >= 60 ? 'text-green-600' : pwin >= 40 ? 'text-yellow-600' : 'text-red-600'}">${pwin}%</span>
                        </div>
                    </div>
                </div>
                <div>
                    <h6 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Shipley Gate Progress</h6>
                    <div class="space-y-1">${gateRows}</div>
                </div>
                ${this._pillEditor('Win Themes (what you say)', 'ws-win-themes', ws.win_themes || [], 'green')}
                ${this._pillEditor('Discriminators (what you uniquely offer)', 'ws-discriminators', ws.discriminators || [], 'blue')}
                ${this._pillEditor('Ghosts (competitor weaknesses to exploit)', 'ws-ghosts', ws.ghosts || [], 'orange')}
                <div>
                    <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Customer Hot Buttons Summary</label>
                    <textarea id="ws-hot-buttons" rows="2" class="mt-1 w-full text-sm border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white">${ws.customer_hot_buttons_summary || ''}</textarea>
                </div>
                <div>
                    <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Notes</label>
                    <textarea id="ws-notes" rows="2" class="mt-1 w-full text-sm border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white">${ws.notes || ''}</textarea>
                </div>
                <button id="ws-save-btn" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700">Save Win Strategy</button>
            </div>`;
            document.getElementById('ws-pwin').addEventListener('input', e => {
                document.getElementById('ws-pwin-label').textContent = e.target.value + '%';
            });
            document.getElementById('ws-save-btn').addEventListener('click', () => this._saveWinStrategy());
            document.querySelectorAll('.gate-check').forEach(cb => cb.addEventListener('change', () => this._saveWinStrategy()));
        } catch (e) { this._setError(e.message); }
    }

    _pillEditor(label, id, items, color) {
        const cls = `bg-${color}-100 dark:bg-${color}-900 text-${color}-700 dark:text-${color}-300`;
        const pills = items.map((t, i) =>
            `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${cls}">${t}<button class="rm-pill hover:text-red-500" data-idx="${i}" data-field="${id}">×</button></span>`).join('');
        return `<div>
            <label class="text-sm font-medium text-gray-700 dark:text-gray-300">${label}</label>
            <div id="${id}-pills" class="flex flex-wrap gap-1 mt-1 min-h-6">${pills}</div>
            <div class="flex gap-2 mt-1">
                <input id="${id}-input" type="text" placeholder="Add item…" class="flex-1 text-sm ${CAPTURE_INPUT_CLS}">
                <button class="add-pill px-2 py-1 text-sm bg-gray-200 dark:bg-gray-600 rounded hover:bg-gray-300 dark:hover:bg-gray-500" data-field="${id}">+</button>
            </div>
        </div>`;
    }

    async _saveWinStrategy() {
        const pwin = parseInt(document.getElementById('ws-pwin')?.value || 0) / 100;
        const payload = {
            pwin_score: pwin,
            win_themes:     this._getPills('ws-win-themes'),
            discriminators: this._getPills('ws-discriminators'),
            ghosts:         this._getPills('ws-ghosts'),
            customer_hot_buttons_summary: document.getElementById('ws-hot-buttons')?.value || '',
            notes: document.getElementById('ws-notes')?.value || '',
        };
        document.querySelectorAll('.gate-check').forEach(cb => {
            const g = cb.dataset.gate;
            payload[`gate_${g}_complete`] = cb.checked;
            const dt = document.querySelector(`.gate-date[data-gate="${g}"]`);
            payload[`gate_${g}_date`] = dt ? dt.value : '';
        });
        await fetch(`/api/opportunities/${this.oppId}/win-strategy`, {
            method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
        });
    }

    _getPills(fieldId) {
        return Array.from(document.querySelectorAll(`#${fieldId}-pills span`))
            .map(s => s.firstChild.textContent.trim()).filter(Boolean);
    }

    // ---- Customer Contacts --------------------------------------------------

    async _renderContacts() {
        this._setLoading();
        try {
            const res = await fetch(`/api/opportunities/${this.oppId}/contacts`);
            const { contacts = [] } = await res.json();
            const cards = contacts.length ? contacts.map(c => this._contactCard(c)).join('')
                : '<p class="text-gray-500 dark:text-gray-400 text-sm">No contacts yet.</p>';
            this._content.innerHTML = `
                <div class="mb-3 flex items-center justify-between">
                    <h6 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Customer Stakeholders</h6>
                    <button id="add-contact-btn" class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">+ Add Contact</button>
                </div>
                <div id="contacts-list" class="grid grid-cols-1 gap-3 sm:grid-cols-2">${cards}</div>
                <div id="contact-form" class="hidden mt-4 p-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
                    ${this._contactFormHTML()}
                    <div class="flex gap-2 mt-3">
                        <button id="contact-save-btn" class="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700">Save</button>
                        <button id="contact-cancel-btn" class="px-3 py-1.5 text-sm bg-gray-400 text-white rounded-md hover:bg-gray-500">Cancel</button>
                    </div>
                </div>`;
            document.getElementById('add-contact-btn').addEventListener('click', () =>
                document.getElementById('contact-form').classList.toggle('hidden'));
            document.getElementById('contact-cancel-btn').addEventListener('click', () =>
                document.getElementById('contact-form').classList.add('hidden'));
            document.getElementById('contact-save-btn').addEventListener('click', () => this._saveContact());
            document.querySelectorAll('.delete-contact').forEach(btn =>
                btn.addEventListener('click', e => this._deleteContact(e.target.dataset.id)));
        } catch (e) { this._setError(e.message); }
    }

    _contactCard(c) {
        const roleCls = ROLE_COLORS[c.role] || ROLE_COLORS['User'];
        const stars = Array.from({length:5}, (_, i) =>
            `<span class="${i < c.relationship_strength ? 'text-yellow-400' : 'text-gray-300'}">★</span>`).join('');
        const hotBtns = (c.hot_buttons || []).map(h =>
            `<span class="px-1.5 py-0.5 text-xs bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300 rounded">${h}</span>`).join('');
        return `<div class="p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg">
            <div class="flex items-start justify-between gap-2">
                <div><p class="text-sm font-semibold text-gray-900 dark:text-white">${c.name}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400">${c.title}${c.org ? ` · ${c.org}` : ''}</p>
                </div>
                <div class="flex items-center gap-1 flex-shrink-0">
                    <span class="px-2 py-0.5 text-xs font-medium rounded ${roleCls}">${c.role}</span>
                    <button class="delete-contact text-xs text-gray-400 hover:text-red-500" data-id="${c.id}">✕</button>
                </div>
            </div>
            <div class="flex items-center gap-1 mt-1 text-sm">${stars}</div>
            ${hotBtns ? `<div class="flex flex-wrap gap-1 mt-2">${hotBtns}</div>` : ''}
            ${c.notes ? `<p class="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">${c.notes}</p>` : ''}
        </div>`;
    }

    _contactFormHTML() {
        const roles = ['Decision Maker','KO','PM','Technical Evaluator','Influencer','User'];
        const i = CAPTURE_INPUT_CLS;
        return `<div class="grid grid-cols-2 gap-2 text-sm">
            <input id="cf-name" placeholder="Name *" class="col-span-2 ${i}">
            <input id="cf-title" placeholder="Title" class="${i}">
            <input id="cf-org" placeholder="Organization" class="${i}">
            <select id="cf-role" class="${i}">${roles.map(r=>`<option value="${r}">${r}</option>`).join('')}</select>
            <input id="cf-strength" type="number" min="1" max="5" value="3" placeholder="Rel. strength (1-5)" class="${i}">
            <input id="cf-hot-buttons" placeholder="Hot buttons (comma-sep)" class="col-span-2 ${i}">
            <input id="cf-last-contact" type="date" class="${i}">
            <textarea id="cf-notes" placeholder="Notes" rows="2" class="col-span-2 ${i}"></textarea>
        </div>`;
    }

    async _saveContact() {
        const hb = (document.getElementById('cf-hot-buttons')?.value || '').split(',').map(s=>s.trim()).filter(Boolean);
        const g = id => document.getElementById(id);
        const payload = { name: g('cf-name')?.value, title: g('cf-title')?.value, org: g('cf-org')?.value,
            role: g('cf-role')?.value, relationship_strength: parseInt(g('cf-strength')?.value||3),
            hot_buttons: hb, last_contact_date: g('cf-last-contact')?.value, notes: g('cf-notes')?.value };
        await fetch(`/api/opportunities/${this.oppId}/contacts`, {
            method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
        });
        this._renderContacts();
    }

    async _deleteContact(id) {
        await fetch(`/api/opportunities/${this.oppId}/contacts/${id}`, { method: 'DELETE' });
        this._renderContacts();
    }

    // ---- Utilities ----------------------------------------------------------

    _setLoading() {
        if (this._content) this._content.innerHTML =
            '<div class="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-sm py-4"><div class="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div> Loading…</div>';
    }

    _setError(msg) {
        if (this._content) this._content.innerHTML = `<p class="text-red-500 text-sm py-4">Error: ${msg}</p>`;
    }
}

// Initialise on DOM ready; also handle add-pill / rm-pill events via delegation
document.addEventListener('DOMContentLoaded', () => {
    window.capturePanel = new CapturePanel();

    document.addEventListener('click', e => {
        const addBtn = e.target.closest('.add-pill');
        if (addBtn) {
            const field = addBtn.dataset.field;
            const input = document.getElementById(`${field}-input`);
            const val = input?.value?.trim();
            if (!val) return;
            const container = document.getElementById(`${field}-pills`);
            const colorMatch = field.match(/ws-(win-themes|discriminators|ghosts)/);
            const color = colorMatch
                ? (colorMatch[1]==='ws-win-themes' ? 'green' : colorMatch[1]==='ws-discriminators' ? 'blue' : 'orange')
                : 'gray';
            const cls = `bg-${color}-100 dark:bg-${color}-900 text-${color}-700 dark:text-${color}-300`;
            const span = document.createElement('span');
            span.className = `inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${cls}`;
            span.innerHTML = `${val}<button class="rm-pill hover:text-red-500" data-field="${field}">×</button>`;
            container?.appendChild(span);
            if (input) input.value = '';
        }
        const rmBtn = e.target.closest('.rm-pill');
        if (rmBtn) rmBtn.closest('span')?.remove();
    });
});
