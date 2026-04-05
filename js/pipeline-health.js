/**
 * Pipeline Health Dashboard
 *
 * Fetches /api/pipeline/stats and renders:
 *   - KPI cards: total opps, win rate, active pipeline value, won value
 *   - Stage distribution: horizontal bar chart
 *   - Priority breakdown: pill counts
 */

// Ordered stage display config — matches KANBAN_STAGES in workflows.js
const STAGE_DISPLAY = [
    { key: 'identified',               label: '01 Qualification',        colorClass: 'bg-blue-500' },
    { key: 'qualifying',               label: '01 Qualification',        colorClass: 'bg-blue-500' },
    { key: 'long_lead',                label: '02 Long Lead',             colorClass: 'bg-indigo-500' },
    { key: 'bid_decision',             label: '03 Bid Decision',          colorClass: 'bg-purple-500' },
    { key: 'active',                   label: '04 In Progress',           colorClass: 'bg-yellow-500' },
    { key: 'submitted',                label: '05 Waiting/Review',        colorClass: 'bg-orange-500' },
    { key: 'negotiating',              label: '06 In Negotiation',        colorClass: 'bg-amber-500' },
    { key: 'awarded',                  label: '07 Closed Won',            colorClass: 'bg-green-600' },
    { key: 'lost',                     label: '08 Closed Lost',           colorClass: 'bg-red-500' },
    { key: 'no_bid',                   label: '09 No Bid',                colorClass: 'bg-gray-500' },
    { key: 'cancelled',                label: '20 Closed Other',          colorClass: 'bg-slate-500' },
    { key: 'contract_vehicle_won',     label: '98 Awarded Vehicle',       colorClass: 'bg-emerald-600' },
    { key: 'contract_vehicle_complete',label: '99 Completed Vehicle',     colorClass: 'bg-teal-600' },
];

class PipelineHealthManager {
    constructor() {
        this._stats = null;
    }

    async load() {
        const area = document.getElementById('pipeline-health-area');
        if (!area) return;
        this._setLoading(true);
        try {
            const res = await fetch('/api/pipeline/stats');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.status !== 'success') throw new Error(data.message || 'Stats unavailable');
            this._stats = data.stats;
            this._render(data.stats);
        } catch (e) {
            console.error('Pipeline health: failed to load stats', e);
            this._setError(e.message);
        } finally {
            this._setLoading(false);
        }
    }

    // -----------------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------------

    _render(stats) {
        this._renderKPIs(stats);
        this._renderStageChart(stats);
        this._renderPriority(stats);
    }

    _renderKPIs(stats) {
        const winRateEl   = document.getElementById('ph-win-rate');
        const totalEl     = document.getElementById('ph-total');
        const activeValEl = document.getElementById('ph-active-value');
        const wonValEl    = document.getElementById('ph-won-value');

        if (winRateEl) {
            winRateEl.textContent = stats.win_rate != null
                ? `${(stats.win_rate * 100).toFixed(0)}%`
                : '—';
        }
        if (totalEl) totalEl.textContent = stats.total ?? '—';
        if (activeValEl) activeValEl.textContent = this._fmtValue(stats.active_value);
        if (wonValEl)    wonValEl.textContent    = this._fmtValue(stats.won_value);

        // Sub-labels
        const wonLbl  = document.getElementById('ph-won-count');
        const lostLbl = document.getElementById('ph-lost-count');
        if (wonLbl)  wonLbl.textContent  = `${stats.won_count ?? 0} won`;
        if (lostLbl) lostLbl.textContent = `${stats.lost_count ?? 0} lost`;
    }

    _renderStageChart(stats) {
        const container = document.getElementById('ph-stage-bars');
        if (!container) return;
        container.innerHTML = '';

        const byStage = stats.by_stage || {};

        // Merge qualifying into identified for display (both map to "01 Qualification")
        const merged = {};
        STAGE_DISPLAY.forEach(cfg => {
            const raw = byStage[cfg.key] || { count: 0, value: 0 };
            if (!merged[cfg.label]) {
                merged[cfg.label] = { count: 0, value: 0, colorClass: cfg.colorClass };
            }
            merged[cfg.label].count += raw.count;
            merged[cfg.label].value += raw.value;
        });

        const maxCount = Math.max(...Object.values(merged).map(v => v.count), 1);

        STAGE_DISPLAY
            // De-duplicate by label (qualifying/identified are merged)
            .filter((cfg, idx, arr) => arr.findIndex(c => c.label === cfg.label) === idx)
            .forEach(cfg => {
                const d = merged[cfg.label] || { count: 0, value: 0, colorClass: cfg.colorClass };
                if (d.count === 0) return; // omit empty stages

                const pct = Math.round((d.count / maxCount) * 100);

                const row = document.createElement('div');
                row.className = 'grid grid-cols-[10rem_1fr_4rem_5rem] items-center gap-3 py-1';

                // Label
                const lbl = document.createElement('span');
                lbl.className = 'text-xs text-gray-600 dark:text-gray-400 truncate text-right';
                lbl.textContent = cfg.label;

                // Bar track
                const track = document.createElement('div');
                track.className = 'h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden';
                const fill = document.createElement('div');
                fill.className = `h-full ${d.colorClass} rounded-full transition-all duration-500`;
                fill.style.width = `${pct}%`;
                track.appendChild(fill);

                // Count
                const cnt = document.createElement('span');
                cnt.className = 'text-xs font-medium text-gray-700 dark:text-gray-300 text-right';
                cnt.textContent = d.count;

                // Value
                const val = document.createElement('span');
                val.className = 'text-xs text-gray-500 dark:text-gray-400 text-right';
                val.textContent = this._fmtValue(d.value);

                row.appendChild(lbl);
                row.appendChild(track);
                row.appendChild(cnt);
                row.appendChild(val);
                container.appendChild(row);
            });

        if (container.children.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-400 dark:text-gray-500 text-center py-4">No opportunities yet.</p>';
        }
    }

    _renderPriority(stats) {
        const container = document.getElementById('ph-priority-pills');
        if (!container) return;
        container.innerHTML = '';

        const byPriority = stats.by_priority || {};
        const cfg = {
            high:   'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
            medium: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300',
            low:    'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
        };
        const order = ['high', 'medium', 'low'];

        order.forEach(pri => {
            const count = byPriority[pri];
            if (!count) return;
            const pill = document.createElement('span');
            pill.className = `inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${cfg[pri] || cfg.low}`;
            pill.innerHTML = `<span class="font-bold">${count}</span> ${pri}`;
            container.appendChild(pill);
        });

        if (container.children.length === 0) {
            container.innerHTML = '<span class="text-sm text-gray-400 dark:text-gray-500">—</span>';
        }
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    _fmtValue(v) {
        if (v == null || v === 0) return '$0';
        if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(1)}B`;
        if (v >= 1_000_000)     return `$${(v / 1_000_000).toFixed(1)}M`;
        if (v >= 1_000)         return `$${(v / 1_000).toFixed(0)}K`;
        return `$${v}`;
    }

    _setLoading(on) {
        const spinner = document.getElementById('ph-spinner');
        if (spinner) spinner.classList.toggle('hidden', !on);
    }

    _setError(msg) {
        const container = document.getElementById('ph-stage-bars');
        if (container) {
            container.innerHTML = `<p class="text-sm text-red-500 dark:text-red-400 text-center py-4">Error loading stats: ${msg}</p>`;
        }
    }
}

window.pipelineHealthManager = new PipelineHealthManager();
