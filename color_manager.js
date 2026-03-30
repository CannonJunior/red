/**
 * Color Manager — theme color editing via CSS custom properties.
 *
 * All named colors from styles.css :root are displayed by name, grouped by
 * category, each with a live color swatch and picker. Changes write directly
 * to document.documentElement.style (CSS variable overrides) so they take
 * effect on every element that references the variable.
 *
 * Saved themes store the full set of CSS variable overrides in localStorage.
 */

// ─── Named CSS variable definitions ──────────────────────────────────────────
// Order matches styles.css. Labels are shown in the UI.
const CSS_VAR_GROUPS = [
    {
        group: 'Background',
        vars: [
            { name: '--bg-primary',      label: 'Primary Background' },
            { name: '--bg-secondary',    label: 'Secondary Background' },
            { name: '--bg-tertiary',     label: 'Tertiary Background' },
            { name: '--bg-accent',       label: 'Accent Background' },
            { name: '--bg-accent-hover', label: 'Accent Background (Hover)' },
        ],
    },
    {
        group: 'Text',
        vars: [
            { name: '--text-primary',    label: 'Primary Text' },
            { name: '--text-secondary',  label: 'Secondary Text' },
            { name: '--text-tertiary',   label: 'Tertiary Text' },
            { name: '--text-accent',     label: 'Accent Text' },
            { name: '--text-on-accent',  label: 'Text on Accent' },
        ],
    },
    {
        group: 'Border',
        vars: [
            { name: '--border-primary',  label: 'Primary Border' },
            { name: '--border-secondary','label': 'Secondary Border' },
            { name: '--border-accent',   label: 'Accent Border' },
        ],
    },
];

class ColorManager {
    constructor() {
        this.savedThemes   = this._loadSavedThemes();
        this.customColors  = {};   // varName → hex override currently staged
        this._colorInputs  = [];   // track pickers for Apply / restore
        this._init();
    }

    // ─── Bootstrap ──────────────────────────────────────────────────────────

    _init() {
        this._attachListeners();
        this._renderSavedThemes();
        // Render color grid immediately (colors tab is visible on first open)
        this._renderColorGrid();
    }

    _attachListeners() {
        // Settings button at the bottom of the sidebar → navigate to settings page
        document.getElementById('settings-btn')?.addEventListener('click', () => {
            window.app?.navigateTo('settings');
        });

        // Vertical tab buttons
        document.addEventListener('click', (e) => {
            const tab = e.target.closest('.settings-tab');
            if (tab?.dataset.tab) this.switchTab(tab.dataset.tab);
        });

        // Color Manager buttons
        document.getElementById('restore-defaults-btn')?.addEventListener('click', () => this.restoreDefaults());
        document.getElementById('apply-theme-btn')?.addEventListener('click', () => this.applyTheme());
        document.getElementById('save-theme-btn')?.addEventListener('click', () => this.saveTheme());

        // Re-render when settings area becomes visible (colors may depend on dark/light)
        const settingsArea = document.getElementById('settings-area');
        if (settingsArea) {
            new MutationObserver(() => {
                if (!settingsArea.classList.contains('hidden')) {
                    this._renderColorGrid();
                    this._renderSavedThemes();
                }
            }).observe(settingsArea, { attributes: true, attributeFilter: ['class'] });
        }
    }

    // ─── Tab switching (vertical style) ─────────────────────────────────────

    switchTab(tabName) {
        document.querySelectorAll('.settings-tab').forEach(btn => {
            const isActive = btn.dataset.tab === tabName;
            btn.classList.toggle('active',                isActive);
            btn.classList.toggle('bg-blue-50',            isActive);
            btn.classList.toggle('dark:bg-blue-900/20',   isActive);
            btn.classList.toggle('text-blue-700',         isActive);
            btn.classList.toggle('dark:text-blue-300',    isActive);
            btn.classList.toggle('font-medium',           isActive);
            // inactive state
            btn.classList.toggle('text-gray-600',         !isActive);
            btn.classList.toggle('dark:text-gray-400',    !isActive);
            btn.classList.toggle('hover:bg-gray-100',     !isActive);
            btn.classList.toggle('dark:hover:bg-gray-700',!isActive);
            btn.classList.toggle('hover:text-gray-900',   !isActive);
            btn.classList.toggle('dark:hover:text-white', !isActive);
        });

        document.querySelectorAll('.settings-tab-content').forEach(panel => {
            panel.classList.toggle('hidden', panel.id !== `${tabName}-tab`);
        });
    }

    // ─── Color Grid — CSS variable display ──────────────────────────────────

    _getCurrentValue(varName) {
        // Read the current computed CSS variable value
        const raw = getComputedStyle(document.documentElement)
            .getPropertyValue(varName)
            .trim();
        return raw || '#000000';
    }

