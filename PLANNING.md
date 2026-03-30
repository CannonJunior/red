# PLANNING.md — Robobrain RED: Proposal Workflow System
**Last Updated**: 2026-03-28
**Status**: Architecture Design — Ready for Implementation

---

## 1. Project Overview

Robobrain RED is a zero-cost, locally-running AI agent system for a small GovCon team (≤5 users). This planning document covers the **Proposal Workflow System** — a suite of Claude Code skills and Python libraries that guide a proposal through every stage from opportunity identification to post-award hotwash.

**Core principle**: Every workflow step is a discrete, composable skill. Skills are thin wrappers around a testable `proposal/` core library. State is stored in SQLite (`opportunities.db`), with optional sync to Unanet CRM, SharePoint, and Confluence.

---

## 2. Architecture Overview

```
proposal/                        ← Core library (business logic)
├── __init__.py
├── models.py                    ← GovCon data models (Pydantic)
├── database.py                  ← SQLite schema + queries
├── pipeline.py                  ← Stage-machine state transitions
├── bid_no_bid.py                ← Shipley-based B/NB scoring
├── folder_manager.py            ← Proposal folder structure
├── document_generator.py        ← Template-to-document engine
├── cost_estimator.py            ← Cost/price volume tools
├── meeting_manager.py           ← Meeting agenda + notes
├── hotwash.py                   ← Retrospective + lessons learned
└── integrations/
    ├── __init__.py
    ├── unanet.py                ← Unanet CRM REST API client
    ├── sharepoint.py            ← Microsoft Graph API client
    └── confluence.py            ← Atlassian Confluence REST client

.claude/skills/                  ← Skill wrappers (thin, invoke core)
├── opportunity-curator/
├── bid-no-bid/
├── crm-sync/
├── proposal-setup/
├── document-drafter/
├── cost-estimator/
├── meeting-coordinator/
└── hotwash/

outputs/proposal/                ← All generated artifacts
├── {solicitation-number}/
│   ├── bid-no-bid/
│   ├── documents/
│   ├── cost/
│   └── meetings/

docs/proposal/                   ← Architecture and workflow docs
templates/proposal/              ← Document templates
├── technical_volume.docx
├── management_volume.docx
├── past_performance.docx
├── executive_summary.docx
├── cost_volume.xlsx
├── bid_no_bid_slide.pptx
└── hotwash_template.docx
```

---

## 3. Data Model: GovCon Proposal

The existing `opportunities_api.py` tracks basic opportunities. The proposal system extends this with a `proposals` table and rich GovCon metadata.

