# Guida Configurazione Database IBM Informix

**ThothAI - Supporto Database Informix**  
**Versione:** 1.0  
**Data:** 2025-10-05

---

## Panoramica

ThothAI supporta database IBM Informix tramite connessione SSH + dbaccess. Questa guida spiega come configurare un database Informix in ThothAI.

### Requisiti

#### Sul Server Remoto (Informix)
- ✅ IBM Informix installato e funzionante
- ✅ `dbaccess` disponibile in `$INFORMIXDIR/bin/`
- ✅ Server SSH configurato e accessibile
- ✅ Credenziali database Informix valide

#### Sul Client (ThothAI)
- ✅ ThothAI con `thoth-dbmanager >= 0.7.0`
- ✅ Chiave SSH privata o password per autenticazione SSH
- ✅ Accesso all'admin Django di ThothAI

---

## Configurazione Passo-Passo

### Passo 1: Accedere all'Admin ThothAI

1. Aprire il browser all'indirizzo dell'admin Django:
   - **Locale:** `http://localhost:8200/admin`
   - **Docker:** `http://localhost:8040/admin`

2. Effettuare il login con credenziali admin

3. Navigare a: **Thoth Core → Sql dbs → Add Sql db**

### Passo 2: Basic Information

Compilare la sezione "Basic Information":

| Campo | Valore | Descrizione |
|-------|--------|-------------|
| **Name** | `Production Informix` | Nome identificativo in ThothAI (richiesto) |
| **Db type** | `Informix` | Selezionare dalla dropdown |
| **Db mode** | `prod` / `dev` / `test` | Modalità ambiente |

### Passo 3: Connection Details

Compilare i dettagli di connessione al database Informix:

| Campo | Valore Esempio | Descrizione |
|-------|----------------|-------------|
| **Db host** | `informix-prod.company.com` | Hostname o IP del server Informix |
| **Db port** | `9088` | Porta Informix (default: 9088) |
| **Db name** | `production_db` | Nome del database Informix |
| **Schema** | *(lasciare vuoto)* | Informix non usa schema separato |

### Passo 4: SSH Tunnel ⚠️ OBBLIGATORIO

**IMPORTANTE:** Informix in ThothAI richiede sempre un tunnel SSH.

#### 4.1 Parametri Base SSH

| Campo | Valore | Descrizione |
|-------|--------|-------------|
| **SSH enabled** | ✅ | **DEVE essere abilitato** |
| **SSH host** | `bastion.company.com` | Server SSH (può essere lo stesso del DB) |
| **SSH port** | `22` | Porta SSH (default: 22) |
| **SSH username** | `sshuser` | Username per autenticazione SSH |

#### 4.2 Autenticazione SSH

**Metodo A: Private Key (Raccomandato)**

1. Impostare:
   - **SSH auth method:** `Private key`

2. **Opzione 1 - Upload Chiave:**
   - Cliccare su "SSH private key file (upload)"
   - Selezionare il file della chiave (es: `id_rsa`)
   - Se la chiave è protetta, inserire **SSH private key passphrase**

3. **Opzione 2 - Path Esistente:**
   - Inserire path assoluto in **SSH private key path** (es: `/home/user/.ssh/id_rsa`)
   - Se la chiave è protetta, inserire **SSH private key passphrase**

**Metodo B: Password**

