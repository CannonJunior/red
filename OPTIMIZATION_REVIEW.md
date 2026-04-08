# Optimization Review
**Updated**: 2026-04-06 (session 2)

Items from the previous review (2026-04-05) that were completed are marked ✅.
Items still open are carried forward. New findings are marked 🆕.

---

## 🐛 Bugs (Fix Before Anything Else)

| # | Issue | File | Fix |
|---|-------|------|-----|
| B1 | ✅ ~~**`json.loads()` called on already-parsed dict**~~ | `server/routes/shredding.py` | Fixed: replaced with `data = handler.get_request_body()` |
| B2 | **SQL injection in dynamic UPDATE** | `opportunities_api.py:394` | Field names built via f-string; whitelist allowed fields before interpolation |
| B3 | **No request body size limit** | `request_helpers.py` | Reject bodies > configurable max (e.g. 50 MB) to prevent memory exhaustion |

---

## Security

| # | Issue | File | Fix |
|---|-------|------|-----|
| S1 | ✅ ~~**Path traversal in static serving**~~ | `request_handler.py` | Fixed with `os.path.realpath()` check |
| S2 | **No rate limiting on write endpoints** | All POST/PUT/DELETE routes | Token-bucket limiter per client IP; see `TECH_DEBT.md` item 8 |
| S3 | **Path segment IDs extracted without validation** | `routes/opportunities.py:178`, `routes/ollama_agents.py` | Validate non-empty, no slashes before using in queries |

---

## Performance

| # | Issue | File | Fix |
|---|-------|------|-----|
| P1 | ✅ ~~**No gzip on static assets**~~ | `request_handler.py` | Implemented with `compresslevel=6` |
| P2 | ✅ ~~**If-None-Match never checked**~~ | `request_handler.py` | 304 Not Modified now returned |
| P3 | ✅ ~~**No SQLite `busy_timeout`**~~ | `db_pool.py` | `PRAGMA busy_timeout=5000` added |
| P4 | **Unbounded in-memory static cache** | `static_cache.py` | Add max-size + LRU eviction; currently grows forever |
| P5 | ✅ ~~**No pagination on list endpoints**~~ | `opportunities_api.py` | `limit`/`offset` added to `list_opportunities()`; route reads from query params; response includes `total`/`has_more` |
| P6 | ✅ ~~**Missing DB index on `modified_date DESC`**~~ | `search_system.py` | Fixed: index now uses `modified_date DESC` |
| P7 | ✅ ~~**`search_system.py` uses bare `sqlite3.connect` (6+ calls)**~~ | `search_system.py` | Added `_connect()` method to `UniversalSearchSystem`; all 6 method calls now use the pool |
| P8 | 🆕 **`prompts_api.py` still uses bare `sqlite3.connect`** | `prompts_api.py:44,87` | Migrate to `get_db()` |
| P9 | ✅ ~~**`shredding.py` uses bare `sqlite3.connect` in two handlers**~~ | `shredding.py` | Migrated to `get_db(shredder.db_path)` |

---

## Reliability & Error Handling

| # | Issue | File | Fix |
|---|-------|------|-----|
| R1 | ✅ ~~**52 handlers with identical try/except boilerplate**~~ | All route files | `@error_handler` decorator applied across all route files |
| R2 | ✅ ~~**`proposals.py` missing `@error_handler`**~~ | `server/routes/proposals.py` | Applied to all 10 handlers; manual try/except blocks removed |
| R3 | ✅ ~~**`traceback.print_exc()` leftover in `rag.py`**~~ | `server/routes/rag.py` | Replaced with `error_log(...)` |
| R4 | ✅ ~~**`db_pool.close_all()` never called on shutdown**~~ | `server.py` | `atexit.register(close_all)` added at module level |
| R5 | ✅ ~~**`asyncio.new_event_loop()` blocks the HTTP thread**~~ | `server/routes/chat.py` | Replaced with `asyncio.run()` |
| R6 | ✅ ~~**Mix of `print()` and `debug_log()` in route files**~~ | `chat.py`, `rag.py` | All `print(f"❌ ...")` calls replaced with `error_log(...)` |

---

## Maintainability