### proposals table (extends opportunities)
```sql
CREATE TABLE proposals (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT,             -- FK to opportunities.id
    solicitation_number TEXT UNIQUE, -- e.g., FA8612-26-R-0001
    title TEXT NOT NULL,
    agency TEXT,                     -- e.g., AFRL/RQ
    contracting_office TEXT,
    naics_code TEXT,                 -- e.g., 541715
    set_aside_type TEXT,             -- SDVOSB, 8(a), Full and Open, SB, etc.
    contract_type TEXT,              -- FFP, T&M, CPFF, IDIQ, BPA
    estimated_value REAL,
    rfp_release_date TEXT,
    proposal_due_date TEXT,          -- ISO datetime — critical deadline
    questions_due_date TEXT,
    period_of_performance TEXT,      -- e.g., 24 months base + 2 OY
    source TEXT,                     -- SAM.gov, eBuy, PTAC, industry day, direct
    pipeline_stage TEXT DEFAULT 'identified',
    bid_decision TEXT DEFAULT 'pending', -- bid, no-bid, pending
    bid_decision_date TEXT,
    bid_decision_rationale TEXT,
    pwin_score REAL,                 -- Probability of win (0.0-1.0)
    capture_manager TEXT,
    proposal_manager TEXT,
    volume_leads TEXT,               -- JSON array
    teaming_partners TEXT,           -- JSON array
    key_personnel TEXT,              -- JSON array
    relevant_past_performance TEXT,  -- JSON array of PP IDs
    incumbent TEXT,
    recompete INTEGER DEFAULT 0,     -- boolean
    shred_analysis_id TEXT,          -- FK to shredding output
    crm_opportunity_id TEXT,         -- Unanet CRM ID
    sharepoint_folder_url TEXT,
    sharepoint_site_id TEXT,
    confluence_space_key TEXT,
    submission_method TEXT,          -- PIEE, email, hand delivery, etc.
    color_teams TEXT,                -- JSON: {pink: date, red: date, gold: date}
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### Pipeline Stages (ordered)
```
identified  →  qualifying  →  bid_decision  →  active  →  submitted  →  awarded/lost/no_bid
```

### proposal_meetings table
```sql
CREATE TABLE proposal_meetings (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    meeting_type TEXT,    -- kickoff, pink_team, red_team, gold_team, orals_prep,
                          -- weekly_sync, management_review, hotwash
    title TEXT,
    scheduled_date TEXT,
    actual_date TEXT,
    attendees TEXT,       -- JSON array
    agenda TEXT,
    notes TEXT,           -- meeting notes / action items
    action_items TEXT,    -- JSON array of {owner, item, due_date, status}
    confluence_page_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
);
```

### hotwash_events table
```sql
CREATE TABLE hotwash_events (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    outcome TEXT,             -- won, lost, no_bid, cancelled
    facilitator TEXT,
    event_date TEXT,
    attendees TEXT,           -- JSON array
    what_went_well TEXT,      -- JSON array
    what_to_improve TEXT,     -- JSON array
    lessons_learned TEXT,     -- JSON array
    action_items TEXT,        -- JSON array
    process_score INTEGER,    -- 1-10 self-assessment
    confluence_page_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
);
```

---

## 4. Pipeline State Machine

```
identified
    └─► qualifying        (capture manager assigned, RFP reviewed)
         └─► bid_decision  (B/NB slide created, decision recorded)
              ├─► no_bid   (terminal — logged for lessons learned)
              └─► active   (proposal kickoff held, team assigned)
                   └─► submitted  (final package delivered)
                        ├─► awarded  (contract won — trigger hotwash)
                        └─► lost     (contract lost — trigger hotwash)
