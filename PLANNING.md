# Current Task Plan

## Issue
- Investigate repeated warnings when running `./start-all.sh`:
  - `Session data corrupted`
  - `Not Found: /__reload__/events/`

## Plan
1. Inspect Django settings, middleware, and URL routing relevant to sessions and `django_browser_reload`.
2. Identify misconfiguration or missing conditions causing warnings in non-debug mode.
3. Apply targeted fixes (e.g., conditional URL inclusion), advise on session cleanup, and validate.

## Progress Updates
- 2025-10-05: Completed step 1 (settings and URLs reviewed). Step 2 in progress.

---

## Issue
- Ensure local development exports `DJANGO_API_URL` and `QDRANT_URL` to prevent SQL Generator warnings.

## Plan
1. Inspect `.env.local.template` and `config.yml.local` defaults.
2. Add missing URL entries so `scripts/generate_env_local.py` emits them.
3. Regenerate environment and confirm warnings disappear.

## Progress Updates
- 2025-10-05: Steps 1-2 completed by updating `.env.local.template` and `config.yml` defaults.

---

## Issue
- `start-all.sh` emits warnings about incorrect `.venv` usage during local startup.

## Plan
1. Review `start-all.sh` virtualenv handling and identify warning sources.
2. Ensure the script detaches from inherited virtualenvs and validates local `.venv` directories.
3. Provide follow-up guidance for rerunning the script and monitoring logs.

## Progress Updates
- 2025-10-05: Step 1 complete (script reviewed).
- 2025-10-05: Step 2 complete (script now unsets `VIRTUAL_ENV` and cleans invalid `.venv`).
