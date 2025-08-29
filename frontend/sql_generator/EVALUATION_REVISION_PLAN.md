# Piano di Revisione del Sistema di Valutazione SQL

## Obiettivo
Rivedere il sistema di valutazione finale per ridurre il numero di SQL validi scartati erroneamente ("scarta più SQL di quanto dovrebbe").

## Architettura della Soluzione

### Nuovo Modello di Risultato
- **EnhancedEvaluationResult**: Sostituisce EvaluationResult con stati GOLD/FAILED
- **Gold SQL Integration**: Integrazione di SQL di esempio come riferimento (non per valutazione)

### Agenti Ausiliari (tutti usano lo stesso modello dell'Evaluator)
1. **TestReducer**: Deduplicazione semantica dei test oltre quella esatta
2. **SqlSelector**: Selezione A/B tra SQL equivalenti con test di esecuzione
3. **EvaluatorSupervisor**: Rivalutazione approfondita per casi borderline (8000+ token thinking)

### Sistema a 4 Casi di Valutazione
- **Caso A**: Un solo SQL al 100% → Diretto successo GOLD
- **Caso B**: Più SQL al 100% → SqlSelector per la scelta migliore
- **Caso C**: SQL al 90-99% → EvaluatorSupervisor per rivalutazione approfondita
- **Caso D**: Tutti SQL <90% → Escalation al livello superiore

### Sistema di Escalation
- **BASIC** → **ADVANCED** → **EXPERT**
- Passaggio del contesto di fallimento al livello successivo
- Logging avanzato per tutti i dettagli di valutazione

## Piano di Implementazione Step-by-Step

### Step 0: Checkpoint Iniziale ✅
- Salvataggio del piano come EVALUATION_REVISION_PLAN.md
- Commit iniziale: "checkpoint: before evaluation system revision"

### Step 1: Creare EnhancedEvaluationResult
**File**: `agents/core/agent_result_models.py`
- Nuovo modello con status GOLD/FAILED/NEEDS_REEVALUATION
- Campi per SQL di riferimento (Gold SQL)
- Metadati di valutazione (pass_rates, selected_sql, etc.)

### Step 2: Implementare TestReducer
**File**: `agents/test_reducer_agent.py`
- Agente per deduplicazione semantica dei test
- Utilizza il modello dell'Evaluator con template specifico
- Input: lista test + thinking, Output: lista test ridotta

### Step 3: Integrare Supporto Gold SQL
**File**: `templates/template_evaluate.txt`
- Sezione per Gold SQL examples
- Aggiornamento template per includere riferimenti

### Step 4: Creare SqlSelector
**File**: `agents/sql_selector_agent.py`
- Selezione tra SQL equivalenti (tutti al 100%)
- A/B testing con esecuzione effettiva se possibile
- Assistant agent per confronto dettagliato

### Step 5: Implementare EvaluatorSupervisor
**File**: `agents/evaluator_supervisor_agent.py`
- Rivalutazione approfondita per casi borderline (90-99%)
- Extended thinking (8000+ token)
- Decisione finale GOLD/FAILED

### Step 6: Sistema di Escalation
**File**: `helpers/main_helpers/escalation_manager.py`
- Gestione passaggio BASIC → ADVANCED → EXPERT
- Contesto di fallimento tra livelli
- Coordinamento con generator_type.py

### Step 7: Flusso di Valutazione a 4 Casi
**File**: `helpers/main_helpers/main_evaluation.py`
- Revisione completa di evaluate_sql_candidates()
- Implementazione della logica A/B/C/D
- Integrazione di tutti gli agenti ausiliari

### Step 8: Logging Avanzato
**File**: `helpers/main_helpers/evaluation_logger.py`
- Sistema di logging dettagliato per tutte le fasi
- Tracciamento delle decisioni e dei percorsi
- Metriche di performance del sistema

### Step 9: Test e Documentazione
- Test unitari per tutti i nuovi componenti
- Test di integrazione per il flusso completo
- Documentazione delle modifiche

## Requisiti Tecnici Critici

### Consistenza dei Modelli
- **TUTTI** gli agenti ausiliari devono usare lo stesso modello dell'Evaluator
- Factory pattern per creazione agenti con modello condiviso
- Template diversi ma configurazione modello identica

### Checkpoint Git
- Commit prima di ogni step per rollback sicuro
- Formato: `git commit -m "step X: [descrizione]"`
- Tag per milestone importanti

### Compatibilità
- Mantenere compatibilità con il flusso esistente
- Fallback graceful se agenti ausiliari non disponibili
- Preservare l'interfaccia pubblica esistente

## Metriche di Successo
- Riduzione dei falsi negativi (SQL validi scartati)
- Mantenimento della qualità di selezione SQL
- Performance accettabile (<2x tempo attuale)
- Copertura test ≥90% per nuovi componenti