```

Each transition is guarded by a checklist:
- `identified → qualifying`: solicitation_number, agency, due_date
- `qualifying → bid_decision`: shred analysis complete, capture manager set
- `bid_decision → active`: bid_decision = "bid", team assigned
- `active → submitted`: all volumes complete, folder finalized
- `submitted → awarded/lost`: award notification received

---

## 5. Skill Designs

### Skill 1: opportunity-curator
**Purpose**: Curate and score opportunities from multiple sources against company capabilities
**Inputs**: Source (SAM.gov feed, manual entry, RFP file), capability profile
**Outputs**: Scored opportunity list, recommended action (pursue/pass/monitor)
**Integrations**: Connects to existing `shredding` skill for RFP analysis
**Key Logic**:
- NAICS alignment scoring
- Keyword matching against capability statement
- Past performance relevance scoring
- Incumbent advantage assessment
- Competitive landscape (# of bidders, set-aside history)

### Skill 2: bid-no-bid
**Purpose**: Generate Shipley-based Bid/No-Bid assessment and decision slide
**Inputs**: Proposal ID (or inline opportunity data)
**Outputs**: Scored B/NB worksheet (xlsx), B/NB decision slide (pptx), recorded decision
**Key Scoring Factors** (Shipley Go/No-Go):
- Customer knowledge (1-10)
- Competitive position (1-10)
- Incumbent status (1-10)
- Technical capability match (1-10)
- Past performance relevance (1-10)
- Team/resource availability (1-10)
- Price to win estimate feasibility (1-10)
- Risk assessment (1-10)
**Decision Thresholds**: Score ≥70 → Bid; 50-70 → Conditional; <50 → No-Bid

### Skill 3: crm-sync
**Purpose**: Bidirectional sync between local proposals DB and Unanet CRM / SharePoint
**Inputs**: Proposal ID, target system (unanet|sharepoint|both)
**Outputs**: CRM record IDs, SharePoint URLs, sync status report
**Unanet Mapping**:
- Opportunity name → Unanet pipeline opportunity name
- Pipeline stage → Unanet stage
- Estimated value → Unanet value
- Due date → Unanet close date
- Capture manager → Unanet owner
**SharePoint Mapping**:
- Creates site/folder: `Proposals/{Year}/{Solicitation-Number}_{Title}/`
- Sub-folders: `00_RFP`, `01_Analysis`, `02_BidNoBid`, `03_Working`, `04_Reviews`, `05_Final`

### Skill 4: proposal-setup
**Purpose**: Scaffold complete proposal infrastructure (folders, schedule, team)
**Inputs**: Proposal ID
**Outputs**: Local folder structure, SharePoint library, Confluence space, proposal schedule
**Creates**:
- `outputs/proposal/{solicitation}/` with standard sub-directories
- SharePoint document library with metadata columns
- Confluence space with proposal brief and schedule pages
- Kickoff meeting agenda

### Skill 5: document-drafter
**Purpose**: Generate draft proposal volumes from RFP requirements and templates
**Inputs**: Proposal ID, volume type (technical|management|past_performance|executive_summary)
**Outputs**: Draft .docx files in proposal working folder
**Uses**: Shredding output for requirement-to-section mapping, local Ollama for drafting
**Template Locations**: `templates/proposal/`

### Skill 6: cost-estimator
**Purpose**: Build cost/price volume from labor categories and rates
**Inputs**: Proposal ID, period of performance, labor mix, subcontractor data
**Outputs**: Cost volume .xlsx with Section B price schedule, narrative
**Features**:
- Labor category → rate mapping (from config)
- Wrap rate calculations (fringe, overhead, G&A, fee)
- Subcontractor cost consolidation
- Historical rate file import/export
- Unanet rate import support

### Skill 7: meeting-coordinator
**Purpose**: Schedule proposal meetings, generate agendas, capture and distribute notes
**Inputs**: Meeting type, proposal ID, date, attendees
**Outputs**: Meeting agenda (.docx), notes page in Confluence, action item tracking
**Meeting Types**: kickoff, pink_team, red_team, gold_team, orals_prep, weekly_sync, hotwash

### Skill 8: hotwash
**Purpose**: Conduct structured post-proposal retrospective and capture lessons learned
**Inputs**: Proposal ID, outcome (won|lost|no_bid)
**Outputs**: Hotwash report (.docx), lessons learned in Confluence, process improvement items
**Captures**: What worked, what to improve, timeline compliance, team performance, process gaps

---

## 6. External Integration Architecture

### 6.1 Unanet CRM
**Auth**: API key in `UNANET_API_KEY` env var
**Base URL**: `UNANET_BASE_URL` env var (e.g., `https://yourcompany.unanet.biz/`)
**Key Endpoints**:
```
POST   {base}/rest/opportunity          Create opportunity
PUT    {base}/rest/opportunity/{id}     Update opportunity
GET    {base}/rest/opportunity          List/search
POST   {base}/rest/opportunity/{id}/activity  Log activity
GET    {base}/rest/person               Get staff list for assignment
```
**Field Mapping Table** (configured in `proposal/integrations/unanet_mapping.json`):
```json
{
  "solicitation_number": "external_id",
  "title": "name",
  "pipeline_stage": "stage_code",
  "estimated_value": "potential_revenue",
  "proposal_due_date": "close_date",
  "capture_manager": "owner_username",
  "agency": "client_name"
}
```

### 6.2 SharePoint (Microsoft Graph API)
**Auth**: OAuth2 Device Code Flow — stored in `~/.red/sharepoint_token.json`
**Scope**: `Sites.ReadWrite.All Files.ReadWrite.All`
**Key Operations**:
```python
# Create proposal folder
POST /sites/{site-id}/drives/{drive-id}/root/children
# Upload document
PUT /sites/{site-id}/drives/{drive-id}/items/{parent-id}:/{filename}:/content
# Set metadata
PATCH /sites/{site-id}/drives/{drive-id}/items/{item-id}/listItem/fields
# Create sharing link (for external reviewers)
POST /sites/{site-id}/drives/{drive-id}/items/{item-id}/createLink
```
**Folder Naming**: `{YYYY-YYYY}_{Agency}_{Solicitation-Number}_{ShortTitle}`
**SharePoint List Columns**: SolicitationNumber, Agency, DueDate, PipelineStage, BidDecision, PWin, CaptureManager

