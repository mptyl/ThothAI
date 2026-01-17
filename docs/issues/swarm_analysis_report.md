# ThothAI Docker Swarm Configuration Analysis Report

**Data**: 12 Gennaio 2026  
**Richiesta**: Analisi dei difetti di configurazione dello Swarm stack in ThothAI

---

## 1. Riepilogo Esecutivo

L'analisi del codice ThothAI ha identificato **4 difetti principali** nella configurazione dello Swarm stack che spiegano i fallimenti documentati in [swarm-report.md](file:///Users/mp/ThothAI/docs/installation/swarm-report.md). I problemi riguardano principalmente la **gestione dei volumi**, **i vincoli di placement** e i **timeout degli health check**.

### Tabella Riepilogativa Difetti

| # | Difetto | File Coinvolto | Impatto | Severità |
|:--:|---------|----------------|---------|:--------:|
| 1 | Volumi locali in cluster multi-nodo | [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) | Servizi bloccati | 🔴 CRITICO |
| 2 | Placement constraints inconsistenti | [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) | Distribuzione errata | 🟠 ALTO |
| 3 | Health check start_period eccessivo | [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) | Ritardi diagnostica | 🟡 MEDIO |
| 4 | Mismatch nomi volumi | [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh) / [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) | Volumi non condivisi | 🟠 ALTO |

---

## 2. Analisi Dettagliata dei Difetti

### 2.1 Difetto Critico: Volumi con Driver `local`

**File**: [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) (righe 283-301)

```yaml
volumes:
  backend-static:
    driver: local
  thoth-backend-db:
    driver: local
  thoth-backend-secrets:
    driver: local
  thoth-shared-data:
    driver: local
  # ... tutti con driver: local
```

**Problema**: In Docker Swarm, i volumi con driver `local` sono confinati al singolo nodo fisico dove vengono creati. Quando i servizi vengono distribuiti su nodi diversi:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SCENARIO IN PRODUZIONE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   NODO m1                  NODO m2                  NODO m3          │
│   ┌──────────┐             ┌──────────┐             ┌──────────┐    │
│   │ backend  │             │ frontend │             │ proxy    │    │
│   │ (writes  │             │ (waits   │             │ (waits   │    │
│   │ secrets) │             │ secrets) │             │ static)  │    │
│   └────┬─────┘             └────┬─────┘             └────┬─────┘    │
│        │                        │                        │          │
│        ▼                        ▼                        ▼          │
│   ┌──────────┐             ┌──────────┐             ┌──────────┐    │
│   │ volume   │      ✗      │ volume   │      ✗      │ volume   │    │
│   │ (local)  │◄──────────► │ (EMPTY)  │◄──────────► │ (EMPTY)  │    │
│   └──────────┘ NESSUNA     └──────────┘ NESSUNA     └──────────┘    │
│                REPLICA                  REPLICA                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Conseguenza**: 
- Il `backend` su m1 genera i secrets in `/vol/secrets`
- Il `frontend` su m2 non trova i file e resta in loop "Secrets not ready yet"
- Docker interpreta il blocco come unhealthy e invia SIGKILL (exit 137)

**Correlazione con il report**:
> "Ipotesi 1: Volumi Locali in Cluster Multi-Nodo (Causa Principale)"  
> Lo stack utilizza driver `local` per i volumi [...] Il `frontend` su `m2` non può vedere i file di configurazione inizializzati dal `backend` su `m1`

---

### 2.2 Difetto: Placement Constraints Inconsistenti

**File**: [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml)

| Servizio | Placement Constraint | Riga |
|----------|---------------------|:----:|
| backend | `node.role == manager` | 52 |
| sql-generator | `node.role == manager` | 161 |
| thoth-qdrant | `node.role == manager` | 270 |
| **frontend** | ❌ NESSUNO | - |
| **proxy** | ❌ NESSUNO | - |
| **mermaid-service** | ❌ NESSUNO | - |

**Problema**: Solo 3 servizi su 6 hanno vincoli di placement. I servizi senza vincoli possono essere schedulati su qualsiasi nodo worker, con conseguente problema di accesso ai volumi condivisi.

**Esempio dal docker-stack.yml**:

```yaml
# Backend (riga 52) - HA constraint
deploy:
  placement:
    constraints:
      - node.role == manager

# Frontend (riga 104) - NON ha constraint!
deploy:
  replicas: 1
  restart_policy:
    condition: on-failure
  # MANCA: placement constraints!
```

**Conseguenza**: In un cluster con più nodi, il frontend può essere schedulato su un nodo diverso dal backend, rendendo impossibile la lettura dei volumi `thoth-backend-secrets`.

---

### 2.3 Difetto: Health Check con start_period Eccessivo