| # | Issue | File | Fix |
|---|-------|------|-----|
| M1 | ✅ ~~**Unused `parse_qs` module-level import**~~ | `routes_builder.py` | Moved inside `_qp()` |
| M2 | **Dual query param parsing** | `routes_builder.py` (`_qp()`) vs `handler.get_query_params()` | All routes now use `handler.get_query_params()`; `_qp()` can be removed |
| M3 | 🆕 **Files exceeding the 500-line CLAUDE.md limit** | See table below | Split into sub-modules |
| M4 | 🆕 **`capture.js` and `capture-intel.js` bypass `api-client.js`** | `js/capture.js`, `js/capture-intel.js` | 12+ raw `fetch()` calls; migrate to `api.get/post/delete` |
| M5 | 🆕 **`chat-interface.js` bypasses `api-client.js`** | `js/chat-interface.js:55,272,281,362` | 4+ raw `fetch()` calls to migrate |
| M6 | ✅ ~~**`Pyright` can't resolve `server.utils.error_handler`**~~ | All route files | `pyrightconfig.json` added at project root with `venvPath` + `reportMissingImports: none` |

---

## Files Over 500-Line Limit

| File | Lines | Action |
|------|-------|--------|
| `js/chat-interface.js` | 1415 | Split: `chat-core.js`, `chat-agent.js`, `chat-rag.js` |
| `opportunities_api.py` | 995 | Split: `opportunities_db.py`, `opportunities_tasks_db.py` |
| `js/navigation.js` | 890 | Split: `nav-router.js`, `nav-sidebar.js` |
| `js/opportunities-manager.js` | 845 | Split: `opp-table.js`, `opp-detail.js` |
| `proposal/database.py` | 634 | Split: `proposal/db_schema.py`, `proposal/db_queries.py` |
| `prompts_api.py` | 643 | Split: `prompts_db.py`, `prompts_search.py` |
| `proposal/lessons_search.py` | 595 | Split at FTS vs Ollama boundary |
| `proposal/skill_effectiveness.py` | 583 | Split: `skill_tracker.py`, `win_loss_analysis.py` |
| `proposal/cost_estimator.py` | 577 | Split: `labor_rates.py`, `cost_estimator.py` |
| `proposal/bid_no_bid_slide.py` | 559 | Split at slide-builder boundary |
| `server/routes/chat.py` | 531 | Move `handle_mcp_tool_call` + helpers to `routes/mcp_tools.py` |

---

## Quick Wins (low effort / high impact)

All quick wins completed. Remaining open items:

1. **Fix SQL injection whitelist** (B2) — `opportunities_api.py:394`
2. **Add request body size limit** (B3) — `server/utils/request_helpers.py`
3. **Migrate `search_system.py` to `get_db()`** (P7) — 6 call sites
4. **Migrate `capture.js` / `capture-intel.js`** (M4) — raw fetch() calls
5. **Migrate `chat-interface.js`** (M5) — raw fetch() calls

---

## Items Completed Since Last Review (2026-04-05)

- ✅ Path traversal protection in static file serving
- ✅ If-None-Match → 304 Not Modified
- ✅ SQLite `busy_timeout=5000` in db_pool
- ✅ Gzip compression for text assets
- ✅ Moved `parse_qs` import inside `_qp()`
- ✅ `@error_handler` decorator applied to all route files (except `proposals.py`)

## Items Completed 2026-04-06 (session 2)

- ✅ B1: Fixed `json.loads()` on already-parsed dict in `shredding.py`
- ✅ P6: Fixed `modified_date DESC` index in `search_system.py`
- ✅ P9: Migrated `shredding.py` bare `sqlite3.connect` calls to `get_db()`
- ✅ P5: Added `limit`/`offset` pagination to `list_opportunities()`; default 100; response includes `total` + `has_more`
- ✅ P7: Migrated `search_system.py` to `_connect()` pool pattern (6 call sites)
- ✅ R2: Applied `@error_handler` to all 10 handlers in `proposals.py`
- ✅ R3: Replaced `traceback.print_exc()` in `rag.py` with `error_log()`
- ✅ R4: Registered `close_all()` with `atexit` in `server.py`
- ✅ R5: Replaced `asyncio.new_event_loop()` with `asyncio.run()` in `chat.py`
- ✅ R6: Replaced all `print(f"❌ ...")` calls in `chat.py` and `rag.py` with `error_log()`
- ✅ M6: Added `pyrightconfig.json` to eliminate false-positive Pyright import diagnostics
