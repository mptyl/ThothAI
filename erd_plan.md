# Piano di Implementazione: Azione Admin ERD-only per SqlDb

## Scopo
- Aggiungere in Django Admin un’azione per generare esclusivamente l’ERD (Mermaid) per uno o più `SqlDb`, salvando il risultato nel campo `SqlDb.erd`.
- Non modificare il codice esistente di generazione ERD/documentazione; riutilizzarlo dove opportuno.
- L’azione deve essere indipendente dalla generazione della documentazione completa.
- Escludiamo intenzionalmente ogni dettaglio su come viene determinato il modello LLM: verrà deciso separatamente.

## Deliverable
- Azione admin “Generate ERD (AI assisted)” disponibile in `SqlDb` list admin (bulk) e, opzionale, nella scheda dettaglio (`object-tools`).
- Nuovo modulo con funzione di servizio che produce e salva l’ERD senza toccare la pipeline di documentazione esistente.
- Messaggi chiari in admin su successo/errore e percorso di eventuali file generati (se previsti).

## Modifiche ai file (mirate e minimali)
- Nuovo file: `backend/thoth_core/thoth_ai/thoth_workflow/generate_db_erd_only.py`
  - Esporta una funzione admin action `generate_db_erd_only(modeladmin, request, queryset)`.
  - Comportamento:
    - Accetta selezione multipla; elabora in loop ogni `SqlDb` selezionato (con eventuale limite soft/warning se selezione è grande).
    - Costruisce i dati di schema da DB applicativo:
      - Usa helper esistenti per schema e parsing (vedi “Riutilizzo helper” sotto).
      - Genera SOLO l’ERD e lo salva in `db.erd` con `update_fields=["erd"]`.
    - Notifica con `messages.success/warning/error` per ogni DB e un riepilogo finale.
  - Riutilizzo helper (senza modifiche agli esistenti):
    - `generate_schema_string_from_models(db_id)` e `extract_mermaid_diagram(...)` da `generate_db_documentation.py`.
    - Query su `SqlTable`, `SqlColumn`, `Relationship` come già fatto nella doc generation.
    - Eventuale generazione immagine on-demand per preview web via `backend/thoth_ai_backend/mermaid_utils.py` (solo se richiesto; non indispensabile per l’azione admin).
  - Nota importante: nessuna logica/decisione su determinazione LLM inclusa qui; la funzione invoca il generatore ERD esistente secondo le convenzioni attuali del progetto.

- Aggiornamento: `backend/thoth_core/admin_models/admin_sqldb.py`
  - Import: `from thoth_core.thoth_ai.thoth_workflow.generate_db_erd_only import generate_db_erd_only`.
  - Aggiungere `generate_db_erd_only` alla tupla `actions` di `SqlDbAdmin` (vicino a `generate_db_documentation`).
  - Opzionale (miglior UX):
    - Aggiungere `get_urls` su `SqlDbAdmin` per un endpoint admin dedicato `/<id>/generate-erd/` che chiama internamente l’azione per il singolo DB e poi fa redirect alla change page.
    - Aggiungere `change_form_template` per `SqlDb` e un template custom con link object-tools “Generate ERD (AI assisted)”.

- Nuovo (opzionale): `backend/thoth_core/templates/admin/thoth_core/sqldb/change_form.html`
  - Estende `admin/change_form.html` e inserisce il link “Generate ERD (AI assisted)” negli object-tools verso l’URL registrato da `get_urls`.
  - Nessuna altra personalizzazione necessaria.

## Flusso dell’Azione ERD-only
1. Admin seleziona 1+ `SqlDb` dalla lista o clicca il pulsante nella scheda dettaglio.
2. Per ogni DB selezionato:
   - Costruisce contesto schema (tabelle, colonne, relazioni) riusando gli helper esistenti.
   - Invoca il generatore dell’ERD esistente per produrre il diagramma in formato Mermaid.
   - Estrae l’eventuale blocco ```mermaid ...``` e salva il testo risultante in `SqlDb.erd`.
   - Registra esito nei messaggi admin.
3. Mostra un riepilogo finale (successi/fallimenti).

## Validazioni ed Error Handling
- Selezione vuota: messaggio `error` e nessuna azione.
- DB senza tabelle/relazioni: consentito; l’ERD potrebbe essere minimale/vuoto → messaggio `warning` esplicativo.
- Errori durante generazione/estrazione/salvataggio: messaggi `error` per DB, il processo continua sugli altri selezionati.
- Protezioni basilari per selezioni molto ampie (es. > 10): messaggio `warning` prima di procedere; la scelta di continuare avviene comunque (nessun prompt interattivo necessario lato admin).

## Esperienza in Admin
- Azione bulk: menu azioni in lista `SqlDb` come “Generate ERD (AI assisted)”.
- Pulsante nella change page (opzionale): object-tools “Generate ERD (AI assisted)”.
- Messaggistica:
  - Successo: “ERD generato e salvato in ‘erd’ per <DB>”.
  - Warning: “Nessuna struttura trovata per <DB> (ERD minimale)”.
  - Errore: “Errore generazione ERD per <DB>: <dettaglio>”.

## Out of Scope (esplicitamente escluso)
- Qualsiasi logica sulla determinazione/risoluzione del modello LLM o dei provider per la generazione. Questo verrà definito in un passaggio successivo e collegato alla funzione qui descritta.
- Modifiche alla funzione esistente di generazione della documentazione o ai relativi template.

## Checklist di Implementazione
- [ ] Creare `backend/thoth_core/thoth_ai/thoth_workflow/generate_db_erd_only.py` con:
  - [ ] Funzione `generate_db_erd_only(modeladmin, request, queryset)`.
  - [ ] Costruzione dati schema (tabelle, colonne, relazioni) riusando helper esistenti.
  - [ ] Invocazione generatore ERD e salvataggio `SqlDb.erd`.
  - [ ] Messaggi admin granulari + riepilogo.
- [ ] Aggiornare `backend/thoth_core/admin_models/admin_sqldb.py`:
  - [ ] Import e aggiunta dell’azione in `actions`.
  - [ ] (Opzionale) `get_urls` + view admin per il singolo DB.
  - [ ] (Opzionale) `change_form_template` per aggiungere il link object-tools.
- [ ] (Opzionale) Aggiungere `backend/thoth_core/templates/admin/thoth_core/sqldb/change_form.html` con il link “Generate ERD (AI assisted)”.
- [ ] Test manuale rapido in admin: selezione singola e multipla; validare aggiornamento del campo `erd` e messaggi.

## Note di Manutenzione
- Il campo `SqlDb.erd` esiste già e ospita il contenuto Mermaid; nessuna migrazione richiesta.
- Il codice ERD già esistente rimane invariato; questo piano aggiunge solo un punto di ingresso separato e UI admin.
- Eventuali estensioni future (es. export SVG/PNG/PDF) possono riutilizzare `backend/thoth_ai_backend/mermaid_utils.py` senza impatti sull’azione admin.

