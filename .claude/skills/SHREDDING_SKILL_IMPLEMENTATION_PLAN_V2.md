# RFP Shredding Skill - Implementation Plan V2 (APPROVED)

**Date**: 2025-12-23
**Status**: Ready for Implementation
**Scope**: Full MVP with Web UI
**Test Case**: JADC2 RFP (SAM.gov f958fc4096c0480baeb316e856799a9c)

---

## Executive Summary - Updated

This is the **approved implementation plan** for the RFP shredding skill, incorporating stakeholder feedback:

**Key Updates from V1**:
1. ✅ **This plan IS the MVP** - Full feature implementation, not reduced scope
2. ✅ **Web UI for Compliance Matrix** - Primary interface with CSV export capability
3. ✅ **Priority: Feature Completeness** - Agentic AI approach provides speed
4. ✅ **Test Case**: JADC2 opportunity from SAM.gov
5. ✅ **Future Extensions**: Proposal filling (PowerPoint, PDF templates)

**Core Capabilities** (MVP Scope):
- Extract requirements from RFP PDFs (Section C, L, M)
- Web-based compliance matrix interface
- Task generation and assignment (users + AI agents)
- CSV export of compliance matrix
- Integration with opportunities, tasks, and search systems
- Real-time compliance status tracking

**Future Features** (Post-MVP):
- Auto-fill proposal templates (PowerPoint, PDF, Word)
- SAM.gov API integration for automatic RFP downloads
- Win theme extraction from Section M
- Collaborative proposal writing workflow
- Analytics and reporting dashboard

---

## Implementation Approach - Revised

### Development Philosophy

**Feature Completeness Over Speed**:
- Build robust, production-ready components
- Full web UI implementation (not deferred)
- Comprehensive testing with real RFPs
- Agent-native architecture ensures performance

**Why This Approach Works**:
- Agents handle heavy processing (Ollama classification)
- Web UI for human oversight and collaboration
- Async processing prevents UI blocking
- Export options (CSV) for external tools

---

## Technical Architecture - Web UI First

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Application                          │
│  (Port 9090 - Existing Server)                             │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼──────────┐  ┌──▼─────────────────┐
│   RFP Upload │  │ Compliance Matrix  │
│    Modal     │  │   UI Component     │
│              │  │                    │
│  - File pick │  │  - Sortable table  │
│  - Metadata  │  │  - Inline editing  │
│  - Progress  │  │  - Status filters  │
└───┬──────────┘  │  - CSV export      │
    │             │  - Task assignment │
    │             └──┬─────────────────┘
    │                │
┌───▼────────────────▼───────────────────────────────────────┐
│              Backend API (FastAPI)                          │
│                                                             │
│  /api/shredding/upload-rfp      [POST]                     │
│  /api/shredding/requirements    [GET, PUT, DELETE]         │
│  /api/shredding/matrix/{opp_id} [GET]                      │
│  /api/shredding/export-csv      [GET]                      │
│  /api/shredding/assign-task     [POST]                     │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴──────────────┐
    │                       │
┌───▼────────────┐   ┌──────▼─────────────┐
│  Shredding     │   │   Agent System     │
│  Engine        │   │                    │
│                │   │  - Classification  │
│  - Docling     │   │  - Task assignment │
│  - Section ID  │   │  - Status updates  │
│  - Req Extract │   └────────────────────┘
│  - Ollama LLM  │
└───┬────────────┘
    │
┌───▼────────────────────────────────────────────────────────┐
│              Data Layer (SQLite)                            │
│                                                             │
│  opportunities.db (existing)                                │
│  ├─ requirements (NEW)                                      │
│  ├─ rfp_metadata (NEW)                                      │
│  ├─ opportunities (existing)                                │
│  └─ tasks (existing)                                        │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow - Upload to Export

```
User Action: Upload RFP PDF
    ↓
Frontend: Upload modal → FormData → /api/shredding/upload-rfp
    ↓
Backend:
  1. Save PDF to uploads/rfps/
  2. Trigger async shredding job
  3. Return job_id to frontend
    ↓
Frontend: Show progress indicator
    ↓
Shredding Engine (Background):
  1. Docling → Extract text from PDF
  2. Detect sections (C, L, M) using regex + headers
  3. Extract requirements (compliance keywords)
  4. Ollama → Classify each requirement
  5. Create opportunity in opportunities.db
  6. Create requirement records
  7. Generate tasks (one per requirement)
  8. Assign tasks (users or agents)
  9. Index in search_system
    ↓
Backend: WebSocket → Send completion event to frontend
    ↓
Frontend: Navigate to compliance matrix view
    ↓
User Action: View/Edit Matrix
    ↓
Frontend: Compliance Matrix UI Component
  - Sortable/filterable table
  - Inline status updates
  - Task assignment dropdown
  - Notes editing
    ↓
User Action: Export CSV
    ↓
Backend: /api/shredding/export-csv → Generate CSV file
    ↓
Frontend: Trigger download
```

---

## Database Schema - Final

### requirements Table

```sql
CREATE TABLE requirements (
    -- Identity
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    task_id TEXT,

    -- Source Information
    section TEXT NOT NULL,              -- C, L, M, etc.
    page_number INTEGER,
    paragraph_id TEXT,
    source_text TEXT NOT NULL,          -- Full requirement text

    -- Classification (from Ollama)
    compliance_type TEXT NOT NULL,      -- mandatory, recommended, optional
    requirement_category TEXT,          -- technical, management, cost, deliverable
    priority TEXT DEFAULT 'medium',     -- high, medium, low
    risk_level TEXT DEFAULT 'green',    -- red, yellow, green

    -- Compliance Tracking
    compliance_status TEXT DEFAULT 'not_started',  -- fully, partially, not_compliant, not_started
    proposal_section TEXT,              -- Where addressed in proposal (e.g., "4.2.3")
    proposal_page INTEGER,              -- Page number in proposal

    -- Assignment
    assignee_id TEXT,                   -- User ID or Agent ID
    assignee_type TEXT,                 -- 'user' or 'agent'
    assignee_name TEXT,                 -- Display name (cached)

    -- Metadata
    keywords TEXT,                      -- JSON array: ["shall", "security", "testing"]
    dependencies TEXT,                  -- JSON array of requirement IDs
    notes TEXT,                         -- User notes
    extracted_entities TEXT,            -- JSON: dates, agencies, contacts (from NER)

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date TIMESTAMP,
    completed_at TIMESTAMP,

    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX idx_requirements_opportunity ON requirements(opportunity_id);
CREATE INDEX idx_requirements_section ON requirements(section);
CREATE INDEX idx_requirements_compliance ON requirements(compliance_status);
CREATE INDEX idx_requirements_assignee ON requirements(assignee_id);
CREATE INDEX idx_requirements_priority ON requirements(priority);
CREATE INDEX idx_requirements_updated ON requirements(updated_at DESC);
```