**Proposal Folder Structure**:
```
Proposals/
└── FY26/
    └── AFRL_FA8612-26-R-0001_SomeEffort/
        ├── 00_RFP/             ← Original solicitation package
        ├── 01_Analysis/        ← Shredded requirements, gap analysis
        ├── 02_BidNoBid/        ← B/NB worksheet and decision slide
        ├── 03_Working/         ← Live drafts (internal access only)
        │   ├── Vol-1-Technical/
        │   ├── Vol-2-Management/
        │   ├── Vol-3-Cost/
        │   └── Vol-4-PastPerf/
        ├── 04_Reviews/         ← Color team markups
        │   ├── Pink-Team_{date}/
        │   ├── Red-Team_{date}/
        │   └── Gold-Team_{date}/
        └── 05_Final/           ← Submission-ready package
            ├── Internal/       ← Signed copies, internal distribution
            └── Submission/     ← Exact files sent to government
```

### 6.3 Confluence
**Auth**: API token in `CONFLUENCE_API_TOKEN`, user email in `CONFLUENCE_EMAIL`
**Base URL**: `CONFLUENCE_BASE_URL` env var
**Key Operations**:
```
POST /wiki/rest/api/content              Create page
PUT  /wiki/rest/api/content/{id}        Update page
POST /wiki/rest/api/content/{id}/child/attachment  Upload file
GET  /wiki/rest/api/content/search      Search pages
```
**Space Key Pattern**: `PROP{ShortCode}` (e.g., `PROPFA8612`)
**Page Templates**: Stored in `templates/proposal/confluence/`

**Space Structure**:
```
PROP-{Solicitation} Space
├── 📋 Opportunity Brief          ← Opportunity overview, B/NB rationale
├── 📊 Capture Plan               ← Win strategy, competitive analysis
├── 👥 Team & Org Chart           ← Team assignments, subcontractors
├── 📅 Proposal Schedule          ← Timeline, milestones, color reviews
├── 📝 Technical Notes/           ← Technical approach working notes
├── 🎨 Color Team Reviews/
│   ├── Pink Team — {date}
│   ├── Red Team — {date}
│   └── Gold Team — {date}
├── 📞 Meeting Notes/
│   ├── Kickoff Meeting — {date}
│   ├── Weekly Sync — {date}
│   └── Management Reviews/
└── 🔁 Hotwash & Lessons Learned  ← Post-submission retrospective
```

---

## 7. Sonnet 4.6 Optimizations

The project predates `claude-sonnet-4-6`. The following optimizations apply:

### Model Selection by Task
| Task | Model | Reason |
|------|-------|--------|
| Bid/No-Bid analysis | `claude-sonnet-4-6` (extended thinking) | Complex multi-factor strategic reasoning |
| Document drafting | `claude-sonnet-4-6` | High-quality prose generation |
| Requirement classification | `claude-haiku-4-5-20251001` | Fast, cheap classification at scale |
| Cost estimation reasoning | `claude-sonnet-4-6` (extended thinking) | Financial accuracy critical |
| Meeting notes synthesis | `claude-sonnet-4-6` | Structured output quality |
| Opportunity scoring | `claude-haiku-4-5-20251001` | High-volume batch scoring |

### Extended Thinking Usage
Use `thinking` parameter (budget_tokens: 8000-16000) for:
- Bid/No-Bid strategic assessment
- Technical approach gap analysis
- Win strategy development
- Cost volume assumptions

