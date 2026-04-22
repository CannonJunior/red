/**
 * opportunities-import-export.js
 *
 * Handles CSV import (with field-mapping modal), CSV/JSON export,
 * and Delete All for the Opportunities section.
 *
 * Depends on: OpportunitiesManager (window.app.opportunitiesManager)
 */

class OpportunitiesImportExport {
    constructor() {
        // Populated after parse step; held for the confirm step (always CSV string).
        this._pendingCsvContent = null;
        this._pendingHeaders = [];
        this._opportunityFields = [];
        this._autoFieldMap = {};   // server-detected column mapping (CRM export)
        this._init();
    }

    _init() {
        // Inject the field-mapping modal into the DOM on first load.
        this._injectModal();
        this._bindButtons();
    }

    // -----------------------------------------------------------------------
    // Modal injection
    // -----------------------------------------------------------------------

    _injectModal() {
        if (document.getElementById('csv-import-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'csv-import-modal';
        modal.className = 'fixed inset-0 z-50 hidden';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/50" id="csv-import-modal-backdrop"></div>
            <div class="absolute inset-0 flex items-center justify-center p-4">
                <div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
                    <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Import Opportunities from CSV / XLS</h3>
                        <button id="csv-import-modal-close" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="flex-1 overflow-y-auto p-6">
                        <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            Map each column from your CSV or XLS file to an Opportunity field.
                            Columns mapped to <strong>Name</strong> are required.
                        </p>
                        <div id="csv-mapping-table" class="space-y-2"></div>
                        <div id="csv-preview-section" class="mt-6 hidden">
                            <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Preview (first rows)</p>
                            <div id="csv-preview-table" class="overflow-x-auto text-xs"></div>
                        </div>
                    </div>
                    <div class="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
                        <span id="csv-row-count" class="text-sm text-gray-500 dark:text-gray-400"></span>
                        <div class="flex gap-3">
                            <button id="csv-import-cancel-btn" class="px-4 py-2 text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm">Cancel</button>
                            <button id="csv-import-confirm-btn" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">Import</button>
                        </div>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modal);

        document.getElementById('csv-import-modal-backdrop').addEventListener('click', () => this._hideModal());
        document.getElementById('csv-import-modal-close').addEventListener('click', () => this._hideModal());
        document.getElementById('csv-import-cancel-btn').addEventListener('click', () => this._hideModal());
        document.getElementById('csv-import-confirm-btn').addEventListener('click', () => this._confirmImport());
    }

    _showModal() { document.getElementById('csv-import-modal').classList.remove('hidden'); }
    _hideModal() { document.getElementById('csv-import-modal').classList.add('hidden'); }

    // -----------------------------------------------------------------------
    // Button wiring
    // -----------------------------------------------------------------------

    _bindButtons() {
        const importBtn = document.getElementById('import-csv-btn');
        const fileInput = document.getElementById('import-csv-file-input');
        const exportCsvBtn = document.getElementById('export-csv-btn');
        const exportJsonBtn = document.getElementById('export-json-btn');
        const deleteAllBtn = document.getElementById('delete-all-opportunities-btn');

        if (importBtn && fileInput) {
            importBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this._handleFileSelected(e));
        }

        if (exportCsvBtn) exportCsvBtn.addEventListener('click', () => this._exportAs('csv'));
        if (exportJsonBtn) exportJsonBtn.addEventListener('click', () => this._exportAs('json'));
        if (deleteAllBtn) deleteAllBtn.addEventListener('click', () => this._deleteAll());
    }

    // -----------------------------------------------------------------------
    // Import — Step 1: Parse headers (CSV or XLS/XLSX)
    // -----------------------------------------------------------------------

