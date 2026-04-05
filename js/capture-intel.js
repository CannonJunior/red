/**
 * Shipley Capture Intelligence Panel — Market Intel Extension
 *
 * Extends CapturePanel.prototype with:
 *   _renderCompetitors, _renderActivities, _renderPTW
 * and their supporting helpers.
 *
 * Must be loaded AFTER capture.js.
 */

/* eslint-disable no-undef */

const ACT_ICONS = {
    'Meeting': '🤝', 'Call': '📞', 'Email': '📧', 'Conference': '🎤',
    'Site Visit': '🏢', 'Industry Day': '📅', 'RFI Response': '📋',
};

Object.assign(CapturePanel.prototype, {

    // ---- Competitive Intelligence -------------------------------------------

    async _renderCompetitors() {
        this._setLoading();
        try {
            const { competitors = [] } = await (await fetch(`/api/opportunities/${this.oppId}/competitors`)).json();
            const cards = competitors.length
                ? competitors.map(c => this._competitorCard(c)).join('')
                : '<p class="text-gray-500 dark:text-gray-400 text-sm">No competitors tracked yet.</p>';
            this._content.innerHTML = `
                <div class="mb-3 flex items-center justify-between">
                    <div>
                        <h6 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Competitive Landscape</h6>
                        <p class="text-xs text-gray-500 dark:text-gray-400">Tip: Ask "How would [Competitor] attack our proposal?" — Black Hat review</p>
                    </div>
                    <button id="add-comp-btn" class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">+ Add Competitor</button>
                </div>
                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">${cards}</div>
                <div id="comp-form" class="hidden mt-4 p-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
                    ${this._compFormHTML()}
                    <div class="flex gap-2 mt-3">
                        <button id="comp-save-btn" class="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700">Save</button>
                        <button id="comp-cancel-btn" class="px-3 py-1.5 text-sm bg-gray-400 text-white rounded-md hover:bg-gray-500">Cancel</button>
                    </div>
                </div>`;
            document.getElementById('add-comp-btn').addEventListener('click', () =>
                document.getElementById('comp-form').classList.toggle('hidden'));
            document.getElementById('comp-cancel-btn').addEventListener('click', () =>
                document.getElementById('comp-form').classList.add('hidden'));
            document.getElementById('comp-save-btn').addEventListener('click', () => this._saveCompetitor());
            document.querySelectorAll('.delete-comp').forEach(b =>
                b.addEventListener('click', e => this._deleteCompetitor(e.target.dataset.id)));
        } catch (e) { this._setError(e.message); }
    },

    _competitorCard(c) {
        const bidColor = c.likely_bid === 'Yes' ? 'text-red-600' : c.likely_bid === 'No' ? 'text-green-600' : 'text-yellow-600';
        const strs = (c.strengths||[]).map(s=>`<li class="text-xs">${s}</li>`).join('');
        const weaks = (c.weaknesses||[]).map(w=>`<li class="text-xs">${w}</li>`).join('');
        return `<div class="p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg">
            <div class="flex items-center justify-between gap-2 mb-2">
                <div class="flex items-center gap-2">
                    <p class="text-sm font-semibold text-gray-900 dark:text-white">${c.company_name}</p>
                    ${c.is_incumbent ? '<span class="px-1.5 py-0.5 text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded font-medium">INCUMBENT</span>' : ''}
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                    <span class="text-xs font-medium ${bidColor}">Bid: ${c.likely_bid}</span>
                    <button class="delete-comp text-xs text-gray-400 hover:text-red-500" data-id="${c.id}">✕</button>
                </div>
            </div>
            ${c.estimated_price ? `<p class="text-xs text-gray-600 dark:text-gray-400 mb-1">Est. Price: $${(c.estimated_price/1e6).toFixed(2)}M</p>` : ''}
            <div class="grid grid-cols-2 gap-2 mt-1">
                ${strs ? `<div><p class="text-xs font-medium text-gray-500 mb-0.5">Strengths</p><ul class="text-green-700 dark:text-green-400 list-disc list-inside">${strs}</ul></div>` : ''}
                ${weaks ? `<div><p class="text-xs font-medium text-gray-500 mb-0.5">Weaknesses</p><ul class="text-red-600 dark:text-red-400 list-disc list-inside">${weaks}</ul></div>` : ''}
            </div>
            ${c.likely_approach ? `<p class="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">Approach: ${c.likely_approach}</p>` : ''}
        </div>`;
    },

    _compFormHTML() {
        const i = typeof CAPTURE_INPUT_CLS !== 'undefined' ? CAPTURE_INPUT_CLS : 'border border-gray-300 rounded px-2 py-1 bg-white text-gray-900';
        return `<div class="grid grid-cols-2 gap-2 text-sm">
            <input id="comp-name" placeholder="Company Name *" class="col-span-2 ${i}">
            <select id="comp-bid" class="${i}"><option value="Maybe">Likely to bid: Maybe</option><option value="Yes">Yes</option><option value="No">No</option></select>
            <input id="comp-price" type="number" placeholder="Est. price ($)" class="${i}">
            <label class="flex items-center gap-2 col-span-2 text-gray-700 dark:text-gray-300"><input id="comp-incumbent" type="checkbox"> Incumbent</label>
            <input id="comp-strengths" placeholder="Strengths (comma-sep)" class="col-span-2 ${i}">
            <input id="comp-weaknesses" placeholder="Weaknesses (comma-sep)" class="col-span-2 ${i}">
            <input id="comp-approach" placeholder="Likely approach/strategy" class="col-span-2 ${i}">
        </div>`;
    },

    async _saveCompetitor() {
        const split = id => (document.getElementById(id)?.value||'').split(',').map(s=>s.trim()).filter(Boolean);
        const g = id => document.getElementById(id);
        const payload = { company_name: g('comp-name')?.value, likely_bid: g('comp-bid')?.value,
            estimated_price: parseFloat(g('comp-price')?.value)||null,
            is_incumbent: g('comp-incumbent')?.checked,
            strengths: split('comp-strengths'), weaknesses: split('comp-weaknesses'),
            likely_approach: g('comp-approach')?.value };
        await fetch(`/api/opportunities/${this.oppId}/competitors`, {
            method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
        });
        this._renderCompetitors();
    },

    async _deleteCompetitor(id) {
        await fetch(`/api/opportunities/${this.oppId}/competitors/${id}`, { method: 'DELETE' });
        this._renderCompetitors();
    },

    // ---- Engagement Log -----------------------------------------------------

    async _renderActivities() {
        this._setLoading();
        try {
            const { activities = [] } = await (await fetch(`/api/opportunities/${this.oppId}/activities`)).json();
            const rows = activities.length ? activities.map(a => {
                const icon = ACT_ICONS[a.activity_type] || '📌';
                const cas = (a.customer_attendees||[]).join(', ');
                const ours = (a.our_attendees||[]).join(', ');
                const ais = (a.action_items||[]).map(ai=>`<li>${ai}</li>`).join('');
                return `<div class="p-3 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-sm font-medium text-gray-900 dark:text-white">${icon} ${a.activity_type} — ${a.activity_date}</span>
                        <button class="delete-act text-xs text-gray-400 hover:text-red-500" data-id="${a.id}">✕</button>
                    </div>
                    ${cas ? `<p class="text-xs text-gray-500">Customer: ${cas}</p>` : ''}
                    ${ours ? `<p class="text-xs text-gray-500">Our Team: ${ours}</p>` : ''}
                    ${a.topics_covered ? `<p class="text-xs text-gray-700 dark:text-gray-300 mt-1"><strong>Topics:</strong> ${a.topics_covered}</p>` : ''}
                    ${a.intelligence_gathered ? `<p class="text-xs text-blue-700 dark:text-blue-300 mt-1"><strong>Intel:</strong> ${a.intelligence_gathered}</p>` : ''}
                    ${ais ? `<div class="mt-1"><p class="text-xs font-medium text-gray-500">Action Items:</p><ul class="text-xs text-gray-700 dark:text-gray-300 list-disc list-inside">${ais}</ul></div>` : ''}
                    ${a.follow_up_required ? '<span class="text-xs text-orange-600 font-medium">⚠ Follow-up required</span>' : ''}
                </div>`;
            }).join('') : '<p class="text-gray-500 dark:text-gray-400 text-sm">No interactions logged yet.</p>';
            const today = new Date().toISOString().slice(0,10);
            const types = ['Meeting','Call','Email','Conference','Site Visit','Industry Day','RFI Response'];
            const i = typeof CAPTURE_INPUT_CLS !== 'undefined' ? CAPTURE_INPUT_CLS : 'border border-gray-300 rounded px-2 py-1 bg-white text-gray-900';
            this._content.innerHTML = `
                <div class="mb-3 flex items-center justify-between">
                    <h6 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Customer Engagement History</h6>
                    <button id="add-act-btn" class="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">+ Log Activity</button>
                </div>
                <div class="space-y-2 mb-4">${rows}</div>
                <div id="act-form" class="hidden p-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
                    <div class="grid grid-cols-2 gap-2 text-sm">
                        <input id="act-date" type="date" value="${today}" class="${i}">
                        <select id="act-type" class="${i}">${types.map(t=>`<option>${t}</option>`).join('')}</select>
                        <input id="act-cust" placeholder="Customer attendees (comma-sep)" class="col-span-2 ${i}">
                        <input id="act-ours" placeholder="Our attendees (comma-sep)" class="col-span-2 ${i}">
                        <textarea id="act-topics" placeholder="Topics covered" rows="2" class="col-span-2 ${i}"></textarea>
                        <textarea id="act-intel" placeholder="Intelligence gathered (hot buttons, concerns, biases…)" rows="2" class="col-span-2 ${i}"></textarea>
                        <input id="act-actions" placeholder="Action items (comma-sep)" class="col-span-2 ${i}">
                        <label class="flex items-center gap-2 text-gray-700 dark:text-gray-300"><input id="act-followup" type="checkbox"> Follow-up required</label>
                    </div>
                    <div class="flex gap-2 mt-3">
                        <button id="act-save-btn" class="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700">Log</button>
                        <button id="act-cancel-btn" class="px-3 py-1.5 text-sm bg-gray-400 text-white rounded-md hover:bg-gray-500">Cancel</button>
                    </div>
                </div>`;
            document.getElementById('add-act-btn').addEventListener('click', () =>
                document.getElementById('act-form').classList.toggle('hidden'));
            document.getElementById('act-cancel-btn').addEventListener('click', () =>
                document.getElementById('act-form').classList.add('hidden'));
            document.getElementById('act-save-btn').addEventListener('click', () => this._saveActivity());
            document.querySelectorAll('.delete-act').forEach(b =>
                b.addEventListener('click', e => this._deleteActivity(e.target.dataset.id)));
        } catch (e) { this._setError(e.message); }
    },

    async _saveActivity() {
        const split = id => (document.getElementById(id)?.value||'').split(',').map(s=>s.trim()).filter(Boolean);
        const g = id => document.getElementById(id);
        const payload = { activity_date: g('act-date')?.value, activity_type: g('act-type')?.value,
            customer_attendees: split('act-cust'), our_attendees: split('act-ours'),
            topics_covered: g('act-topics')?.value, intelligence_gathered: g('act-intel')?.value,
            action_items: split('act-actions'), follow_up_required: g('act-followup')?.checked };
        await fetch(`/api/opportunities/${this.oppId}/activities`, {
            method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
        });
        this._renderActivities();
    },

    async _deleteActivity(id) {
        await fetch(`/api/opportunities/${this.oppId}/activities/${id}`, { method: 'DELETE' });
        this._renderActivities();
    },

    // ---- Price-to-Win -------------------------------------------------------

    async _renderPTW() {
        this._setLoading();
        try {
            const { ptw: p = {} } = await (await fetch(`/api/opportunities/${this.oppId}/ptw`)).json();
            const fmt = v => v != null ? `$${(v/1e6).toFixed(3)}M` : '—';
            const gapColor = p.cost_gap != null
                ? (p.cost_gap >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400')
                : 'text-gray-500';
            const gapBg = p.cost_gap == null ? 'bg-gray-50 dark:bg-gray-700'
                : p.cost_gap >= 0 ? 'bg-green-50 dark:bg-green-950' : 'bg-red-50 dark:bg-red-950';
            const i = typeof CAPTURE_INPUT_CLS !== 'undefined' ? CAPTURE_INPUT_CLS : 'border border-gray-300 rounded px-2 py-1 bg-white text-gray-900';
            const wi = `mt-0.5 w-full ${i}`;
            this._content.innerHTML = `<div class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div class="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"><p class="text-xs text-gray-500 uppercase tracking-wide">PTW Target (Winning Price Window)</p><p class="text-xl font-bold text-gray-900 dark:text-white mt-0.5">${fmt(p.ptw_target)}</p></div>
                    <div class="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"><p class="text-xs text-gray-500 uppercase tracking-wide">Our Price (cost + fee)</p><p class="text-xl font-bold text-gray-900 dark:text-white mt-0.5">${fmt(p.our_price)}</p></div>
                    <div class="p-3 ${gapBg} rounded-lg col-span-2"><p class="text-xs text-gray-500 uppercase tracking-wide">PTW Gap (Target − Our Price)</p><p class="text-2xl font-bold ${gapColor} mt-0.5">${fmt(p.cost_gap)}${p.cost_gap != null ? (p.cost_gap >= 0 ? ' ✓ Competitive' : ' ✗ Over PTW — adjust strategy') : ''}</p></div>
                </div>
                <div class="grid grid-cols-2 gap-3 text-sm">
                    <div><label class="text-xs text-gray-500">PTW Target ($)</label><input id="ptw-target" type="number" value="${p.ptw_target||''}" class="${wi}"></div>
                    <div><label class="text-xs text-gray-500">Our Est. Cost ($)</label><input id="ptw-cost" type="number" value="${p.our_estimated_cost||''}" class="${wi}"></div>
                    <div><label class="text-xs text-gray-500">Fee/Profit %</label><input id="ptw-fee" type="number" step="0.1" value="${((p.fee_percent||0.08)*100).toFixed(1)}" class="${wi}"></div>
                    <div><label class="text-xs text-gray-500">Unanet ERP Project ID</label><input id="ptw-unanet" value="${p.unanet_project_id||''}" placeholder="Link to cost data" class="${wi}"></div>
                    <div><label class="text-xs text-gray-500">Competitor Low ($)</label><input id="ptw-comp-low" type="number" value="${p.competitor_price_low||''}" class="${wi}"></div>
                    <div><label class="text-xs text-gray-500">Competitor High ($)</label><input id="ptw-comp-high" type="number" value="${p.competitor_price_high||''}" class="${wi}"></div>
                    <div class="col-span-2"><label class="text-xs text-gray-500">Pricing Notes / Strategy</label><textarea id="ptw-notes" rows="2" class="${wi}">${p.pricing_notes||''}</textarea></div>
                </div>
                <p class="text-xs text-gray-400 dark:text-gray-500">Enter Unanet ERP Project ID to link actual cost data from your accounting system. Price-to-Win analysis follows Shipley's Winning Price Window methodology.</p>
                <button id="ptw-save-btn" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700">Save PTW Analysis</button>
            </div>`;
            document.getElementById('ptw-save-btn').addEventListener('click', () => this._savePTW());
        } catch (e) { this._setError(e.message); }
    },

    async _savePTW() {
        const g = id => document.getElementById(id);
        const payload = { ptw_target: parseFloat(g('ptw-target')?.value)||null,
            our_estimated_cost: parseFloat(g('ptw-cost')?.value)||null,
            fee_percent: (parseFloat(g('ptw-fee')?.value)||8)/100,
            unanet_project_id: g('ptw-unanet')?.value||'',
            competitor_price_low: parseFloat(g('ptw-comp-low')?.value)||null,
            competitor_price_high: parseFloat(g('ptw-comp-high')?.value)||null,
            pricing_notes: g('ptw-notes')?.value||'' };
        await fetch(`/api/opportunities/${this.oppId}/ptw`, {
            method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
        });
        this._renderPTW();
    },

});
