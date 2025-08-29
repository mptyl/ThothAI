# README-UNI-IT
Questo documento è stato creato specificamente per UNI. Contiene informazioni e istruzioni rilevanti per il progetto Thoth in ambito UNI ed è rilasciato solo nel repository UNI

### 1.1 Prerequisiti 

#### 1.1.1 Repository UNI da cui clonare i progetti
I sorgenti delle applicazioni, che sono rilasciate con licenza MIT, sono disponibili su GIT agli indirizzi https://gitlab.uni.com:tylconsulting/Thoth.git e https://gitlab.uni.com:tylconsulting/ThothSL.git


## 2. Architettura del Sistema

Oltre al database california_schools c'è a disposizione un database tratto da Iside e realizzato appositamente per sperimentazioni in ambiente UNI

#### 2.2.1 Database Staging
- Schema: `uniprj_staging`
- Derivato da Iside con ETL custom e ottimizzato per AI tramite renaming dei campi ed eliminazione dei record cancellati 
- [Download backup del database](https://drive.google.com/file/d/1CORpfBs9elktO6D3K3N_N3NDt2Aiwmyz/view?usp=sharing)

### Configurazione del SqlDb di staging
Per il database staging la configurazione deve essere:
  - **Name:** staging
  - **Db host:** thoth-db
  - **Db type:** PostgreSQL
  - **DB name:** staging
  - **DB port:** 5432
  - **Schema:** uniprj_staging
  - **User name:** thoth-user
  - **Password:** thoth-password
  - **Db model:** dev
  - **Vector db:** staging - Qdrant (o altro nome se non usato il nome staging nel vectordb)
  - **Language:** Italian

### Configurazione del SqlDb unicum
P er il database unicum la configurazione deve essere:
  - **Name:** unicum
  - **Db host:** cetus-test.uni.com
  - **Db type:** PostgreSQL
  - **DB name:** unicum
  - **DB port:** 5432
  - **Schema:** tier1
  - **User name:** username dell'utente con cui accedere a unicum
  - **Password:** password associata allo username
  - **Db model:** dev
  - **Vector db:** Tier1 - Qdrant
  - **Language:** Lingua in cui sono espresse le descrizioni e in cui si vogliono generare i commenti
