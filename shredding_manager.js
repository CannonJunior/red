/**
 * RFP Shredding & Compliance Matrix Manager
 *
 * Handles RFP shredding workflow and compliance matrix display.
 */

class ShreddingManager {
    constructor() {
        this.currentOpportunityId = null;
        this.requirements = [];
        this.filters = {
            section: '',
            compliance_type: '',
            category: '',
            priority: '',
            status: ''
        };
        this.init();
    }

    init() {
        console.log('Initializing Shredding Manager...');
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Upload RFP button
        const uploadBtn = document.getElementById('upload-rfp-btn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => this.showUploadDialog());
        }

        // Filter dropdowns
        const filterElements = ['section-filter', 'compliance-filter', 'category-filter', 'priority-filter', 'status-filter'];
        filterElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', (e) => {
                    const filterKey = id.replace('-filter', '').replace('-', '_');
                    this.filters[filterKey] = e.target.value;
                    this.loadRequirements(this.currentOpportunityId);
                });
            }
        });

        // Export CSV button
        const exportBtn = document.getElementById('export-matrix-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportMatrix());
        }
    }

    /**
     * Show upload RFP dialog
     */
    showUploadDialog() {
        // Create modal dialog
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl">
                <h2 class="text-2xl font-semibold mb-4">Upload RFP for Shredding</h2>

                <form id="upload-rfp-form" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium mb-2">RFP PDF File *</label>
                        <input type="file" id="rfp-file" accept=".pdf" required
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                    </div>

                    <div>
                        <label class="block text-sm font-medium mb-2">RFP Number *</label>
                        <input type="text" id="rfp-number" placeholder="FA8732-25-R-0001" required
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                    </div>

                    <div>
                        <label class="block text-sm font-medium mb-2">Opportunity Name *</label>
                        <input type="text" id="opportunity-name" placeholder="IT Support Services" required
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                    </div>

                    <div>
                        <label class="block text-sm font-medium mb-2">Due Date *</label>
                        <input type="date" id="due-date" required
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                    </div>

                    <div>
                        <label class="block text-sm font-medium mb-2">Agency</label>
                        <input type="text" id="agency" placeholder="Air Force"
                            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium mb-2">NAICS Code</label>
                            <input type="text" id="naics-code" placeholder="541512"
                                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-2">Set-Aside</label>
                            <select id="set-aside"
                                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                                <option value="">None</option>
                                <option value="Small Business">Small Business</option>
                                <option value="8(a)">8(a)</option>
                                <option value="HUBZone">HUBZone</option>
                                <option value="SDVOSB">SDVOSB</option>
                                <option value="WOSB">WOSB</option>
                            </select>
                        </div>
                    </div>

                    <div class="flex items-center space-x-4">
                        <label class="flex items-center">
                            <input type="checkbox" id="create-tasks" checked
                                class="mr-2">
                            Create Tasks
                        </label>
                        <label class="flex items-center">
                            <input type="checkbox" id="auto-assign" checked
                                class="mr-2">
                            Auto-Assign
                        </label>
                    </div>

                    <div class="flex justify-end space-x-3 mt-6">
                        <button type="button" id="cancel-upload-btn"
                            class="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700">
                            Cancel
                        </button>
                        <button type="submit"
                            class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600">
                            Start Shredding
                        </button>
                    </div>
                </form>

                <div id="upload-progress" class="hidden mt-4">
                    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div id="upload-progress-bar"
                            class="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style="width: 0%"></div>
                    </div>
                    <p id="upload-status" class="text-sm text-gray-600 dark:text-gray-400 mt-2"></p>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Cancel button
        document.getElementById('cancel-upload-btn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        // Form submission
        document.getElementById('upload-rfp-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleUpload(modal);
        });
    }

    /**
     * Handle RFP upload and shredding
     */
    async handleUpload(modal) {
        const fileInput = document.getElementById('rfp-file');
        const file = fileInput.files[0];

        if (!file) {
            alert('Please select a PDF file');
            return;
        }

        // Show progress
        document.getElementById('upload-rfp-form').classList.add('hidden');
        document.getElementById('upload-progress').classList.remove('hidden');

        // Upload file first (you'll need to implement file upload endpoint)
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Update progress
            this.updateProgress(10, 'Uploading PDF...');

            // Upload file (implement this endpoint)
            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('File upload failed');
            }

            const uploadData = await uploadResponse.json();
            const filePath = uploadData.file_path;

            this.updateProgress(30, 'Starting RFP shredding...');

            // Start shredding
            const shreddingResponse = await fetch('/api/shredding/shred', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_path: filePath,
                    rfp_number: document.getElementById('rfp-number').value,
                    opportunity_name: document.getElementById('opportunity-name').value,
                    due_date: document.getElementById('due-date').value,
                    agency: document.getElementById('agency').value || null,
                    naics_code: document.getElementById('naics-code').value || null,
                    set_aside: document.getElementById('set-aside').value || null,
                    create_tasks: document.getElementById('create-tasks').checked,
                    auto_assign: document.getElementById('auto-assign').checked
                })
            });

            if (!shreddingResponse.ok) {
                const error = await shreddingResponse.json();
                throw new Error(error.error || 'Shredding failed');
            }

            const result = await shreddingResponse.json();

            this.updateProgress(100, 'Shredding complete!');

            // Show success message
            setTimeout(() => {
                document.body.removeChild(modal);
                this.showShredResults(result);
            }, 1000);

        } catch (error) {
            console.error('Upload/shredding failed:', error);
            document.getElementById('upload-status').textContent = `Error: ${error.message}`;
            document.getElementById('upload-status').classList.add('text-red-500');
        }
    }

    updateProgress(percent, message) {
        document.getElementById('upload-progress-bar').style.width = `${percent}%`;
        document.getElementById('upload-status').textContent = message;
    }

    /**
     * Show shredding results
     */
    showShredResults(result) {
        alert(`
RFP Shredding Complete!

Opportunity ID: ${result.opportunity_id}
Total Requirements: ${result.total_requirements}
- Mandatory: ${result.mandatory_count}
- Recommended: ${result.recommended_count}
- Optional: ${result.optional_count}

Tasks Created: ${result.tasks_created}
Matrix File: ${result.matrix_file}
        `);

        // Load the compliance matrix
        this.loadComplianceMatrix(result.opportunity_id);
    }

    /**
     * Load compliance matrix for opportunity
     */
    async loadComplianceMatrix(opportunityId) {
        this.currentOpportunityId = opportunityId;

        // Load status
        await this.loadStatus(opportunityId);

        // Load requirements
        await this.loadRequirements(opportunityId);
    }

    /**
     * Load opportunity status
     */
    async loadStatus(opportunityId) {
        try {
            const response = await fetch(`/api/shredding/status/${opportunityId}`);
            if (!response.ok) {
                throw new Error('Failed to load status');
            }

            const status = await response.json();
            this.displayStatus(status);

        } catch (error) {
            console.error('Failed to load status:', error);
        }
    }

    /**
     * Display opportunity status
     */
    displayStatus(status) {
        const statusContainer = document.getElementById('compliance-status');
        if (!statusContainer) return;

        const req = status.requirements;
        const completionRate = req.completion_rate || 0;

        statusContainer.innerHTML = `
            <div class="grid grid-cols-4 gap-4 mb-6">
                <div class="bg-white dark:bg-gray-800 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">Total Requirements</div>
                    <div class="text-2xl font-bold">${req.total}</div>
                </div>
                <div class="bg-white dark:bg-gray-800 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">Mandatory</div>
                    <div class="text-2xl font-bold text-red-500">${req.mandatory}</div>
                </div>
                <div class="bg-white dark:bg-gray-800 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">Compliant</div>
                    <div class="text-2xl font-bold text-green-500">${req.compliant}</div>
                </div>
                <div class="bg-white dark:bg-gray-800 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">Completion Rate</div>
                    <div class="text-2xl font-bold">${completionRate.toFixed(1)}%</div>
                </div>
            </div>

            <div class="bg-white dark:bg-gray-800 p-4 rounded-lg mb-6">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-sm font-medium">Compliance Progress</span>
                    <span class="text-sm text-gray-500">${req.compliant} / ${req.total}</span>
                </div>
                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div class="bg-green-500 h-2 rounded-full transition-all duration-300"
                        style="width: ${completionRate}%"></div>
                </div>
            </div>
        `;
    }

    /**
     * Load requirements
     */
    async loadRequirements(opportunityId) {
        if (!opportunityId) return;

        try {
            // Build query params
            const params = new URLSearchParams();
            Object.entries(this.filters).forEach(([key, value]) => {
                if (value) {
                    params.append(key, value);
                }
            });

            const response = await fetch(`/api/shredding/requirements/${opportunityId}?${params}`);
            if (!response.ok) {
                throw new Error('Failed to load requirements');
            }

            const data = await response.json();
            this.requirements = data.requirements;
            this.displayRequirements();

        } catch (error) {
            console.error('Failed to load requirements:', error);
        }
    }

    /**
     * Display requirements table
     */
    displayRequirements() {
        const tableContainer = document.getElementById('requirements-table');
        if (!tableContainer) return;

        if (this.requirements.length === 0) {
            tableContainer.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <p>No requirements found</p>
                    <button onclick="shreddingManager.showUploadDialog()"
                        class="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600">
                        Upload RFP
                    </button>
                </div>
            `;
            return;
        }

        tableContainer.innerHTML = `
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-gray-50 dark:bg-gray-700 sticky top-0">
                        <tr>
                            <th class="px-4 py-3 text-left font-medium">ID</th>
                            <th class="px-4 py-3 text-left font-medium">Section</th>
                            <th class="px-4 py-3 text-left font-medium">Requirement</th>
                            <th class="px-4 py-3 text-left font-medium">Type</th>
                            <th class="px-4 py-3 text-left font-medium">Category</th>
                            <th class="px-4 py-3 text-left font-medium">Priority</th>
                            <th class="px-4 py-3 text-left font-medium">Risk</th>
                            <th class="px-4 py-3 text-left font-medium">Status</th>
                            <th class="px-4 py-3 text-left font-medium">Assigned To</th>
                            <th class="px-4 py-3 text-left font-medium">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                        ${this.requirements.map(req => this.renderRequirementRow(req)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    /**
     * Render single requirement row
     */
    renderRequirementRow(req) {
        const complianceColors = {
            'fully_compliant': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
            'partially_compliant': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
            'non_compliant': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
            'not_started': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
        };

        const priorityColors = {
            'high': 'text-red-600',
            'medium': 'text-yellow-600',
            'low': 'text-green-600'
        };

        const riskColors = {
            'red': 'bg-red-500',
            'yellow': 'bg-yellow-500',
            'green': 'bg-green-500'
        };

        return `
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
                <td class="px-4 py-3 font-mono text-xs">${req.id}</td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded text-xs font-medium">
                        ${req.section}
                    </span>
                </td>
                <td class="px-4 py-3 max-w-md truncate" title="${req.source_text}">
                    ${req.source_text}
                </td>
                <td class="px-4 py-3 capitalize">${req.compliance_type}</td>
                <td class="px-4 py-3 capitalize">${req.category || 'unknown'}</td>
                <td class="px-4 py-3 ${priorityColors[req.priority] || ''} font-medium capitalize">
                    ${req.priority}
                </td>
                <td class="px-4 py-3">
                    <div class="w-4 h-4 rounded-full ${riskColors[req.risk_level] || ''}"></div>
                </td>
                <td class="px-4 py-3">
                    <select class="px-2 py-1 ${complianceColors[req.compliance_status] || ''} rounded text-xs font-medium border-none"
                        onchange="shreddingManager.updateRequirementStatus('${req.id}', this.value)">
                        <option value="not_started" ${req.compliance_status === 'not_started' ? 'selected' : ''}>Not Started</option>
                        <option value="fully_compliant" ${req.compliance_status === 'fully_compliant' ? 'selected' : ''}>Fully Compliant</option>
                        <option value="partially_compliant" ${req.compliance_status === 'partially_compliant' ? 'selected' : ''}>Partially Compliant</option>
                        <option value="non_compliant" ${req.compliance_status === 'non_compliant' ? 'selected' : ''}>Non-Compliant</option>
                    </select>
                </td>
                <td class="px-4 py-3 text-xs">
                    ${req.assignee_name || req.assignee_id || 'Unassigned'}
                </td>
                <td class="px-4 py-3">
                    <button onclick="shreddingManager.editRequirement('${req.id}')"
                        class="text-blue-500 hover:text-blue-700 text-xs">
                        Edit
                    </button>
                </td>
            </tr>
        `;
    }

    /**
     * Update requirement status
     */
    async updateRequirementStatus(requirementId, newStatus) {
        try {
            const response = await fetch(`/api/shredding/requirements/${requirementId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    compliance_status: newStatus
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update status');
            }

            // Reload status
            if (this.currentOpportunityId) {
                await this.loadStatus(this.currentOpportunityId);
            }

        } catch (error) {
            console.error('Failed to update status:', error);
            alert('Failed to update status');
        }
    }

    /**
     * Edit requirement
     */
    editRequirement(requirementId) {
        // Find requirement
        const req = this.requirements.find(r => r.id === requirementId);
        if (!req) return;

        // TODO: Implement full edit modal
        alert(`Edit requirement: ${requirementId}`);
    }

    /**
     * Export compliance matrix as CSV
     */
    async exportMatrix() {
        if (!this.currentOpportunityId) {
            alert('No opportunity loaded');
            return;
        }

        try {
            const response = await fetch(`/api/shredding/matrix/${this.currentOpportunityId}`);
            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `compliance_matrix_${this.currentOpportunityId}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (error) {
            console.error('Export failed:', error);
            alert('Failed to export matrix');
        }
    }
}

// Initialize manager
const shreddingManager = new ShreddingManager();
