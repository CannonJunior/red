/**
 * app.js — Thin orchestrator
 *
 * Instantiates all managers and wires them together via window.app.
 * All class definitions live in js/ subdirectory modules loaded before this file.
 */

class App {
    constructor() {
        this.themeManager = new ThemeManager();
        this.chatInterface = new ChatInterface();
        this.navigation = new Navigation();
        this.visualizationManager = new VisualizationManager();
        this.opportunitiesManager = new OpportunitiesManager();
        this.init();
    }

    init() {
        this.showSplashScreen();
        this.setupApp();
    }

    showSplashScreen() {
        const splash = document.getElementById('splash');
        const app = document.getElementById('app');

        // Hide splash and reveal app after brief loading delay.
        // #app starts at opacity:0 (CSS) — adding .loaded triggers the fade-in.
        // The CSS animation fallback in styles.css will reveal the app after
        // 3.5s even if this timer never fires (e.g. due to a JS error).
        setTimeout(() => {
            if (splash) splash.style.display = 'none';
            if (app) {
                app.classList.remove('hidden'); // no-op but harmless
                // Force a reflow so the opacity transition fires correctly
                void app.offsetHeight;
                app.classList.add('loaded');
            }
        }, 2000);
    }

    setupApp() {
        // Initialize any additional app functionality
        debugLog('App initialized successfully');

        // Setup error handling
        window.addEventListener('error', (e) => {
            console.error('App error:', e.error);
        });

        // Setup performance monitoring
        if (window.performance) {
            window.addEventListener('load', () => {
                const loadTime = performance.now();
                debugLog(`App loaded in ${Math.round(loadTime)}ms`);
            });
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    window.integrationManager = new IntegrationManager();

    // Initialize CAG Manager
    if (typeof CAGManager !== 'undefined') {
        window.app.cagManager = new CAGManager();
        debugLog('✅ CAG Manager initialized');
    }

    // Initialize MCP Agent System integration
    initializeMCPAgentIntegration();

    // Make integration manager available globally for future use
    debugLog('Robobrain loaded and ready');
    debugLog('🤖 MCP Agent System integration initialized');
});
