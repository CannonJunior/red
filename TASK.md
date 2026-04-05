# TASK.md — Robobrain RED Task Tracker
**Last Updated**: 2026-04-01

---

## ✅ Completed Tasks

| Task | Date | Notes |
|------|------|-------|
| Shredding skill — RFP requirement extraction | 2025-12-26 | See outputs/shredding/ |
| Career Monster — academic position analysis | 2025-12-27 | See career_monster/ |
| Agent system — MCP server + Ollama runtime | 2026-01-07 | See agent_system/ |
| PLANNING.md — Proposal Workflow Architecture | 2026-03-28 | See PLANNING.md |
| Shipley Capture Intelligence — full feature set | 2026-04-01 | capture_api.py, server/routes/capture.py, js/capture.js, js/capture-intel.js; Win Strategy/PTW/Contacts/Competitors/Activities tabs |
| Auto-task creation + Pipeline Tasks settings + All-Tasks list | 2026-04-04 | config/tracking_task_templates.json; server/routes/settings_api.py; /api/settings/tracking-tasks GET/PUT; /api/all-tasks GET; js/tasks-list.js; js/pipeline-tasks-settings.js; Tasks sidebar item in Lists |

---

## 🚧 Phase 0: Foundation — IN PROGRESS

### P0-1: Core Proposal Library
- [x] Create `proposal/` Python package with Pydantic models
- [x] Create `proposal/database.py` with SQLite schema migration
- [x] Create `proposal/pipeline.py` with state machine
- [x] Create `tests/proposal/` test suite skeleton

### P0-2: Configuration & Environment
- [x] Create `.env.example` with all integration API variables
- [x] Create `config/model_config.py` (Sonnet 4.6, Haiku 4.5)
- [x] Update any existing `claude-sonnet-4-5` references to `claude-sonnet-4-6`
- [x] Add `msal` and `jinja2` to pyproject.toml dependencies

### P0-3: Document Templates
- [x] Create `templates/proposal/` directory structure
- [x] Create Technical Volume base template (.docx)
- [x] Create Management Volume base template (.docx)
- [x] Create Past Performance template (.docx)
- [x] Create Cost Volume template (.xlsx)
- [x] Create Bid/No-Bid slide template (.pptx)
- [x] Create Hotwash Report template (.docx)
- [x] Create Confluence page templates (Jinja2 HTML)

---

## 📋 Phase 1: Core Tracking Skills

### P1-1: opportunity-curator skill
- [x] `proposal/opportunity_scorer.py` — NAICS + keyword scoring
- [x] `proposal/sam_gov_parser.py` — SAM.gov feed ingestion
- [x] `.claude/skills/opportunity-curator/` — Skill definition
- [x] Tests: `tests/proposal/test_opportunity_scorer.py` — 41 tests passing

### P1-2: bid-no-bid skill
- [x] `proposal/bid_no_bid.py` — Shipley scoring matrix (20 tests passing)
- [x] `proposal/bid_no_bid_slide.py` — PPTX generation (6-slide deck)
- [x] `.claude/skills/bid-no-bid/` — Skill definition
- [x] Tests: `tests/proposal/test_bid_no_bid.py`

### P1-3: proposal-setup skill
- [x] `proposal/folder_manager.py` — Local folder creation (20 tests passing)
- [x] `proposal/schedule_generator.py` — Proposal timeline + XLSX export
- [x] `.claude/skills/proposal-setup/` — Skill definition
- [x] Tests: `tests/proposal/test_folder_manager.py`

---

## 📝 Phase 2: Document Generation Skills

### P2-1: document-drafter skill
- [x] `proposal/document_generator.py` — Template → DOCX engine
- [x] Jinja2 + python-docx hybrid approach
- [x] Requirement-to-section mapping (from shredding output)
- [x] Ollama-powered prose generation
- [x] `.claude/skills/document-drafter/` — Skill definition (SKILL.md updated)
- [x] Tests: `tests/proposal/test_document_generator.py` — 24 tests passing

### P2-2: cost-estimator skill
- [x] `proposal/cost_estimator.py` — Labor/wrap rate calculator + XLSX Section B builder
- [x] Rate file import/export (JSON)
- [x] `.claude/skills/cost-estimator/` — Skill definition (pre-existing)
- [x] Tests: `tests/proposal/test_cost_estimator.py` — 31 tests passing

---

## 🔗 Phase 3: CRM & Collaboration Integrations

### P3-1: Unanet CRM integration
- [x] `proposal/integrations/unanet.py` — REST API client
- [x] `proposal/integrations/unanet_mapping.json` — Field mapping config (all 12 stage codes)
- [x] Bidirectional sync (push local → Unanet, pull Unanet → local) — `proposal/integrations/unanet_sync.py`; UnanetSyncManager with push_all/pull_all/sync; 3 conflict strategies; 32 tests (2026-04-04)
- [x] `.claude/skills/crm-sync/` — Skill definition (covers Unanet + SharePoint)
- [x] Tests: `tests/proposal/integrations/test_unanet_client.py` — 36 tests passing (2026-03-31)

