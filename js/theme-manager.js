// Theme management
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 'system';
        this.init();
    }

    init() {
        this.applyTheme();
        this.setupThemeToggle();

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (this.theme === 'system') {
                this.applyTheme();
            }
        });
    }

    applyTheme() {
        const isDark = this.theme === 'dark' ||
            (this.theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

        document.documentElement.classList.toggle('dark', isDark);

        // Update theme toggle icons
        this.updateThemeIcons(isDark);

        // Update favicon for dark mode
        this.updateFavicon(isDark);
    }

    updateThemeIcons(isDark) {
        const lightIcon = document.querySelector('.theme-icon-light');
        const darkIcon = document.querySelector('.theme-icon-dark');

        if (lightIcon && darkIcon) {
            if (isDark) {
                // In dark mode, show sun icon (to switch to light)
                lightIcon.classList.remove('hidden');
                lightIcon.classList.add('block');
                darkIcon.classList.remove('block');
                darkIcon.classList.add('hidden');
            } else {
                // In light mode, show moon icon (to switch to dark)
                lightIcon.classList.remove('block');
                lightIcon.classList.add('hidden');
                darkIcon.classList.remove('hidden');
                darkIcon.classList.add('block');
            }
        }
    }

    toggleTheme() {
        // Simple toggle between light and dark (skip system for direct toggle)
        if (this.theme === 'dark') {
            this.setTheme('light');
        } else {
            this.setTheme('dark');
        }
    }

    setTheme(newTheme) {
        this.theme = newTheme;
        localStorage.setItem('theme', this.theme);
        this.applyTheme();
        this.updateThemeSelectors();

        debugLog(`Theme changed to: ${this.theme}`);
    }

    updateFavicon(isDark) {
        const favicon = document.querySelector('link[rel="icon"]');
        const appleTouchIcon = document.querySelector('link[rel="apple-touch-icon"]');

        if (isDark) {
            // In dark mode, use the dark variant
            if (favicon) favicon.href = 'robobrain-dark.svg';
            if (appleTouchIcon) appleTouchIcon.href = 'robobrain-dark.svg';
        } else {
            // In light mode, use the original
            if (favicon) favicon.href = 'robobrain.svg';
            if (appleTouchIcon) appleTouchIcon.href = 'robobrain.svg';
        }
    }

    updateThemeSelectors() {
        // Update theme selector in settings if it exists
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.value = this.theme;
        }
    }

    setupThemeToggle() {
        const toggleButton = document.querySelector('.theme-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleTheme();
            });
        }
    }
}
