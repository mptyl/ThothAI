# ThothAI – Dependency Update Plan (2025-10-04)

## Goal
- Regenerate lockfiles and sync environments.
- Verify services start successfully.

## Steps
1) Pin `thoth-dbmanager==0.6.0` where needed.
   - backend/pyproject.toml: already pinned to 0.6.0. 
   - frontend/sql_generator/pyproject.toml: updated to 0.6.0. 
2) Regenerate lockfiles with uv.
   - backend/: `uv lock` 
   - frontend/sql_generator/: `uv lock` 
3) Sync environments.
   - backend/: `uv sync --frozen` 
   - frontend/sql_generator/: `uv sync --frozen` 
4) Start the stack.
   - `./start-all.sh` 
5) Validate.
   - Confirm no dependency resolution errors. 
   - Confirm services on ports: 8200 (backend), 8180 (SQL Gen), 3200 (frontend), 6334 (Qdrant), 8003 (Mermaid). 

## Python 3.13 SSH Tunnel Fix (2025-10-04)

### Issue
- **Error:** `name 'stop_event' is not defined` when testing SSH tunnel database connections
- **Cause:** Python 3.13 stricter scoping rules in class bodies (PEP 709)
- **Affected:** thoth-dbmanager v0.6.0, SSH tunnel feature

### Solution Applied
- Created monkey patch: `backend/thoth_core/utilities/ssh_tunnel_patch.py` 
- Auto-applied in: `backend/thoth_core/utilities/utils.py:initialize_database_plugins()` 
- Documentation: `docs/SSH_TUNNEL_PYTHON313_FIX.md` 

### Status
- **RESOLVED**  - Patch automatically applied at backend startup
- SSH tunnel database connections should now work with Python 3.13
- Remove patch when thoth-dbmanager v0.6.1+ is released with upstream fix

## Notes
- Use PyPI for `thoth-dbmanager`, do not use local path.
- Correct local source path (for reference only): `/Users/Thoth/thoth_sqldb2`.