1. Impostare:
   - **SSH auth method:** `Password`
   - **SSH password:** *(password SSH dell'utente)*

#### 4.3 Parametri SSH Avanzati (Opzionali)

Espandere la sezione "SSH Tunnel" per parametri avanzati:

| Campo | Default | Quando Modificare |
|-------|---------|-------------------|
| SSH local bind host | `127.0.0.1` | Raramente necessario |
| SSH local bind port | *(automatico)* | Solo se servono porte specifiche |
| SSH known_hosts path | *(vuoto)* | Per validazione strict host key |
| SSH strict host key check | ✅ | Disabilitare solo per test |
| SSH connect timeout | `30` sec | Aumentare per connessioni lente |
| SSH keepalive interval | `30` sec | Per mantenere tunnel attivo |
| SSH compression | ❌ | Abilitare su connessioni lente |

### Passo 5: Authentication

Credenziali del database Informix:

| Campo | Valore | Descrizione |
|-------|--------|-------------|
| **User name** | `informix` | Username database Informix |
| **Password** | `********` | Password database Informix |

### Passo 6: Informix Configuration

Parametri specifici di Informix:

| Campo | Valore Esempio | Descrizione |
|-------|----------------|-------------|
| **Informix server** | `ns1i10` | Nome INFORMIXSERVER (valore variabile `$INFORMIXSERVER`) |
| **Informix protocol** | `onsoctcp` | Protocollo connessione (default: onsoctcp) |
| **Informix dir** | `/u/appl/ids10` | Path INFORMIXDIR sul server remoto |

**Come trovare questi valori sul server Informix:**

```bash
# Connessione SSH al server
ssh sshuser@informix-prod.company.com

# Verificare INFORMIXSERVER
echo $INFORMIXSERVER
# Output: ns1i10

# Verificare INFORMIXDIR
echo $INFORMIXDIR
# Output: /u/appl/ids10

# Verificare dbaccess funzionante
$INFORMIXDIR/bin/dbaccess --version
```

### Passo 7: Salvare e Testare

1. Cliccare **Save** in fondo alla pagina
2. Verificare che non ci siano errori di validazione
3. Tornare alla lista "Sql dbs"
4. Selezionare il database Informix appena creato
5. Dal menu "Actions" scegliere **Test connection**
6. Verificare messaggio di successo: ✅ *"Connection successful"*

---

## Operazioni Post-Configurazione

### Importare Metadata Database

Dopo aver configurato e testato la connessione:

1. Selezionare il database Informix dalla lista
2. Dal menu "Actions" scegliere:
   - **Create tables** - importa tabelle e colonne
   - **Create relationships** - importa foreign key
   - **Create db elements** - importa tutto (tabelle, FK, indici)

### Generare Documentazione AI

Per generare descrizioni automatiche con AI:

1. Selezionare il database
2. Actions → **Generate scope** - genera descrizione database
3. Actions → **Generate all comments** - genera commenti AI per tabelle/colonne
4. Actions → **Generate db erd** - genera diagramma ER in formato Mermaid

### Associare Vector Database

Per abilitare ricerca semantica:

1. Andare su **Thoth Core → Vector dbs → Add Vector db**
2. Creare un Vector DB (es: nome `Informix Production VectorDB`)
3. Tornare al SqlDb Informix
4. Modificare campo **Vector db** → selezionare il VectorDB creato
5. Salvare

---

## Esempio Configurazione Completa

### Scenario: Database Produzione con SSH Key

```yaml
# Basic Information
Name: Production ERP
Db type: Informix
Db mode: prod

# Connection Details
Db host: erp-db.mycompany.com
Db port: 9088
Db name: erp_prod
Schema: (vuoto)

# SSH Tunnel
SSH enabled: ✅
SSH host: bastion.mycompany.com
SSH port: 22
SSH username: dbadmin
SSH auth method: Private key
SSH private key path: /opt/thoth/keys/informix_key
SSH private key passphrase: (se protetta)
SSH strict host key check: ✅

# Authentication
User name: erp_user
Password: ********

# Informix Configuration
Informix server: erp_server_01
Informix protocol: onsoctcp
Informix dir: /opt/IBM/informix
```

### Scenario: Database Sviluppo con Password SSH

```yaml
# Basic Information
Name: Dev Informix
Db type: Informix
Db mode: dev

# Connection Details
Db host: localhost
Db port: 9088
Db name: dev_db
Schema: (vuoto)

# SSH Tunnel
SSH enabled: ✅
SSH host: localhost
SSH port: 22
SSH username: developer
SSH auth method: Password
SSH password: ********
SSH strict host key check: ❌ (per sviluppo locale)

# Authentication
User name: informix
Password: informix

# Informix Configuration
Informix server: dev_server
Informix protocol: onsoctcp
Informix dir: /u/appl/ids10
```

---

## Troubleshooting

### Errore: "SSH tunnel is required for Informix connections"

**Causa:** SSH non è abilitato  
**Soluzione:** 
- Verificare che il campo **SSH enabled** sia spuntato ✅
- Informix in ThothAI richiede sempre SSH tunnel

### Errore: "SSH connection failed"

**Possibili cause e soluzioni:**

1. **Host SSH non raggiungibile**
   ```bash
   # Testare connessione SSH manualmente
   ssh -p 22 sshuser@bastion.company.com
   ```

2. **Credenziali SSH errate**
   - Verificare username SSH
   - Se usa chiave: verificare path e permessi (`chmod 600 /path/to/key`)
   - Se usa password: verificare password corretta

3. **Chiave SSH protetta senza passphrase**
   - Se la chiave ha una passphrase, inserirla nel campo apposito

4. **Firewall blocca porta SSH**
   - Verificare che la porta SSH (default 22) sia aperta

### Errore: "dbaccess command not found"

**Causa:** `dbaccess` non è disponibile sul server remoto  
**Soluzione:**
```bash
# Connettersi al server via SSH
ssh sshuser@informix-server.com

# Verificare INFORMIXDIR
echo $INFORMIXDIR

# Testare dbaccess
$INFORMIXDIR/bin/dbaccess --version

# Se non funziona, verificare installazione Informix
ls -la /u/appl/ids10/bin/dbaccess
```

### Errore: "Query execution failed"

**Possibili cause:**

1. **INFORMIXSERVER errato**
   - Verificare valore in campo **Informix server**
   - Confrontare con `echo $INFORMIXSERVER` sul server

2. **Database non esistente**
   - Verificare che il database esista:
   ```bash
   echo "SELECT * FROM systables WHERE tabid = 1" | dbaccess production_db
   ```

3. **Permessi utente insufficienti**
   - Verificare che l'utente abbia accesso al database
   ```bash
   echo "SELECT USER FROM systables WHERE tabid = 1" | dbaccess production_db
   ```

### Errore: "Connection timeout"

**Causa:** SSH tunnel o database lento  
**Soluzione:**
- Aumentare **SSH connect timeout** (es: da 30 a 60 secondi)
- Verificare latenza rete con `ping informix-server.com`
- Abilitare **SSH compression** se la banda è limitata

### Debug Avanzato

Per diagnosticare problemi complessi:

1. **Verificare log Django:**
   ```bash
   # Locale
   tail -f backend/logs/django.log
   
   # Docker
   docker compose logs -f backend
   ```

2. **Testare connessione SSH manualmente:**
   ```bash
   ssh -v sshuser@bastion.company.com \
       "echo 'SELECT 1 FROM systables WHERE tabid = 1' | /u/appl/ids10/bin/dbaccess production_db"
   ```

3. **Verificare variabili ambiente Informix sul server:**
   ```bash
   ssh sshuser@informix-server.com env | grep INFORMIX
   ```

---

## Best Practices

### Sicurezza

1. **Sempre usare chiavi SSH invece di password**
   - Più sicuro e non scade
   - Gestione centralizzata delle chiavi

2. **Proteggere chiavi SSH con passphrase**
   - Secondo livello di sicurezza
   - ThothAI gestisce la passphrase in modo sicuro

3. **Abilitare strict host key check in produzione**
   - Previene attacchi man-in-the-middle
   - Configurare `known_hosts` appropriato

4. **Usare utenti database con privilegi minimi**
   - Solo SELECT per query read-only
   - Evitare utenti con privilegi DBA

### Performance

1. **Abilitare SSH compression per connessioni remote**
   - Riduce banda necessaria
   - Aumenta leggermente CPU usage

2. **Configurare SSH keepalive**
   - Previene timeout su query lunghe
   - Default 30 secondi è generalmente OK

3. **Usare schema/database dedicato per ThothAI**
   - Migliori performance su import metadata
   - Riduce scope delle query

### Manutenzione

1. **Rotazione chiavi SSH**
   - Upload nuova chiave via admin
   - Path viene aggiornato automaticamente

2. **Monitoraggio connessioni**
   - Usare "Test connection" periodicamente
   - Verificare log per errori intermittenti

3. **Backup configurazione**
   - Esportare SqlDb via azione "Export as CSV"
   - Include tutti i parametri (password escluse)

---

## FAQ

### Q: Posso usare Informix senza SSH?
**A:** No, l'implementazione attuale di ThothAI richiede sempre SSH tunnel per Informix. Questo garantisce compatibilità multi-piattaforma senza bisogno di driver ODBC locali.

### Q: Quali versioni di Informix sono supportate?
**A:** ThothAI usa `dbaccess` che è disponibile in tutte le versioni moderne di Informix (10.x, 11.x, 12.x, 14.x). Testato principalmente con Informix 11.70 e 12.10.

### Q: Posso connettermi a Informix in Docker?
**A:** Sì, ma il server SSH deve essere accessibile dal container ThothAI. Usare `host.docker.internal` per server su host locale, o hostname/IP per server remoti.

### Q: Il campo "schema" è obbligatorio?
**A:** No, lasciarlo vuoto. Informix usa il database come namespace, non ha il concetto di schema separato come PostgreSQL.

### Q: Come cambio la password del database?
**A:** Modificare il SqlDb nell'admin → cambiare campo **Password** → salvare. La password è criptata nel database Django.

### Q: Posso usare la stessa chiave SSH per più database?
**A:** Sì, se i database sono sullo stesso server o accessibili con le stesse credenziali SSH. Specificare lo stesso path alla chiave.

---

## Risorse Aggiuntive

### Documentazione Informix
- [IBM Informix Documentation](https://www.ibm.com/docs/en/informix-servers/)
- [Informix dbaccess Guide](https://www.ibm.com/docs/en/informix-servers/14.10?topic=reference-dbaccess-utility)

### ThothAI
- [README principale](../README.md)
- [Piano di integrazione Informix](../INFORMIX_INTEGRATION_PLAN.md)
- [Riepilogo implementazione](../INFORMIX_IMPLEMENTATION_SUMMARY.md)

### Supporto
Per problemi o domande:
1. Verificare questa guida e la sezione Troubleshooting
2. Controllare i log Django/SQL Generator
3. Aprire issue su GitHub repository ThothAI

---

**Versione documento:** 1.0  
**Ultimo aggiornamento:** 2025-10-05