### rfp_metadata Table

```sql
CREATE TABLE rfp_metadata (
    -- Identity
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL UNIQUE,

    -- RFP Identification
    rfp_number TEXT,                    -- e.g., "FA8732-25-R-0001"
    rfp_title TEXT NOT NULL,
    issuing_agency TEXT,
    office_name TEXT,
    naics_code TEXT,
    naics_description TEXT,
    set_aside TEXT,                     -- e.g., "Small Business", "8(a)", "HUBZone"
    contract_type TEXT,                 -- e.g., "FFP", "CPFF", "T&M"

    -- Dates
    posted_date TIMESTAMP,
    response_due_date TIMESTAMP,
    questions_due_date TIMESTAMP,
    estimated_award_date TIMESTAMP,

    -- Document Information
    file_path TEXT NOT NULL,            -- Path to original PDF
    file_name TEXT,
    file_size_bytes INTEGER,
    page_count INTEGER,
    sections_found TEXT,                -- JSON array: ["A", "B", "C", "L", "M"]

    -- Processing Metadata
    shredded_at TIMESTAMP,
    shredded_by TEXT,                   -- User ID who initiated
    processing_time_seconds REAL,
    total_requirements INTEGER DEFAULT 0,
    mandatory_requirements INTEGER DEFAULT 0,
    optional_requirements INTEGER DEFAULT 0,

    -- Source
    source_url TEXT,                    -- SAM.gov URL
    source_system TEXT DEFAULT 'sam.gov',
    sam_opportunity_id TEXT,            -- SAM.gov opportunity ID

    -- Status
    shredding_status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,

    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
);

CREATE INDEX idx_rfp_metadata_rfp_number ON rfp_metadata(rfp_number);
CREATE INDEX idx_rfp_metadata_due_date ON rfp_metadata(response_due_date);
CREATE INDEX idx_rfp_metadata_status ON rfp_metadata(shredding_status);
```

---

## Web UI Components - Detailed Design

### 1. RFP Upload Modal

**Location**: Opportunities page, header button "📄 Upload RFP"

**HTML Structure**:
```html
<dialog id="rfp-upload-modal" class="modal">
    <div class="modal-header">
        <h2>Upload RFP for Shredding</h2>
        <button class="close-btn" onclick="closeRFPUploadModal()">×</button>
    </div>

    <form id="rfp-upload-form" class="modal-body">
        <!-- File Upload -->
        <div class="form-group">
            <label>RFP Document *</label>
            <div class="file-upload-area" id="file-drop-zone">
                <input type="file" id="rfp-file" accept=".pdf" required hidden>
                <div class="upload-placeholder">
                    <svg>📄</svg>
                    <p>Drag & drop RFP PDF here or <span class="link">browse</span></p>
                    <p class="hint">Supports PDF files up to 50MB</p>
                </div>
                <div class="file-preview" hidden>
                    <span class="file-name"></span>
                    <span class="file-size"></span>
                    <button type="button" class="remove-file">Remove</button>
                </div>
            </div>
        </div>

        <!-- RFP Metadata -->
        <div class="form-row">
            <div class="form-group">
                <label>RFP Number *</label>
                <input type="text" id="rfp-number" placeholder="e.g., FA8732-25-R-0001" required>
            </div>
            <div class="form-group">
                <label>NAICS Code</label>
                <input type="text" id="naics-code" placeholder="e.g., 541512">
            </div>
        </div>

        <div class="form-group">
            <label>Opportunity Name *</label>
            <input type="text" id="opportunity-name" placeholder="e.g., JADC2 IT Support Services" required>
        </div>

        <div class="form-row">
            <div class="form-group">
                <label>Response Due Date *</label>
                <input type="datetime-local" id="due-date" required>
            </div>
            <div class="form-group">
                <label>Questions Due Date</label>
                <input type="datetime-local" id="questions-date">
            </div>
        </div>

        <div class="form-group">
            <label>Issuing Agency</label>
            <input type="text" id="agency" placeholder="e.g., Department of Defense">
        </div>

        <!-- Processing Options -->
        <div class="form-section">
            <h3>Processing Options</h3>
            <label class="checkbox">
                <input type="checkbox" id="extract-requirements" checked disabled>
                <span>Extract requirements from document</span>
            </label>
            <label class="checkbox">
                <input type="checkbox" id="create-tasks" checked>
                <span>Create tasks for each requirement</span>
            </label>
            <label class="checkbox">
                <input type="checkbox" id="auto-assign">
                <span>Auto-assign tasks to agents based on category</span>
            </label>
        </div>

        <!-- Progress Indicator (shown during upload) -->
        <div id="upload-progress" class="progress-container" hidden>
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
            <p class="progress-text">Uploading and processing RFP...</p>
            <div class="progress-steps">
                <div class="step" data-step="upload">
                    <span class="step-icon">⏳</span>
                    <span>Uploading</span>
                </div>
                <div class="step" data-step="extract">
                    <span class="step-icon">⏳</span>
                    <span>Extracting text</span>
                </div>
                <div class="step" data-step="classify">
                    <span class="step-icon">⏳</span>
                    <span>Classifying requirements</span>
                </div>
                <div class="step" data-step="complete">
                    <span class="step-icon">⏳</span>
                    <span>Finalizing</span>
                </div>
            </div>
        </div>
    </form>

    <div class="modal-footer">
        <button type="button" class="btn-secondary" onclick="closeRFPUploadModal()">
            Cancel
        </button>
        <button type="submit" class="btn-primary" form="rfp-upload-form">
            <svg>🔍</svg> Shred RFP
        </button>
    </div>
</dialog>
```