    async _handleFileSelected(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Reset file input so the same file can be re-selected after cancel.
        event.target.value = '';

        const isXls = /\.(xls|xlsx)$/i.test(file.name);

        try {
            let data;
            if (isXls) {
                data = await this._parseXls(file);
            } else {
                data = await this._parseCsv(file);
            }

            if (data.status !== 'success') {
                alert(`Parse error: ${data.message}`);
                return;
            }

            // csv_content is always a CSV string — either read directly (CSV)
            // or returned from the server's XLS→CSV conversion.
            this._pendingCsvContent = data.csv_content;
            this._pendingHeaders = data.headers;
            this._opportunityFields = data.opportunity_fields || [];
            this._autoFieldMap = data.auto_field_map || {};
            this._renderMappingUI(data.headers, data.preview, data.row_count, data.schema_detected);
            this._showModal();
        } catch (err) {
            alert(`Failed to parse file: ${err.message}`);
        }
    }

    async _parseCsv(file) {
        const csvContent = await file.text();
        const res = await fetch('/api/opportunities/import/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ csv_content: csvContent }),
        });
        const data = await res.json();
        // Attach csv_content so the caller can store it uniformly.
        if (data.status === 'success') data.csv_content = csvContent;
        return data;
    }

    async _parseXls(file) {
        // Read binary, base64-encode, send to server for XLS→CSV conversion.
        // Chunk size MUST be a multiple of 3 so each chunk encodes to base64
        // without padding — otherwise intermediate '=' chars corrupt the result.
        const buf = await file.arrayBuffer();
        const bytes = new Uint8Array(buf);
        let b64 = '';
        const CHUNK = 3 * 4096; // 12288 — multiple of 3, no mid-string padding
        for (let i = 0; i < bytes.byteLength; i += CHUNK) {
            b64 += btoa(String.fromCharCode(...bytes.subarray(i, i + CHUNK)));
        }

        const res = await fetch('/api/opportunities/import/xls-parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ xls_content: b64 }),
        });
        // Server returns the converted csv_content along with headers/preview.
        return res.json();
    }

    _renderMappingUI(headers, preview, rowCount, schemaDetected) {
        // --- row count label ---
        document.getElementById('csv-row-count').textContent =
            `${rowCount} data row${rowCount !== 1 ? 's' : ''} detected`;

        // --- mapping dropdowns ---
        const fieldOptions = [
            '<option value="">-- skip --</option>',
            ...this._opportunityFields.map(f =>
                `<option value="${f.key}"${f.required ? ' data-required="true"' : ''}>${f.label}${f.required ? ' *' : ''}</option>`
            ),
        ].join('');

        const table = document.getElementById('csv-mapping-table');

        // Show auto-detection banner when server recognised the CRM schema
        const banner = schemaDetected === 'crm_export'
            ? `<div class="mb-3 px-3 py-2 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg text-sm text-blue-700 dark:text-blue-300 flex items-center gap-2">
                   <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
                   CRM export format detected — columns pre-mapped automatically. Review and adjust below.
               </div>`
            : '';

        table.innerHTML = banner + headers.map(col => {
            // Server auto_field_map takes priority; fallback to local heuristic
            const autoMatch = this._autoFieldMap[col] || this._autoMatch(col);
            const selected = autoMatch
                ? fieldOptions.replace(`value="${autoMatch}"`, `value="${autoMatch}" selected`)
                : fieldOptions;
            return `
                <div class="flex items-center gap-3">
                    <span class="w-48 text-sm text-gray-700 dark:text-gray-300 truncate" title="${this._esc(col)}">
                        ${this._esc(col)}
                    </span>
                    <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                    <select data-csv-col="${this._esc(col)}"
                            class="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500">
                        ${selected}
                    </select>
                </div>`;
        }).join('');

        // --- preview table ---
        if (preview && preview.length) {
            const previewSection = document.getElementById('csv-preview-section');
            previewSection.classList.remove('hidden');
            const previewTable = document.getElementById('csv-preview-table');
            const thCells = headers.map(h => `<th class="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-left whitespace-nowrap">${this._esc(h)}</th>`).join('');
            const rows = preview.map(row =>
                `<tr>${row.map(cell => `<td class="px-2 py-1 border-t border-gray-100 dark:border-gray-700 whitespace-nowrap">${this._esc(String(cell))}</td>`).join('')}</tr>`
            ).join('');
            previewTable.innerHTML = `<table class="w-full border-collapse"><thead><tr>${thCells}</tr></thead><tbody>${rows}</tbody></table>`;
        }
    }

    _autoMatch(colName) {
        const lower = colName.toLowerCase().replace(/[\s_-]/g, '');
        const map = {
            'name': 'name', 'title': 'name', 'opportunity': 'name',
            'description': 'description', 'desc': 'description',
            'pipelinestage': 'pipeline_stage', 'stage': 'pipeline_stage', 'pipeline': 'pipeline_stage',
            'priority': 'priority',
            'value': 'value', 'estimatedvalue': 'value', 'estvalue': 'value', 'amount': 'value',
            'tags': 'tags', 'labels': 'tags', 'categories': 'tags',
            'status': 'status',
        };
        return map[lower] || '';
    }

    // -----------------------------------------------------------------------
    // CSV Import — Step 2: Confirm with field mapping
    // -----------------------------------------------------------------------

    async _confirmImport() {
        const selects = document.querySelectorAll('#csv-mapping-table select');
        const fieldMap = {};
        selects.forEach(sel => {
            if (sel.value) fieldMap[sel.dataset.csvCol] = sel.value;
        });

        // Validate at least one column mapped to 'name'
        const hasName = Object.values(fieldMap).includes('name');
        if (!hasName) {
            alert('Please map at least one column to "Name" before importing.');
            return;
        }

        const confirmBtn = document.getElementById('csv-import-confirm-btn');
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Importing…';

        try {
            const res = await fetch('/api/opportunities/import/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    csv_content: this._pendingCsvContent,
                    field_map: fieldMap,
                }),
            });
            const data = await res.json();

            this._hideModal();
            this._pendingCsvContent = null;

            const msg = data.message || `Imported ${data.imported} opportunities`;
            const errNote = data.errors && data.errors.length
                ? `\n\nSkipped rows:\n${data.errors.slice(0, 5).join('\n')}${data.errors.length > 5 ? `\n…and ${data.errors.length - 5} more` : ''}`
                : '';
            alert(msg + errNote);

            // Reload the opportunities list
            if (window.app && window.app.opportunitiesManager) {
                window.app.opportunitiesManager.loadOpportunities();
            }
        } catch (err) {
            alert(`Import failed: ${err.message}`);
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Import';
        }
    }

    // -----------------------------------------------------------------------
    // Export
    // -----------------------------------------------------------------------

    _exportAs(format) {
        // Trigger download via a temporary anchor pointing at the export endpoint.
        const a = document.createElement('a');
        a.href = `/api/opportunities/export?format=${format}`;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    // -----------------------------------------------------------------------
    // Delete All
    // -----------------------------------------------------------------------

    async _deleteAll() {
        const confirmed = window.confirm(
            'Delete ALL opportunities? This cannot be undone.'
        );
        if (!confirmed) return;

        try {
            const res = await fetch('/api/opportunities', { method: 'DELETE' });
            const data = await res.json();
            if (data.status === 'success') {
                alert(data.message || 'All opportunities deleted.');
                if (window.app && window.app.opportunitiesManager) {
                    window.app.opportunitiesManager.loadOpportunities();
                }
            } else {
                alert(`Error: ${data.message || 'Delete failed'}`);
            }
        } catch (err) {
            alert(`Delete failed: ${err.message}`);
        }
    }

    // -----------------------------------------------------------------------
    // Util
    // -----------------------------------------------------------------------

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }
}

// Instantiate after DOM is ready; app.js runs DOMContentLoaded which fires
// after all scripts load, so we hook the same event here.
document.addEventListener('DOMContentLoaded', () => {
    window.opportunitiesImportExport = new OpportunitiesImportExport();
});
