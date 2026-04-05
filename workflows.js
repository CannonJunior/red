/**
 * Workflows — Proposal Pipeline Kanban Board
 *
 * Displays all proposals as cards in vertical swim lanes, one per
 * Unanet CRM stage code. Horizontally scrollable.
 * Supports:
 *   - Drag-and-drop to move opportunities between stages
 *   - Per-card expand/collapse to reveal task pills
 *   - Global expand-all / collapse-all toggle
 */

const KANBAN_STAGES = [
    { code: '01-Qualification',     slug: '01-qual',       localStages: ['identified', 'qualifying'],          colorClass: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200',   headerClass: 'bg-blue-500' },
    { code: '02-Long Lead',         slug: '02-lead',       localStages: ['long_lead'],                         colorClass: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200', headerClass: 'bg-indigo-500' },
    { code: '03-Bid Decision',      slug: '03-bid',        localStages: ['bid_decision'],                      colorClass: 'bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-200', headerClass: 'bg-purple-500' },
    { code: '04-In Progress',       slug: '04-progress',   localStages: ['active'],                            colorClass: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-200', headerClass: 'bg-yellow-500' },
    { code: '05-Waiting/Review',    slug: '05-review',     localStages: ['submitted'],                         colorClass: 'bg-orange-100 dark:bg-orange-900/40 text-orange-800 dark:text-orange-200', headerClass: 'bg-orange-500' },
    { code: '06-In Negotiation',    slug: '06-nego',       localStages: ['negotiating'],                       colorClass: 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200',  headerClass: 'bg-amber-500' },
    { code: '07-Closed Won',        slug: '07-won',        localStages: ['awarded'],                           colorClass: 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200',  headerClass: 'bg-green-600' },
    { code: '08-Closed Lost',       slug: '08-lost',       localStages: ['lost'],                              colorClass: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200',     headerClass: 'bg-red-500' },
    { code: '09-Closed No Bid',     slug: '09-nobid',      localStages: ['no_bid'],                            colorClass: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300',     headerClass: 'bg-gray-500' },
    { code: '20-Closed Other',      slug: '20-other',      localStages: ['cancelled'],                         colorClass: 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300', headerClass: 'bg-slate-500' },
    { code: '98-Awarded Contract',  slug: '98-vehicle',    localStages: ['contract_vehicle_won'],              colorClass: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200', headerClass: 'bg-emerald-600' },
    { code: '99-Completed Contract',slug: '99-complete',   localStages: ['contract_vehicle_complete'],         colorClass: 'bg-teal-100 dark:bg-teal-900/40 text-teal-800 dark:text-teal-200', headerClass: 'bg-teal-600' },
];

const STAGE_MAP = {};
KANBAN_STAGES.forEach(s => s.localStages.forEach(ls => { STAGE_MAP[ls] = s.slug; }));

const SLUG_TO_STAGE = {};
KANBAN_STAGES.forEach(s => { SLUG_TO_STAGE[s.slug] = s.localStages[0]; });

// Task status → pill color
const TASK_STATUS_COLORS = {
    'pending':     'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200',
    'in_progress': 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300',
    'completed':   'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300',
    'blocked':     'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300',
    'done':        'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300',
};

class WorkflowsManager {
    constructor() {
        this.baseUrl     = '';
        this.opportunities = [];
        this._dragId      = null;
        this._isDragging  = false;
        this._allExpanded = false;
        // Cache: opportunityId → task array (fetched lazily)
        this._taskCache  = {};
    }

    async load() {
        const board = document.getElementById('kanban-board');
        if (!board) return;

        if (!board.children.length) {
            this._buildBoard(board);
            this._wireGlobalToggle();
        }

        document.querySelectorAll('.kanban-col-body').forEach(col => {
            col.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-500 px-2 py-3 text-center">Loading...</div>';
        });

        try {
            const res = await fetch(`${this.baseUrl}/api/opportunities`);
            const data = await res.json();
            this.opportunities = data.opportunities || data.items || data || [];
        } catch (e) {
            console.error('Workflows: failed to load opportunities', e);
            this.opportunities = [];
        }

        // Clear task cache on full reload so stale tasks aren't shown
        this._taskCache = {};
        this._allExpanded = false;
        this._syncExpandLabel();

        this._populateBoard();
    }

    // -----------------------------------------------------------------------
    // Board construction
    // -----------------------------------------------------------------------

    _buildBoard(board) {
        board.innerHTML = KANBAN_STAGES.map(stage => `
            <div class="kanban-col flex flex-col w-64 flex-shrink-0 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60">
                <div class="kanban-col-header px-3 py-2.5 ${stage.headerClass} flex items-center justify-between">
                    <span class="text-xs font-semibold text-white truncate">${stage.code}</span>
                    <span class="kanban-count ml-2 text-xs bg-white/30 text-white font-bold px-1.5 py-0.5 rounded-full flex-shrink-0" id="kcount-${stage.slug}">0</span>
                </div>
                <div class="kanban-col-body flex-1 overflow-y-auto p-2 space-y-2 min-h-[4rem]"
                     id="kcol-${stage.slug}"
                     data-slug="${stage.slug}">
                </div>
            </div>
        `).join('');

        board.querySelectorAll('.kanban-col-body').forEach(col => {
            col.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                col.classList.add('ring-2', 'ring-blue-400', 'dark:ring-blue-500', 'bg-blue-50/40', 'dark:bg-blue-900/10');
                let ph = col.querySelector('.drag-placeholder');
                if (!ph) {
                    ph = document.createElement('div');
                    ph.className = 'drag-placeholder h-14 rounded-lg border-2 border-dashed border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 pointer-events-none';
                }
                const after = this._dragAfterElement(col, e.clientY);
                if (after) col.insertBefore(ph, after);
                else col.appendChild(ph);
            });
            col.addEventListener('dragleave', (e) => {
                if (col.contains(e.relatedTarget)) return;
                col.classList.remove('ring-2', 'ring-blue-400', 'dark:ring-blue-500', 'bg-blue-50/40', 'dark:bg-blue-900/10');
                col.querySelector('.drag-placeholder')?.remove();
            });
            col.addEventListener('drop', (e) => {
                e.preventDefault();
                col.classList.remove('ring-2', 'ring-blue-400', 'dark:ring-blue-500', 'bg-blue-50/40', 'dark:bg-blue-900/10');
                col.querySelector('.drag-placeholder')?.remove();
                const id = e.dataTransfer.getData('text/plain') || this._dragId;
                if (id) {
                    const newStage = SLUG_TO_STAGE[col.dataset.slug];
                    if (newStage) this._moveCard(id, newStage);
                }
            });
        });
    }

    _wireGlobalToggle() {
        const btn = document.getElementById('expand-all-workflows-btn');
        if (!btn) return;
        btn.addEventListener('click', () => {
            this._allExpanded = !this._allExpanded;
            this._syncExpandLabel();
            document.querySelectorAll('.kanban-card').forEach(card => {
                const id = card.dataset.id;
                if (id) this._setCardExpanded(card, id, this._allExpanded);
            });
        });
    }

    _syncExpandLabel() {
        const label = document.getElementById('expand-all-workflows-label');
        const btn   = document.getElementById('expand-all-workflows-btn');
        if (!label || !btn) return;
        label.textContent = this._allExpanded ? 'Collapse All' : 'Expand All';
        const chevron = btn.querySelector('svg');
        if (chevron) chevron.style.transform = this._allExpanded ? 'rotate(180deg)' : '';
    }

    // -----------------------------------------------------------------------
    // Populate
    // -----------------------------------------------------------------------

    _populateBoard() {
        KANBAN_STAGES.forEach(stage => {
            const col   = document.getElementById(`kcol-${stage.slug}`);
            const count = document.getElementById(`kcount-${stage.slug}`);
            if (col)   col.innerHTML = '';
            if (count) count.textContent = '0';
        });

        const colCounts = {};
        KANBAN_STAGES.forEach(s => { colCounts[s.slug] = 0; });

        this.opportunities.forEach(opp => {
            const stage = opp.pipeline_stage || opp.status || 'identified';
            const slug  = STAGE_MAP[stage] || '01-qual';
            const col   = document.getElementById(`kcol-${slug}`);
            if (!col) return;
            col.appendChild(this._buildCard(opp));
            colCounts[slug] = (colCounts[slug] || 0) + 1;
        });

        KANBAN_STAGES.forEach(s => {
            const col     = document.getElementById(`kcol-${s.slug}`);
            const countEl = document.getElementById(`kcount-${s.slug}`);
            const n = colCounts[s.slug] || 0;
            if (countEl) countEl.textContent = n;
            if (col && n === 0) {
                col.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-500 text-center py-4 select-none">No proposals</div>';
            }
        });
    }

    // -----------------------------------------------------------------------
    // Card
    // -----------------------------------------------------------------------

    _buildCard(opp) {
        const cardId  = opp.id || opp.proposal_id || '';
        const title   = opp.title || opp.name || opp.opportunity_name || 'Untitled';
        const agency  = opp.agency || '';
        const value   = opp.estimated_value != null ? opp.estimated_value : (opp.value != null ? opp.value : null);
        const dueDate = opp.proposal_due_date || opp.due_date || null;

        const card = document.createElement('div');
        card.className = 'kanban-card bg-white dark:bg-gray-700 rounded-lg shadow-sm border border-gray-100 dark:border-gray-600 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-500 transition-all select-none overflow-hidden';
        card.draggable = true;
        card.dataset.id = cardId;

        // ── value string ──
        let valueStr = '';
        if (value != null && value > 0) {
            valueStr = value >= 1_000_000
                ? `$${(value / 1_000_000).toFixed(1)}M`
                : value >= 1_000
                    ? `$${(value / 1_000).toFixed(0)}K`
                    : `$${value}`;
        }

        // ── due date string ──
        let dueDateStr = '';
        if (dueDate) {
            try {
                const d = new Date(dueDate);
                const diffDays = Math.ceil((d - new Date()) / 86400000);
                const formatted = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                const cls = diffDays < 0 ? 'text-red-500 dark:text-red-400'
                    : diffDays <= 7     ? 'text-orange-500 dark:text-orange-400'
                                        : 'text-gray-400 dark:text-gray-500';
                dueDateStr = `<span class="text-xs ${cls} flex items-center gap-1 flex-shrink-0">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                    </svg>
                    ${formatted}${diffDays < 0 ? ' (overdue)' : diffDays <= 7 ? ` (${diffDays}d)` : ''}
                </span>`;
            } catch (_) {}
        }

        // ── card header (always visible) ──
        const header = document.createElement('div');
        header.className = 'p-3';

        // Top row: drag handle + title + expand chevron
        const topRow = document.createElement('div');
        topRow.className = 'flex items-start justify-between gap-2 mb-1';

        // Drag handle (grip dots) — makes the affordance visible
        const dragHandle = document.createElement('div');
        dragHandle.className = 'drag-handle flex-shrink-0 cursor-grab text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-400 mt-0.5';
        dragHandle.title = 'Drag to move stage';
        dragHandle.innerHTML = `<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 10 16">
            <circle cx="3" cy="2" r="1.2"/><circle cx="7" cy="2" r="1.2"/>
            <circle cx="3" cy="7" r="1.2"/><circle cx="7" cy="7" r="1.2"/>
            <circle cx="3" cy="12" r="1.2"/><circle cx="7" cy="12" r="1.2"/>
        </svg>`;

        const titleEl = document.createElement('div');
        titleEl.className = 'text-sm font-medium text-gray-900 dark:text-white leading-snug line-clamp-2 flex-1';
        titleEl.textContent = title;

        // Chevron button
        const chevronBtn = document.createElement('button');
        chevronBtn.className = 'flex-shrink-0 p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors cursor-pointer mt-0.5';
        chevronBtn.title = 'Expand tasks';
        chevronBtn.innerHTML = `<svg class="w-3.5 h-3.5 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"/>
        </svg>`;

        topRow.appendChild(dragHandle);
        topRow.appendChild(titleEl);
        topRow.appendChild(chevronBtn);
        header.appendChild(topRow);

        // Agency + meta row
        if (agency) {
            const agencyEl = document.createElement('div');
            agencyEl.className = 'text-xs text-gray-500 dark:text-gray-400 mb-1.5 truncate';
            agencyEl.textContent = agency;
            header.appendChild(agencyEl);
        }

        if (valueStr || dueDateStr) {
            const metaRow = document.createElement('div');
            metaRow.className = 'flex items-center justify-between gap-1 flex-wrap';
            metaRow.innerHTML = `
                ${valueStr ? `<span class="text-xs font-semibold text-blue-600 dark:text-blue-400">${valueStr}</span>` : '<span></span>'}
                ${dueDateStr}
            `;
            header.appendChild(metaRow);
        }

        // ── tasks panel (collapsed by default) ──
        const tasksPanel = document.createElement('div');
        tasksPanel.className = 'kanban-tasks-panel hidden border-t border-gray-100 dark:border-gray-600 px-3 pt-2 pb-3';
        tasksPanel.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-500 italic">Loading tasks…</div>';

        card.appendChild(header);
        card.appendChild(tasksPanel);

        // ── drag events on card (dragstart must be on the draggable element itself) ──
        card.addEventListener('dragstart', (e) => {
            this._dragId     = cardId;
            this._isDragging = true;
            e.dataTransfer.setData('text/plain', cardId);
            e.dataTransfer.effectAllowed = 'move';
            card.classList.add('opacity-50');
        });
        card.addEventListener('dragend', () => {
            this._dragId = null;
            card.classList.remove('opacity-50');
            // Defer reset so drop-triggered click handlers see the flag
            setTimeout(() => { this._isDragging = false; }, 0);
        });

        // ── chevron: toggle expand ──
        chevronBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // don't fire the card navigate click
            const expanded = tasksPanel.classList.contains('hidden');
            this._setCardExpanded(card, cardId, expanded);
        });

        // ── card body click: navigate to detail ──
        titleEl.style.cursor = 'pointer';
        titleEl.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this._isDragging) return;
            this._navigateToDetail(cardId);
        });
        header.addEventListener('click', (e) => {
            if (this._isDragging) return;
            if (e.target === chevronBtn || chevronBtn.contains(e.target)) return;
            if (e.target === dragHandle || dragHandle.contains(e.target)) return;
            this._navigateToDetail(cardId);
        });

        return card;
    }

    // -----------------------------------------------------------------------
    // Expand / collapse
    // -----------------------------------------------------------------------

    async _setCardExpanded(card, opportunityId, expand) {
        const panel     = card.querySelector('.kanban-tasks-panel');
        const chevronSvg = card.querySelector('.kanban-tasks-panel ~ * svg, button svg');
        // Find the chevron inside the card header
        const btn = card.querySelector('button');
        const svg = btn ? btn.querySelector('svg') : null;

        if (!panel) return;

        if (expand) {
            panel.classList.remove('hidden');
            if (svg) svg.style.transform = 'rotate(180deg)';
            if (btn) btn.title = 'Collapse tasks';
            await this._loadTasksIntoPanel(panel, opportunityId);
        } else {
            panel.classList.add('hidden');
            if (svg) svg.style.transform = '';
            if (btn) btn.title = 'Expand tasks';
        }
    }

    async _loadTasksIntoPanel(panel, opportunityId) {
        // Use cache if available
        if (this._taskCache[opportunityId]) {
            this._renderTaskPills(panel, this._taskCache[opportunityId]);
            return;
        }

        panel.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-500 italic">Loading tasks…</div>';

        try {
            const res = await fetch(`${this.baseUrl}/api/opportunities/${opportunityId}/tasks`);
            if (res.ok) {
                const data = await res.json();
                const tasks = data.tasks || [];
                this._taskCache[opportunityId] = tasks;
                this._renderTaskPills(panel, tasks);
            } else {
                panel.innerHTML = '<div class="text-xs text-red-400 italic">Failed to load tasks.</div>';
            }
        } catch (e) {
            panel.innerHTML = '<div class="text-xs text-red-400 italic">Error loading tasks.</div>';
        }
    }

    _renderTaskPills(panel, tasks) {
        if (tasks.length === 0) {
            panel.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-500 italic">No tasks.</div>';
            return;
        }

        panel.innerHTML = '';
        const wrap = document.createElement('div');
        wrap.className = 'flex flex-wrap gap-1.5';

        tasks.forEach(task => {
            const pill = document.createElement('span');
            const colorCls = TASK_STATUS_COLORS[task.status] || TASK_STATUS_COLORS['pending'];
            pill.className = `inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colorCls}`;
            pill.title = `${task.status}${task.progress ? ' · ' + task.progress + '%' : ''}`;

            // Status dot
            const dot = document.createElement('span');
            dot.className = 'w-1.5 h-1.5 rounded-full flex-shrink-0 ' + this._statusDotColor(task.status);

            const label = document.createElement('span');
            label.className = 'truncate max-w-[9rem]';
            label.textContent = task.name;

            pill.appendChild(dot);
            pill.appendChild(label);
            wrap.appendChild(pill);
        });

        panel.appendChild(wrap);
    }

    _statusDotColor(status) {
        const map = {
            'pending':     'bg-gray-400 dark:bg-gray-300',
            'in_progress': 'bg-blue-500',
            'completed':   'bg-green-500',
            'done':        'bg-green-500',
            'blocked':     'bg-red-500',
        };
        return map[status] || 'bg-gray-400';
    }

    // -----------------------------------------------------------------------
    // Opportunity detail drawer — see js/workflow-drawer.js for implementation
    // The mixin in workflow-drawer.js overrides _navigateToDetail and adds
    // _openDrawer, _closeDrawer, _populateDrawer, _loadDrawerTasks,
    // _renderDrawerTasks, _stageLabel, and _formatDue.
    // -----------------------------------------------------------------------

    // Placeholder: overridden by workflow-drawer.js mixin at runtime.
    _navigateToDetail(cardId) { void cardId; }

    // -----------------------------------------------------------------------
    // Drag-and-drop helpers
    // -----------------------------------------------------------------------

    /** Return the card element the dragged card should be inserted before, or null to append. */
    _dragAfterElement(col, mouseY) {
        const cards = [...col.querySelectorAll('.kanban-card:not(.opacity-50)')];
        return cards.reduce((closest, card) => {
            const { top, height } = card.getBoundingClientRect();
            const offset = mouseY - top - height / 2;
            return offset < 0 && offset > closest.offset
                ? { offset, el: card }
                : closest;
        }, { offset: Number.NEGATIVE_INFINITY, el: null }).el;
    }

    // -----------------------------------------------------------------------
    // Drag-and-drop stage move
    // -----------------------------------------------------------------------

    async _moveCard(opportunityId, newPipelineStage) {
        try {
            const response = await fetch(`${this.baseUrl}/api/opportunities/${opportunityId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pipeline_stage: newPipelineStage,
                    status: newPipelineStage,
                }),
            });

            if (response.ok) {
                const opp = this.opportunities.find(o => (o.id || o.proposal_id) === opportunityId);
                if (opp) opp.pipeline_stage = newPipelineStage;
                this._populateBoard();
                if (window.app?.opportunitiesManager) {
                    window.app.opportunitiesManager.reloadCurrentOpportunity(opportunityId);
                }
            } else {
                console.error('Workflows: failed to move card', opportunityId, newPipelineStage);
            }
        } catch (e) {
            console.error('Workflows: error moving card', e);
        }
    }

    // -----------------------------------------------------------------------
    // Utilities
    // -----------------------------------------------------------------------

    _esc(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

window.workflowsManager = new WorkflowsManager();