**JavaScript Handler**:
```javascript
async function uploadRFP() {
    const form = document.getElementById('rfp-upload-form');
    const formData = new FormData();

    formData.append('file', document.getElementById('rfp-file').files[0]);
    formData.append('rfp_number', document.getElementById('rfp-number').value);
    formData.append('opportunity_name', document.getElementById('opportunity-name').value);
    formData.append('due_date', document.getElementById('due-date').value);
    formData.append('naics_code', document.getElementById('naics-code').value);
    formData.append('agency', document.getElementById('agency').value);
    formData.append('create_tasks', document.getElementById('create-tasks').checked);
    formData.append('auto_assign', document.getElementById('auto-assign').checked);

    // Show progress
    document.getElementById('upload-progress').hidden = false;
    updateProgressStep('upload', 'active');

    try {
        const response = await fetch('/api/shredding/upload-rfp', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.status === 'success') {
            // Connect to WebSocket for progress updates
            const ws = new WebSocket(`ws://localhost:9090/ws/shredding/${result.job_id}`);

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateProgressStep(data.step, data.status);

                if (data.step === 'complete' && data.status === 'done') {
                    // Navigate to compliance matrix
                    window.location.href = `/opportunities/${result.opportunity_id}?tab=requirements`;
                }
            };
        } else {
            showError(result.message);
        }
    } catch (error) {
        showError('Failed to upload RFP: ' + error.message);
    }
}
```

### 2. Compliance Matrix UI Component

**Location**: Opportunities page, new "Requirements" tab

**HTML Structure**:
```html
<div id="compliance-matrix-view" class="requirements-tab">
    <!-- Header with Stats -->
    <div class="matrix-header">
        <div class="stats-row">
            <div class="stat-card">
                <span class="stat-label">Total Requirements</span>
                <span class="stat-value" id="total-reqs">47</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Completed</span>
                <span class="stat-value green" id="completed-reqs">30</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">In Progress</span>
                <span class="stat-value orange" id="inprogress-reqs">12</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Not Started</span>
                <span class="stat-value gray" id="pending-reqs">5</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Compliance</span>
                <span class="stat-value blue" id="compliance-pct">64%</span>
            </div>
        </div>

        <!-- Progress Bar -->
        <div class="compliance-progress">
            <div class="progress-bar">
                <div class="progress-fill" style="width: 64%"></div>
            </div>
            <span class="progress-label">30 of 47 requirements complete</span>
        </div>
    </div>

    <!-- Filters and Actions -->
    <div class="matrix-controls">
        <div class="filters">
            <select id="filter-section" onchange="filterMatrix()">
                <option value="">All Sections</option>
                <option value="C">Section C (Technical)</option>
                <option value="L">Section L (Instructions)</option>
                <option value="M">Section M (Evaluation)</option>
            </select>

            <select id="filter-status" onchange="filterMatrix()">
                <option value="">All Status</option>
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
            </select>

            <select id="filter-compliance" onchange="filterMatrix()">
                <option value="">All Compliance</option>
                <option value="mandatory">Mandatory</option>
                <option value="recommended">Recommended</option>
                <option value="optional">Optional</option>
            </select>

            <select id="filter-priority" onchange="filterMatrix()">
                <option value="">All Priority</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
            </select>

            <input type="text" id="search-requirements"
                   placeholder="Search requirements..."
                   oninput="filterMatrix()">
        </div>

        <div class="actions">
            <button class="btn-secondary" onclick="exportCSV()">
                <svg>📥</svg> Export CSV
            </button>
            <button class="btn-secondary" onclick="viewGantt()">
                <svg>📊</svg> View Gantt
            </button>
            <button class="btn-primary" onclick="assignAll()">
                <svg>👥</svg> Assign All
            </button>
        </div>
    </div>

    <!-- Compliance Matrix Table -->
    <div class="matrix-table-container">
        <table id="compliance-matrix" class="matrix-table">
            <thead>
                <tr>
                    <th class="sortable" data-sort="req_id">Req ID</th>
                    <th class="sortable" data-sort="section">Section</th>
                    <th class="sortable" data-sort="page">Page</th>
                    <th class="requirement-text">Requirement Text</th>
                    <th class="sortable" data-sort="compliance_type">Type</th>
                    <th class="sortable" data-sort="category">Category</th>
                    <th class="sortable" data-sort="priority">Priority</th>
                    <th class="sortable" data-sort="compliance_status">Status</th>
                    <th class="sortable" data-sort="assignee">Assigned To</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="matrix-body">
                <!-- Dynamically populated rows -->
                <tr data-req-id="C-001" class="requirement-row">
                    <td>
                        <span class="req-badge section-C">C-001</span>
                    </td>
                    <td>C</td>
                    <td>15</td>
                    <td class="requirement-text">
                        <div class="text-preview">
                            The contractor shall provide secure authentication...
                        </div>
                        <button class="expand-btn" onclick="expandRequirement('C-001')">
                            Show full
                        </button>
                    </td>
                    <td>
                        <span class="badge badge-mandatory">Mandatory</span>
                    </td>
                    <td>
                        <span class="badge badge-technical">Technical</span>
                    </td>
                    <td>
                        <span class="priority priority-high">High</span>
                    </td>
                    <td>
                        <select class="status-select" onchange="updateStatus('C-001', this.value)">
                            <option value="not_started">Not Started</option>
                            <option value="in_progress" selected>In Progress</option>
                            <option value="completed">Completed</option>
                        </select>
                    </td>
                    <td>
                        <select class="assignee-select" onchange="updateAssignee('C-001', this.value)">
                            <option value="">Unassigned</option>
                            <optgroup label="Users">
                                <option value="user-john">John Doe</option>
                                <option value="user-sarah">Sarah Miller</option>
                            </optgroup>
                            <optgroup label="Agents">
                                <option value="agent-tech" selected>Agent-Technical-Writer</option>
                                <option value="agent-security">Agent-Security</option>
                            </optgroup>
                        </select>
                    </td>
                    <td class="actions-cell">
                        <button class="icon-btn" onclick="viewRequirementDetail('C-001')" title="View details">
                            <svg>👁️</svg>
                        </button>
                        <button class="icon-btn" onclick="editNotes('C-001')" title="Add notes">
                            <svg>📝</svg>
                        </button>
                    </td>
                </tr>
                <!-- More rows... -->
            </tbody>
        </table>
    </div>

    <!-- Pagination -->
    <div class="matrix-pagination">
        <span class="pagination-info">Showing 1-25 of 47 requirements</span>
        <div class="pagination-controls">
            <button class="page-btn" disabled>‹</button>
            <button class="page-btn active">1</button>
            <button class="page-btn">2</button>
            <button class="page-btn">›</button>
        </div>
    </div>