### P3-2: SharePoint integration
- [x] `proposal/integrations/sharepoint.py` — Microsoft Graph API client
- [x] MSAL device code OAuth2 flow with token caching
- [x] Folder structure creation per proposal
- [x] Document upload and metadata tagging
- [x] External sharing link generation
- [x] Tests: `tests/proposal/integrations/test_sharepoint_client.py` — 30 tests passing (2026-03-31)

### P3-3: Confluence integration
- [x] `proposal/integrations/confluence.py` — Atlassian REST API client
- [x] Space creation per proposal
- [x] Page creation from Jinja2 templates
- [x] Meeting notes page workflow
- [x] Attachment upload support
- [x] Tests: `tests/proposal/integrations/test_confluence.py` — 26 tests passing

---

## 📅 Phase 4: Meeting & Retrospective Skills

### P4-1: meeting-coordinator skill
- [x] `proposal/meeting_coordinator.py` — Agenda generation, notes, action item tracking
- [x] Agenda templates for all 9 meeting types (kickoff, color teams, weekly, orals, etc.)
- [x] Action item tracking with overdue/upcoming alerts
- [x] DOCX meeting summary export + Ollama note summarization
- [x] `.claude/skills/meeting-coordinator/` — Skill definition (pre-existing)
- [x] Tests: `tests/proposal/test_meeting_coordinator.py` — 39 tests passing

### P4-2: hotwash skill
- [x] `proposal/hotwash.py` — Retrospective data capture + lessons-learned engine
- [x] Debrief notes capture with strengths/weaknesses/deficiencies
- [x] Hotwash report generation (DOCX) with outcome color-coding
- [x] Ollama-assisted cross-cutting process improvement insights
- [x] `.claude/skills/hotwash/` — Skill definition (pre-existing)
- [x] Tests: `tests/proposal/test_hotwash.py` — 28 tests passing

---

## 🔄 Phase 5: Continuous Improvement Loop

### P5-1: Pipeline Health Dashboard
- [x] Proposal pipeline summary view (win rate, stage distribution, total/active/won value, priority breakdown) — `GET /api/pipeline/stats` (2026-03-31)
- [x] Integration with existing web UI at localhost:9090 — `pipeline-health-area` panel + nav item + `js/pipeline-health.js` (2026-03-31)
- [x] Tests: `tests/proposal/test_pipeline_stats.py` — 21 tests passing (2026-03-31)
- [x] Lessons learned search (RAG over hotwash reports) — `proposal/lessons_search.py`; SQLite FTS5 keyword search + Ollama semantic fallback; filters by category/impact/outcome; 28 tests (2026-04-04)

### P5-2: Skill Self-Improvement
- [x] Per-proposal skill effectiveness rating — `proposal/skill_effectiveness.py` SkillTracker.rate(); 1-5 score per skill per proposal outcome
- [x] Lessons learned → skill prompt injection — SkillTracker.inject_lessons() / format_lessons_as_context(); category-aware FTS retrieval
- [x] Win/loss pattern analysis — SkillTracker.win_loss_analysis(); pWin calibration + value patterns; 33 tests (2026-04-04)

### P5-3: Technical Debt (from TECH_DEBT.md)
- [x] Refactor monolithic server.py — `server/router.py` + `_build_router()` registry; do_GET/POST/DELETE/PUT replaced with 9-line dispatcher; 186 lines removed (2026-03-31)
- [x] Add database indexes to search_system.db — pipeline_stage, priority, tasks.status, tasks.assigned_to, task_history.opportunity_id (2026-03-31)
- [x] Add request validation middleware (Pydantic) — `server/request_models.py`; create/update opportunity routes validated (2026-03-31)
- [x] Connection pooling for SQLite — `server/db_pool.py` thread-local pool + WAL mode; all OpportunitiesManager query methods migrated (2026-03-31)

---

## 🐛 Discovered During Work

- [x] Skills Interface → management page with skill on/off toggles (2026-03-29)
- [x] Create New Ollama Agent → full-screen view instead of modal (2026-03-29)
- [x] Skills Interface submenu dynamically reflects enabled skills from management page (2026-03-29)

### 🟡 Medium Priority — Failing Tests (pre-existing, discovered 2026-03-30)

- [x] **FIX: `tests/shredding/test_requirement_classifier.py`** — 21 tests passing (2026-03-30)
  - Root cause: tests used dict access (`result['category']`) but `classify()` returns `RequirementClassification` dataclass; batch test passed `List[str]` not `List[Dict]`; rewrote with mocked Ollama for determinism
- [x] **FIX: `tests/shredding/test_requirement_extractor.py`** — 17 tests passing (2026-03-30)
  - Root cause: tests passed `page=N` kwarg (actual: `start_page=N`); used dict access on `Requirement` dataclass; deduplication test needed explicit `deduplicate_requirements()` call

---

## 📌 Backlog / Future Considerations

- SAM.gov automated feed polling (daily cron via `schedule` skill)
- eBuy integration for task order opportunities
- PTAC/APEX accelerator feed integration
- Price-to-win (PTW) analysis tool
- Competitive intelligence tracking
- Teaming partner CRM (track partner capabilities)
- Proposal library / boilerplate RAG (search past proposals)
- Color team markup ingestion (Track Changes from Word)
- Government source selection criteria analysis
- Section M (evaluation criteria) weight extraction from shredding

---

*Tasks are marked complete in the Completed section. Add new discoveries to "Discovered During Work".*
