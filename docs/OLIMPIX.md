# Configurazione Database Olimpix - Informix

**Data configurazione:** 2025-10-05  
**Database:** olimpix (IBM Informix)  
**Ambiente:** Produzione

---

## Panoramica

Questo documento descrive la configurazione del database Informix `olimpix` in ThothAI, inclusi i parametri di connessione SSH e le specifiche Informix.

---

## Configurazione Completa

### Basic Information

| Campo | Valore | Note |
|-------|--------|------|
| **Name** | `olimpix` | Nome identificativo in ThothAI |
| **Db type** | `Informix` | Tipo database |
| **Db mode** | `prod` | Ambiente produzione |

### Connection Details

| Campo | Valore | Note |
|-------|--------|------|
| **Db host** | `192.168.1.100` | IP o hostname del server Informix |
| **Db port** | `9088` | Porta Informix (default) |
| **Db name** | `olimpix` | Nome del database Informix |
| **Schema** | *(vuoto)* | Informix non usa schema separato |

### SSH Tunnel Configuration

⚠️ **OBBLIGATORIO** - Informix in ThothAI richiede sempre tunnel SSH

| Campo | Valore | Note |
|-------|--------|------|
| **SSH enabled** | ✅ | DEVE essere abilitato |
| **SSH host** | `192.168.1.100` | Server SSH (stesso del DB host) |
| **SSH port** | `22` | Porta SSH standard |
| **SSH username** | `informixuser` | Username per autenticazione SSH |
| **SSH auth method** | `Private key` | Metodo di autenticazione |
| **SSH private key path** | `/home/user/.ssh/id_rsa` | Path alla chiave privata SSH |
| **SSH private key passphrase** | *(se protetta)* | Passphrase della chiave |
| **SSH strict host key check** | ✅ | Validazione host key |
| **SSH connect timeout** | `30` | Timeout connessione (secondi) |
| **SSH keepalive interval** | `30` | Intervallo keepalive (secondi) |

### Authentication (Database Credentials)

| Campo | Valore | Note |
|-------|--------|------|
| **User name** | `olimpix_user` | Username database Informix |
| **Password** | `********` | Password database Informix |

### Informix Configuration

⚠️ **PARAMETRI CRITICI** - Devono corrispondere alla configurazione del server remoto

| Campo | Valore | Note |
|-------|--------|------|
| **Informix server** | `ns1i10` | Nome INFORMIXSERVER (valore variabile `$INFORMIXSERVER`) |
| **Informix protocol** | `onsoctcp` | Protocollo connessione (default) |
| **Informix dir** | `/u/appl/ids10` | Path INFORMIXDIR sul server remoto |

---

## Come Trovare i Valori Informix

Per ottenere i valori corretti dei parametri Informix, connettersi via SSH al server e eseguire:

```bash
# Connessione SSH al server
ssh informixuser@192.168.1.100

# 1. Verificare INFORMIXSERVER
echo $INFORMIXSERVER
# Output atteso: ns1i10

# 2. Verificare INFORMIXDIR
echo $INFORMIXDIR
# Output atteso: /u/appl/ids10

# 3. Verificare configurazione sqlhosts
cat $INFORMIXDIR/etc/sqlhosts | grep -v "^#"
# Output esempio:
# ns1i10    onsoctcp    localhost    9088

# 4. Testare dbaccess
$INFORMIXDIR/bin/dbaccess olimpix - <<EOF
select count(*) from systables;
EOF
# Se funziona, la configurazione è corretta
```

---

## Formato YAML Configurazione

```yaml
# Basic Information
Name: olimpix
Db type: Informix
Db mode: prod

# Connection Details
Db host: 192.168.1.100
Db port: 9088
Db name: olimpix
Schema: (vuoto)

# SSH Tunnel
SSH enabled: ✅
SSH host: 192.168.1.100
SSH port: 22
SSH username: informixuser
SSH auth method: Private key
SSH private key path: /home/user/.ssh/id_rsa
SSH private key passphrase: (se protetta)
SSH strict host key check: ✅
SSH connect timeout: 30
SSH keepalive interval: 30

# Authentication
User name: olimpix_user
Password: ********

# Informix Configuration
Informix server: ns1i10
Informix protocol: onsoctcp
Informix dir: /u/appl/ids10
```

---

## Test di Connessione

### Dall'Admin Django

