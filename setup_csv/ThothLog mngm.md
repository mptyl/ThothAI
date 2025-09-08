# Miglioramenti alla gestione del ThothLog

## Miglioramenti generali 

- tutti yimestamp vanno visualizzati in una riga con partenza, arrivo e duration affiancati l'uno all'altro, non su righe diverse

## Sezione Main Information

- l'Evaluation  Result della sezione Main Information rimane sempre Unknown al momento: mostrare lo status finale dell'elaborazione (A, B, ecc.)

## Sezione Time and Language
- da dove vengono la question language e la database language? La prima dovrebbe venire dall'agente Translator quando è stato reiconosciuto un linguaggio diverso dal linguaggio del database. Se il linguaggio è lo stesso, allora la question language deve essere uguale al database language. Il database lenguage dovrebbe essere un attributo del database gestito a livello di workspace
- tra flags attivati manca il flag 'belt and suspenders'. Inserirlo come gli altri, verde se acceso, grigio se spento

## Sezione Phase 2 - Keywords Generation & Data Preparation
- la lista delle keywords generate va mostrata senza che sia inserita in un altra sezione shrinking 
-  vanno tolti i timestamp relativi alla schema preparation,
- il LHS similar columns va mostrato in un blocco shrinking come Schema with examples. lo stesso vale per Reduced Schema se non lo è già

## Sezione Phase 3 - Context Helpers Generation

- i Gold Examples devono essere mostrati in un blocco shrinking come Schema with examples, se non è già così


## Sezione Phase 6 - Test Reduction
- mancano i timestamp della test reduction, verifica che siano dati raccolto, trasferito via log e salvato

## Sezione Phase 7 - SQL Evaluation e Winner Selection 

- mancano i timestamp della sql reduction, verifica che siano dati raccolto, trasferito via log e salvato

- forse mancano i timestamp della fase belt and suspenders verifica che siano dati raccolto, trasferito via log e salvato

- rinominare da Advanced Evaluation a SQL Evaluation e da Enhanced Evaluation Answers  in Evaluation Answers  

- Inserisci nella la sezione Phase 7 la Evaluation Answers ma formattala in modo compatibile con django admin

## Sezione Advanced Evaluation
Elimina completamente la sezione Advanced Evaluation