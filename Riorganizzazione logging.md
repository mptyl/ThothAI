# Riorganizzazione losing

Il processo di generazione degli sql attraversa varie fasi. Voglio che tutti i dati salienti delle varie fasi siano loggati e presentati nella ThothLog admin page

## Fasi

### Fase preliminare
1. avvio del processo generale con rilevamento:
- timestamp inizio processo, 
- utente richiedente, 
- domanda effettuata (in lingua della domanda), 
- flag attivati, 
- functionality_level all'avvio,
- workspace di contesto della domanda
2. validazione della domanda - rilevare timmestamp iniziale e finale
3. traduzione della domanda con rilevamento di
- lingua del database
- se la domanda è espressa in altra lingua rispetto a quella del database registrare:
    * la traduzione della domanda nella lingua del database,
    * la lingua in cui è espressa la domanda

### Generazione delle keyword e preparazione dei dati

1. generazione delle keywords. Registrare:
- timestamp inizio fase,
- keywords generate
- timestamp fine fase
2. Ricerche di similarità su LSH e database vettoriale. Registrare:
- timestamp inizio fase,
- similar columns generate tramite ricerva LSH
- schema with examples
- schema from vectordb
- reduced schema
- used schema
- timestamp fine fase 

### Generazione aiuuti di contesto 
1. context from vector db, Registrare
- timestamp inizio fase
- evidence estratte
- gold sql estratti
- timestamp fine fase


### Fase di generazione SQL
1 Generazione degli SQL
- timestamp inizio fase 
- generazione degli sql
- timestamp fine fase

### Fase di generazione dei test
1. Generazione dei test
- timestamp inizio fase
- generazione dei test
- timestamp fine fase

### Fase di riduzione dei test (se effettuata)
- riduzione dei test

### Fase di valutazione SQL e selezione vincitore
- valutazione SQL
- selezione vincitore

### Finale
- rilevamento timestamp finale

## Struttura dell'admin page di ThothLog
la pagina admin deve essere organizzata

## Sezione 1:
### Prima riga: 
- Question in lingua originale che occupa il 50% della riga
- Esito (Gold, Silver ecc.) che occupa il restante 50% della riga
### Seconda riga:
- SQL con una textarea di 600px (70% riga)
- Duration dell'intero processo (30% della riga)
### Terza riga:
- username (50%)
- workspace (50%)
### Quarta riga:
- Timestamp inizio processo (50%)
- Timestamp fine processo (50%)
### Quinta riga:
- lingua della domanda (50%)
- lingua del database (50%)
### Sesta riga:
- Translated Question
- Directives (Textarea di 5 righe che occupa il 100% dello spazio disponibile con 5px di paddin a sx e dx

## Sezione 2



