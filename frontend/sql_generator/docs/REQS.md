# Requirements for thoth_ui
Il workflow per la generazione degli sql deve essere completato.
Al momento, guardando lo script main.py di sql_generation, troviamo la seguente situazione:
- la funzione generate_sql, che prepara la successiva chiamata a generate_response inizializza e registra in state una serie di oggetti e di variabili che saranno utili in generate_response

- la funzione generate_response,il vero workhorse:
    - fa la validazione, e se necessario la traduzione, della question. Se viene eseguita una traduzione un tool associato all'agente aggiorna i dati di lingua usata e question tradotta in state
    - estrae le keywords dalla question
    - legge le evidence e gli sql da usare come few shots dal database vettoriale
    - legge le informazioni LSH e da vectordb che hanno a che fare con le keywords
    - costruisce lo used_mschema sulla base di qual'è il sql_generator e lo salva nelSystemState
    - genera il pool di SQL chiamandone un numero variabile, configurato nel backend, in parallelo
    - genera il pool di Test Units chiamandone un numero variabile, configurato nel backend, in parallelo
    - genera ed esegue l'Evaluation tramite un apposito Agent ottenendo una lista di giudizi di tipoPassed/Failed generati dal Evaluator Agent
    - sceglie il miglior SQL, lo presenta a video in risposta alla chat e produce una spiegazione in linguaggio naturale del SQL generato

    - invia a django il log di ciò che ha fatto

## Like Implementation
Il task di like deve permettere all'utente di apprezzare il lavoro di Thoth confermando che l'SQL generato è adatto a rispondere alla question.
Per poterlo implementare bisogna:
- che nel box di input, in fondo a destra, compaia la classica icona del like (solo like, no dislike)
- L'icona diventa attiva al termine di una gestione andata a buon fine quando almeno la table ( o un valore, dipende dal rendering della risposta) è presenta a video. L'utente può premere like e il sistema deve fagli apparire un box contenente un testo, un bottone cancel e un bottone con scritto "ok, remember"!  in cui spiega che se confermerà con l'ok questa particolare combinazione di question ed sql verrà salvata nella memoria di sistema per facilitare le prossime question. Usa un tono professionale e sintetico, non usare termini tecnici. E' una richiesta di conferma a un utente non tecnico. 

Se l'utente conferma devi:
- prendere la question come espressa dall'utente, nel linguaggio in cui è stata espressa
- prendere la prima delle evidence estratte
- prendere il SQL generato
 e salvare il tutto come una SQLDocument nel database vettoriale tramite vdbmanager





