// Opportunities Manager

/** Simple debounce — delays fn by ms after the last call. */
function _debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

// Pipeline stage definitions — must match KANBAN_STAGES in workflows.js
const PIPELINE_STAGE_OPTIONS = [
    { value: 'identified',               label: '01 — Qualification' },
    { value: 'long_lead',                label: '02 — Long Lead' },
    { value: 'bid_decision',             label: '03 — Bid Decision' },
    { value: 'active',                   label: '04 — In Progress' },
    { value: 'submitted',                label: '05 — Submitted / Review' },
    { value: 'negotiating',              label: '06 — In Negotiation' },
    { value: 'awarded',                  label: '07 — Closed Won' },
    { value: 'lost',                     label: '08 — Closed Lost' },
    { value: 'no_bid',                   label: '09 — Closed No Bid' },
    { value: 'cancelled',                label: '20 — Closed Other' },
    { value: 'contract_vehicle_won',     label: '98 — Awarded Contract Vehicle' },
    { value: 'contract_vehicle_complete',label: '99 — Completed Contract Vehicle' },
];

// Map legacy status values → pipeline_stage for existing records
const LEGACY_STATUS_MAP = {
    'open':        'identified',
    'in_progress': 'active',
    'won':         'awarded',
    'lost':        'lost',
};

class OpportunitiesManager {
    constructor() {
        this.opportunities = [];
        this.currentOpportunity = null;
        this.calendarManager = null;
        this.ganttManager = null;
        this._editMode = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeVisualizations();
    }

    initializeVisualizations() {
        if (typeof SVGCalendarManager !== 'undefined') {
            this.calendarManager = new SVGCalendarManager('svg-calendar-container');
        }
        if (typeof GanttChartManager !== 'undefined') {
            this.ganttManager = new GanttChartManager('gantt-chart-container');
        }
    }

    setupEventListeners() {
        // Cache task-modal form elements once — avoids repeated getElementById in hot paths
        this._tf = {
            modal:    document.getElementById('task-modal'),
            form:     document.getElementById('task-form'),
            title:    document.getElementById('task-modal-title'),
            id:       document.getElementById('task-id'),
            oppId:    document.getElementById('task-opportunity-id'),
            name:     document.getElementById('task-name'),
            desc:     document.getElementById('task-description'),
            start:    document.getElementById('task-start-date'),
            end:      document.getElementById('task-end-date'),
            status:   document.getElementById('task-status'),
            progress: document.getElementById('task-progress'),
            assignTo: document.getElementById('task-assigned-to'),
        };

        // Add opportunity button (opens create modal)
        const addBtn = document.getElementById('add-opportunity-btn');
        if (addBtn) addBtn.addEventListener('click', () => this.showCreateOpportunityModal());

        // Create modal close/cancel
        const closeModal = document.getElementById('close-opportunity-modal');
        const cancelBtn = document.getElementById('cancel-opportunity-btn');
        if (closeModal) closeModal.addEventListener('click', () => this.hideOpportunityModal());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.hideOpportunityModal());

