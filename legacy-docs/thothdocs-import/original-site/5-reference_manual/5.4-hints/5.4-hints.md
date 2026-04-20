# Hints

Gli "hints" sono un elemento fondamentale nel sistema Thoth per supportare il processo di conversione da testo a SQL (text-to-SQL). Questo documento fornisce una panoramica sul loro scopo, utilizzo e gestione all'interno del framework.

## 1 - Introduzione agli Hints

Gli hints sono testi conservati in un database vettoriale, composti da un unico elemento: un testo esplicativo che chiarisce termini complessi o suggerisce interpretazioni non intuitive. Il loro obiettivo principale è facilitare l'associazione tra i concetti espressi in una domanda o richiesta in linguaggio naturale e lo schema del database sottostante.

### 1.1 - Ruolo nel Processo Text-to-SQL

Nel contesto del sistema Thoth, ogni volta che un utente pone una domanda, il processo di generazione dell'SQL prevede una fase preliminare in cui vengono estratti hints "simili" o "pertinenti" alla richiesta. Questi hints vengono poi forniti come contesto aggiuntivo all'agente responsabile della generazione dell'SQL, migliorando la precisione e la coerenza delle query generate.

### 1.2 - Benefici degli Hints

Gli hints aiutano a colmare il divario tra il linguaggio naturale e la struttura tecnica di un database. Ad esempio, possono spiegare come un termine comune utilizzato dall'utente si traduca in una specifica colonna o tabella del database, oppure fornire suggerimenti su come interpretare una richiesta ambigua in un un contesto specifico.

## 2 - Gestione degli Hints

La gestione degli hints è un processo chiave per garantire che il sistema Thoth possa sfruttare al meglio queste informazioni di supporto. Gli hints vengono creati, caricati e aggiornati attraverso procedure specifiche integrate nel framework.

### 2.1 - Caricamento nel Database Vettoriale

Gli hints possono essere caricati nel database vettoriale a partire da un file `dev.json`, fornito all'interno del framework BIRD. Questo file contiene una raccolta strutturata di dati, inclusi gli hints, che vengono elaborati e indicizzati nel database vettoriale per consentire un rapido recupero durante il processo di generazione dell'SQL. Questo approccio permette di arricchire il sistema con informazioni di contesto predefinite, pronte per essere utilizzate in risposta a domande pertinenti.

### 2.2 - Creazione e Aggiornamento tramite Preprocessing

Gli hints possono essere generati o aggiornati durante le fasi di preprocessing del sistema Thoth. Questo processo consente di analizzare dati esistenti o nuovi input per creare hints che riflettano meglio le specificità del database o le esigenze degli utenti. Attraverso un'interfaccia dedicata, gli amministratori possono rivedere e ottimizzare gli hints per garantire che siano sempre rilevanti e utili.

### 2.3 - Interfaccia Utente per la Gestione (CRUD)

Thoth offre un'interfaccia utente (UI) per la gestione completa degli hints, permettendo operazioni di creazione, lettura, aggiornamento ed eliminazione (CRUD). Questa interfaccia consente agli utenti autorizzati di inserire nuovi hints, modificarli in base a feedback o cambiamenti nello schema del database, e rimuoverli se non più necessari, mantenendo il database vettoriale sempre aggiornato e funzionale.

## 3 - Utilizzo Pratico degli Hints

Gli hints trovano applicazione in diversi scenari all'interno del sistema Thoth, migliorando l'interazione tra utenti e database.

### 3.1 - Supporto alla Generazione di SQL

Come già accennato, gli hints vengono utilizzati come contesto aggiuntivo per l'agente che genera l'SQL. Quando una domanda viene posta, il sistema identifica gli hints più rilevanti e li integra nel processo, aiutando a produrre query SQL più accurate e aderenti alle intenzioni dell'utente.

### 3.2 - Adattamento a Database Specifici

Gli hints possono essere personalizzati per riflettere le peculiarità di un database specifico. Questo significa che, anche in presenza di schemi complessi o terminologie uniche, gli hints possono guidare il sistema nella traduzione corretta delle richieste utente in query eseguibili.

## 4 - Conclusione

Gli hints rappresentano uno strumento essenziale per migliorare l'efficacia del processo text-to-SQL nel sistema Thoth. Fornendo spiegazioni e contesti aggiuntivi, permettono una traduzione più precisa delle richieste in linguaggio naturale in query SQL, facilitando l'interazione con database complessi. La loro gestione, attraverso caricamento da file, preprocessing e interfacce utente dedicate, garantisce che il sistema rimanga flessibile e adattabile alle esigenze degli utenti.

## 5 - Esempi di Hints

Di seguito sono riportati alcuni esempi di hints estratti dal file `dev.json`. Questi esempi illustrano come gli hints aiutino a chiarire concetti complessi o suggeriscano interpretazioni non intuitive, facilitando l'associazione tra le domande poste dagli utenti e lo schema del database.

### 5.1 - california_schools

- **Database ID**: california_schools
- **Domanda**: "What is the highest eligible free rate for K-12 students in the schools in Alameda County?"
- **Hint**: "Eligible free rate for K-12 = `Free Meal Count (K-12)` / `Enrollment (K-12)`"

- **Database ID**: california_schools
- **Domanda**: "Please list the zip code of all the charter schools in Fresno County Office of Education."
- **Hint**: "Charter schools refers to `Charter School (Y/N)` = 1 in the table fprm"