</div>
```

**JavaScript Controller**:
```javascript
class ComplianceMatrixUI {
    constructor(opportunityId) {
        this.opportunityId = opportunityId;
        this.requirements = [];
        this.filteredRequirements = [];
        this.sortColumn = 'req_id';
        this.sortDirection = 'asc';

        this.init();
    }

    async init() {
        await this.loadRequirements();
        this.renderMatrix();
        this.attachEventListeners();
        this.updateStats();
    }

    async loadRequirements() {
        const response = await fetch(`/api/shredding/requirements/${this.opportunityId}`);
        const data = await response.json();
        this.requirements = data.requirements;
        this.filteredRequirements = [...this.requirements];
    }

    renderMatrix() {
        const tbody = document.getElementById('matrix-body');
        tbody.innerHTML = '';

        this.filteredRequirements.forEach(req => {
            const row = this.createRequirementRow(req);
            tbody.appendChild(row);
        });
    }

    createRequirementRow(req) {
        const tr = document.createElement('tr');
        tr.dataset.reqId = req.id;
        tr.className = 'requirement-row';

        tr.innerHTML = `
            <td><span class="req-badge section-${req.section}">${req.req_id}</span></td>
            <td>${req.section}</td>
            <td>${req.page_number || '-'}</td>
            <td class="requirement-text">
                <div class="text-preview">${this.truncate(req.source_text, 80)}</div>
                <button class="expand-btn" onclick="complianceMatrix.expandRequirement('${req.id}')">
                    Show full
                </button>
            </td>
            <td><span class="badge badge-${req.compliance_type}">${this.formatComplianceType(req.compliance_type)}</span></td>
            <td><span class="badge badge-${req.requirement_category}">${this.formatCategory(req.requirement_category)}</span></td>
            <td><span class="priority priority-${req.priority}">${this.formatPriority(req.priority)}</span></td>
            <td>${this.createStatusSelect(req)}</td>
            <td>${this.createAssigneeSelect(req)}</td>
            <td class="actions-cell">
                <button class="icon-btn" onclick="complianceMatrix.viewDetail('${req.id}')">👁️</button>
                <button class="icon-btn" onclick="complianceMatrix.editNotes('${req.id}')">📝</button>
            </td>
        `;

        return tr;
    }