1. Accedere a: http://localhost:8200/admin/thoth_core/sqldb/
2. Selezionare il database `olimpix`
3. Dal menu "Actions" scegliere **Test connection**
4. Verificare messaggio: ✅ *"Connection successful"*

### Log Attesi

Quando la connessione funziona correttamente, nei log Django dovresti vedere:

```
INFO Database plugins module imported successfully
INFO Informix plugin manually enabled (workaround for thoth-dbmanager 0.7.0 bug)
INFO Available database plugins: postgresql, sqlite, informix
INFO Successfully created informix manager for olimpix
```

---

## Troubleshooting

### Errore: "INFORMIXSERVER value is not listed in sqlhosts"

**Causa:** Il valore in "Informix server" non corrisponde a quello nel file `sqlhosts` del server remoto.

**Soluzione:**
1. Connettersi via SSH al server Informix
2. Eseguire: `cat $INFORMIXDIR/etc/sqlhosts | grep -v "^#"`
3. Usare **esattamente** il nome della prima colonna come valore per "Informix server"

### Errore: "SSH connection failed"

**Causa:** Parametri SSH non corretti o server non raggiungibile.

**Soluzione:**
1. Verificare che il server SSH sia raggiungibile: `ping 192.168.1.100`
2. Testare connessione SSH manualmente: `ssh informixuser@192.168.1.100`
3. Verificare che la chiave privata abbia i permessi corretti: `chmod 600 /home/user/.ssh/id_rsa`
4. Se si usa password SSH, verificare che sia corretta

### Errore: "Database authentication failed"

**Causa:** Username o password del database Informix non corretti.

**Soluzione:**
1. Verificare le credenziali connettendosi manualmente via SSH:
   ```bash
   ssh informixuser@192.168.1.100
   dbaccess olimpix
   ```
2. Aggiornare username e password nell'admin Django

---

## Operazioni Post-Configurazione

### 1. Importare Metadata Database

Dopo aver configurato e testato la connessione:

1. Selezionare il database `olimpix` dalla lista
2. Dal menu "Actions" scegliere:
   - **Create tables** - importa tabelle e colonne
   - **Create relationships** - importa foreign key
   - **Create db elements** - importa tutto (consigliato)

### 2. Associare Vector Database

Per abilitare ricerca semantica:

1. Andare su **Thoth Core → Vector dbs → Add Vector db**
2. Creare un Vector DB (es: nome `Olimpix VectorDB`)
3. Tornare al SqlDb `olimpix`
4. Modificare campo **Vector db** → selezionare il VectorDB creato
5. Salvare

### 3. Generare Documentazione AI

Per generare descrizioni automatiche:

1. Selezionare il database `olimpix`
2. Actions → **Generate scope** - genera descrizione database
3. Actions → **Generate all comments** - genera commenti AI per tabelle/colonne
4. Actions → **Generate db erd** - genera diagramma ER in formato Mermaid

---

## Note Tecniche

### Approccio SSH + dbaccess

ThothAI usa `InformixSSHAdapter` di thoth-dbmanager che:
1. Apre tunnel SSH al server remoto
2. Esegue comandi `dbaccess` sul server via SSH
3. Parsa output testuale di dbaccess
4. **Zero driver ODBC locali richiesti** - solo `paramiko` (Python SSH)

### Workaround thoth-dbmanager 0.7.0

Il supporto Informix in ThothAI include un workaround temporaneo per un bug in thoth-dbmanager 0.7.0 dove il plugin Informix non è registrato in `DATABASE_DEPENDENCIES`. Il workaround è implementato in:
- `backend/thoth_core/utilities/utils.py` (funzione `initialize_database_plugins`)
- `backend/thoth_core/dbmanagement.py` (funzione `get_db_manager`)

Quando thoth-dbmanager 0.7.1+ sarà rilasciato con il fix, il workaround potrà essere rimosso.

### Riferimenti

- **Documentazione completa Informix:** `docs/INFORMIX_CONFIGURATION_GUIDE.md`
- **Dettagli implementazione:** `docs/INFORMIX_IMPLEMENTATION_SUMMARY.md`
- **Workaround bug 0.7.0:** `docs/INFORMIX_WORKAROUND_0.7.0.md`
- **Guida integrazione:** `docs/INFORMIX_INTEGRATION_COMPLETE.md`

---

## Changelog

- **2025-10-05:** Configurazione iniziale database olimpix
- **2025-10-05:** Applicato workaround thoth-dbmanager 0.7.0
- **2025-10-05:** Risolto errore INFORMIXSERVER con parametri corretti
