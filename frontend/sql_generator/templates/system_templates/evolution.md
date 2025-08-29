# AS IS                                                                                          │
Con qualche possibile imprecisione, il processo finale di valutazione degli sql generati è il  seguente:                               

- Al momento gli sql generati vengono confrontati con i test dall'Agent Evaluator
L'Evaluator esprime un giudizio numerico confrontando tutti i test ricevuti e assegnando un OK/KO per ogni test 
Al termine l'Evaluator emette la lista degli SQL con gli ok generati.

- A valle una specifica funzione seleziona l'sql innanzitutto verificando se almeno uno ha
avuto il 100% di ok. In questo caso se c'è un unico sql al 100% viene giudicato vincitore senza
ulteriori analisi. Altrimenti una funzione python valuta la complessità del sql e decreta
vincitore il più semplice.                                                                    
- Nel caso di successo superiore al 90% dei test ma inferiore al 100% viene scelto il migliore 
o il più semplice a parità di percentuale di test passati.                                
- nel caso nessuno superi l'80% di successo, viene giudicato fallita la generazione del sql

# TO BE                                                                                          
Il processo desiderato è il seguente:
- L'Agent Evaluator avrà come Result un oggetto contenente:
    -- una string dal nome result che potrà contenere GOLD o FAILED
    -- una lista di tuple. Ogni elmento della tupla sarà composto da:
       1)string che conterrà il sql è stati valutati
       2)lista di tuple. Ogni tupla contenente il test effettuato e fallito e il motivo del fallimento

    Ovviamente se il result è GOLD allora la lista `sql_list` conterrà solo il sql vincitore
    Se il result è FAILED allora la lista `sql_list` conterrà tutti gli sql scartati, con l'indicazione dei test falliti e del motivo del fallimento.
- L'Agent Evaluator si avvale di diversi Agent ausiliari, che gli fanno da Tool.
- al system prompt dell'Agent Evaluator dovrà essere aggiunta la nota che tra gli elementi a disposizione per la valutazione ci saranno i Gold SQL con la chiara specifica che si tratta di elemeti di ausilio al giudizio, non di sql da giudicare.
- allo user prompt dell'Agent Evaluator dovranno essere aggiunti i Gold SQL ribadendp che si tratta di elemeti di ausilio al giudizio, non di sql da giudicare.
- Il primo tool, che chiamiamo TestReducer, verrà chiamato all'inizio dall'Evaluator e prenderà in input tutti i test da effettuare e
fornirà in output una lista di test semanticamente unici. Infatti i test generati dai TestGenerator vengono deduplicati 
prima di chiamare l'Evaluator, ma i TestGenerator producono molti test formalmente diversi ma che, in pratica, verificano la stessa cosa. 
Il compito del TestReducer è arrivare a un sottoinsieme dei Test in entrata che siano diversi tra di loro nell sostanza di cosa testano, e non solo nel loro testo.                            
- Ricevuta indietro dal Testreducer la lista resa essenziale, l'Evaluator valuta tutti gli SQL a fronte della lista ormai ridotta dei test. Si daranno quattro casi:
A) Uno e un solo SQL supera tutti i test                                                         
B) Più di un SQL supera tutti i test                                                             
C) Nessuno degli SQL supera tutti i test ma alcuni superano (>=) il 90% dei test                 
D) Nessuno raggiunge nemmeno il 90%                                                              
                                                                                                   
## Caso A: 
L'SQL viene giudicato vincitore e l'Evaluator termina con GOLD nel `result` e il il solo testo del SQL vincitorecome componente della lista `sql_list`                       

## Caso B: 
viene attivato il secondo agente, da denominare SqlSelector che si comporterà come segue:
- chiamerà un Tool python (da scrivere) che, usando il thoth-dbmanager, chiamerà ogni query da valutare con limit 10
- le query, accompagnate dai dati appena estratti, verranno valutati a coppie secondo una logica A/B Test da un SqlSelectorAssistent 
che giudicherà quale delle due deve essere considerata la migliore (in caso di parità ne sceglierà una a caso)
- alla fine il vincitore verrà restituito al SqlSelector il quale llo restituirà al Evaluator che lo giudicherà come vincitore

## Caso C. 
L'Evaluator, per ogni sql col 90% di successo, farà fare a un Agent, che chiamaremo EvaluatorSupervisor, un secondo giro di valutazione dei test non passati chiedendo la massima attenzione soprattutto nel valutare se il mancato superamento di quel test è di gravità tale da rendere necesario giudicare errato l'SQL. Il modello deve sforzarsi di rivalutare la question,lo schema, le directives gli hints, i Gold SQL a disposizione e con il massimo thinking possibile decidere definitivamente se bocciare l'SQL o no rispetto a ogni test fallito.

In caso che sia presente più di un SQL con un giudizio > 90% di successo, gli EvaluatorSupervisor potranno essere chiamati in parallelo.
Alla fine l'Evaluator avrà dagli EvaluatorSupervisor una lista di SQL con, per ogni test, il giudizio finale. Se in questa lista ci sarà uno o più SQL al 100% si rientrerà nel caso A o B, altrimenti si rientra nel caso D

## Caso D.
Il caso D è quello in cui nessun SQL è stato giudicato valido. A questo punto l'Evaluator terminerà con FAILED nel `result` e la lista `sql_list` conterrà tutti gli SQL che sono stati scartati, mentre la lista sottostante conterrà i test falliti e il motivo del fallimento.

Il follow-up dell'Evaluator sarà quindi di due tipi. Nel caso Gold la query verrò eseguita e il risultato mostrato come oggi. Nel caso di fallimento si farà invece escalation sul livello successivo di functionality. Se l'elaborazione sql_generation -> test_generation è 
avvenuta con functionality_level BASIC, si proverà con functionality_level ADVANCED, fino alla EXPERT. Ne caso, malgrado l'escalation, nessun SQL verrà ritenuto valido la generazione dovrà essere giudicata FAILED.

# Gestione dell'escalation
L'escalation va fatta con user prompt diversi da quelli usati per l'elaborazione base. Oltre ai dati forniti normalmente, deve essere creata una sezione in cui si avvisano gli Agent che è già stata tentata una elaborazione e che sono stati prodotti degli sql, che non hanno superati i test per i motivi esposti. Il template dovrà quindi accogliere la lista degli sql giudicati falliti e, per ogni sql, la lista dei test falliti e il motivo del fallimento. L'informazione deve essere seguita dall'invito a non produrre SQL già falliti e soprattutto a tenere conto del giudizio di fallimento espresso per evitare di fare lo stesso errore. L'indicazione non deve essere imperativa, in quanto esiste sempre la possibilità che siano i test ad essere sbagliati, piuttosto a tenere conto di questa informazione nel fare la propria generazione

ciò significa ovviamente che il piano deve prevedere degli  attributi alla classe che traccerà l'avanzamento del prpcesso di generazione e valutazione, la quale dovrà, per ogli fiunctionality_level, memorizzare gli sql generati, i test generati e i motivi di fallimento per ogni test fatto ad ogni sql generato. Qindi una struttuta non banale ce dovrà essere poi trasferita al backend per entrare nei suoi log

# Gestione dei Log
I log andranno rivsti. Dovranno essere memorizzati gli SQL generati, i test generati e i risultati dell'applicazione dei test agli SQL.
Come anche adesso, va memrizzato l'SQL vincitore e loggato in modo che possa poi essere indicato nella procedura "like"
del front-end, comme avviene adesso.

Produci il piano e savalo come .md in modo che possa riprenderlo successivamente per il perfezionamento e l'implementazione