    async updateStatus(reqId, newStatus) {
        try {
            await fetch(`/api/shredding/requirements/${reqId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({compliance_status: newStatus})
            });

            // Update local state
            const req = this.requirements.find(r => r.id === reqId);
            if (req) {
                req.compliance_status = newStatus;
                if (newStatus === 'completed') {
                    req.completed_at = new Date().toISOString();
                }
            }

            this.updateStats();
            this.showToast('Status updated successfully');
        } catch (error) {
            this.showError('Failed to update status');
        }
    }

    async exportCSV() {
        const response = await fetch(`/api/shredding/export-csv/${this.opportunityId}`);
        const blob = await response.blob();

        // Trigger download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compliance_matrix_${this.opportunityId}.csv`;
        a.click();
    }

    filterMatrix() {
        const section = document.getElementById('filter-section').value;
        const status = document.getElementById('filter-status').value;
        const compliance = document.getElementById('filter-compliance').value;
        const priority = document.getElementById('filter-priority').value;
        const search = document.getElementById('search-requirements').value.toLowerCase();

        this.filteredRequirements = this.requirements.filter(req => {
            if (section && req.section !== section) return false;
            if (status && req.compliance_status !== status) return false;
            if (compliance && req.compliance_type !== compliance) return false;
            if (priority && req.priority !== priority) return false;
            if (search && !req.source_text.toLowerCase().includes(search)) return false;
            return true;
        });

        this.renderMatrix();
        this.updateStats();
    }

    updateStats() {
        const total = this.requirements.length;
        const completed = this.requirements.filter(r => r.compliance_status === 'completed').length;
        const inProgress = this.requirements.filter(r => r.compliance_status === 'in_progress').length;
        const pending = this.requirements.filter(r => r.compliance_status === 'not_started').length;
        const compliancePct = Math.round((completed / total) * 100);

        document.getElementById('total-reqs').textContent = total;
        document.getElementById('completed-reqs').textContent = completed;
        document.getElementById('inprogress-reqs').textContent = inProgress;
        document.getElementById('pending-reqs').textContent = pending;
        document.getElementById('compliance-pct').textContent = `${compliancePct}%`;

        // Update progress bar
        document.querySelector('.progress-fill').style.width = `${compliancePct}%`;
        document.querySelector('.progress-label').textContent = `${completed} of ${total} requirements complete`;
    }
}

// Initialize on page load
let complianceMatrix;
document.addEventListener('DOMContentLoaded', () => {
    const opportunityId = new URLSearchParams(window.location.search).get('opp_id');
    if (opportunityId) {
        complianceMatrix = new ComplianceMatrixUI(opportunityId);
    }
});
```

### 3. Requirement Detail Panel

**Slide-out panel** for viewing/editing full requirement details:

```html
<div id="requirement-detail-panel" class="detail-panel" hidden>
    <div class="panel-header">
        <h3 id="detail-req-id">Requirement C-012</h3>
        <button class="close-btn" onclick="closeDetailPanel()">×</button>
    </div>

    <div class="panel-body">
        <!-- Source Info -->
        <div class="detail-section">
            <h4>Source</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="label">Section:</span>
                    <span id="detail-section">C (Technical)</span>
                </div>
                <div class="detail-item">
                    <span class="label">Page:</span>
                    <span id="detail-page">23</span>
                </div>
                <div class="detail-item">
                    <span class="label">Paragraph:</span>
                    <span id="detail-paragraph">3.4.2</span>
                </div>
            </div>
        </div>

        <!-- Full Text -->
        <div class="detail-section">
            <h4>Requirement Text</h4>
            <div id="detail-text" class="requirement-full-text">
                The contractor shall provide a secure web portal with two-factor
                authentication capability that complies with NIST 800-63B standards...
            </div>
        </div>

        <!-- Classification -->
        <div class="detail-section">
            <h4>Classification</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="label">Compliance Type:</span>
                    <span id="detail-compliance-type">Mandatory</span>
                </div>
                <div class="detail-item">
                    <span class="label">Category:</span>
                    <span id="detail-category">Technical</span>
                </div>
                <div class="detail-item">
                    <span class="label">Priority:</span>
                    <span id="detail-priority">High ⚠️</span>
                </div>
                <div class="detail-item">
                    <span class="label">Risk:</span>
                    <span id="detail-risk">Yellow</span>
                </div>
            </div>

            <div class="keywords-section">
                <span class="label">Keywords:</span>
                <div id="detail-keywords" class="keyword-tags">
                    <span class="tag">shall</span>
                    <span class="tag">secure</span>
                    <span class="tag">authentication</span>
                    <span class="tag">NIST 800-63B</span>
                </div>
            </div>
        </div>

        <!-- Compliance Status -->
        <div class="detail-section">
            <h4>Compliance Status</h4>
            <div class="form-group">
                <label>Status:</label>
                <select id="detail-status" class="form-control">
                    <option value="not_started">Not Started</option>
                    <option value="in_progress" selected>In Progress</option>
                    <option value="completed">Completed</option>
                </select>
            </div>

            <div class="form-group">
                <label>Proposal Reference:</label>
                <input type="text" id="detail-proposal-section"
                       placeholder="e.g., Section 4.3" class="form-control">
            </div>

            <div class="form-group">
                <label>Proposal Page:</label>
                <input type="number" id="detail-proposal-page"
                       placeholder="e.g., 35" class="form-control">
            </div>
        </div>

        <!-- Assignment -->
        <div class="detail-section">
            <h4>Assignment</h4>
            <div class="form-group">
                <label>Assigned To:</label>
                <select id="detail-assignee" class="form-control">
                    <option value="">Unassigned</option>
                    <optgroup label="Users">
                        <option value="user-john">John Doe</option>
                        <option value="user-sarah">Sarah Miller</option>
                    </optgroup>
                    <optgroup label="Agents">
                        <option value="agent-security" selected>Agent-Security</option>
                        <option value="agent-tech">Agent-Technical-Writer</option>
                    </optgroup>
                </select>
            </div>

            <div class="form-group">
                <label>Due Date:</label>
                <input type="date" id="detail-due-date" class="form-control">
            </div>
        </div>

        <!-- Dependencies -->
        <div class="detail-section">
            <h4>Dependencies</h4>
            <div id="detail-dependencies" class="dependency-list">
                <div class="dependency-item">
                    → <a href="#" onclick="viewRequirement('C-010')">C-010</a>
                    (Authentication framework)
                </div>
                <div class="dependency-item">
                    → <a href="#" onclick="viewRequirement('C-015')">C-015</a>
                    (User management)
                </div>
            </div>
            <button class="btn-link" onclick="addDependency()">+ Add Dependency</button>
        </div>

        <!-- Notes -->
        <div class="detail-section">
            <h4>Notes</h4>
            <textarea id="detail-notes" class="form-control" rows="4"
                      placeholder="Add notes or concerns about this requirement...">
Need to clarify MFA requirements with customer.
Check if FIDO2 compliance is required.
            </textarea>
        </div>
    </div>

    <div class="panel-footer">
        <button class="btn-secondary" onclick="closeDetailPanel()">Cancel</button>
        <button class="btn-danger" onclick="deleteRequirement()">Delete</button>
        <button class="btn-primary" onclick="saveRequirementDetail()">Save Changes</button>
    </div>
</div>
```

---

## Backend API Specification

### Endpoints

**POST /api/shredding/upload-rfp**
```python
@router.post("/shredding/upload-rfp")
async def upload_rfp(
    file: UploadFile,
    rfp_number: str = Form(...),
    opportunity_name: str = Form(...),
    due_date: str = Form(...),
    naics_code: Optional[str] = Form(None),
    agency: Optional[str] = Form(None),
    create_tasks: bool = Form(True),
    auto_assign: bool = Form(False)
):
    """
    Upload RFP PDF and initiate shredding process.

    Returns:
        {
            "status": "success",
            "job_id": "uuid",
            "opportunity_id": "uuid",
            "message": "RFP upload initiated"
        }
    """
    # Save file
    file_path = save_uploaded_file(file)

    # Create async shredding job
    job_id = str(uuid.uuid4())

    # Start background task
    background_tasks.add_task(
        shred_rfp_async,
        job_id=job_id,
        file_path=file_path,
        metadata={
            'rfp_number': rfp_number,
            'opportunity_name': opportunity_name,
            'due_date': due_date,
            'naics_code': naics_code,
            'agency': agency,
            'create_tasks': create_tasks,
            'auto_assign': auto_assign
        }
    )

    return {
        "status": "success",
        "job_id": job_id,
        "message": "RFP shredding initiated"
    }
```

**GET /api/shredding/requirements/{opportunity_id}**
```python
@router.get("/shredding/requirements/{opportunity_id}")
async def get_requirements(opportunity_id: str):
    """
    Get all requirements for an opportunity.

    Returns:
        {
            "requirements": [
                {
                    "id": "uuid",
                    "req_id": "C-001",
                    "section": "C",
                    "page_number": 15,
                    "source_text": "The contractor shall...",
                    "compliance_type": "mandatory",
                    "requirement_category": "technical",
                    "priority": "high",
                    "compliance_status": "in_progress",
                    "assignee_id": "agent-tech",
                    "assignee_name": "Agent-Technical-Writer",
                    ...
                }
            ],
            "total": 47,
            "stats": {
                "completed": 30,
                "in_progress": 12,
                "not_started": 5
            }
        }
    """
    conn = sqlite3.connect('opportunities.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM requirements
        WHERE opportunity_id = ?
        ORDER BY section, page_number
    """, (opportunity_id,))

    requirements = [dict(row) for row in cursor.fetchall()]

    # Calculate stats
    stats = {
        'completed': sum(1 for r in requirements if r['compliance_status'] == 'completed'),
        'in_progress': sum(1 for r in requirements if r['compliance_status'] == 'in_progress'),
        'not_started': sum(1 for r in requirements if r['compliance_status'] == 'not_started')
    }

    return {
        'requirements': requirements,
        'total': len(requirements),
        'stats': stats
    }
```

**PUT /api/shredding/requirements/{req_id}**
```python
@router.put("/shredding/requirements/{req_id}")
async def update_requirement(
    req_id: str,
    update_data: RequirementUpdate
):
    """
    Update a specific requirement.

    Body:
        {
            "compliance_status": "in_progress",
            "proposal_section": "4.3",
            "proposal_page": 35,
            "assignee_id": "agent-security",
            "notes": "Need clarification on MFA requirements"
        }
    """
    conn = sqlite3.connect('opportunities.db')
    cursor = conn.cursor()

    # Build UPDATE query dynamically
    update_fields = []
    values = []

    for field, value in update_data.dict(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        values.append(value)

    values.append(datetime.now().isoformat())
    values.append(req_id)

    cursor.execute(f"""
        UPDATE requirements
        SET {', '.join(update_fields)}, updated_at = ?
        WHERE id = ?
    """, values)

    conn.commit()
    conn.close()

    return {"status": "success", "updated": req_id}
```

**GET /api/shredding/export-csv/{opportunity_id}**
```python
@router.get("/shredding/export-csv/{opportunity_id}")
async def export_csv(opportunity_id: str):
    """
    Export compliance matrix as CSV file.

    Returns: CSV file download
    """
    import csv
    import io

    # Get requirements
    requirements = get_requirements_from_db(opportunity_id)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'Req ID', 'Section', 'Page', 'Paragraph', 'Requirement Text',
        'Compliance Type', 'Category', 'Priority', 'Risk',
        'Compliance Status', 'Proposal Section', 'Proposal Page',
        'Assigned To', 'Due Date', 'Status', 'Notes', 'Keywords'
    ])

    writer.writeheader()

    for req in requirements:
        writer.writerow({
            'Req ID': req['req_id'],
            'Section': req['section'],
            'Page': req['page_number'],
            'Paragraph': req['paragraph_id'],
            'Requirement Text': req['source_text'],
            'Compliance Type': req['compliance_type'],
            'Category': req['requirement_category'],
            'Priority': req['priority'],
            'Risk': req['risk_level'],
            'Compliance Status': req['compliance_status'],
            'Proposal Section': req['proposal_section'],
            'Proposal Page': req['proposal_page'],
            'Assigned To': req['assignee_name'],
            'Due Date': req['due_date'],
            'Status': req['compliance_status'],
            'Notes': req['notes'],
            'Keywords': ', '.join(json.loads(req['keywords'] or '[]'))
        })

    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=compliance_matrix_{opportunity_id}.csv'
        }
    )
```

**WebSocket /ws/shredding/{job_id}**
```python
@router.websocket("/ws/shredding/{job_id}")
async def shredding_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket for real-time shredding progress updates.

    Sends messages like:
        {"step": "upload", "status": "active", "progress": 10}
        {"step": "extract", "status": "active", "progress": 40}
        {"step": "classify", "status": "active", "progress": 70}
        {"step": "complete", "status": "done", "progress": 100, "opportunity_id": "uuid"}
    """
    await websocket.accept()

    # Subscribe to Redis channel for this job
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"shredding:{job_id}")

    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await websocket.send_json(data)

                if data.get('step') == 'complete':
                    break
    finally:
        await websocket.close()
```

---

## Implementation Timeline - Feature Complete

### Week 1: Foundation & Database

**Days 1-2: Database & Migration**
- [ ] Create schema migration script
- [ ] Add `requirements` table
- [ ] Add `rfp_metadata` table
- [ ] Test migration on dev database
- [ ] Create rollback capability

**Days 3-5: Core Document Processing**
- [ ] Extend DocumentProcessor for RFP parsing
- [ ] Implement section detection (regex patterns)
- [ ] Test with JADC2 RFP
- [ ] Handle multi-column PDF layouts
- [ ] Extract page numbers and paragraph IDs

### Week 2: Requirement Extraction & Classification

**Days 1-3: Requirement Extraction**
- [ ] Implement compliance keyword detection
- [ ] Handle conditional requirements ("if...then")
- [ ] Extract source metadata (page, para)
- [ ] Sentence segmentation
- [ ] Test with Section C, L, M separately

**Days 4-5: Ollama Classification**
- [ ] Create prompt templates
- [ ] Implement batch classification
- [ ] Test classification accuracy
- [ ] Iterate on prompts
- [ ] Add caching for performance

### Week 3: Backend API & Integration

**Days 1-2: API Endpoints**
- [ ] POST /upload-rfp
- [ ] GET /requirements
- [ ] PUT /requirements/{id}
- [ ] GET /export-csv
- [ ] WebSocket for progress

**Days 3-4: Opportunities Integration**
- [ ] Extend opportunities_api
- [ ] Create opportunity from RFP
- [ ] Generate tasks from requirements
- [ ] Link requirements to tasks
- [ ] Test task assignment logic

**Day 5: Search Integration**
- [ ] Add REQUIREMENT object type
- [ ] Index requirements
- [ ] Test search functionality

### Week 4: Web UI Components

**Days 1-2: RFP Upload Modal**
- [ ] Design modal UI
- [ ] File upload with drag-drop
- [ ] Metadata form
- [ ] Progress indicator
- [ ] WebSocket integration

**Days 3-5: Compliance Matrix UI**
- [ ] Matrix table component
- [ ] Sortable columns
- [ ] Inline editing (status, assignee)
- [ ] Filters (section, status, etc.)
- [ ] Stats dashboard
- [ ] CSV export button

### Week 5: Detail Panel & Enhancements

**Days 1-2: Requirement Detail Panel**
- [ ] Slide-out panel design
- [ ] Full requirement view
- [ ] Edit all fields
- [ ] Dependency management
- [ ] Notes editor

**Days 3-4: Agent Assignment**
- [ ] Auto-assignment logic
- [ ] Agent selection dropdown
- [ ] Task creation for agents
- [ ] Status sync with tasks

**Day 5: Polish & UX**
- [ ] Loading states
- [ ] Error handling
- [ ] Toast notifications
- [ ] Responsive design
- [ ] Accessibility (ARIA labels)

### Week 6: Testing & Documentation

**Days 1-2: JADC2 RFP Testing**
- [ ] Download JADC2 RFP
- [ ] Upload through UI
- [ ] Verify section extraction
- [ ] Check requirement accuracy
- [ ] Test compliance matrix
- [ ] Export CSV and validate

**Days 3-4: Skill Documentation**
- [ ] Write SKILL.md
- [ ] Create reference docs
- [ ] Add example outputs
- [ ] Write API documentation
- [ ] Create user guide

**Day 5: Deployment Prep**
- [ ] Final code review
- [ ] Performance testing
- [ ] Security audit
- [ ] Deployment checklist
- [ ] User training materials

---

## Testing Plan

### Unit Tests

**Document Processing** (`tests/test_shredding_document.py`)
```python
def test_section_detection():
    """Test detection of Sections A-M in RFP PDF."""
    doc = process_rfp("sample_rfp.pdf")
    assert 'C' in doc.sections
    assert 'L' in doc.sections
    assert 'M' in doc.sections

def test_page_number_extraction():
    """Test page number preservation."""
    doc = process_rfp("sample_rfp.pdf")
    req = doc.sections['C'].requirements[0]
    assert req.page_number > 0

def test_paragraph_id_extraction():
    """Test paragraph ID extraction (e.g., 3.2.1)."""
    doc = process_rfp("sample_rfp.pdf")
    req = doc.sections['C'].requirements[0]
    assert req.paragraph_id is not None
```

**Requirement Extraction** (`tests/test_requirement_extraction.py`)
```python
def test_mandatory_keyword_detection():
    """Test detection of mandatory requirements."""
    text = "The contractor shall provide secure authentication."
    req = extract_requirement(text)
    assert req.compliance_type == "mandatory"

def test_conditional_requirement():
    """Test conditional requirement parsing."""
    text = "If the system fails, the contractor must provide backup."
    req = extract_requirement(text)
    assert req.compliance_type == "mandatory"
    assert "conditional" in req.keywords

def test_optional_keyword():
    """Test optional requirement detection."""
    text = "The contractor may provide additional features."
    req = extract_requirement(text)
    assert req.compliance_type == "optional"
```

**Ollama Classification** (`tests/test_classification.py`)
```python
def test_technical_classification():
    """Test classification of technical requirements."""
    text = "The system shall use AES-256 encryption."
    classification = classify_requirement(text)
    assert classification['category'] == 'technical'
    assert classification['priority'] == 'high'

def test_management_classification():
    """Test classification of management requirements."""
    text = "The contractor shall submit monthly progress reports."
    classification = classify_requirement(text)
    assert classification['category'] == 'management'
```

### Integration Tests

**End-to-End RFP Shredding** (`tests/test_e2e_shredding.py`)
```python
async def test_full_rfp_shredding():
    """Test complete RFP shredding workflow."""
    # Upload RFP
    response = await client.post('/api/shredding/upload-rfp', data={
        'file': open('test_rfp.pdf', 'rb'),
        'rfp_number': 'TEST-001',
        'opportunity_name': 'Test RFP',
        'due_date': '2025-12-31'
    })

    assert response.status_code == 200
    job_id = response.json()['job_id']

    # Wait for completion
    await wait_for_job_completion(job_id, timeout=300)

    # Verify opportunity created
    opp_id = get_opportunity_id_from_job(job_id)
    assert opp_id is not None

    # Verify requirements extracted
    reqs = await client.get(f'/api/shredding/requirements/{opp_id}')
    assert reqs.json()['total'] > 0

    # Verify CSV export
    csv = await client.get(f'/api/shredding/export-csv/{opp_id}')
    assert csv.status_code == 200
    assert 'text/csv' in csv.headers['content-type']
```

### JADC2 Acceptance Test

**Manual Test Checklist**:
1. [ ] Download JADC2 RFP from SAM.gov
2. [ ] Upload through web UI
3. [ ] Wait for processing (note time: _____ minutes)
4. [ ] Verify sections detected (A, B, C, L, M)
5. [ ] Check total requirements extracted: _____
6. [ ] Verify at least 70% classified as mandatory/optional correctly
7. [ ] Test inline editing (change status, assignee)
8. [ ] Test filters (section, status, compliance type)
9. [ ] Test search functionality
10. [ ] Export CSV and open in Excel
11. [ ] Verify all columns populated
12. [ ] Create a task from requirement
13. [ ] Assign to agent and verify in agent system
14. [ ] Check compliance percentage calculation

**Success Criteria**:
- Processing time: <30 minutes for 100-page RFP
- Section detection: >90% accuracy
- Requirement extraction: >80% accuracy
- Classification accuracy: >75% (manual review of 50 random requirements)
- UI responsiveness: All actions <2 seconds
- CSV export: All data present and formatted correctly

---

## Future Extensions (Post-MVP)

### Phase 7: Proposal Filling

**Capability**: Auto-populate proposal templates with responses

**Technical Approach**:
```python
# New endpoints
POST /api/shredding/generate-proposal
  - Input: opportunity_id, template_file (PowerPoint/Word)
  - Output: Filled proposal draft

# Workflow:
1. Load proposal template
2. For each requirement in compliance matrix:
   - Find matching slide/section
   - Retrieve response from historical proposals (RAG)
   - Use Ollama to adapt response to current RFP
   - Insert into template
3. Generate filled proposal
4. Return for human review
```

**UI Components**:
- Template manager (upload .pptx, .docx, .pdf templates)
- Response library (historical winning proposals)
- Proposal preview with diff highlighting
- Approval workflow

**Data Models**:
```sql
CREATE TABLE proposal_templates (
    id TEXT PRIMARY KEY,
    name TEXT,
    file_path TEXT,
    template_type TEXT,  -- 'powerpoint', 'word', 'pdf'
    sections TEXT        -- JSON mapping of sections
);

CREATE TABLE proposal_responses (
    id TEXT PRIMARY KEY,
    requirement_type TEXT,
    response_text TEXT,
    source_proposal_id TEXT,
    win_status TEXT,     -- 'won', 'lost'
    effectiveness_score REAL
);
```

### Phase 8: Win Theme Extraction

**Capability**: Identify customer priorities from Section M

**Technical Approach**:
- Parse Section M evaluation criteria
- Extract scoring weights
- Identify discriminators
- Generate win theme suggestions

### Phase 9: SAM.gov API Integration

**Capability**: Auto-download matching RFPs

**Technical Approach**:
```python
# SAM.gov API integration
import requests

def fetch_opportunities(naics_codes, keywords):
    """Fetch opportunities from SAM.gov API."""
    api_key = os.getenv('SAM_GOV_API_KEY')

    response = requests.get(
        'https://api.sam.gov/opportunities/v2/search',
        params={
            'api_key': api_key,
            'naics': ','.join(naics_codes),
            'keywords': keywords,
            'active': 'true'
        }
    )

    return response.json()

# Scheduled task to check for new RFPs
@scheduler.scheduled_job('interval', hours=6)
async def check_new_rfps():
    """Check SAM.gov for new matching RFPs every 6 hours."""
    opportunities = fetch_opportunities(
        naics_codes=['541512', '541519'],  # IT services
        keywords='software development'
    )

    for opp in opportunities:
        if is_new_opportunity(opp['id']):
            # Auto-download and shred
            await auto_shred_rfp(opp)
```

---

## Success Metrics - Revised

### MVP Success Criteria

**Must Have** (Go/No-Go):
- [ ] Extract requirements from JADC2 RFP with >75% accuracy
- [ ] Web UI compliance matrix functional (view, edit, filter, sort)
- [ ] CSV export with all 13 columns
- [ ] Create opportunity and tasks from RFP
- [ ] Process JADC2 in <30 minutes

**Should Have** (Quality):
- [ ] Requirement extraction accuracy: >85%
- [ ] Classification accuracy: >80%
- [ ] User completes workflow in <10 clicks
- [ ] UI responsive (<2s for all actions)

**Nice to Have** (Enhancements):
- Agent assignment working
- Search integration complete
- Gantt chart visualization

### Long-Term Metrics (6 months)

**Usage**:
- RFPs processed: >50
- Requirements extracted: >5,000
- Compliance matrices generated: >50

**Quality**:
- Proposal win rate: +15% (vs historical)
- Time to proposal submission: -40%
- Team satisfaction: >4.2/5.0

**Business Impact**:
- ROI: 10x cost savings on RFP analysis
- New business pipeline: +$5M in qualified opportunities

---

## Deployment Checklist

### Pre-Deployment

- [ ] All unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] JADC2 acceptance test passed
- [ ] Database migration tested
- [ ] Rollback plan documented
- [ ] User documentation complete
- [ ] API documentation published

### Deployment

- [ ] Backup production database
- [ ] Run database migration
- [ ] Deploy backend code
- [ ] Deploy frontend code
- [ ] Verify health endpoints
- [ ] Test file upload
- [ ] Test compliance matrix load
- [ ] Test CSV export

### Post-Deployment

- [ ] Monitor error logs
- [ ] Check WebSocket connections
- [ ] Verify Ollama classification working
- [ ] Test with small RFP (<20 pages)
- [ ] User acceptance testing
- [ ] Gather feedback
- [ ] Create known issues list

---

## Conclusion

This implementation plan provides a **feature-complete MVP** for the RFP shredding skill, prioritizing:

1. ✅ **Web UI First** - Compliance matrix as primary interface
2. ✅ **CSV Export** - For external tool compatibility
3. ✅ **Full Integration** - With opportunities, tasks, agents, search
4. ✅ **Production Quality** - Comprehensive testing, error handling
5. ✅ **JADC2 Test Case** - Real-world validation

**Timeline**: 6 weeks for complete MVP
**Estimated LOC**: ~5,000 lines (backend + frontend + tests)
**Dependencies**: spacy, openpyxl (manageable additions)
**Risk**: Medium (managed with incremental testing)

**Next Steps**:
1. Create database migration
2. Implement Week 1 tasks (foundation)
3. Test with JADC2 RFP
4. Iterate based on results

**Ready to proceed with implementation!** 🚀
