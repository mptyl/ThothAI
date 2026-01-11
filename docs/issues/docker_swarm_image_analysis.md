# Analisi Problema "No such image" su Docker Swarm

**Data**: 11 Gennaio 2026  
**Progetto**: ThothAI  
**Problema**: Durante il deploy su Docker Swarm remoto (Linux Intel), 4 immagini custom falliscono con "No such image", mentre Mermaid e Qdrant vengono scaricate correttamente.

---

## 1. Riepilogo Esecutivo

L'analisi ha escluso problemi di architettura hardware (MacBook ARM vs Linux Intel). Tutte le immagini Docker sono correttamente multi-architettura. La causa più probabile è la **mancata propagazione della variabile `DOCKER_USERNAME`** sul nodo Swarm remoto durante il deploy.

---

## 2. Verifica Architettura Immagini

Ho verificato i manifest di tutte le immagini su Docker Hub. Tutte supportano correttamente entrambe le architetture:

| Immagine | linux/amd64 | linux/arm64 | Stato |
|----------|:-----------:|:-----------:|:-----:|
| `tylconsulting/thoth-backend:latest` | ✅ | ✅ | OK |
| `tylconsulting/thoth-frontend:latest` | ✅ | ✅ | OK |
| `tylconsulting/thoth-proxy:latest` | ✅ | ✅ | OK |
| `tylconsulting/thoth-sql-generator:latest` | ✅ | ✅ | OK |
| `tylconsulting/thoth-mermaid-service:latest` | ✅ | ✅ | OK |
| `qdrant/qdrant:latest` | ✅ | ✅ | OK |

### Esempio output manifest (thoth-backend):
```json
{
   "manifests": [
      {
         "platform": { "architecture": "amd64", "os": "linux" }
      },
      {
         "platform": { "architecture": "arm64", "os": "linux" }
      }
   ]
}
```

> [!IMPORTANT]
> **Conclusione**: Il problema NON è causato da incompatibilità di architettura hardware.

---

## 3. Analisi del Flusso di Deploy

### 3.1 Script `push.sh`