- **Database ID**: california_schools
- **Domanda**: "How many schools with an average score in Math greater than 400 in the SAT test are exclusively virtual?"
- **Hint**: "Exclusively virtual refers to Virtual = 'F'"

### 5.2 - financial

- **Database ID**: financial
- **Domanda**: "How many accounts who choose issuance after transaction are staying in East Bohemia region?"
- **Hint**: "A3 contains the data of region; 'POPLATEK PO OBRATU' represents for 'issuance after transaction'."

- **Database ID**: financial
- **Domanda**: "List out the account numbers of female clients who are oldest and has lowest average salary, calculate the gap between this lowest average salary with the highest average salary?"
- **Hint**: "Female means gender = 'F'; A11 refers to average salary; Gap = highest average salary - lowest average salary; If the person A's birthdate > B's birthdate, it means that person B is order than person A."

### 5.3 - toxicology

- **Database ID**: toxicology
- **Domanda**: "In the non-carcinogenic molecules, how many contain chlorine atoms?"
- **Hint**: "non-carcinogenic molecules refers to label = '-'; chlorine atoms refers to element = 'cl'"

- **Database ID**: toxicology
- **Domanda**: "What is the percentage of carbon in double-bond molecules?"
- **Hint**: "carbon refers to element = 'c'; double-bond molecules refers to bond_type = '='; percentage = DIVIDE(SUM(element = 'c'), COUNT(atom_id))"

### 5.4 - card_games

- **Database ID**: card_games
- **Domanda**: "What are the borderless cards available without powerful foils?"
- **Hint**: "borderless' refers to borderColor; poweful foils refers to cardKingdomFoilId paired with cardKingdomId AND cardKingdomId is not null"

- **Database ID**: card_games
- **Domanda**: "List all the mythic rarity print cards banned in gladiator format."
- **Hint**: "mythic rarity printing refers to rarity = 'mythic'; card banned refers to status = 'Banned'; in gladiator format refers to format = 'gladiator';"

### 5.5 - codebase_community

- **Database ID**: codebase_community
- **Domanda**: "Which user has a higher reputation, Harlan or Jarrod Dixon?"
- **Hint**: "\"Harlan\" and \"Jarrod Dixon\" are both DisplayName; highest reputation refers to Max(Reputation)"

- **Database ID**: codebase_community
- **Domanda**: "What is the display name of the user who is the owner of the most valuable post?"
- **Hint**: "most valuable post refers to Max(FavoriteCount)"

### 5.6 - superhero

- **Database ID**: superhero
- **Domanda**: "Please list all the superpowers of 3-D Man."
- **Hint**: "3-D Man refers to superhero_name = '3-D Man'; superpowers refers to power_name"

- **Database ID**: superhero
- **Domanda**: "How many superheroes have the super power of \"Super Strength\"?"
- **Hint**: "super power of \"Super Strength\" refers to power_name = 'Super Strength'"

### 5.7 - formula_1

- **Database ID**: formula_1
- **Domanda**: "Please list the reference names of the drivers who are eliminated in the first period in race number 20."
- **Hint**: "driver reference name refers to driverRef; first qualifying period refers to q1; drivers who are eliminated in the first qualifying period refers to 5 drivers with MAX(q1); race number refers to raceId;"

- **Database ID**: formula_1
- **Domanda**: "What is the surname of the driver with the best lap time in race number 19 in the second qualifying period?"
- **Hint**: "race number refers to raceId; second qualifying period refers to q2; best lap time refers to MIN(q2);"

### 5.8 - european_football_2

- **Database ID**: european_football_2
- **Domanda**: "Which player has the highest overall rating? Indicate the player's api id."
- **Hint**: "highest overall rating refers to MAX(overall_rating);"

- **Database ID**: european_football_2
- **Domanda**: "What is the height of the tallest player? Indicate his name."
- **Hint**: "tallest player refers to MAX(height);"

### 5.9 - trombosis_prediction

- **Database ID**: trombosis_prediction
- **Domanda**: "Are there more in-patient or outpatient who were male? What is the deviation in percentage?"
- **Hint**: "male refers to SEX = 'M'; in-patient refers to Admission = '+'; outpatient refers to Admission = '-'; percentage = DIVIDE(COUNT(ID) where SEX = 'M' and Admission = '+', COUNT(ID) where SEX = 'M' and Admission = '-')"

- **Database ID**: trombosis_prediction
- **Domanda**: "What is the percentage of female patient were born after 1930?"
- **Hint**: "female refers to Sex = 'F'; patient who were born after 1930 refers to year(Birthday) > '1930'; calculation = DIVIDE(COUNT(ID) where year(Birthday) > '1930' and SEX = 'F'), (COUNT(ID) where SEX = 'F')"

### 5.10 - student_club

- **Database ID**: student_club
- **Domanda**: "What's Angela Sanders's major?"
- **Hint**: "Angela Sanders is the full name; full name refers to first_name, last_name; major refers to major_name."

- **Database ID**: student_club
- **Domanda**: "How many students in the Student_Club are from the College of Engineering?"
- **Hint**: ""

### 5.11 - debit_card_specializing

- **Database ID**: debit_card_specializing
- **Domanda**: "How many gas stations in CZE has Premium gas?"
- **Hint**: ""

- **Database ID**: debit_card_specializing
- **Domanda**: "What is the ratio of customers who pay in EUR against customers who pay in CZK?"
- **Hint**: "ratio of customers who pay in EUR against customers who pay in CZK = count(Currency = 'EUR') / count(Currency = 'CZK')."
