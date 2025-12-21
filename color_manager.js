/**
 * Color Manager - Manages application color themes and customization
 */

class ColorManager {
    constructor() {
        this.detectedColors = [];
        this.currentTheme = 'light';
        this.customColors = {};
        this.savedThemes = this.loadSavedThemes();

        this.init();
    }

    init() {
        this.attachEventListeners();
        this.loadCurrentTheme();
    }

    attachEventListeners() {
        // Settings button
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.openSettings());
        }

        // Close settings
        const closeBtn = document.getElementById('close-settings-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSettings());
        }

        // Settings tabs
        const tabs = document.querySelectorAll('.settings-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Detect colors button
        const detectBtn = document.getElementById('detect-colors-btn');
        if (detectBtn) {
            detectBtn.addEventListener('click', () => this.detectColors());
        }

        // Theme selector
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.addEventListener('change', (e) => this.loadTheme(e.target.value));
        }

        // Save theme button
        const saveThemeBtn = document.getElementById('save-theme-btn');
        if (saveThemeBtn) {
            saveThemeBtn.addEventListener('click', () => this.saveTheme());
        }

        // Restore defaults button
        const restoreBtn = document.getElementById('restore-defaults-btn');
        if (restoreBtn) {
            restoreBtn.addEventListener('click', () => this.restoreDefaults());
        }

        // Apply theme button
        const applyBtn = document.getElementById('apply-theme-btn');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyTheme());
        }
    }

    openSettings() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    closeSettings() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    switchTab(tabName) {
        // Update tab buttons
        const tabs = document.querySelectorAll('.settings-tab');
        tabs.forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active', 'text-blue-600', 'dark:text-blue-400', 'border-blue-600', 'dark:border-blue-400');
                tab.classList.remove('text-gray-600', 'dark:text-gray-400', 'border-transparent');
            } else {
                tab.classList.remove('active', 'text-blue-600', 'dark:text-blue-400', 'border-blue-600', 'dark:border-blue-400');
                tab.classList.add('text-gray-600', 'dark:text-gray-400', 'border-transparent');
            }
        });

        // Update tab content
        const contents = document.querySelectorAll('.settings-tab-content');
        contents.forEach(content => {
            if (content.id === `${tabName}-tab`) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        });
    }

    async detectColors() {
        console.log('🎨 Detecting colors from DOM...');

        const colors = new Map();

        // Get all elements
        const allElements = document.querySelectorAll('*');

        allElements.forEach(element => {
            const computed = window.getComputedStyle(element);

            // Extract colors from computed styles
            const properties = [
                { name: 'Background', prop: 'backgroundColor' },
                { name: 'Text', prop: 'color' },
                { name: 'Border', prop: 'borderColor' }
            ];

            properties.forEach(({ name, prop }) => {
                const value = computed[prop];
                if (value && value !== 'rgba(0, 0, 0, 0)' && value !== 'transparent') {
                    const hexValue = this.rgbToHex(value);
                    if (hexValue && hexValue !== '#000000' && hexValue !== '#ffffff') {
                        const key = `${name}-${hexValue}`;
                        if (!colors.has(key)) {
                            colors.set(key, {
                                category: name,
                                value: hexValue,
                                count: 1
                            });
                        } else {
                            colors.get(key).count++;
                        }
                    }
                }
            });
        });

        // Convert Map to array and sort by usage count
        this.detectedColors = Array.from(colors.values())
            .sort((a, b) => b.count - a.count);

        console.log(`✅ Detected ${this.detectedColors.length} unique colors`);

        this.renderColorGrid();
    }

    rgbToHex(rgb) {
        if (!rgb) return null;

        // Check if already hex
        if (rgb.startsWith('#')) return rgb;

        // Parse RGB/RGBA
        const match = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (!match) return null;

        const r = parseInt(match[1]);
        const g = parseInt(match[2]);
        const b = parseInt(match[3]);

        return '#' + [r, g, b].map(x => {
            const hex = x.toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        }).join('');
    }

    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    renderColorGrid() {
        const grid = document.getElementById('color-grid');
        if (!grid) return;

        if (this.detectedColors.length === 0) {
            grid.innerHTML = '<div class="text-center text-gray-500 dark:text-gray-400 col-span-full py-8">No colors detected</div>';
            return;
        }

        grid.innerHTML = '';

        this.detectedColors.forEach((colorData, index) => {
            const colorItem = document.createElement('div');
            colorItem.className = 'bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4';
            colorItem.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-medium text-gray-600 dark:text-gray-400">${colorData.category}</span>
                    <span class="text-xs text-gray-500 dark:text-gray-500">Used ${colorData.count}x</span>
                </div>
                <div class="flex items-center space-x-3">
                    <div class="w-12 h-12 rounded-lg border-2 border-gray-300 dark:border-gray-600" style="background-color: ${colorData.value}"></div>
                    <div class="flex-1">
                        <input type="color"
                               id="color-${index}"
                               value="${colorData.value}"
                               class="w-full h-8 rounded cursor-pointer"
                               data-original="${colorData.value}">
                        <input type="text"
                               value="${colorData.value}"
                               class="w-full mt-1 px-2 py-1 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded text-gray-900 dark:text-white font-mono"
                               id="color-text-${index}"
                               readonly>
                    </div>
                </div>
            `;

            // Add event listener for color picker
            const colorInput = colorItem.querySelector(`#color-${index}`);
            const colorText = colorItem.querySelector(`#color-text-${index}`);
            const preview = colorItem.querySelector('div[style*="background-color"]');

            colorInput.addEventListener('input', (e) => {
                const newColor = e.target.value;
                colorText.value = newColor;
                preview.style.backgroundColor = newColor;
                this.customColors[colorData.value] = newColor;
            });

            grid.appendChild(colorItem);
        });
    }

    loadTheme(themeName) {
        console.log(`Loading theme: ${themeName}`);

        if (themeName === 'light' || themeName === 'dark') {
            // Toggle theme
            if (themeName === 'dark') {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            this.currentTheme = themeName;
        } else if (themeName === 'custom') {
            // Load custom theme
            const customTheme = this.savedThemes.find(t => t.name === 'custom');
            if (customTheme) {
                this.applyCustomTheme(customTheme);
            }
        }

        // Re-detect colors after theme change
        setTimeout(() => this.detectColors(), 100);
    }

    applyCustomTheme(theme) {
        if (!theme || !theme.colors) return;

        // Apply each color mapping
        Object.entries(theme.colors).forEach(([original, custom]) => {
            this.customColors[original] = custom;
        });

        this.applyTheme();
    }

    applyTheme() {
        console.log('🎨 Applying theme changes...');

        // Create style element for custom colors
        let styleEl = document.getElementById('custom-theme-styles');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'custom-theme-styles';
            document.head.appendChild(styleEl);
        }

        // Build CSS rules
        const cssRules = [];

        Object.entries(this.customColors).forEach(([original, custom]) => {
            // This is a simplified approach - in production you'd need more sophisticated color replacement
            cssRules.push(`
                [style*="background-color: ${original}"] {
                    background-color: ${custom} !important;
                }
                [style*="color: ${original}"] {
                    color: ${custom} !important;
                }
            `);
        });

        styleEl.textContent = cssRules.join('\n');

        console.log(`✅ Applied ${Object.keys(this.customColors).length} custom colors`);
    }

    saveTheme() {
        const themeNameInput = document.getElementById('theme-name-input');
        const themeName = themeNameInput.value.trim() || 'Custom Theme';

        const theme = {
            name: themeName,
            colors: { ...this.customColors },
            createdAt: new Date().toISOString(),
            baseTheme: this.currentTheme
        };

        // Add or update theme
        const existingIndex = this.savedThemes.findIndex(t => t.name === themeName);
        if (existingIndex >= 0) {
            this.savedThemes[existingIndex] = theme;
        } else {
            this.savedThemes.push(theme);
        }

        // Save to localStorage
        localStorage.setItem('customThemes', JSON.stringify(this.savedThemes));

        console.log(`✅ Saved theme: ${themeName}`);

        // Update saved themes list
        this.renderSavedThemes();

        // Clear input
        themeNameInput.value = '';
    }

    renderSavedThemes() {
        const listContainer = document.getElementById('saved-themes-list');
        if (!listContainer) return;

        if (this.savedThemes.length === 0) {
            listContainer.innerHTML = '<div class="text-sm text-gray-500 dark:text-gray-400">No custom themes saved yet</div>';
            return;
        }

        listContainer.innerHTML = '';

        this.savedThemes.forEach(theme => {
            const themeItem = document.createElement('div');
            themeItem.className = 'flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg';
            themeItem.innerHTML = `
                <div>
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${theme.name}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                        ${Object.keys(theme.colors).length} colors · ${new Date(theme.createdAt).toLocaleDateString()}
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button class="load-theme-btn px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700" data-theme="${theme.name}">
                        Load
                    </button>
                    <button class="delete-theme-btn px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700" data-theme="${theme.name}">
                        Delete
                    </button>
                </div>
            `;

            // Add event listeners
            themeItem.querySelector('.load-theme-btn').addEventListener('click', () => {
                this.applyCustomTheme(theme);
            });

            themeItem.querySelector('.delete-theme-btn').addEventListener('click', () => {
                this.deleteTheme(theme.name);
            });

            listContainer.appendChild(themeItem);
        });
    }

    deleteTheme(themeName) {
        if (!confirm(`Delete theme "${themeName}"?`)) return;

        this.savedThemes = this.savedThemes.filter(t => t.name !== themeName);
        localStorage.setItem('customThemes', JSON.stringify(this.savedThemes));
        this.renderSavedThemes();
    }

    restoreDefaults() {
        if (!confirm('Restore default color scheme? This will remove all customizations.')) return;

        this.customColors = {};

        // Remove custom styles
        const styleEl = document.getElementById('custom-theme-styles');
        if (styleEl) {
            styleEl.remove();
        }

        // Reset to system theme
        this.loadTheme(this.currentTheme);

        console.log('✅ Restored default colors');
    }

    loadSavedThemes() {
        try {
            const saved = localStorage.getItem('customThemes');
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Failed to load saved themes:', error);
            return [];
        }
    }

    loadCurrentTheme() {
        // Check if user has dark mode preference
        const isDark = document.documentElement.classList.contains('dark');
        this.currentTheme = isDark ? 'dark' : 'light';

        // Render saved themes
        this.renderSavedThemes();
    }
}

// Initialize color manager when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.colorManager = new ColorManager();
    });
} else {
    window.colorManager = new ColorManager();
}