Lo script [push.sh](file:///Users/mp/ThothAI/push.sh) costruisce correttamente le immagini multi-architettura:

```bash
PLATFORMS="linux/amd64,linux/arm64"

docker buildx build $NO_CACHE \
    --platform "$PLATFORMS" \
    -f "$dockerfile" \
    -t "$REGISTRY_URL/thoth-$image_name:$VERSION" \
    --push \
    "$context"
```

### 3.2 File docker-stack.yml

Ho identificato una **differenza critica** tra i file di deploy:

#### docker-stack.yml (usato per Swarm)
```yaml
# Riga 13
image: ${DOCKER_USERNAME}/thoth-backend:${VERSION:-latest}
```
⚠️ **Nessun valore di default per DOCKER_USERNAME**

#### docker-compose-hub.yml (usato per Docker Compose)
```yaml
# Riga 4  
image: ${DOCKER_USERNAME:-tylconsulting}/thoth-backend:${VERSION:-latest}
```
✅ **Ha il valore di default `tylconsulting`**

### 3.3 Comportamento delle immagini

| Immagine | Definizione | Dipende da variabile |
|----------|-------------|:--------------------:|
| thoth-backend | `${DOCKER_USERNAME}/thoth-backend:...` | ✅ Sì |
| thoth-frontend | `${DOCKER_USERNAME}/thoth-frontend:...` | ✅ Sì |
| thoth-proxy | `${DOCKER_USERNAME}/thoth-proxy:...` | ✅ Sì |
| thoth-sql-generator | `${DOCKER_USERNAME}/thoth-sql-generator:...` | ✅ Sì |
| thoth-mermaid-service | `${DOCKER_USERNAME}/thoth-mermaid-service:...` | ✅ Sì |
| qdrant | `qdrant/qdrant:latest` | ❌ No (hardcoded) |

> [!WARNING]
> La tabella sopra suggerisce che **anche Mermaid** dovrebbe fallire se il problema fosse la variabile. Tuttavia, potrebbero esserci differenze nel timing o nell'ordine di deploy che causano comportamenti diversi.

---

## 4. Ipotesi Diagnostiche

### Ipotesi 1: Variabile DOCKER_USERNAME non propagata (PRIORITÀ ALTA)

**Meccanismo**: Quando la CLI esegue il deploy via SSH/Docker Context, le variabili d'ambiente potrebbero non essere correttamente trasferite al nodo remoto.

**Conseguenza**: L'immagine viene risolta come:
```
/thoth-backend:latest  ← ERRORE: manca il registry prefix
```

**Evidenza**: Il file `docker-stack.yml` non ha valori di default, mentre `docker-compose-hub.yml` li ha.

### Ipotesi 2: Differenza tra CLI e script shell (PRIORITÀ MEDIA)

Lo script [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh) usa `envsubst` per sostituire le variabili **prima** del deploy:

```bash
envsubst < docker-stack.yml > docker-stack-swarm.yml
docker stack deploy -c docker-stack-swarm.yml "$STACK_NAME"
```

La CLI Python usa `_replace_env_vars()` che potrebbe non gestire tutti i casi edge.

### Ipotesi 3: Timing/Cache Docker (PRIORITÀ BASSA)

Il nodo Swarm potrebbe avere immagini cached parziali o manifest corrotti che causano comportamenti inconsistenti.

### Ipotesi 4: File stack diverso (PRIORITÀ BASSA)

Esistono due file `docker-stack.yml`:
- [/Users/mp/ThothAI/docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml)
- [/Users/mp/ThothAI/cli/thothai-cli/src/thothai_cli/templates/docker-stack.yml](file:///Users/mp/ThothAI/cli/thothai-cli/src/thothai_cli/templates/docker-stack.yml)

La CLI potrebbe utilizzare un file diverso da quello previsto.

---

## 5. Procedure Diagnostiche

### 5.1 Verificare il nome immagine effettivo (sul server remoto)

```bash
# Dopo un deploy fallito, verificare come Docker ha interpretato il nome immagine
docker service inspect thothai-swarm_backend --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
```

**Risultato atteso se la variabile manca**:
```
/thoth-backend:latest
```

**Risultato corretto**:
```
tylconsulting/thoth-backend:latest
```

### 5.2 Verificare il file swarm_config.env sul server

```bash
ssh user@server "cat /opt/thothai/swarm_config.env | grep DOCKER_USERNAME"
```

### 5.3 Verificare lo stato dei servizi

```bash
docker service ls --filter "label=com.docker.stack.namespace=thothai-swarm"
docker service ps thothai-swarm_backend --no-trunc
```

### 5.4 Test di pull manuale

```bash
# Sul server remoto
docker pull tylconsulting/thoth-backend:latest
docker pull tylconsulting/thoth-frontend:latest
docker pull tylconsulting/thoth-proxy:latest
docker pull tylconsulting/thoth-sql-generator:latest
```

Se il pull manuale funziona, conferma che il problema è nella risoluzione del nome durante il deploy.

---

## 6. Soluzione Applicata

> [!NOTE]
> **La Soluzione A è già stata applicata** nella versione **1.3.8** della CLI `thothai-cli`.

### Modifiche effettuate

Sono stati modificati i seguenti file aggiungendo il valore di default `:-tylconsulting` a tutte le definizioni delle immagini:

- [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) (root del progetto)
- [cli/thothai-cli/src/thothai_cli/templates/docker-stack.yml](file:///Users/mp/ThothAI/cli/thothai-cli/src/thothai_cli/templates/docker-stack.yml) (template CLI)

**Esempio della modifica:**
```diff
# Prima (problematico)
- image: ${DOCKER_USERNAME}/thoth-backend:${VERSION:-latest}

# Dopo (corretto)
+ image: ${DOCKER_USERNAME:-tylconsulting}/thoth-backend:${VERSION:-latest}
```

La modifica è stata applicata a tutte e 5 le immagini custom:
- `thoth-backend`
- `thoth-frontend`
- `thoth-sql-generator`
- `thoth-proxy`
- `thoth-mermaid-service`

---

## 7. Istruzioni per l'Utente

Per applicare la correzione su un'installazione esistente, seguire questi passaggi:

### 7.1 Aggiornare la CLI

```bash
# Sul server o sulla macchina locale dove è installata la CLI
uv pip install thothai-cli --upgrade

# Oppure con pip
pip install thothai-cli --upgrade
```

Verificare che la versione sia almeno **1.3.8**:
```bash
thothai --version
```

### 7.2 Aggiornare il file docker-stack.yml

> [!IMPORTANT]
> Il comando `thothai init` **NON sovrascrive** i file esistenti per proteggere le configurazioni personalizzate. È necessario **cancellare manualmente** il vecchio `docker-stack.yml` prima di rigenerarlo.

```bash
# Spostarsi nella directory di installazione ThothAI
cd /path/to/thothai-installation

# Cancellare il vecchio docker-stack.yml
rm docker-stack.yml

# Rigenerare i file con la nuova versione
thothai init --mode swarm
```

### 7.3 Eseguire il deploy

```bash
# Deploy locale
thothai swarm deploy

# Oppure deploy remoto
thothai swarm deploy --server ssh://user@hostname
```

---

## 8. Verifiche in Caso di Problemi Persistenti

Se dopo aver applicato la soluzione il problema persiste, eseguire le seguenti verifiche diagnostiche:

### 8.1 Verificare il nome immagine effettivo

Dopo un deploy fallito, controllare come Docker ha interpretato il nome dell'immagine:

```bash
docker service inspect thothai-swarm_backend --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
```

**Risultato atteso (corretto)**:
```
tylconsulting/thoth-backend:latest
```

**Risultato errato** (indica che la variabile non è stata sostituita):
```
/thoth-backend:latest
```

### 8.2 Verificare la configurazione swarm_config.env

```bash
cat swarm_config.env | grep DOCKER_USERNAME
```

Deve mostrare:
```
DOCKER_USERNAME=tylconsulting
```

### 8.3 Verificare lo stato dei servizi

```bash
docker service ls --filter "label=com.docker.stack.namespace=thothai-swarm"
docker service ps thothai-swarm_backend --no-trunc
```

### 8.4 Test di pull manuale

Verificare che le immagini siano effettivamente scaricabili sul server remoto:

```bash
docker pull tylconsulting/thoth-backend:latest
docker pull tylconsulting/thoth-frontend:latest
docker pull tylconsulting/thoth-proxy:latest
docker pull tylconsulting/thoth-sql-generator:latest
docker pull tylconsulting/thoth-mermaid-service:latest
```

Se il pull manuale funziona ma il deploy no, il problema è nella risoluzione delle variabili durante il deploy.

### 8.5 Verificare il contenuto del docker-stack.yml generato

Controllare che il file contenga effettivamente i valori di default:

```bash
grep "DOCKER_USERNAME" docker-stack.yml
```

Deve mostrare righe come:
```yaml
image: ${DOCKER_USERNAME:-tylconsulting}/thoth-backend:${VERSION:-latest}
```

Se invece mostra:
```yaml
image: ${DOCKER_USERNAME}/thoth-backend:${VERSION:-latest}
```

Significa che il file non è stato aggiornato correttamente. Ripetere la procedura della sezione 7.2.

---

## 9. Soluzioni Alternative (se la Soluzione A non funziona)

### Soluzione B: Forzare DOCKER_USERNAME nella CLI

Modificare [docker_manager.py](file:///Users/mp/ThothAI/cli/thothai-cli/src/thothai_cli/core/docker_manager.py) nella funzione `swarm_up()` (circa riga 1631):

```python
swarm_env = self._get_swarm_env()
# Aggiungere questa riga:
swarm_env['DOCKER_USERNAME'] = swarm_env.get('DOCKER_USERNAME', 'tylconsulting')
stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
```

### Soluzione C: Usare envsubst nella CLI

Modificare la CLI per eseguire esplicitamente `envsubst` sul file stack prima del deploy, allineandola al comportamento dello script shell `install-swarm.sh`.

---

## 10. File Analizzati

- [push.sh](file:///Users/mp/ThothAI/push.sh) - Script build/push immagini
- [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) - Configurazione Swarm
- [docker-compose-hub.yml](file:///Users/mp/ThothAI/docker-compose-hub.yml) - Configurazione Compose Hub
- [swarm_config.env](file:///Users/mp/ThothAI/swarm_config.env) - Variabili Swarm
- [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh) - Script deploy Swarm
- [docker_manager.py](file:///Users/mp/ThothAI/cli/thothai-cli/src/thothai_cli/core/docker_manager.py) - CLI Docker Manager
- [swarm.py](file:///Users/mp/ThothAI/cli/thothai-cli/src/thothai_cli/commands/swarm.py) - Comandi CLI Swarm
- [init.py](file:///Users/mp/ThothAI/cli/thothai-cli/src/thothai_cli/commands/init.py) - Comando init CLI

---

**Stato**: ✅ Soluzione A applicata in CLI v1.3.8  
**Data aggiornamento**: 11 Gennaio 2026

*Documento generato automaticamente dall'analisi del codebase ThothAI*

