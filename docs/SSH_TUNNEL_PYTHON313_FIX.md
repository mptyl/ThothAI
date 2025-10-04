# SSH Tunnel Python 3.13 Compatibility Fix

## Issue Description

When testing database connections that use SSH tunnels with Python 3.13, you may encounter the following error:

```
ERROR Failed to create database manager for [database_name]: 
Failed to create postgresql manager: name 'stop_event' is not defined
```

## Root Cause

This is a **Python 3.13 compatibility issue** in `thoth-dbmanager` version 0.6.0. The problem occurs in the `ssh_tunnel.py` file's `_build_handler` method.

### Technical Details

Python 3.13 introduced stricter scoping rules for class bodies (PEP 709 - Comprehension Inlining). The following pattern, which worked in Python 3.12, now fails:

```python
def _build_handler(self, transport):
    stop_event = self._stop_event  # local variable
    
    class Handler(_ForwardHandler):
        stop_event = stop_event  # ← Error in Python 3.13
```

In Python 3.13, when assigning a class attribute, the name on the right side cannot reference a variable from the enclosing scope if it has the same name as the attribute being created on the left side.

## Solution

### Automatic Fix (Already Applied)

A monkey patch has been implemented and is automatically applied when the backend starts. The patch is located at:

```
backend/thoth_core/utilities/ssh_tunnel_patch.py
```

The fix is automatically applied in `initialize_database_plugins()` in:

```
backend/thoth_core/utilities/utils.py
```

### What the Patch Does

The patch renames the local variable to avoid the name collision:

**Original (buggy) code:**
```python
def _build_handler(self, transport):
    config = self.config
    stop_event = self._stop_event  # ← Same name as class attribute
    
    class Handler(_ForwardHandler):
        stop_event = stop_event  # ← Fails in Python 3.13
```

**Patched (fixed) code:**
```python
def _build_handler(self, transport):
    config = self.config
    stop_evt = self._stop_event  # ← Renamed variable
    
    class Handler(_ForwardHandler):
        stop_event = stop_evt  # ← Now works in Python 3.13
```

## Verification

To verify the patch is working:

1. Restart your Django backend server
2. Check the logs for: `Applied SSH tunnel patch for Python 3.13 compatibility`
3. Test your SSH tunnel database connection again

## Future Resolution

This patch should be removed once `thoth-dbmanager` is updated to version 0.6.1 or higher with the fix incorporated upstream.

### Reporting Upstream

If you maintain `thoth-dbmanager`, please update the package with this fix:

**File to modify:** `thoth_dbmanager/helpers/ssh_tunnel.py`  
**Method:** `SSHTunnel._build_handler`  
**Line:** ~365-375

## Affected Configurations

This issue only affects database connections with:
- SSH tunnel enabled (`ssh_enabled=True`)
- Python 3.13 runtime
- thoth-dbmanager version 0.6.0

## Alternative Workarounds

If the automatic patch doesn't work:

1. **Downgrade Python to 3.12:**
   ```bash
   pyenv install 3.12.8
   pyenv local 3.12.8
   ```

2. **Wait for upstream fix:** Monitor https://pypi.org/project/thoth-dbmanager/ for version 0.6.1+

3. **Manual patch:** Edit the installed package directly (not recommended for production)

## References

- **Python PEP 709:** Comprehension Inlining (https://peps.python.org/pep-0709/)
- **Python 3.13 Release Notes:** https://docs.python.org/3.13/whatsnew/3.13.html
- **Issue Location:** `thoth_dbmanager/helpers/ssh_tunnel.py:365-375`
