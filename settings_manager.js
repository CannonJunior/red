/**
 * Settings Manager — Typography and Source Code tabs
 *
 * Handles:
 *  - Typography: font family, font scale, line height; persisted in localStorage
 *  - Source Code: lazy-loads /api/source-tree and renders an interactive file tree
 *
 * Hooks into the existing ColorManager tab-switching system by observing the
 * visibility of each tab's content div via MutationObserver.
 */

class SettingsManager {
    constructor() {
        this._sourceLoaded = false;
        this._treeState   = {};   // nodeId → expanded bool

        this._typography  = this._loadTypography();
        this._init();
    }

    // -------------------------------------------------------------------------
    // Bootstrap
    // -------------------------------------------------------------------------

    _init() {
        // Apply saved typography immediately on page load
        this._applyTypography(this._typography);
        this._syncTypographyControls(this._typography);

        // Attach Typography control listeners
        this._attachTypographyListeners();

        // Watch for Source Code tab becoming visible (lazy load)
        this._watchTabVisibility('source-code-tab', () => this._loadSourceTree());

        // Watch for Typography tab becoming visible (sync controls to saved state)
        this._watchTabVisibility('typography-tab', () => this._syncTypographyControls(this._typography));

        // Reset button
        const resetBtn = document.getElementById('reset-typography-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this._resetTypography());
        }
    }

    /**
     * Observe when a settings tab content div becomes visible.
     * ColorManager adds/removes `hidden` via class — MutationObserver catches it.
     */
    _watchTabVisibility(tabId, callback) {
        const el = document.getElementById(tabId);
        if (!el) return;

        const observer = new MutationObserver(() => {
            if (!el.classList.contains('hidden')) {
                callback();
            }
        });
        observer.observe(el, { attributes: true, attributeFilter: ['class'] });
    }

    // -------------------------------------------------------------------------
    // Typography
    // -------------------------------------------------------------------------

    _defaultTypography() {
        return {
            fontFamily: 'Montserrat',
            fontScale:  1.0,
            lineHeight: 1.5,
        };
    }

    _loadTypography() {
        try {
            const raw = localStorage.getItem('red_typography');
            return raw ? { ...this._defaultTypography(), ...JSON.parse(raw) } : this._defaultTypography();
        } catch (_) {
            return this._defaultTypography();
        }
    }

    _saveTypography(settings) {
        this._typography = settings;
        localStorage.setItem('red_typography', JSON.stringify(settings));
    }

    _applyTypography(settings) {
        const root = document.documentElement;
        // Font family
        const fontStack = settings.fontFamily === 'Montserrat'
            ? "'Montserrat', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            : `${settings.fontFamily}, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`;
        root.style.setProperty('--font-family', fontStack);
        // Font scale (multiplied against the 14px base in styles.css)
        root.style.setProperty('--user-font-scale', String(settings.fontScale));
        // Line height
        root.style.setProperty('--user-line-height', String(settings.lineHeight));
    }

    _syncTypographyControls(settings) {
        // Font family cards
        document.querySelectorAll('.font-option-card').forEach(card => {
            const font = card.dataset.font;
            const isSelected = font === settings.fontFamily;
            card.classList.toggle('border-blue-500',      isSelected);
            card.classList.toggle('bg-blue-50',           isSelected);
            card.classList.toggle('dark:bg-blue-900/20',  isSelected);
            card.classList.toggle('border-gray-200',      !isSelected);
            card.classList.toggle('dark:border-gray-600', !isSelected);
            const radio = card.querySelector('input[type=radio]');
            if (radio) radio.checked = isSelected;
        });

        // Font scale slider
        const slider = document.getElementById('font-scale-slider');
        if (slider) slider.value = String(settings.fontScale);
        this._updateScaleLabel(settings.fontScale);

        // Line height radios
        document.querySelectorAll('input[name="line-height"]').forEach(radio => {
            radio.checked = parseFloat(radio.value) === settings.lineHeight;
        });
        this._updateLineHeightCards(settings.lineHeight);

        // Preview
        this._updatePreview(settings);
    }

