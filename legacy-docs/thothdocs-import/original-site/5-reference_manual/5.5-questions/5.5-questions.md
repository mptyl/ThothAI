# Questions

Le "Questions" rappresentano un elemento fondamentale nel sistema Thoth per la generazione di query SQL. Questo documento fornisce una panoramica sul loro ruolo e sulla loro importanza all'interno del processo, spiegando come vengono utilizzate per migliorare l'accuratezza e la pertinenza delle query generate.

## 1 - Introduzione alle Questions

Le Questions sono documenti strutturati conservati in un database vettoriale, progettati per supportare il processo di generazione automatica di SQL in Thoth. Ogni Question è composta da tre elementi principali:

- **Domanda (Question)**: Una richiesta o interrogazione formulata in linguaggio naturale, che rappresenta il tipo di informazione che un utente potrebbe cercare.
- **Hint**: Un suggerimento o contesto aggiuntivo che aiuta a chiarire l'intento della domanda, spesso fornendo dettagli sul database o sulle tabelle rilevanti, sulle formule utilizzate, su termini specifici che non trovano immediata rispondenza in tabelle e colonne, ecc..
- **SQL**: La query SQL corrispondente che risponde alla domanda, data l'informazione contenuta nell'hint.

Questa combinazione di elementi permette di creare un legame tra l'intento dell'utente espresso in linguaggio naturale e la sua traduzione in una query SQL eseguibile.

## 2 - Ruolo delle Questions nel Processo di Generazione SQL

### 2.1 - Contesto per l'Agente di Generazione
Nel sistema Thoth, quando un utente pone una domanda, il processo di generazione SQL non parte da zero. Al contrario, nelle fasi preliminari, il sistema estrae dal database vettoriale alcune Questions pertinenti, ossia domande simili o correlate a quella posta dall'utente. Queste Questions vengono fornite come contesto all'agente AI responsabile della generazione della query SQL.

### 2.2 - Utilizzo come Few-Shot Examples
Le Questions fungono da esempi pratici, noti come "few-shot examples", all'interno del prompt utilizzato dall'agente di generazione SQL. Includendo nel prompt una serie di triplette (domanda, hint, SQL), l'agente può apprendere dai pattern e dalle strutture di queste esempi, migliorando la sua capacità di generare query SQL accurate e rilevanti per la nuova domanda dell'utente. Questo approccio consente di guidare l'agente verso soluzioni che rispettano il contesto del database e l'intento dell'utente.

### 2.3 - Selezione Dinamica e Fallback
Thoth seleziona dinamicamente le Questions più rilevanti dal database vettoriale in base alla somiglianza con la domanda dell'utente. Se non vengono trovate abbastanza Questions pertinenti, il sistema ricorre a esempi predefiniti (fallback) per garantire che l'agente abbia comunque un contesto sufficiente per operare. Questo meccanismo assicura che il processo di generazione SQL sia robusto anche in assenza di dati specifici nel database vettoriale.

## 3 - Benefici delle Questions

### 3.1 - Miglioramento della Precisione
L'uso delle Questions come contesto aumenta significativamente la precisione delle query SQL generate. Fornendo esempi concreti di come una domanda in linguaggio naturale si traduce in SQL, l'agente può meglio comprendere l'intento dell'utente e produrre risultati più accurati.

### 3.2 - Adattamento al Contesto del Database
Le Questions includono spesso hint che forniscono informazioni specifiche sul database, come la struttura delle tabelle o i campi disponibili. Questo aiuta l'agente a generare query che sono non solo sintatticamente corrette, ma anche semanticamente appropriate per il database in uso.

### 3.3 - Esperienza Utente Migliorata
Grazie alle Questions, gli utenti ottengono risposte più rapide e pertinenti alle loro richieste. Questo si traduce in un'esperienza utente più fluida, riducendo la necessità di riformulare domande o correggere manualmente le query generate.

## 4 - Inserimento delle Questions nel Database Vettoriale

Le Questions possono essere inserite nel database vettoriale di Thoth attraverso due modalità distinte, offrendo flessibilità agli amministratori e agli utenti del sistema:

### 4.1 - Funzione di Preprocessing del Backend
Thoth fornisce una specifica funzione di preprocessing nel backend che consente di caricare e strutturare le Questions nel database vettoriale. Questa funzione è progettata per automatizzare l'inserimento di grandi quantità di dati, facilitando l'aggiornamento e l'espansione del database con nuove triplette di domande, hint e query SQL. In particolare, legge i dati da un file JSON denominato `dev.json`. Poiché questo file è fornito da BIRD, il framework di test più noto nell'ambito della ricerca text-to-SQL, si è deciso di facilitarne l'uso, rendendo il processo di integrazione più semplice ed efficiente. Questa funzione è particolarmente utile per inizializzare o aggiornare il database con esempi predefiniti o raccolti da fonti esterne.

### 4.2 - Inserimento tramite UI del Backend
Oltre alla funzione di preprocessing, Thoth offre un'interfaccia utente (UI) dedicata nel backend che permette agli utenti autorizzati di inserire manualmente nuove Questions. Attraverso questa UI, è possibile aggiungere record individuali, specificando direttamente la domanda, l'hint e la query SQL associata. Questo metodo è ideale per aggiornamenti mirati o per testare nuove Questions senza la necessità di processi automatizzati.

## 5 - Conclusione

Le Questions sono un pilastro del sistema Thoth, consentendo di trasformare domande in linguaggio naturale in query SQL efficaci attraverso un uso intelligente di esempi contestuali. Integrando domande, hint e query SQL in un database vettoriale, Thoth offre un supporto prezioso agli utenti, migliorando la qualità e l'efficienza del processo di interrogazione dei database.
