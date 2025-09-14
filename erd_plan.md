# Implementation Plan: Admin ERD-only Action for SqlDb

## Scope
- Add a Django Admin action to generate only the ERD (Mermaid) for one or more `SqlDb` objects, saving the result into the `SqlDb.erd` field.
- Do not change existing ERD/documentation generation code; reuse it where appropriate.
- The action must be independent from full documentation generation.
- Deliberately exclude any logic/decisions about which LLM model to use; that will be decided separately.

## Deliverables
- Admin action “Generate ERD (AI assisted)” available in the `SqlDb` list admin (bulk) and, optionally, on the detail page (`object-tools`).
- New module with a service function that produces and saves the ERD without touching the existing documentation pipeline.
- Clear admin messaging on success/error and any generated file paths (if applicable).

## File Changes (targeted and minimal)
- New file: `backend/thoth_core/thoth_ai/thoth_workflow/generate_db_erd_only.py`
  - Exports an admin action function `generate_db_erd_only(modeladmin, request, queryset)`.
  - Behavior:
    - Accepts multi-selection; loops through each selected `SqlDb` (with an optional soft limit/warning if the selection is large).
    - Builds schema data from the application DB:
      - Reuse existing helpers for schema and parsing (see “Helper reuse” below).
      - Generate ONLY the ERD and save it into `db.erd` with `update_fields=["erd"]`.
    - Notify with `messages.success/warning/error` per DB and a final summary.
  - Helper reuse (no changes to existing helpers):
    - `generate_schema_string_from_models(db_id)` and `extract_mermaid_diagram(...)` from `generate_db_documentation.py`.
    - Queries on `SqlTable`, `SqlColumn`, `Relationship` as already done in the doc generation.
    - Optional image generation on-demand for web preview via `backend/thoth_ai_backend/mermaid_utils.py` (only if required; not essential for the admin action).
  - Important note: no logic/decision on LLM model resolution is included here; the function invokes the existing ERD generator following the project’s current conventions.

- Update: `backend/thoth_core/admin_models/admin_sqldb.py`
  - Import: `from thoth_core.thoth_ai.thoth_workflow.generate_db_erd_only import generate_db_erd_only`.
  - Add `generate_db_erd_only` to the `actions` tuple of `SqlDbAdmin` (near `generate_db_documentation`).
  - Optional (better UX):
    - Add `get_urls` on `SqlDbAdmin` for a dedicated admin endpoint `/<id>/generate-erd/` that calls the action internally for the single DB and then redirects back to the change page.
    - Add `change_form_template` for `SqlDb` and a custom template with an object-tools link “Generate ERD (AI assisted)”.

- New (optional): `backend/thoth_core/templates/admin/thoth_core/sqldb/change_form.html`
  - Extends `admin/change_form.html` and inserts the “Generate ERD (AI assisted)” link in object-tools pointing to the URL registered by `get_urls`.
  - No other customization needed.

## ERD-only Action Flow
1. Admin selects 1+ `SqlDb` from the list or clicks the button on the detail page.
2. For each selected DB:
   - Build the schema context (tables, columns, relationships) by reusing existing helpers.
   - Invoke the existing ERD generator to produce the diagram in Mermaid format.
   - Extract the ```mermaid ...``` block if present and save the resulting text into `SqlDb.erd`.
   - Log the outcome via admin messages.
3. Show a final summary (success/failures).

## Validation and Error Handling
- Empty selection: `error` message and no action.
- DB without tables/relationships: allowed; the ERD may be minimal/empty → show an explanatory `warning`.
- Errors during generation/extraction/save: `error` messages per DB; continue processing the remaining selections.
- Basic safeguards for very large selections (e.g., > 10): show a `warning` before proceeding; continue without interactive prompts.

## Admin Experience
- Bulk action: actions menu in the `SqlDb` list as “Generate ERD (AI assisted)”.
- Button on the change page (optional): object-tools “Generate ERD (AI assisted)”.
- Messaging:
  - Success: “ERD generated and saved in ‘erd’ for <DB>”.
  - Warning: “No structure found for <DB> (minimal ERD)”.
  - Error: “ERD generation error for <DB>: <detail>”.

## Out of Scope (explicitly excluded)
- Any logic regarding LLM model/provider resolution for generation. This will be defined later and linked to the function described here.
- Changes to the existing documentation generation function or related templates.

## Implementation Checklist
- [ ] Create `backend/thoth_core/thoth_ai/thoth_workflow/generate_db_erd_only.py` with:
  - [ ] Function `generate_db_erd_only(modeladmin, request, queryset)`.
  - [ ] Schema data construction (tables, columns, relationships) reusing existing helpers.
  - [ ] ERD generator invocation and `SqlDb.erd` save.
  - [ ] Granular admin messages + summary.
- [ ] Update `backend/thoth_core/admin_models/admin_sqldb.py`:
  - [ ] Import and add the action to `actions`.
  - [ ] (Optional) `get_urls` + admin view for the single DB.
  - [ ] (Optional) `change_form_template` to add the object-tools link.
- [ ] (Optional) Add `backend/thoth_core/templates/admin/thoth_core/sqldb/change_form.html` with the “Generate ERD (AI assisted)” link.
- [ ] Quick manual test in admin: single and multiple selections; validate `erd` field update and messages.

## Maintenance Notes
- The `SqlDb.erd` field already exists and stores Mermaid content; no migration required.
- The existing ERD code remains unchanged; this plan adds only a separate entry point and admin UI.
- Future extensions (e.g., export SVG/PNG/PDF) can reuse `backend/thoth_ai_backend/mermaid_utils.py` without impacting the admin action.
