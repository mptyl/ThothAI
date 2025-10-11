# Informix Foreign Key Detection - Library Update

**Date:** 2025-01-11  
**Action:** Library Fix Applied  
**Status:** ✅ COMPLETED

---

## Summary

The Informix foreign key detection issue has been **permanently resolved** by updating the `thoth-dbmanager` library to version **0.7.4**. The temporary patch that was previously used in ThothAI has been removed.

---

## What Was Done

### 1. Library Update (thoth-dbmanager)

**Updated file:** `/Users/mp/Thoth/thoth_sqldb2/thoth_dbmanager/adapters/informix_ssh.py`

The `get_foreign_keys_as_documents()` method was updated to use a compatible query that works with older Informix versions:

- **Old approach (0.7.3):** Used array syntax `ref.foreign[1]` and `ref.primary[1]`
- **New approach (0.7.4):** Uses `sysindexes.part1` to get column numbers

This change is compatible with Informix 10.x and older versions that don't support direct array subscript access in SQL queries.

### 2. Library Published to PyPI

```bash
cd /Users/mp/Thoth/thoth_sqldb2
uv build
uv publish --token $(cat .pypi-token)
```

**Published packages:**
- `thoth_dbmanager-0.7.4.tar.gz`
- `thoth_dbmanager-0.7.4-py3-none-any.whl`

### 3. ThothAI Updated

**Files modified:**
- `backend/pyproject.toml` - Updated to `thoth-dbmanager[postgresql,sqlite]==0.7.4`
- `frontend/sql_generator/pyproject.toml` - Updated to `thoth-dbmanager[postgresql,sqlite]==0.7.4`

**Files removed:**
- `backend/thoth_core/patches/` - Entire directory removed
- `backend/thoth_core/patches/informix_fk_patch.py` - Patch implementation
- `backend/thoth_core/patches/__init__.py` - Patch module
- `docs/INFORMIX_FK_PATCH.md` - Patch documentation
- `backend/scripts/test_patch_applied.py` - Patch test script
- All investigation scripts (9 files removed)

**Files modified:**
- `backend/thoth_core/apps.py` - Removed patch import and application

### 4. Dependencies Synchronized

```bash
cd backend && uv lock --refresh && uv sync
cd frontend/sql_generator && uv lock --refresh && uv sync
```

Both environments now use `thoth-dbmanager==0.7.4` from PyPI.

---

## Verification

Test script created: `backend/scripts/test_informix_fk_new_library.py`

**Test results:**
```
✓ Found database: olimpix
✓ Created database manager (InformixSSHAdapter)
✓ No patch marker found - using library's native implementation
✓✓✓ SUCCESS! Retrieved 210 foreign key relationships ✓✓✓
✓ Foreign key count matches expected value (~210)
```

Sample foreign keys retrieved:
1. banche_agenzie01: agenzie.banca -> banche.bn_codice
2. cespiti_ammfisc01: ammfisc.cespite_ammort -> cespiti.codice_cespite
3. ctrlav_anaope01: anaope.centro_lavoro -> ctrlav.codice_clv
... (207 more)

---

## Technical Details

### Query Changes in thoth-dbmanager 0.7.4

The new implementation uses `sysindexes.part1` instead of array access:

```sql
SELECT 
    fk_con.constrname as constraint_name,
    st_source.tabname as source_table,
    sc_source.colname as source_column,
    st_target.tabname as target_table,
    sc_target.colname as target_column
FROM sysconstraints fk_con
JOIN sysreferences ref ON fk_con.constrid = ref.constrid
JOIN systables st_source ON fk_con.tabid = st_source.tabid
JOIN systables st_target ON ref.ptabid = st_target.tabid
JOIN sysindexes fk_idx ON fk_con.idxname = fk_idx.idxname AND fk_idx.tabid = st_source.tabid
JOIN syscolumns sc_source ON sc_source.tabid = st_source.tabid AND sc_source.colno = fk_idx.part1
JOIN sysconstraints pk_con ON pk_con.tabid = st_target.tabid AND pk_con.constrtype = 'P'
JOIN sysindexes pk_idx ON pk_con.idxname = pk_idx.idxname AND pk_idx.tabid = st_target.tabid
JOIN syscolumns sc_target ON sc_target.tabid = st_target.tabid AND sc_target.colno = pk_idx.part1
WHERE fk_con.constrtype = 'R'
  AND st_source.tabid >= 100
  AND st_target.tabid >= 100
ORDER BY st_source.tabname, fk_con.constrname
```

### Limitation

This implementation handles **single-column foreign keys**. Multi-column FKs will only show the first column pair (`part1`). This is acceptable for most use cases and covers the olimpix database requirements.

---

## Benefits

1. **No more monkey-patching** - Cleaner codebase, easier to maintain
2. **Upstream fix** - Other users of thoth-dbmanager benefit from the fix
3. **Compatibility** - Works with older Informix versions (10.x and earlier)
4. **Tested** - Verified with 210 FK relationships in production database

---

## Rollback (If Needed)

If issues arise, you can temporarily rollback:

1. Revert pyproject.toml changes to use `thoth-dbmanager==0.7.3`
2. Restore the patch from git history:
   ```bash
   git checkout HEAD~1 -- backend/thoth_core/patches/
   git checkout HEAD~1 -- backend/thoth_core/apps.py
   ```
3. Run `uv sync` in both backend and sql_generator

---

## Related Files

- Test script: `backend/scripts/test_informix_fk_new_library.py`
- Library source: `/Users/mp/Thoth/thoth_sqldb2/thoth_dbmanager/adapters/informix_ssh.py`
- PyPI package: https://pypi.org/project/thoth-dbmanager/0.7.4/

---

## References

- thoth-dbmanager GitHub: https://github.com/mptyl/thoth-dbmanager
- Related doc: `docs/OLIMPIX.md`
- Related doc: `docs/INFORMIX_INTEGRATION_COMPLETE.md`