**File**: [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) (riga 43)

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/admin/login/"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 1200s  # ← 20 MINUTI!
```

**Problema**: Con uno `start_period` di 20 minuti, Docker non segnala problemi per i primi 20 minuti di vita del container, anche se il servizio non risponde. Questo:
1. Ritarda l'identificazione dei problemi
2. Maschera errori di startup che potrebbero essere diagnosticati prima
3. Consuma risorse per container che non partiranno mai

> [!WARNING]
> Un `start_period` così lungo è stato probabilmente introdotto per compensare tempi di migrazione database lunghi, ma nasconde i veri problemi di configurazione.

---

### 2.4 Difetto: Mismatch nei Nomi dei Volumi

**Confronto tra i file**:

| Nome in [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh) (riga 241) | Nome in [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) |
|--------------------------------------|----------------------------|
| `thoth-secrets` | `thoth-backend-secrets` ❌ |
| `thoth-backend-static` | `backend-static` ❌ |
| `thoth-backend-media` | `backend-media` ❌ |
| `thoth-frontend-cache` | `frontend-cache` ❌ |
| `thoth-qdrant-data` | `qdrant-data` ❌ |

**Codice problematico in install-swarm.sh** (righe 240-247):
```bash
local volumes=(
  "thoth-secrets"           # ← docker-stack.yml usa "thoth-backend-secrets"
  "thoth-backend-static"    # ← docker-stack.yml usa "backend-static"
  "thoth-backend-media"     # ← docker-stack.yml usa "backend-media"
  "thoth-frontend-cache"    # ← docker-stack.yml usa "frontend-cache"
  "thoth-qdrant-data"       # ← docker-stack.yml usa "qdrant-data"
  "thoth-shared-data"       # ✓ OK
  "thoth-data-exchange"     # ✓ OK
)
```

**Conseguenza**: Lo script pre-crea volumi con nomi diversi da quelli attesi dallo stack, quindi Docker Swarm crea NUOVI volumi vuoti durante il deploy.

---

## 3. Analisi del File push.sh

**File**: [push.sh](file:///Users/mp/ThothAI/push.sh)

Lo script [push.sh](file:///Users/mp/ThothAI/push.sh) è stato analizzato e **non presenta difetti** relativi alla configurazione Swarm. Funziona correttamente per:

- ✅ Build multi-architettura (amd64 + arm64)
- ✅ Push su Docker Hub/registry privato
- ✅ Gestione corretta del builder buildx
- ✅ Tag con versione e `latest`

> [!NOTE]
> I difetti identificati sono tutti nella **configurazione di deploy** ([docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml), [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh)), non nello script di build.

---

## 4. Raccomandazioni di Correzione

### 4.1 Correzione Critica: Storage Condiviso

**Opzione A - NFS Driver** (consigliata per produzione):
```yaml
volumes:
  thoth-shared-data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=${NFS_SERVER},rw
      device: ":/exports/thothai/shared-data"
```

**Opzione B - Placement Constraint Unico** (workaround rapido):
```yaml
# Aggiungere a TUTTI i servizi:
deploy:
  placement:
    constraints:
      - node.hostname == docker-prod-m1
```

### 4.2 Correzione: Allineare Nomi Volumi

Modificare [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh) per usare gli stessi nomi di [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml):
```bash
local volumes=(
  "thoth-backend-secrets"
  "backend-static"
  "backend-media"
  "frontend-cache"
  "qdrant-data"
  "thoth-shared-data"
  "thoth-data-exchange"
)
```

### 4.3 Correzione: Health Check

Ridurre `start_period` e aggiungere health check a tutti i servizi:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/admin/login/"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 120s  # 2 minuti invece di 20
```

---

## 5. File Analizzati

| File | Cosa definisce |
|------|----------------|
| [swarm-report.md](file:///Users/mp/ThothAI/docs/installation/swarm-report.md) | Report del tentativo di installazione |
| [push.sh](file:///Users/mp/ThothAI/push.sh) | Script di build e push immagini |
| [docker-stack.yml](file:///Users/mp/ThothAI/docker-stack.yml) | Configurazione Swarm stack |
| [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh) | Script di deploy Swarm |
| [swarm_config.env.template](file:///Users/mp/ThothAI/swarm_config.env.template) | Template variabili Swarm |
| [docker_swarm_image_analysis.md](file:///Users/mp/ThothAI/docs/issues/docker_swarm_image_analysis.md) | Analisi precedente su problemi immagini |

---

## 6. Conclusioni

Il fallimento documentato nel report è causato da una **combinazione di difetti architetturali**:

1. **Causa primaria**: I volumi `local` non sono condivisibili tra nodi in un cluster Swarm multi-nodo
2. **Causa aggravante**: I placement constraints inconsistenti permettono la distribuzione dei servizi su nodi diversi
3. **Causa secondaria**: Lo script [install-swarm.sh](file:///Users/mp/ThothAI/install-swarm.sh) pre-crea volumi con nomi diversi da quelli usati nello stack
4. **Effetto collaterale**: Gli health check con timeout lungo mascherano il problema per 20 minuti

> [!IMPORTANT]
> Il successo nel cluster di test è stato "accidentale" perché lo scheduler ha posizionato la maggior parte dei servizi sullo stesso nodo (`docker-test-m2`). In produzione, con più carico distribuito, lo scheduler ha distribuito i servizi su più nodi, esponendo il difetto.

Lo script [push.sh](file:///Users/mp/ThothAI/push.sh) è corretto e non richiede modifiche.

---

*Report generato da analisi del codebase ThothAI*
