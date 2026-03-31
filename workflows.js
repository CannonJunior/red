/**
 * Workflows — Proposal Pipeline Kanban Board
 *
 * Displays all proposals as cards in vertical swim lanes, one per
 * Unanet CRM stage code. Horizontally scrollable.
 * Supports drag-and-drop to move opportunities between stages.
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

// Map local pipeline_stage value → KANBAN_STAGES index
const STAGE_MAP = {};
KANBAN_STAGES.forEach(s => s.localStages.forEach(ls => { STAGE_MAP[ls] = s.slug; }));

// Map slug → first localStage value (used when dropping to determine the new stage)
const SLUG_TO_STAGE = {};
KANBAN_STAGES.forEach(s => { SLUG_TO_STAGE[s.slug] = s.localStages[0]; });

class WorkflowsManager {
    constructor() {
        this.baseUrl = '';
        this.opportunities = [];
        this._dragId = null; // id of card being dragged
    }

    async load() {
        const board = document.getElementById('kanban-board');
        if (!board) return;

        // Build columns if not already built
        if (!board.children.length) {
            this._buildBoard(board);
        }

        // Show loading state
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

        this._populateBoard();
    }

    _buildBoard(board) {
        board.innerHTML = KANBAN_STAGES.map(stage => `
            <div class="kanban-col flex flex-col w-60 flex-shrink-0 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60">
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

        // Attach drop listeners to all column bodies
        board.querySelectorAll('.kanban-col-body').forEach(col => {
            col.addEventListener('dragover', (e) => {
                e.preventDefault();
                col.classList.add('ring-2', 'ring-blue-400', 'dark:ring-blue-500');
            });
            col.addEventListener('dragleave', () => {
                col.classList.remove('ring-2', 'ring-blue-400', 'dark:ring-blue-500');
            });
            col.addEventListener('drop', (e) => {
                e.preventDefault();
                col.classList.remove('ring-2', 'ring-blue-400', 'dark:ring-blue-500');
                const id = e.dataTransfer.getData('text/plain') || this._dragId;
                if (id) {
                    const newStage = SLUG_TO_STAGE[col.dataset.slug];
                    if (newStage) this._moveCard(id, newStage);
                }
            });
        });
    }

    _populateBoard() {
        // Clear all columns
        KANBAN_STAGES.forEach(stage => {
            const col = document.getElementById(`kcol-${stage.slug}`);
            const count = document.getElementById(`kcount-${stage.slug}`);
            if (col) col.innerHTML = '';
            if (count) count.textContent = '0';
        });

        const colCounts = {};
        KANBAN_STAGES.forEach(s => { colCounts[s.slug] = 0; });

        this.opportunities.forEach(opp => {
            const stage = opp.pipeline_stage || opp.status || 'identified';
            const slug = STAGE_MAP[stage] || '01-qual';
            const col = document.getElementById(`kcol-${slug}`);
            if (!col) return;

            col.appendChild(this._buildCard(opp));
            colCounts[slug] = (colCounts[slug] || 0) + 1;
        });

        // Update counts + empty state
        KANBAN_STAGES.forEach(s => {
            const col = document.getElementById(`kcol-${s.slug}`);
            const countEl = document.getElementById(`kcount-${s.slug}`);
            const n = colCounts[s.slug] || 0;
            if (countEl) countEl.textContent = n;
            if (col && n === 0) {
                col.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-500 text-center py-4 select-none">No proposals</div>';
            }
        });
    }

    _buildCard(opp) {
        const card = document.createElement('div');
        card.className = 'kanban-card bg-white dark:bg-gray-700 rounded-lg p-3 shadow-sm border border-gray-100 dark:border-gray-600 cursor-grab hover:shadow-md hover:border-blue-300 dark:hover:border-blue-500 transition-all select-none';
        card.draggable = true;
        card.dataset.id = opp.id || opp.proposal_id || '';

        const cardId = opp.id || opp.proposal_id || '';
        const title = opp.title || opp.name || opp.opportunity_name || 'Untitled';
        const agency = opp.agency || '';
        const value = opp.estimated_value != null ? opp.estimated_value : (opp.value != null ? opp.value : null);
        const dueDate = opp.proposal_due_date || opp.due_date || null;
        const stageVal = opp.pipeline_stage || opp.status || '';
        const stageMeta = KANBAN_STAGES.find(s => s.localStages.includes(stageVal));
        const stageBadgeClass = stageMeta ? stageMeta.colorClass : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300';

        let valueStr = '';
        if (value != null && value > 0) {
            valueStr = value >= 1_000_000
                ? `$${(value / 1_000_000).toFixed(1)}M`
                : value >= 1_000
                    ? `$${(value / 1_000).toFixed(0)}K`
                    : `$${value}`;
        }

        let dueDateStr = '';
        if (dueDate) {
            try {
                const d = new Date(dueDate);
                const now = new Date();
                const diffDays = Math.ceil((d - now) / 86400000);
                const formatted = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                const urgencyClass = diffDays < 0
                    ? 'text-red-500 dark:text-red-400'
                    : diffDays <= 7
                        ? 'text-orange-500 dark:text-orange-400'
                        : 'text-gray-400 dark:text-gray-500';
                dueDateStr = `<span class="text-xs ${urgencyClass} flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                    </svg>
                    ${formatted}${diffDays < 0 ? ' (overdue)' : diffDays <= 7 ? ` (${diffDays}d)` : ''}
                </span>`;
            } catch (_) {}
        }

        card.innerHTML = `
            <div class="text-sm font-medium text-gray-900 dark:text-white leading-snug mb-1 line-clamp-2">${this._esc(title)}</div>
            ${agency ? `<div class="text-xs text-gray-500 dark:text-gray-400 mb-2 truncate">${this._esc(agency)}</div>` : ''}
            <div class="flex items-center justify-between gap-1 flex-wrap">
                ${valueStr ? `<span class="text-xs font-semibold text-blue-600 dark:text-blue-400">${valueStr}</span>` : '<span></span>'}
                ${dueDateStr}
            </div>
        `;

        // Drag events
        card.addEventListener('dragstart', (e) => {
            this._dragId = cardId;
            e.dataTransfer.setData('text/plain', cardId);
            e.dataTransfer.effectAllowed = 'move';
            card.classList.add('opacity-50');
        });
        card.addEventListener('dragend', () => {
            this._dragId = null;
            card.classList.remove('opacity-50');
        });

        // Click: navigate to opportunity detail
        card.addEventListener('click', () => {
            if (window.app?.opportunitiesManager && cardId) {
                const opp = this.opportunities.find(o => (o.id || o.proposal_id) === cardId);
                if (opp) {
                    window.app.navigateTo('opportunities');
                    window.app.opportunitiesManager.showOpportunityDetail(opp);
                } else {
                    window.app.navigateTo('opportunities');
                    window.app.opportunitiesManager.loadOpportunities();
                }
            }
        });

        return card;
    }

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
                // Update local state immediately for snappy UX
                const opp = this.opportunities.find(o => (o.id || o.proposal_id) === opportunityId);
                if (opp) opp.pipeline_stage = newPipelineStage;

                // Re-render kanban
                this._populateBoard();

                // Sync opportunities manager so the detail view + list stay current
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

    _esc(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

window.workflowsManager = new WorkflowsManager();