    _renderColorGrid() {
        const grid = document.getElementById('color-grid');
        if (!grid) return;

        grid.innerHTML = '';
        this._colorInputs = [];

        CSS_VAR_GROUPS.forEach(({ group, vars }) => {
            // Group header
            const header = document.createElement('div');
            header.className = 'col-span-full';
            header.innerHTML = `
                <h5 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-3 pt-2">${group}</h5>
            `;
            grid.appendChild(header);

            vars.forEach((v) => {
                const currentHex = this._toHex(this._getCurrentValue(v.name));
                const row = document.createElement('div');
                row.className = 'flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-0';
                row.innerHTML = `
                    <div class="flex items-center space-x-3 min-w-0">
                        <div class="color-swatch w-8 h-8 rounded-md border border-gray-300 dark:border-gray-600 flex-shrink-0 shadow-sm"
                             style="background-color:${currentHex}"></div>
                        <div class="min-w-0">
                            <div class="text-sm font-medium text-gray-900 dark:text-white truncate">${v.label}</div>
                            <div class="text-xs text-gray-400 dark:text-gray-500 font-mono">${v.name}</div>
                        </div>
                    </div>
                    <div class="flex items-center space-x-2 flex-shrink-0 ml-4">
                        <input type="text"
                               class="color-hex-input w-20 px-2 py-1 text-xs font-mono bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500"
                               value="${currentHex}" maxlength="7" spellcheck="false">
                        <input type="color"
                               class="color-picker w-8 h-8 rounded cursor-pointer border border-gray-300 dark:border-gray-600 p-0.5 bg-white dark:bg-gray-700"
                               value="${currentHex}">
                    </div>
                `;

                const swatch    = row.querySelector('.color-swatch');
                const hexInput  = row.querySelector('.color-hex-input');
                const picker    = row.querySelector('.color-picker');

                // Color picker → update swatch + hex input + stage override
                picker.addEventListener('input', (e) => {
                    const hex = e.target.value;
                    hexInput.value = hex;
                    swatch.style.backgroundColor = hex;
                    this.customColors[v.name] = hex;
                    // Live preview
                    document.documentElement.style.setProperty(v.name, hex);
                });

                // Hex text input → sync picker + swatch
                hexInput.addEventListener('change', (e) => {
                    const hex = e.target.value.trim();
                    if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
                        picker.value = hex;
                        swatch.style.backgroundColor = hex;
                        this.customColors[v.name] = hex;
                        document.documentElement.style.setProperty(v.name, hex);
                    }
                });

                this._colorInputs.push({ varName: v.name, picker, hexInput, swatch });
                grid.appendChild(row);
            });
        });
    }

    // ─── Apply / Restore ────────────────────────────────────────────────────

    applyTheme() {
        // Changes are already applied live; this is a no-op confirm action
        console.log(`✅ Theme applied (${Object.keys(this.customColors).length} overrides active)`);
    }

    restoreDefaults() {
        if (!confirm('Restore default colors? All unsaved changes will be lost.')) return;

        this.customColors = {};

        // Clear all inline CSS variable overrides
        CSS_VAR_GROUPS.forEach(({ vars }) => {
            vars.forEach(v => {
                document.documentElement.style.removeProperty(v.name);
            });
        });

        // Refresh grid to show reverted values
        this._renderColorGrid();
    }

    // ─── Save / Load themes ──────────────────────────────────────────────────

    saveTheme() {
        const nameInput = document.getElementById('theme-name-input');
        const name = nameInput?.value.trim() || 'Custom Theme';

        // Snapshot all current CSS variable values (not just staged overrides)
        const colors = {};
        CSS_VAR_GROUPS.forEach(({ vars }) => {
            vars.forEach(v => {
                colors[v.name] = this._toHex(this._getCurrentValue(v.name));
            });
        });

        const theme = { name, colors, createdAt: new Date().toISOString() };
        const idx = this.savedThemes.findIndex(t => t.name === name);
        if (idx >= 0) {
            this.savedThemes[idx] = theme;
        } else {
            this.savedThemes.push(theme);
        }

        localStorage.setItem('customThemes', JSON.stringify(this.savedThemes));
        if (nameInput) nameInput.value = '';
        this._renderSavedThemes();
        console.log(`✅ Saved theme: ${name}`);
    }

    _applyLoadedTheme(theme) {
        if (!theme?.colors) return;

        this.customColors = { ...theme.colors };
        Object.entries(theme.colors).forEach(([varName, hex]) => {
            document.documentElement.style.setProperty(varName, hex);
        });

        // Refresh grid to reflect loaded values
        this._renderColorGrid();
    }

    _renderSavedThemes() {
        const list = document.getElementById('saved-themes-list');
        if (!list) return;

        if (this.savedThemes.length === 0) {
            list.innerHTML = '<div class="text-sm text-gray-500 dark:text-gray-400">No custom themes saved yet</div>';
            return;
        }

        list.innerHTML = '';
        this.savedThemes.forEach(theme => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700';
            item.innerHTML = `
                <div>
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${theme.name}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                        ${Object.keys(theme.colors).length} colors · ${new Date(theme.createdAt).toLocaleDateString()}
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button class="load-btn px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                            data-theme="${theme.name}">Load</button>
                    <button class="delete-btn px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                            data-theme="${theme.name}">Delete</button>
                </div>
            `;

            item.querySelector('.load-btn').addEventListener('click', () => this._applyLoadedTheme(theme));
            item.querySelector('.delete-btn').addEventListener('click', () => this._deleteTheme(theme.name));
            list.appendChild(item);
        });
    }

    _deleteTheme(name) {
        if (!confirm(`Delete theme "${name}"?`)) return;
        this.savedThemes = this.savedThemes.filter(t => t.name !== name);
        localStorage.setItem('customThemes', JSON.stringify(this.savedThemes));
        this._renderSavedThemes();
    }

    _loadSavedThemes() {
        try {
            return JSON.parse(localStorage.getItem('customThemes') || '[]');
        } catch (_) {
            return [];
        }
    }

    // ─── Utility ─────────────────────────────────────────────────────────────

    _toHex(value) {
        if (!value) return '#000000';
        if (value.startsWith('#') && value.length === 7) return value;

        // RGB/RGBA → hex
        const m = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (!m) return '#000000';
        return '#' + [m[1], m[2], m[3]]
            .map(n => parseInt(n).toString(16).padStart(2, '0'))
            .join('');
    }
}

// ─── Init ────────────────────────────────────────────────────────────────────
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.colorManager = new ColorManager();
    });
} else {
    window.colorManager = new ColorManager();
}
