# Current Task Plan

## Issue
- Update the frontend Documentation page so it mirrors key narratives from `/Users/mp/Thoth/thoth_docs`.

## Plan
1. **Content Analysis** – Review MkDocs sections (index, quickstart, docker install) to capture the story, lingua, and assets to bring into the React page, noting any translation needs.
2. **UI Rewrite** – Adapt `frontend/app/documentation/page.tsx` with the new content structure (intro, feature pillars, quickstart, install, architecture) while keeping the authenticated header intact.
3. **Validation** – Run a sanity pass for React/TypeScript errors, verify component imports, and ensure links/images resolve correctly.

## Progress Updates
- 2025-11-14: Plan drafted; documentation review underway.
- 2025-11-17: User manual section 4.1.7 (Workspaces) drafted and committed in thoth_docs.

## Issue ✅ RESOLVED
- **Informix Foreign Key Detection Failure**: Database `olimpix` has 210 FK constraints but `create_relationships` action detected 0 relationships.

## Root Cause
- thoth-dbmanager 0.7.3 uses array syntax `ref.foreign[1]` and `ref.primary[1]` which is not supported in some Informix versions.
- SQL error: `Column (foreign) not found in any table in the query`

## Solution Implemented
1. **Investigated** using multiple test scripts to understand Informix system catalog structure
2. **Developed** alternative query using `sysindexes.part1` to access column numbers
3. **Created** monkey-patch in `backend/thoth_core/patches/informix_fk_patch.py`
4. **Verified** patch retrieves all 210 FK relationships successfully

## Files Created/Modified
- `backend/thoth_core/patches/informix_fk_patch.py` - Patch implementation
- `backend/thoth_core/patches/__init__.py` - Patch module init
- `backend/thoth_core/apps.py` - Auto-apply patch on Django startup
- `docs/INFORMIX_FK_PATCH.md` - Complete documentation
- Multiple diagnostic scripts in `backend/scripts/` for investigation

## Status
✅ **RESOLVED** - Patch is working and can detect all 210 FK relationships in olimpix database

## Next Steps
- Report issue to thoth-dbmanager repository
- Remove patch when thoth-dbmanager 0.7.4+ is released with fix
- Consider enhancing patch to support multi-column FKs if needed

---

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
