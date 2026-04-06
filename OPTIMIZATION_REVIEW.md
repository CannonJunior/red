# Optimization Review
**Updated**: 2026-04-06

Items from the previous review (2026-04-05) that were completed are marked ✅.
Items still open are carried forward. New findings are marked 🆕.

---

## 🐛 Bugs (Fix Before Anything Else)

| # | Issue | File | Fix |
|---|-------|------|-----|
| B1 | 🆕 **`json.loads()` called on already-parsed dict** — `get_request_body()` returns `dict\|None`, not bytes; `json.loads(dict)` raises `TypeError` at runtime | `server/routes/shredding.py:67,353` | Replace `body = get_request_body(handler); data = json.loads(body)` with `data = handler.get_request_body()` |
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
| P5 | **No pagination on list endpoints** | `opportunities_api.py:268` | Add `limit`/`offset` query params; unbounded table scans at scale |
| P6 | **Missing DB index on `modified_date DESC`** | `search_system.py:200` | `CREATE INDEX IF NOT EXISTS idx_objects_modified ON searchable_objects(modified_date DESC)` |
| P7 | 🆕 **`search_system.py` uses bare `sqlite3.connect` (6+ calls)** | `search_system.py` | Replace with `get_db()` from `server/db_pool.py` for WAL + busy_timeout benefits |
| P8 | 🆕 **`prompts_api.py` still uses bare `sqlite3.connect`** | `prompts_api.py:44,87` | Migrate to `get_db()` |
| P9 | 🆕 **`shredding.py` uses bare `sqlite3.connect` in two handlers** | `shredding.py:235,387` | Migrate to `get_db(shredder.db_path)` |

---

## Reliability & Error Handling

| # | Issue | File | Fix |
|---|-------|------|-----|
| R1 | ✅ ~~**52 handlers with identical try/except boilerplate**~~ | All route files | `@error_handler` decorator applied across all route files |
| R2 | 🆕 **`proposals.py` missing `@error_handler`** — 10 handlers still use manual `try/except Exception as exc` | `server/routes/proposals.py` | Apply `@error_handler` to all 10 handlers; remove manual blocks |
| R3 | 🆕 **`traceback.print_exc()` leftover in `rag.py`** | `server/routes/rag.py:148-149` | Replace with `error_log(f"...: {ingest_error}", exception=ingest_error)` |
| R4 | **`db_pool.close_all()` never called on shutdown** | `db_pool.py`, `server.py` | Register `atexit.register(close_all)` at server startup |
| R5 | **`asyncio.new_event_loop()` blocks the HTTP thread** | `server/routes/chat.py:420` | Use `asyncio.run()` (Python 3.7+); cleaner and less error-prone |
| R6 | **Mix of `print()` and `debug_log()` in route files** | `server/routes/chat.py`, `rag.py` | Replace remaining `print(f"❌ ...")` calls with `error_log(...)` |

---

## Maintainability

| # | Issue | File | Fix |
|---|-------|------|-----|
| M1 | ✅ ~~**Unused `parse_qs` module-level import**~~ | `routes_builder.py` | Moved inside `_qp()` |
| M2 | **Dual query param parsing** | `routes_builder.py` (`_qp()`) vs `handler.get_query_params()` | All routes now use `handler.get_query_params()`; `_qp()` can be removed |
| M3 | 🆕 **Files exceeding the 500-line CLAUDE.md limit** | See table below | Split into sub-modules |
| M4 | 🆕 **`capture.js` and `capture-intel.js` bypass `api-client.js`** | `js/capture.js`, `js/capture-intel.js` | 12+ raw `fetch()` calls; migrate to `api.get/post/delete` |
| M5 | 🆕 **`chat-interface.js` bypasses `api-client.js`** | `js/chat-interface.js:55,272,281,362` | 4+ raw `fetch()` calls to migrate |
| M6 | 🆕 **`Pyright` can't resolve `server.utils.error_handler`** | All route files | Add `pyrightconfig.json` at project root with `pythonPath` / `venvPath` |

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

1. **Fix `shredding.py` `json.loads` bug** (B1) — 2 lines changed, prevents runtime crash
2. **Apply `@error_handler` to `proposals.py`** (R2) — removes ~60 lines of boilerplate
3. **Replace `traceback.print_exc()` in `rag.py`** (R3) — 3 lines
4. **Register `close_all()` with `atexit`** (R4) — 2 lines in `server.py`
5. **Add `pyrightconfig.json`** (M6) — eliminates all false-positive import diagnostics

---

## Items Completed Since Last Review (2026-04-05)

- ✅ Path traversal protection in static file serving
- ✅ If-None-Match → 304 Not Modified
- ✅ SQLite `busy_timeout=5000` in db_pool
- ✅ Gzip compression for text assets
- ✅ Moved `parse_qs` import inside `_qp()`
- ✅ `@error_handler` decorator applied to all route files (except `proposals.py`)
