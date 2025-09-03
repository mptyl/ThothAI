# Istruzioni per Utenti Windows - ThothAI

## Configurazione Git per Windows

### Prima di clonare il repository

Configura Git per gestire correttamente le terminazioni di riga:

```bash
# IMPORTANTE: Esegui questo comando PRIMA di clonare
git config --global core.autocrlf true
```

Questo comando:
- Converte automaticamente LF → CRLF quando scarichi i file (per compatibilità Windows)
- Converte automaticamente CRLF → LF quando fai commit (per mantenere LF nel repository)

### Clone del repository

```bash
git clone https://github.com/mptyl/ThothAI.git
cd ThothAI
```

## Preparazione per Docker

Docker su Windows usa container Linux che richiedono terminazioni di riga Unix (LF). 
Anche se hai configurato `core.autocrlf true`, gli script nei container devono avere LF.

### Metodo 1: PowerShell + WSL (Raccomandato)

1. **Prepara l'ambiente con PowerShell:**
   ```powershell
   .\scripts\prepare-docker-env.ps1
   ```

2. **Correggi le terminazioni di riga in WSL o Git Bash:**
   ```bash
   # Apri WSL o Git Bash
   ./scripts/prepare-docker-build.sh
   ```

3. **Avvia Docker:**
   ```powershell
   docker-compose up --build
   ```

### Metodo 2: Solo WSL

Se preferisci lavorare completamente in WSL:

```bash
# In WSL
cd ~/ThothAI

# Prepara l'ambiente
./scripts/prepare-docker-build.sh

# Avvia Docker
docker-compose up --build
```

## Quando eseguire la correzione delle terminazioni

Devi eseguire `prepare-docker-build.sh` **SEMPRE**:

1. ✅ Dopo il primo clone del repository
2. ✅ Dopo ogni `git pull` che aggiorna script shell
3. ✅ Prima di ogni `docker-compose build`
4. ✅ Se vedi errori come:
   - `/bin/bash^M: bad interpreter`
   - `No such file or directory` per file che esistono
   - Script che si bloccano all'avvio dei container

## Troubleshooting

### Errore: "No such file or directory"

**Causa**: Script con terminazioni Windows (CRLF) invece di Unix (LF)

**Soluzione**:
```bash
# In WSL o Git Bash
./scripts/fix-line-endings.sh
docker-compose build --no-cache
docker-compose up
```

### Errore: Container bloccati all'avvio

**Causa**: Entrypoint scripts con CRLF

**Soluzione**:
```bash
# In WSL o Git Bash
./scripts/prepare-docker-build.sh
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Come verificare le terminazioni di riga

In Git Bash o WSL:
```bash
# Verifica un file specifico
file backend/entrypoint-backend.sh

# Output corretto: "... ASCII text"
# Output problematico: "... ASCII text, with CRLF line terminators"
```

## Best Practices

1. **Configura Git PRIMA di clonare:**
   ```bash
   git config --global core.autocrlf true
   ```

2. **Usa sempre WSL o Git Bash per script shell:**
   - Non eseguire script .sh da PowerShell o CMD
   - PowerShell può interpretare male le terminazioni di riga

3. **Workflow consigliato per ogni sessione di sviluppo:**
   ```powershell
   # 1. In PowerShell - Pull degli aggiornamenti
   git pull
   
   # 2. In PowerShell - Prepara ambiente
   .\scripts\prepare-docker-env.ps1
   ```
   
   ```bash
   # 3. In WSL/Git Bash - Correggi terminazioni
   ./scripts/prepare-docker-build.sh
   ```
   
   ```powershell
   # 4. In PowerShell - Avvia Docker
   docker-compose up --build
   ```

4. **Per sviluppo locale (senza Docker):**
   - I file Python e JavaScript funzionano con CRLF su Windows
   - Solo gli script shell richiedono LF

## Note Importanti

- **Il repository mantiene sempre LF**: Tutti i file nel repository GitHub hanno terminazioni Unix
- **Windows può usare CRLF localmente**: Per i file Python/JS/HTML va bene
- **Docker richiede sempre LF**: Gli script shell nei container Linux devono avere LF
- **La conversione è automatica**: Con `core.autocrlf true` Git gestisce tutto automaticamente
- **prepare-docker-build.sh è essenziale**: Garantisce che Docker funzioni correttamente

## Supporto

Se hai problemi con le terminazioni di riga:

1. Verifica la configurazione Git:
   ```bash
   git config --get core.autocrlf
   # Dovrebbe mostrare: true
   ```

2. Esegui la correzione completa:
   ```bash
   # In WSL o Git Bash
   ./scripts/prepare-docker-build.sh
   ```

3. Ricostruisci i container:
   ```powershell
   docker-compose down
   docker-compose build --no-cache
   docker-compose up
   ```

Per assistenza aggiuntiva, consulta la documentazione completa in `docs/WINDOWS_INSTALLATION.md`