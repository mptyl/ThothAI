**Multilingual Relevance Guard**

- **Overview**  
  - Goal: make `relevance_guard.py` classify evidence-critical tests correctly in all European/Mediterranean languages listed in `language_utils.py`, leveraging both the original question language and the database language stored in `SystemState`.  
  - Key behavior: lexical relevance via BM25 and structural hits are now language-aware, producing better STRICT/WEAK/IRRELEVANT buckets.

- **Language Handling**  
  - Unicode normalization (`NFKC`) + `casefold()` before tokenization to ensure accent-insensitive matching.  
  - Language-specific stopwords sourced from `helpers/stopwords.py` (en, it, es, pt, fr, de, nl, sv, no, da, fi, is, pl, cs, sk, hu, ro, bg, hr, sr, sl, el, tr, ru, uk).  
  - Stopword set chosen as `union_stopwords(question_language, db_language)` with safe English fallback.  
  - `resolve_language_code(..)` maps codes (e.g., `pt-BR`) or names (“Italian”) to canonical ISO-639-1 codes.

- **Adaptive Weights & Structure**  
  - SQL entity extraction unchanged; tables/columns drive structural hits.  
  - Dynamic weighting: for morphologically rich languages (`fi`, `hu`, `tr`, `el`, `ru`, `uk`, `pl`, `cs`, `sk`, `bg`, `ro`, `sl`, `hr`, `sr`) **and** when tables/columns are available, weights adjust to `w_bm25=0.45`, `w_struct=0.55`.  
  - Default weights (`cfg.w_bm25`, `cfg.w_struct`) remain for other cases.  
  - JSONL diagnostics now include `languages.question` and `languages.database`.

- **Integration Points**  
  - `SqlGenerationDeps` carries `question_language` & `db_language`.  
  - `StateFactory.create_agent_deps("sql_generation")` populates these via `resolve_language_code(state.original_language)` & `resolve_language_code(state.request.language)`.  
  - `SqlValidators.create_sql_validator` forwards `(ctx.deps.question_language, ctx.deps.db_language)` to `classify_tests`.

- **Testing Guidance**
  - **Unit Tests**  
    ```bash
    cd frontend/sql_generator
    uv run pytest frontend/sql_generator/tests/test_relevance_guard_multilang.py
    ```  
    - Parametrized cases cover it/es/fr/de/el/tr/ru/uk (relevant test classified as STRICT/WEAK; distractor becomes IRRELEVANT).  
    - Morphology test (hu): verifies structural anchors promote STRICT.
  - **Manual Smoke**  
    1. Prepare a workspace where the question language differs from the database language.  
    2. Run the pipeline (`./start-all.sh` locally or Docker stack).  
    3. Inspect the log (`frontend/sql_generator/logs/relevance.jsonl` or `/app/logs/relevance.jsonl`) to confirm language metadata and correct strict/weak/irrelevant counts.
  - **Env Tuning**  
    - `RELEVANCE_W_BM25`, `RELEVANCE_W_STRUCT` remain configurable; the dynamic adjustment only overrides them for the targeted language set when structural anchors are present.

- **Future Extensions**  
  - Add mixed-language test cases (e.g., Italian question translated to English DB) to `test_relevance_guard_multilang.py`.  
  - Expose config knobs for language-specific weight presets if fine-tuning becomes necessary.

