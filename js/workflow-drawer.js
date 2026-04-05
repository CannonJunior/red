/**
 * Workflow Kanban — Inline Card Expander
 *
 * Overrides WorkflowsManager._navigateToDetail so that clicking a card
 * expands it in-place within its Kanban column, showing the full opportunity
 * detail without navigating away or opening any overlay panel.
 *
 * Mixed into WorkflowsManager.prototype after workflows.js loads.
 */

/* eslint-disable no-unused-vars */

/**
 * Toggle the inline detail panel for the clicked card.
 * Collapses any other open card first.
 *
 * @param {string} cardId
 */
function _wod_navigateToDetail(cardId) {
    if (!cardId) return;

    const card = document.querySelector(`.kanban-card[data-id="${CSS.escape(cardId)}"]`);
    if (!card) return;

    // Toggle: already expanded → collapse
    if (card.dataset.wdExpanded === '1') {
        this._inlineCollapseCard(card);
        return;
    }

    // Collapse any other expanded card first
    document.querySelectorAll('.kanban-card[data-wd-expanded="1"]').forEach(other => {
        this._inlineCollapseCard(other);
    });

    const opp = this.opportunities.find(o => (o.id || o.proposal_id) === cardId);
    if (opp) {
        this._inlineExpandCard(card, opp);
    } else {
        fetch(`${this.baseUrl}/api/opportunities/${cardId}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                const fetched = data?.opportunity || data;
                if (fetched) this._inlineExpandCard(card, fetched);
            })
            .catch(() => {});
    }
}

/**
 * Expand the card inline with the full opportunity detail panel.
 *
 * @param {HTMLElement} card
 * @param {Object}      opp
 */
function _wod_inlineExpandCard(card, opp) {
    // Hide the simple task-pills panel while detail is open
    const tasksPill = card.querySelector('.kanban-tasks-panel');
    if (tasksPill) tasksPill.classList.add('hidden');

    // Build and inject detail panel (initially height=0 for animation)
    const panel = this._buildInlinePanel(opp);
    panel.style.cssText = 'max-height:0;overflow:hidden;opacity:0;' +
        'transition:max-height 0.28s ease,opacity 0.2s ease';
    card.appendChild(panel);

    // Trigger expansion on next frame so transition fires
    requestAnimationFrame(() => {
        panel.style.maxHeight = panel.scrollHeight + 200 + 'px'; // +200 for tasks load
        panel.style.opacity   = '1';
    });

    card.dataset.wdExpanded = '1';

    // Wire collapse button
    panel.querySelector('.wod-collapse-btn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        this._inlineCollapseCard(card);
    });

    // Wire "open full view" button
    panel.querySelector('.wod-open-full-btn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        this._inlineCollapseCard(card);
        const oppId = opp.id || opp.proposal_id;
        if (window.app?.opportunitiesManager && oppId) {
            window.app.navigateTo('opportunities');
            window.app.opportunitiesManager.showOpportunityDetail(opp);
        }
    });

    // Load tasks into the inline panel
    const taskContainer = panel.querySelector('.wod-inline-tasks');
    if (taskContainer) {
        this._loadTasksIntoPanel(taskContainer, opp.id || opp.proposal_id).then(() => {
            // Grow max-height now that tasks have rendered
            panel.style.maxHeight = panel.scrollHeight + 'px';
        });
    }
}

/**
 * Collapse and remove the inline detail panel from a card.
 *
 * @param {HTMLElement} card
 */
function _wod_inlineCollapseCard(card) {
    const panel = card.querySelector('.wod-inline-panel');
    if (!panel) return;

    panel.style.maxHeight = '0';
    panel.style.opacity   = '0';

    setTimeout(() => {
        panel.remove();
        // Restore the task-pills panel to its previous visibility state
        const tasksPill = card.querySelector('.kanban-tasks-panel');
        const svg = card.querySelector('button svg');
        if (tasksPill && svg?.style.transform === 'rotate(180deg)') {
            tasksPill.classList.remove('hidden');
        }
        delete card.dataset.wdExpanded;
    }, 280);
}

/**
 * Build the DOM element for the inline detail panel.
 *
 * @param {Object} opp  Opportunity object.
 * @returns {HTMLElement}
 */
function _wod_buildInlinePanel(opp) {
    const oppId    = opp.id || opp.proposal_id || '';
    const stage    = opp.pipeline_stage || opp.status || 'identified';
    const priority = opp.priority || 'medium';
    const value    = opp.estimated_value ?? opp.value ?? null;
    const desc     = opp.description || opp.notes || '';
    const tags     = opp.tags || [];
    const created  = opp.created_at ? new Date(opp.created_at).toLocaleDateString() : '';

    // Stage badge colors
    const stageColorCls = (KANBAN_STAGES.find(s => s.localStages.includes(stage)) || KANBAN_STAGES[0]).colorClass;
    const stageLabel    = this._stageLabel(stage);

    // Priority badge colors
    const priColors = {
        high:   'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
        medium: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300',
        low:    'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
    };
    const priLabel = priority.charAt(0).toUpperCase() + priority.slice(1);

    // Value chip
    let valueFormatted = '';
    if (value != null && value > 0) {
        valueFormatted = value >= 1e6
            ? `$${(value / 1e6).toFixed(1)}M`
            : value >= 1000
                ? `$${(value / 1000).toFixed(0)}K`
                : `$${value}`;
    }

    // Gov-specific fields
    const solicitation = opp.solicitation_number || '';
    const naics        = opp.naics_code
        ? `${opp.naics_code}${opp.naics_description ? ' — ' + opp.naics_description : ''}`
        : '';
    const setAside = opp.set_aside_type && opp.set_aside_type !== 'unknown'
        ? opp.set_aside_type : '';
    const pwin = opp.pwin_score != null
        ? `${Math.round(opp.pwin_score * 100)}%` : '';
    const hasGov = solicitation || naics || setAside || pwin;

    const esc = s => String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');

    const panel = document.createElement('div');
    panel.className = 'wod-inline-panel border-t border-gray-200 dark:border-gray-600 ' +
        'bg-gray-50 dark:bg-gray-900/30 rounded-b-lg';

    panel.innerHTML = `
        <!-- Toolbar: collapse + open full -->
        <div class="flex items-center justify-between px-3 pt-2.5 pb-1.5">
            <button class="wod-collapse-btn flex items-center gap-1 text-xs text-gray-400
                           hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    title="Collapse">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5"
                          d="M5 15l7-7 7 7"/>
                </svg>
                Collapse
            </button>
            <button class="wod-open-full-btn text-xs text-blue-600 dark:text-blue-400
                           hover:underline transition-colors" title="Open full view">
                Full view →
            </button>
        </div>

        <!-- Stage / Priority / Value badges -->
        <div class="flex flex-wrap gap-1 px-3 pb-2">
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${esc(stageColorCls)}">
                ${esc(stageLabel)}
            </span>
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold
                         ${priColors[priority] || priColors.medium}">
                ${esc(priLabel)}
            </span>
            ${valueFormatted ? `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold
                         bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200">
                ${esc(valueFormatted)}
            </span>` : ''}
        </div>

        <!-- Metadata grid -->
        <div class="grid grid-cols-2 gap-x-2 gap-y-1.5 px-3 pb-2.5 text-xs">
            ${opp.agency || opp.client_name ? `
            <div class="col-span-2">
                <span class="text-gray-400 dark:text-gray-500">Agency</span>
                <div class="text-gray-800 dark:text-gray-200 font-medium truncate">
                    ${esc(opp.agency || opp.client_name || '')}
                </div>
            </div>` : ''}
            ${this._formatDue(opp.proposal_due_date || opp.due_date) !== '—' ? `
            <div>
                <span class="text-gray-400 dark:text-gray-500">Due</span>
                <div class="text-gray-800 dark:text-gray-200">${esc(this._formatDue(opp.proposal_due_date || opp.due_date))}</div>
            </div>` : ''}
            ${value != null ? `
            <div>
                <span class="text-gray-400 dark:text-gray-500">Value</span>
                <div class="text-gray-800 dark:text-gray-200">$${Number(value).toLocaleString()}</div>
            </div>` : ''}
            ${created ? `
            <div>
                <span class="text-gray-400 dark:text-gray-500">Created</span>
                <div class="text-gray-800 dark:text-gray-200">${esc(created)}</div>
            </div>` : ''}
        </div>

        ${desc.trim() ? `
        <!-- Description -->
        <div class="px-3 pb-2.5">
            <div class="text-xs text-gray-400 dark:text-gray-500 font-medium mb-1">Description</div>
            <div class="text-xs text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800
                        rounded-md p-2 border border-gray-200 dark:border-gray-700
                        max-h-24 overflow-y-auto whitespace-pre-line">${esc(desc)}</div>
        </div>` : ''}

        ${tags.length > 0 ? `
        <!-- Tags -->
        <div class="px-3 pb-2.5">
            <div class="text-xs text-gray-400 dark:text-gray-500 font-medium mb-1">Tags</div>
            <div class="flex flex-wrap gap-1">
                ${tags.map(t => `<span class="px-1.5 py-0.5 text-xs rounded
                    bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200">${esc(t)}</span>`).join('')}
            </div>
        </div>` : ''}

        ${hasGov ? `
        <!-- Gov fields -->
        <div class="grid grid-cols-2 gap-x-2 gap-y-1.5 px-3 pb-2.5 text-xs
                    border-t border-gray-200 dark:border-gray-700 pt-2">
            ${solicitation ? `<div class="col-span-2">
                <span class="text-gray-400 dark:text-gray-500">Solicitation #</span>
                <div class="text-gray-800 dark:text-gray-200 font-mono break-all">${esc(solicitation)}</div>
            </div>` : ''}
            ${naics ? `<div class="col-span-2">
                <span class="text-gray-400 dark:text-gray-500">NAICS</span>
                <div class="text-gray-800 dark:text-gray-200">${esc(naics)}</div>
            </div>` : ''}
            ${setAside ? `<div>
                <span class="text-gray-400 dark:text-gray-500">Set-Aside</span>
                <div class="text-gray-800 dark:text-gray-200">${esc(setAside)}</div>
            </div>` : ''}
            ${pwin ? `<div>
                <span class="text-gray-400 dark:text-gray-500">pWin</span>
                <div class="text-gray-800 dark:text-gray-200 font-semibold">${esc(pwin)}</div>
            </div>` : ''}
        </div>` : ''}

        <!-- Tasks -->
        <div class="border-t border-gray-200 dark:border-gray-700 px-3 pt-2 pb-3">
            <div class="text-xs text-gray-400 dark:text-gray-500 font-medium mb-1.5">Tasks</div>
            <div class="wod-inline-tasks flex flex-wrap gap-1.5">
                <div class="text-xs text-gray-400 dark:text-gray-500 italic">Loading tasks…</div>
            </div>
        </div>
    `;

    return panel;
}

/**
 * Map a pipeline_stage value to a human-readable label.
 *
 * @param {string} stage
 * @returns {string}
 */
function _wod_stageLabel(stage) {
    const labels = {
        identified: '01 — Qualification', qualifying: '01 — Qualification',
        long_lead: '02 — Long Lead', bid_decision: '03 — Bid Decision',
        active: '04 — In Progress', submitted: '05 — Waiting/Review',
        negotiating: '06 — In Negotiation', awarded: '07 — Closed Won',
        lost: '08 — Closed Lost', no_bid: '09 — Closed No Bid',
        cancelled: '20 — Closed Other',
        contract_vehicle_won: '98 — Contract Vehicle',
        contract_vehicle_complete: '99 — Completed Vehicle',
    };
    return labels[stage] || stage;
}

/**
 * Format a due-date string with overdue/urgency annotation.
 *
 * @param {string} dateStr  ISO date string.
 * @returns {string}
 */
function _wod_formatDue(dateStr) {
    if (!dateStr) return '—';
    try {
        const d        = new Date(dateStr);
        const diffDays = Math.ceil((d - new Date()) / 86400000);
        const formatted = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        if (diffDays < 0)  return `${formatted} (overdue)`;
        if (diffDays <= 7) return `${formatted} (${diffDays}d)`;
        return formatted;
    } catch (_) {
        return dateStr;
    }
}

// ── Mix into WorkflowsManager ────────────────────────────────────────────────
(function applyInlineExpandMixin() {
    if (typeof WorkflowsManager === 'undefined') {
        console.warn('workflow-drawer.js: WorkflowsManager not found — mixin skipped');
        return;
    }
    WorkflowsManager.prototype._navigateToDetail   = _wod_navigateToDetail;
    WorkflowsManager.prototype._inlineExpandCard   = _wod_inlineExpandCard;
    WorkflowsManager.prototype._inlineCollapseCard = _wod_inlineCollapseCard;
    WorkflowsManager.prototype._buildInlinePanel   = _wod_buildInlinePanel;
    WorkflowsManager.prototype._stageLabel         = _wod_stageLabel;
    WorkflowsManager.prototype._formatDue          = _wod_formatDue;
})();