    _attachTypographyListeners() {
        // Font family cards (click on card or radio)
        document.addEventListener('change', (e) => {
            if (e.target.name === 'font-family') {
                const settings = { ...this._typography, fontFamily: e.target.value };
                this._saveTypography(settings);
                this._applyTypography(settings);
                this._syncTypographyControls(settings);
            }
            if (e.target.name === 'line-height') {
                const lh = parseFloat(e.target.value);
                const settings = { ...this._typography, lineHeight: lh };
                this._saveTypography(settings);
                this._applyTypography(settings);
                this._updateLineHeightCards(lh);
                this._updatePreview(settings);
            }
        });

        // Font scale slider — live update on drag
        const slider = document.getElementById('font-scale-slider');
        if (slider) {
            slider.addEventListener('input', () => {
                const scale = parseFloat(slider.value);
                const settings = { ...this._typography, fontScale: scale };
                this._typography = settings;
                this._applyTypography(settings);
                this._updateScaleLabel(scale);
                this._updatePreview(settings);
            });
            // Save on release
            slider.addEventListener('change', () => {
                this._saveTypography(this._typography);
            });
        }
    }

    _updateScaleLabel(scale) {
        const label = document.getElementById('font-scale-label');
        if (!label) return;
        const pct = Math.round(scale * 100);
        const name = scale <= 0.9 ? 'Compact' : scale <= 1.05 ? 'Normal' : scale <= 1.15 ? 'Large' : 'X-Large';
        label.textContent = `${name} (${pct}%)`;
    }

    _updateLineHeightCards(lh) {
        document.querySelectorAll('.line-height-card').forEach(card => {
            const isSelected = parseFloat(card.dataset.lh) === lh;
            card.classList.toggle('border-blue-500', isSelected);
            card.classList.toggle('border-gray-200',      !isSelected);
            card.classList.toggle('dark:border-gray-600', !isSelected);
        });
    }

    _updatePreview(settings) {
        const preview = document.getElementById('typography-preview');
        if (!preview) return;
        const fontStack = settings.fontFamily === 'Montserrat'
            ? "'Montserrat', 'Inter', sans-serif"
            : `${settings.fontFamily}, sans-serif`;
        const basePx = 14 * settings.fontScale;
        preview.style.fontFamily  = fontStack;
        preview.style.fontSize    = `${basePx.toFixed(1)}px`;
        preview.style.lineHeight  = String(settings.lineHeight);
    }

    _resetTypography() {
        const defaults = this._defaultTypography();
        this._saveTypography(defaults);
        this._applyTypography(defaults);
        this._syncTypographyControls(defaults);
    }

    // -------------------------------------------------------------------------
    // Source Code Tab
    // -------------------------------------------------------------------------

    async _loadSourceTree() {
        if (this._sourceLoaded) return;

        try {
            const resp = await fetch('/api/source-tree');
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();

            this._renderStats(data.stats);
            this._renderTree(data.tree);
            this._sourceLoaded = true;

            // Show expand/collapse controls
            document.getElementById('source-expand-all')?.classList.remove('hidden');
            document.getElementById('source-collapse-all')?.classList.remove('hidden');
        } catch (err) {
            const container = document.getElementById('source-stats-cards');
            if (container) {
                container.innerHTML = `<div class="col-span-full text-sm text-red-500 dark:text-red-400 py-4">
                    Failed to load source tree: ${err.message}
                </div>`;
            }
        }
    }

    _renderStats(stats) {
        const container = document.getElementById('source-stats-cards');
        if (!container) return;

        const fmt = (n) => n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);
        const fmtSize = (bytes) => bytes >= 1048576
            ? `${(bytes / 1048576).toFixed(1)} MB`
            : `${(bytes / 1024).toFixed(0)} KB`;

        const items = [
            { label: 'Files',       value: fmt(stats.files),       icon: '📄' },
            { label: 'Directories', value: fmt(stats.directories),  icon: '📁' },
            { label: 'Lines',       value: fmt(stats.total_lines),  icon: '📝' },
            { label: 'Size',        value: fmtSize(stats.total_size), icon: '💾' },
        ];

