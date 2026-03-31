// Debug mode — set localStorage.setItem('DEBUG_MODE', 'true') to enable verbose logging
const DEBUG_MODE = localStorage.getItem('DEBUG_MODE') === 'true';

function debugLog(...args) {
    if (DEBUG_MODE) {
        console.log(...args);
    }
}