### API Configuration
```python
# config/model_config.py — loaded from .env, never hardcoded
MODELS = {
    "primary": os.getenv("CLAUDE_MODEL_PRIMARY", "claude-sonnet-4-6"),
    "fast": os.getenv("CLAUDE_MODEL_FAST", "claude-haiku-4-5-20251001"),
    "local": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),  # zero-cost fallback
}
```

---

## 8. Technology Stack (Proposal Module)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Data storage | SQLite (opportunities.db) | Zero-cost, local, existing |
| Document generation | python-docx, python-pptx | Free, local, full control |
| Spreadsheet generation | openpyxl | Free, existing dependency |
| PDF output | Docling (existing) | Already installed |
| Unanet sync | requests + API key | Simple REST, no SDK needed |
| SharePoint sync | msal + requests (Graph API) | Microsoft MSAL for OAuth2 |
| Confluence sync | requests + API token | Simple REST, no SDK needed |
| LLM drafting | Ollama (local) + Claude API (optional) | Cost-tiered approach |
| Template rendering | Jinja2 + python-docx | Local, zero-cost |

**New dependencies to add**:
- `msal` — Microsoft Authentication Library for SharePoint OAuth2
- `jinja2` — Template rendering for document generation

---

## 9. File Naming Conventions

All generated outputs follow: `{solicitation-number}_{artifact-type}_{YYYY-MM-DD}.{ext}`

Examples:
- `FA8612-26-R-0001_bid_no_bid_2026-03-28.pptx`
- `FA8612-26-R-0001_technical_volume_draft_2026-04-01.docx`
- `FA8612-26-R-0001_cost_volume_2026-04-05.xlsx`
- `FA8612-26-R-0001_kickoff_meeting_notes_2026-03-30.docx`
- `FA8612-26-R-0001_hotwash_report_2026-06-15.docx`

---

## 10. Implementation Phases

### Phase 0: Foundation (Current)
- [x] PLANNING.md (this document)
- [x] TASK.md
- [ ] `proposal/` core library + data models
- [ ] Database schema migration
- [ ] `.env.example` with all integration variables
- [ ] Update model refs to Sonnet 4.6

### Phase 1: Core Tracking Skills
- [ ] `opportunity-curator` skill + core logic
- [ ] `bid-no-bid` skill + core logic
- [ ] `proposal-setup` skill + folder manager

### Phase 2: Document Generation
- [ ] `document-drafter` skill + template engine
- [ ] `cost-estimator` skill + xlsx generator
- [ ] Proposal document templates

### Phase 3: CRM Integrations
- [ ] Unanet CRM client + `crm-sync` skill
- [ ] SharePoint Graph API client + folder creation
- [ ] Confluence client + space/page creation

### Phase 4: Meeting & Retrospective
- [ ] `meeting-coordinator` skill + notes manager
- [ ] `hotwash` skill + lessons learned DB
- [ ] Confluence page templates

### Phase 5: Improvement Loop
- [ ] Per-proposal skill performance scoring
- [ ] Lessons learned → skill prompt updates
- [ ] Win/loss pattern analysis
- [ ] Automated pipeline health dashboard

---

## 11. Security & Access Control

- All API credentials in `.env` (never committed)
- `.env.example` with placeholder values only
- SharePoint token cached in `~/.red/` (user home, not project dir)
- No credentials in logs, no credentials in SQLite
- Local network only — no external API exposure
- SharePoint external sharing: explicit per-document link only

---

## 12. Testing Strategy

Each skill and core module has pytest tests in `tests/proposal/`:
```
tests/proposal/
├── __init__.py
├── test_models.py          ← Data model validation
├── test_database.py        ← Schema and queries
├── test_pipeline.py        ← State machine transitions
├── test_bid_no_bid.py      ← Scoring logic
├── test_folder_manager.py  ← Folder structure creation
├── test_document_generator.py ← Template rendering
├── test_cost_estimator.py  ← Calculations
└── integrations/
    ├── test_unanet_client.py    ← Mocked HTTP tests
    ├── test_sharepoint_client.py
    └── test_confluence_client.py
```

---

*Architecture designed for a 5-person GovCon team. Skills improve with each proposal cycle.*