        container.innerHTML = items.map(item => `
            <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 text-center">
                <div class="text-2xl mb-1">${item.icon}</div>
                <div class="text-2xl font-bold text-gray-900 dark:text-white">${item.value}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">${item.label}</div>
            </div>
        `).join('');
    }

    _renderTree(nodes) {
        const container = document.getElementById('source-tree-container');
        if (!container) return;

        container.innerHTML = `<div class="p-3">${this._buildTreeHtml(nodes, 0)}</div>`;

        // Attach toggle listeners
        container.querySelectorAll('[data-tree-toggle]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const nodeId = btn.dataset.nodeId;
                const childEl = document.getElementById(`tree-children-${nodeId}`);
                if (!childEl) return;
                const isOpen = !childEl.classList.contains('hidden');
                childEl.classList.toggle('hidden', isOpen);
                btn.textContent = isOpen ? '▶' : '▼';
            });
        });

        // Expand/Collapse All
        document.getElementById('source-expand-all')?.addEventListener('click', () => {
            container.querySelectorAll('[id^="tree-children-"]').forEach(el => el.classList.remove('hidden'));
            container.querySelectorAll('[data-tree-toggle]').forEach(btn => btn.textContent = '▼');
        });
        document.getElementById('source-collapse-all')?.addEventListener('click', () => {
            container.querySelectorAll('[id^="tree-children-"]').forEach(el => el.classList.add('hidden'));
            container.querySelectorAll('[data-tree-toggle]').forEach(btn => btn.textContent = '▶');
        });
    }

    _buildTreeHtml(nodes, depth, parentId = 'root') {
        return nodes.map((node, idx) => {
            const nodeId = `${parentId}-${idx}`;
            const indent = depth * 16;

            if (node.type === 'directory') {
                const lineStr = node.total_lines > 0
                    ? `<span class="text-gray-400 dark:text-gray-500 ml-2">${this._fmtLines(node.total_lines)} lines · ${node.file_count} files</span>`
                    : `<span class="text-gray-400 dark:text-gray-500 ml-2">${node.file_count} files</span>`;
                const childrenHtml = this._buildTreeHtml(node.children || [], depth + 1, nodeId);
                // Top-level dirs open by default, deeper dirs collapsed
                const startOpen = depth < 1;
                return `
                    <div class="leading-6">
                        <div class="flex items-center hover:bg-gray-100 dark:hover:bg-gray-800 rounded px-1 cursor-pointer" style="padding-left:${indent}px">
                            <span data-tree-toggle data-node-id="${nodeId}" class="w-4 text-gray-400 dark:text-gray-500 select-none mr-1 text-xs">${startOpen ? '▼' : '▶'}</span>
                            <span class="mr-1.5">📁</span>
                            <span class="font-medium text-gray-800 dark:text-gray-200">${this._esc(node.name)}/</span>
                            ${lineStr}
                        </div>
                        <div id="tree-children-${nodeId}" class="${startOpen ? '' : 'hidden'}">
                            ${childrenHtml}
                        </div>
                    </div>`;
            } else {
                const ext  = node.extension || '';
                const icon = this._fileIcon(ext);
                const lineStr = node.lines > 0
                    ? `<span class="text-gray-400 dark:text-gray-500 ml-2">${node.lines.toLocaleString()} lines</span>`
                    : '';
                return `
                    <div class="flex items-center leading-6 hover:bg-gray-100 dark:hover:bg-gray-800 rounded px-1" style="padding-left:${indent + 20}px">
                        <span class="mr-1.5">${icon}</span>
                        <span class="text-gray-700 dark:text-gray-300">${this._esc(node.name)}</span>
                        ${lineStr}
                    </div>`;
            }
        }).join('');
    }

    _fileIcon(ext) {
        const map = {
            py: '🐍', js: '📜', html: '🌐', css: '🎨',
            json: '{}', md: '📖', sh: '⚙️', yaml: '📋',
            yml: '📋', toml: '⚙️', sql: '🗄️', txt: '📄',
            mojo: '🔥',
        };
        return map[ext] || '📄';
    }

    _fmtLines(n) {
        return n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);
    }

    _esc(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

// Instantiate after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});