        // Create modal form
        const form = document.getElementById('opportunity-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveNewOpportunity();
            });
        }

        // Detail view buttons
        const closeDetailBtn = document.getElementById('close-opportunity-detail-btn');
        const editBtn        = document.getElementById('edit-opportunity-btn');
        const saveBtn        = document.getElementById('save-opportunity-btn');
        const cancelEditBtn  = document.getElementById('cancel-edit-btn');
        const deleteBtn      = document.getElementById('delete-opportunity-btn');

        if (closeDetailBtn) closeDetailBtn.addEventListener('click', () => this.closeOpportunityDetail());
        if (editBtn)        editBtn.addEventListener('click',   () => this._enterEditMode());
        if (saveBtn)        saveBtn.addEventListener('click',   () => this._saveInlineEdit());
        if (cancelEditBtn)  cancelEditBtn.addEventListener('click', () => this._exitEditMode());
        if (deleteBtn)      deleteBtn.addEventListener('click', () => this.deleteCurrentOpportunity());

        // View toggles
        const toggleCalendarBtn = document.getElementById('toggle-calendar-view');
        const toggleTasksBtn    = document.getElementById('toggle-tasks-view');
        const listViewBtn       = document.getElementById('tasks-list-view-btn');

        if (toggleCalendarBtn) toggleCalendarBtn.addEventListener('click', () => this.showCalendarView());
        if (toggleTasksBtn)    toggleTasksBtn.addEventListener('click',    () => this.showTasksView());
        if (listViewBtn)       listViewBtn.addEventListener('click',       () => this.showListView());

        // Task management
        const addTaskBtn     = document.getElementById('add-task-btn');
        const closeTaskModal = document.getElementById('close-task-modal');
        const cancelTaskBtn  = document.getElementById('cancel-task-btn');
        const taskForm       = document.getElementById('task-form');

        if (addTaskBtn)     addTaskBtn.addEventListener('click',     () => this.showCreateTaskModal());
        if (closeTaskModal) closeTaskModal.addEventListener('click', () => this.hideTaskModal());
        if (cancelTaskBtn)  cancelTaskBtn.addEventListener('click',  () => this.hideTaskModal());
        if (taskForm) {
            taskForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveTask();
            });
        }
    }

    // -----------------------------------------------------------------------
    // Load & Render list
    // -----------------------------------------------------------------------

    async loadOpportunities() {
        try {
            const response = await fetch('/api/opportunities', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            if (response.ok) {
                const data = await response.json();
                this.opportunities = data.opportunities || [];
                this.renderOpportunitiesList();
            }
        } catch (error) {
            console.error('Error loading opportunities:', error);
        }
    }

    renderOpportunitiesList() {
        this._renderSidebarList();
        this._renderMainTable();
        this._wireMainTableFilters();
    }

    _renderSidebarList() {
        const opportunitiesList = document.getElementById('opportunities-list');
        if (!opportunitiesList) return;

        opportunitiesList.innerHTML = '';

        if (this.opportunities.length === 0) {
            opportunitiesList.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400 px-3 py-2">No opportunities yet</p>';
            return;
        }

        this.opportunities.forEach(opp => {
            const wrapper = document.createElement('div');
            wrapper.className = 'flex items-center gap-1 group';

            const item = document.createElement('button');
            item.className = 'flex-1 text-left px-3 py-2 rounded text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors';
            item.textContent = opp.name;
            item.addEventListener('click', () => {
                this.showOpportunityDetail(opp);
                if (window.app && window.app.currentPage !== 'opportunities') {
                    document.getElementById('chat-area')?.classList.add('hidden');
                    document.getElementById('models-area')?.classList.add('hidden');
                    document.getElementById('settings-area')?.classList.add('hidden');
                    document.getElementById('knowledge-area')?.classList.add('hidden');
                    document.getElementById('cag-knowledge-area')?.classList.add('hidden');
                    document.getElementById('visualizations-area')?.classList.add('hidden');
                    document.getElementById('mcp-area')?.classList.add('hidden');
                    document.getElementById('agents-area')?.classList.add('hidden');
                    document.getElementById('prompts-area')?.classList.add('hidden');
                    document.getElementById('todos-area')?.classList.add('hidden');
                    document.getElementById('opportunities-area')?.classList.remove('hidden');
                    window.app.currentPage = 'opportunities';
                    const pageTitle = document.getElementById('page-title');
                    if (pageTitle) pageTitle.textContent = 'Opportunities';
                    const navItems = document.querySelectorAll('.nav-item.expandable-nav-item');
                    navItems.forEach(nav => {
                        if (nav.textContent.trim().toLowerCase().includes('lists')) {
                            window.app.setActiveNavItem(nav);
                            const expandIcon = nav.querySelector('.expand-icon');
                            if (expandIcon) expandIcon.style.transform = 'rotate(180deg)';
                        }
                    });
                    const listsSubmenu = document.getElementById('lists-submenu');
                    const oppListEl = document.getElementById('opportunities-list');
                    if (listsSubmenu) listsSubmenu.classList.remove('hidden');
                    if (oppListEl) oppListEl.classList.remove('hidden');
                }
            });

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'p-2 text-gray-400 hover:text-red-500 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity';
            deleteBtn.title = 'Delete opportunity';
            deleteBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>`;
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteOpportunityFromList(opp.id, opp.name);
            });

            wrapper.appendChild(item);
            wrapper.appendChild(deleteBtn);
            opportunitiesList.appendChild(wrapper);
        });
    }

    _renderMainTable(search = '', stageFilter = '', priorityFilter = '') {
        const tbody = document.getElementById('opp-main-table-body');
        if (!tbody) return;

        const q        = search.toLowerCase();
        const filtered = this.opportunities.filter(opp => {
            const stage    = opp.pipeline_stage || opp.status || '';
            const priority = opp.priority || '';
            if (stageFilter    && stage    !== stageFilter)    return false;
            if (priorityFilter && priority !== priorityFilter) return false;
            if (q) {
                const haystack = [opp.name, opp.agency, opp.description].join(' ').toLowerCase();
                if (!haystack.includes(q)) return false;
            }
            return true;
        });

        tbody.innerHTML = '';

        if (filtered.length === 0) {
            const emptyMsg = this.opportunities.length === 0
                ? 'No opportunities yet. Click <strong>New Opportunity</strong> to get started.'
                : 'No opportunities match the current filters.';
            tbody.innerHTML = `<tr><td colspan="6" class="px-4 py-12 text-center text-gray-400 dark:text-gray-500 text-sm">${emptyMsg}</td></tr>`;
            return;
        }

        const STAGE_LABELS = {
            identified: '01 — Qualification', qualifying: '01 — Qualification',
            long_lead: '02 — Long Lead', bid_decision: '03 — Bid Decision',
            active: '04 — In Progress', submitted: '05 — Waiting/Review',
            negotiating: '06 — In Negotiation', awarded: '07 — Closed Won',
            lost: '08 — Closed Lost', no_bid: '09 — Closed No Bid',
            cancelled: '20 — Closed Other',
        };
        const STAGE_COLORS = {
            identified: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200',
            qualifying: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200',
            long_lead: 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200',
            bid_decision: 'bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-200',
            active: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-200',
            submitted: 'bg-orange-100 dark:bg-orange-900/40 text-orange-800 dark:text-orange-200',
            negotiating: 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200',
            awarded: 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200',
            lost: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200',
            no_bid: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
            cancelled: 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300',
        };
        const PRI_COLORS = {
            high:   'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
            medium: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300',
            low:    'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
        };

        filtered.forEach(opp => {
            const stage    = opp.pipeline_stage || opp.status || 'identified';
            const priority = opp.priority || 'medium';
            const value    = opp.estimated_value ?? opp.value ?? null;
            const due      = opp.proposal_due_date || opp.due_date || null;

            let valueStr = value != null && value > 0
                ? (value >= 1e6 ? `$${(value / 1e6).toFixed(1)}M`
                    : value >= 1000 ? `$${(value / 1000).toFixed(0)}K`
                    : `$${value}`)
                : '—';

            let dueStr = '—';
            let dueCls = 'text-gray-500 dark:text-gray-400';
            if (due) {
                try {
                    const d        = new Date(due);
                    const diffDays = Math.ceil((d - new Date()) / 86400000);
                    dueStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                    if (diffDays < 0)        dueCls = 'text-red-600 dark:text-red-400 font-medium';
                    else if (diffDays <= 7)  dueCls = 'text-orange-500 dark:text-orange-400 font-medium';
                } catch (_) {}
            }

            const stageLabel = STAGE_LABELS[stage] || stage;
            const stageCls   = STAGE_COLORS[stage]  || STAGE_COLORS.identified;
            const priLabel   = priority.charAt(0).toUpperCase() + priority.slice(1);
            const priCls     = PRI_COLORS[priority]  || PRI_COLORS.medium;

            const tr = document.createElement('tr');
            tr.className = 'hover:bg-gray-50 dark:hover:bg-gray-700/40 cursor-pointer transition-colors';
            tr.innerHTML = `
                <td class="px-4 py-3">
                    <div class="font-medium text-gray-900 dark:text-white leading-snug">${this.escapeHtml(opp.name || 'Untitled')}</div>
                    ${opp.agency ? `<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${this.escapeHtml(opp.agency)}</div>` : ''}
                </td>
                <td class="px-4 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${stageCls}">${this.escapeHtml(stageLabel)}</span>
                </td>
                <td class="px-4 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${priCls}">${this.escapeHtml(priLabel)}</span>
                </td>
                <td class="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 font-medium">${valueStr}</td>
                <td class="px-4 py-3 text-sm ${dueCls}">${dueStr}</td>
                <td class="px-4 py-3 text-right">
                    <button class="opp-row-delete p-1.5 text-gray-300 hover:text-red-500 dark:hover:text-red-400 transition-colors rounded" title="Delete" data-id="${this.escapeHtml(String(opp.id || ''))}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </td>
            `;

            tr.addEventListener('click', (e) => {
                if (e.target.closest('.opp-row-delete')) return;
                this.showOpportunityDetail(opp);
            });
            tr.querySelector('.opp-row-delete')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteOpportunityFromList(opp.id, opp.name);
            });

            tbody.appendChild(tr);
        });
    }

    _wireMainTableFilters() {
        const searchInput    = document.getElementById('opp-search-input');
        const stageSelect    = document.getElementById('opp-stage-filter');
        const prioritySelect = document.getElementById('opp-priority-filter');
        if (!searchInput || searchInput._wired) return;
        searchInput._wired = true;

        const refresh = () => this._renderMainTable(
            searchInput.value,
            stageSelect.value,
            prioritySelect.value,
        );

        // Debounce free-text search to avoid rebuilding the table on every keystroke.
        // Dropdown changes are intentionally instant.
        searchInput.addEventListener('input', _debounce(refresh, 200));
        stageSelect.addEventListener('change', refresh);
        prioritySelect.addEventListener('change', refresh);
    }

    // -----------------------------------------------------------------------
    // Create modal (new opportunities only)
    // -----------------------------------------------------------------------

    showCreateOpportunityModal() {
        this.currentOpportunity = null;
        const modal = document.getElementById('opportunity-modal');
        const modalTitle = document.getElementById('opportunity-modal-title');
        const form = document.getElementById('opportunity-form');
        if (modalTitle) modalTitle.textContent = 'Create Opportunity';
        if (form) form.reset();
        if (modal) modal.classList.remove('hidden');
    }

    hideOpportunityModal() {
        const modal = document.getElementById('opportunity-modal');
        if (modal) modal.classList.add('hidden');
    }

    async saveNewOpportunity() {
        const name = document.getElementById('opportunity-name')?.value?.trim();
        if (!name) return;

        const g = id => document.getElementById(id)?.value?.trim() || '';

        const pipelineStage = g('opportunity-status') || 'identified';
        const priority      = g('opportunity-priority') || 'medium';
        const value         = parseFloat(document.getElementById('opportunity-value')?.value) || 0;
        const tagsRaw       = g('opportunity-tags');
        const tags          = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(t => t) : [];
        const description   = g('opportunity-description');

        try {
            const response = await fetch('/api/opportunities', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name, description,
                    pipeline_stage: pipelineStage,
                    priority, value, tags,
                    probability:       g('opportunity-probability'),
                    proposal_due_date: g('opportunity-proposal-due'),
                    opp_number:        g('opportunity-opp-number'),
                    is_iwa:            g('opportunity-is-iwa'),
                    owning_org:        g('opportunity-owning-org'),
                    proposal_folder:   g('opportunity-proposal-folder'),
                    agency:            g('opportunity-agency'),
                    solicitation_link: g('opportunity-solicitation-link'),
                    deal_type:         g('opportunity-deal-type'),
                })
            });
            if (response.ok) {
                const data = await response.json();
                this.hideOpportunityModal();
                await this.loadOpportunities();
                if (data.opportunity) this.showOpportunityDetail(data.opportunity);
                this._refreshWorkflows();
            }
        } catch (error) {
            console.error('Error creating opportunity:', error);
        }
    }

    // -----------------------------------------------------------------------
    // Detail view — display
    // -----------------------------------------------------------------------

    showOpportunityDetail(opportunity) {
        this.currentOpportunity = opportunity;

        // Exit any active edit before switching
        if (this._editMode) this._exitEditMode(false);

        const detailView = document.getElementById('opportunity-detail-view');
        const mainList   = document.getElementById('opportunities-main-list');
        if (!detailView) return;
        detailView.classList.remove('hidden');
        if (mainList) mainList.classList.add('hidden');

        this._populateDetailFields(opportunity);
        this.loadTasks(opportunity.id);
        document.dispatchEvent(new CustomEvent('opportunitySelected', { detail: { id: opportunity.id } }));
    }

    /**
     * Populate all the permanent form controls in the detail card with
     * the opportunity's current data without changing layout or mode.
     */
    _populateDetailFields(opp) {
        const stage = opp.pipeline_stage || LEGACY_STATUS_MAP[opp.status] || 'identified';

        const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ''; };

        set('opportunity-detail-name',            opp.name || '');
        set('opportunity-detail-value',           opp.value || 0);
        set('opportunity-detail-description',     opp.description || '');
        set('opportunity-detail-probability',     opp.probability || '');
        set('opportunity-detail-proposal-due',    opp.proposal_due_date || '');
        set('opportunity-detail-opp-number',      opp.opp_number || '');
        set('opportunity-detail-is-iwa',          opp.is_iwa || '');
        set('opportunity-detail-owning-org',      opp.owning_org || '');
        set('opportunity-detail-proposal-folder', opp.proposal_folder || '');
        set('opportunity-detail-agency',          opp.agency || '');
        set('opportunity-detail-solicitation-link', opp.solicitation_link || '');
        set('opportunity-detail-deal-type',       opp.deal_type || '');

        const statusEl = document.getElementById('opportunity-detail-status');
        if (statusEl) statusEl.value = stage;

        const priorityEl = document.getElementById('opportunity-detail-priority');
        if (priorityEl) priorityEl.value = opp.priority || 'medium';

        // Created (plain text — always read-only)
        const createdEl = document.getElementById('opportunity-detail-created');
        if (createdEl) createdEl.textContent = opp.created_at ? new Date(opp.created_at).toLocaleDateString() : '-';

        // Tags: badge display (view mode)
        const tagsBadges = document.getElementById('opportunity-detail-tags');
        if (tagsBadges) {
            tagsBadges.innerHTML = '';
            const tags = opp.tags || [];
            if (tags.length > 0) {
                tags.forEach(tag => {
                    const el = document.createElement('span');
                    el.className = 'px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded';
                    el.textContent = tag;
                    tagsBadges.appendChild(el);
                });
            } else {
                tagsBadges.innerHTML = '<span class="text-gray-500 dark:text-gray-400">No tags</span>';
            }
        }

        // Tags: text input (edit mode) — always keep in sync
        const tagsInput = document.getElementById('opportunity-detail-tags-input');
        if (tagsInput) tagsInput.value = (opp.tags || []).join(', ');
    }

    closeOpportunityDetail() {
        if (this._editMode) this._exitEditMode(false);
        document.getElementById('opportunity-detail-view')?.classList.add('hidden');
        document.getElementById('opportunities-main-list')?.classList.remove('hidden');
        document.dispatchEvent(new CustomEvent('opportunityDeselected'));
    }

    // -----------------------------------------------------------------------
    // Inline edit — CSS class toggle only, no DOM restructuring
    // -----------------------------------------------------------------------

    _enterEditMode() {
        if (!this.currentOpportunity) return;
        this._editMode = true;

        const card = document.getElementById('opportunity-detail-card');
        if (!card) return;

        // Toggle CSS: fields become interactive
        card.classList.add('edit-active');

        // Enable all opp-field controls
        card.querySelectorAll('[data-opp-field]').forEach(el => {
            if (el.tagName === 'SELECT') {
                el.disabled = false;
            } else {
                el.removeAttribute('readonly');
            }
        });

        // Swap tags badges → tags text input (same position)
        document.getElementById('opportunity-detail-tags')?.classList.add('hidden');
        const tagsInput = document.getElementById('opportunity-detail-tags-input');
        if (tagsInput) {
            tagsInput.classList.remove('hidden');
            tagsInput.removeAttribute('readonly');
        }

        // Swap Edit → Save + Cancel
        document.getElementById('edit-opportunity-btn')?.classList.add('hidden');
        document.getElementById('save-opportunity-btn')?.classList.remove('hidden');
        document.getElementById('cancel-edit-btn')?.classList.remove('hidden');
    }

    _exitEditMode(repopulate = true) {
        this._editMode = false;

        const card = document.getElementById('opportunity-detail-card');
        if (!card) return;

        // Remove edit styling
        card.classList.remove('edit-active');

        // Disable all opp-field controls
        card.querySelectorAll('[data-opp-field]').forEach(el => {
            if (el.tagName === 'SELECT') {
                el.disabled = true;
            } else {
                el.setAttribute('readonly', '');
            }
        });

        // Swap tags text input → badges
        document.getElementById('opportunity-detail-tags')?.classList.remove('hidden');
        const tagsInput = document.getElementById('opportunity-detail-tags-input');
        if (tagsInput) {
            tagsInput.classList.add('hidden');
            tagsInput.setAttribute('readonly', '');
        }

        // Swap Save/Cancel → Edit
        document.getElementById('save-opportunity-btn')?.classList.add('hidden');
        document.getElementById('cancel-edit-btn')?.classList.add('hidden');
        document.getElementById('edit-opportunity-btn')?.classList.remove('hidden');

        // Re-populate from the stored currentOpportunity (reverts any unsaved typing)
        if (repopulate && this.currentOpportunity) {
            this._populateDetailFields(this.currentOpportunity);
        }
    }

    async _saveInlineEdit() {
        if (!this.currentOpportunity) return;

        const name = document.getElementById('opportunity-detail-name')?.value?.trim();
        if (!name) return;

        const g = id => document.getElementById(id)?.value?.trim() || '';

        const pipelineStage = document.getElementById('opportunity-detail-status')?.value || 'identified';
        const priority      = document.getElementById('opportunity-detail-priority')?.value || 'medium';
        const value         = parseFloat(document.getElementById('opportunity-detail-value')?.value) || 0;
        const tagsRaw       = g('opportunity-detail-tags-input');
        const tags          = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(t => t) : [];
        const description   = g('opportunity-detail-description');

        try {
            const response = await fetch(`/api/opportunities/${this.currentOpportunity.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name, description,
                    pipeline_stage: pipelineStage,
                    priority, value, tags,
                    probability:       g('opportunity-detail-probability'),
                    proposal_due_date: g('opportunity-detail-proposal-due'),
                    opp_number:        g('opportunity-detail-opp-number'),
                    is_iwa:            g('opportunity-detail-is-iwa'),
                    owning_org:        g('opportunity-detail-owning-org'),
                    proposal_folder:   g('opportunity-detail-proposal-folder'),
                    agency:            g('opportunity-detail-agency'),
                    solicitation_link: g('opportunity-detail-solicitation-link'),
                    deal_type:         g('opportunity-detail-deal-type'),
                })
            });

            if (response.ok) {
                const data = await response.json();
                const updated = data.opportunity || data;
                this.currentOpportunity = updated;
                this._exitEditMode(false);       // exit first (restores buttons)
                this._populateDetailFields(updated); // then populate with fresh data
                await this.loadOpportunities();
                this._refreshWorkflows();
            } else {
                console.error('Failed to update opportunity');
            }
        } catch (error) {
            console.error('Error updating opportunity:', error);
        }
    }

    // Called by workflowsManager after a drag-drop stage change
    async reloadCurrentOpportunity(opportunityId) {
        try {
            const response = await fetch(`/api/opportunities/${opportunityId}`);
            if (response.ok) {
                const data = await response.json();
                const opp = data.opportunity;
                const idx = this.opportunities.findIndex(o => o.id === opportunityId);
                if (idx !== -1) this.opportunities[idx] = opp;
                else this.opportunities.unshift(opp);
                this.renderOpportunitiesList();
                if (this.currentOpportunity?.id === opportunityId && !this._editMode) {
                    this.currentOpportunity = opp;
                    this._populateDetailFields(opp);
                }
            }
        } catch (e) {
            console.error('Error reloading opportunity:', e);
        }
    }

    // -----------------------------------------------------------------------
    // Delete
    // -----------------------------------------------------------------------

    async deleteCurrentOpportunity() {
        if (!this.currentOpportunity) return;
        if (!confirm(`Are you sure you want to delete "${this.currentOpportunity.name}"?`)) return;

        try {
            const response = await fetch(`/api/opportunities/${this.currentOpportunity.id}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                this.closeOpportunityDetail();
                await this.loadOpportunities();
                this._refreshWorkflows();
            }
        } catch (error) {
            console.error('Error deleting opportunity:', error);
        }
    }

    async deleteOpportunityFromList(opportunityId, opportunityName) {
        if (!confirm(`Are you sure you want to delete "${opportunityName}"?`)) return;

        try {
            const response = await fetch(`/api/opportunities/${opportunityId}`, { method: 'DELETE' });
            const result = await response.json();
            if (result.status === 'success') {
                if (this.currentOpportunity?.id === opportunityId) this.closeOpportunityDetail();
                await this.loadOpportunities();
                this._refreshWorkflows();
            }
        } catch (error) {
            console.error('Error deleting opportunity:', error);
        }
    }

    // -----------------------------------------------------------------------
    // Views
    // -----------------------------------------------------------------------

    showCalendarView() {
        document.getElementById('svg-calendar-container')?.classList.remove('hidden');
        document.getElementById('gantt-chart-container')?.classList.add('hidden');
        if (this.calendarManager && this.currentOpportunity) {
            this.calendarManager.setOpportunities([this.currentOpportunity]);
            this.calendarManager.render();
        }
    }

    showTasksView() {
        document.getElementById('svg-calendar-container')?.classList.add('hidden');
        document.getElementById('gantt-chart-container')?.classList.remove('hidden');
        if (this.ganttManager && this.currentOpportunity) {
            this.loadTasksForGantt(this.currentOpportunity.id);
        }
    }

    async loadTasksForGantt(opportunityId) {
        try {
            const response = await fetch(`/api/opportunities/${opportunityId}/tasks`);
            if (response.ok) {
                const data = await response.json();
                if (this.ganttManager) {
                    this.ganttManager.setTasks(data.tasks || []);
                    this.ganttManager.render();
                }
            }
        } catch (error) {
            console.error('Error loading tasks for gantt:', error);
        }
    }

    showListView() {
        document.getElementById('tasks-list-container')?.classList.remove('hidden');
        document.getElementById('svg-calendar-container')?.classList.add('hidden');
        document.getElementById('gantt-chart-container')?.classList.add('hidden');
    }

    // -----------------------------------------------------------------------
    // Tasks
    // -----------------------------------------------------------------------

    async loadTasks(opportunityId) {
        try {
            const response = await fetch(`/api/opportunities/${opportunityId}/tasks`);
            if (response.ok) {
                const data = await response.json();
                this.renderTasksList(data.tasks || []);
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
        }
    }

    renderTasksList(tasks) {
        const tbody = document.getElementById('tasks-table-body');
        const emptyState = document.getElementById('tasks-empty-state');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (tasks.length === 0) {
            document.getElementById('tasks-table-wrapper')?.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            return;
        }

        document.getElementById('tasks-table-wrapper')?.classList.remove('hidden');
        if (emptyState) emptyState.classList.add('hidden');

        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700';
            row.dataset.taskId = task.id;
            // Reason: no onclick= strings — inline handlers bypass CSP and couple to global state.
            // All actions wired below with addEventListener after insertion.
            row.innerHTML = `
                <td class="px-3 py-2">
                    <button class="opp-task-banner w-full flex items-center gap-1.5 mb-1 px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors text-left">
                        <svg class="w-3 h-3 text-blue-500 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                        </svg>
                        <span class="text-xs font-medium text-blue-600 dark:text-blue-400">View in Tasks</span>
                    </button>
                    <span class="task-name-cell text-gray-900 dark:text-white">${this.escapeHtml(task.name)}</span>
                </td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.status}</td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.progress}%</td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.start_date}</td>
                <td class="px-3 py-2 text-gray-700 dark:text-gray-300">${task.end_date}</td>
                <td class="px-3 py-2">
                    <button class="task-edit-btn text-blue-600 hover:text-blue-800 mr-2">Edit</button>
                    <button class="task-delete-btn text-red-600 hover:text-red-800">Delete</button>
                </td>
            `;
            row.querySelector('.opp-task-banner').addEventListener('click', () => window.tasksList?.highlightTaskCard(task.id));
            row.querySelector('.task-edit-btn').addEventListener('click',   () => this.editTask(task.id));
            row.querySelector('.task-delete-btn').addEventListener('click', () => this.deleteTask(task.id));
            tbody.appendChild(row);
        });
    }

    showCreateTaskModal() {
        if (!this.currentOpportunity) { alert('Please select an opportunity first'); return; }
        const tf = this._tf;
        if (tf.form)  tf.form.reset();
        if (tf.id)    tf.id.value    = '';
        if (tf.oppId) tf.oppId.value = this.currentOpportunity.id;
        if (tf.title) tf.title.textContent = 'Create Task';
        if (tf.modal) tf.modal.classList.remove('hidden');
    }

    hideTaskModal() {
        this._tf.modal?.classList.add('hidden');
    }

    async saveTask() {
        const tf  = this._tf;
        const taskId       = tf.id?.value    || '';
        const opportunityId = tf.oppId?.value || '';

        const taskData = {
            name:        tf.name?.value    || '',
            description: tf.desc?.value    || '',
            start_date:  tf.start?.value   || '',
            end_date:    tf.end?.value      || '',
            status:      tf.status?.value  || 'pending',
            progress:    parseInt(tf.progress?.value) || 0,
            assigned_to: tf.assignTo?.value || '',
        };

        try {
            const url = taskId
                ? `/api/tasks/${taskId}`
                : `/api/opportunities/${opportunityId}/tasks`;
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
            if (response.ok) {
                this.hideTaskModal();
                this.loadTasks(opportunityId);
            }
        } catch (error) {
            console.error('Error saving task:', error);
        }
    }

    async editTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            if (response.ok) {
                const data = await response.json();
                const task = data.task;
                const tf = this._tf;
                if (tf.id)       tf.id.value       = task.id;
                if (tf.oppId)    tf.oppId.value     = task.opportunity_id;
                if (tf.name)     tf.name.value      = task.name;
                if (tf.desc)     tf.desc.value      = task.description || '';
                if (tf.start)    tf.start.value     = task.start_date;
                if (tf.end)      tf.end.value       = task.end_date;
                if (tf.status)   tf.status.value    = task.status;
                if (tf.progress) tf.progress.value  = task.progress;
                if (tf.assignTo) tf.assignTo.value  = task.assigned_to || '';
                if (tf.title)    tf.title.textContent = 'Edit Task';
                if (tf.modal)    tf.modal.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error loading task:', error);
        }
    }

    async deleteTask(taskId) {
        if (!confirm('Are you sure you want to delete this task?')) return;
        try {
            const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
            if (response.ok && this.currentOpportunity) {
                this.loadTasks(this.currentOpportunity.id);
            }
        } catch (error) {
            console.error('Error deleting task:', error);
        }
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    _refreshWorkflows() {
        if (window.workflowsManager) window.workflowsManager.load();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatStatus(stage) {
        const opt = PIPELINE_STAGE_OPTIONS.find(o => o.value === stage);
        if (opt) return opt.label;
        const legacy = { 'open': 'Open', 'in_progress': 'In Progress', 'won': 'Won', 'lost': 'Lost' };
        return legacy[stage] || stage;
    }

    formatPriority(priority) {
        return priority ? priority.charAt(0).toUpperCase() + priority.slice(1) : 'Medium';
    }
}
