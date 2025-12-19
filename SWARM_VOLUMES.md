# Docker Swarm Volumes: Configurazione e Best Practices per Thoth

## Come Docker Swarm Gestisce i Volumi

### Differenze Fondamentali con Docker Compose

Docker Swarm gestisce i volumi in modo significativamente diverso rispetto a Docker Compose standard:

1. **Volumi per-node vs storage condiviso**: In Swarm un volume creato con il driver `local` vive sul singolo nodo. Per avere accesso multi-nodo serve un driver/una configurazione che punti a storage condiviso (es. NFS via `local`+`type=nfs`, Ceph, Portworx, Longhorn, etc.).
2. **Placement Constraints**: Con volumi per-node (driver `local`) o bind mounts, i servizi richiedono constraints/placement per garantire l'esecuzione sul nodo che possiede fisicamente i dati.
3. **Storage Drivers**: In Swarm puoi usare driver di volume (incluso `local` configurato per NFS) oppure plugin/CSI di terze parti per storage condiviso.
4. **Replica Management**: I volumi non vengono replicati automaticamente tra i nodi; la replica/HA è responsabilità dello storage sottostante.

### Tipi di Volumi in Swarm

1. **Local Volumes** (default):
   - Memorizzati sul filesystem del nodo specifico
   - Non accessibili da altri nodi
   - Adatti per dati temporanei o cache

2. **Bind Mounts**:
   - Legati a un path specifico del filesystem host
   - Funzionano in Swarm, ma sono intrinsecamente **per-node** (se il task viene schedulato su un nodo diverso, il path potrebbe non esistere o contenere dati diversi)
   - Utili per sviluppo e per host dedicati (con placement constraints), meno indicati per produzione multi-nodo

3. **Shared Storage Volumes**:
   - Richiedono driver specifici (NFS, Ceph, etc.)
   - Accessibili da tutti i nodi del cluster
   - Essenziali per dati persistenti in ambienti multi-nodo

## Analisi delle Configurazioni Attuali

### docker-stack.yml (Produzione Swarm)

**Volumi Configurati:**

- `thoth-backend-db`: Database SQLite del backend
- `thoth-shared-data`: Dati condivisi tra servizi
- `thoth-logs`: Log centralizzati
- `backend-static`/`backend-media`: File statici Django
- `frontend-cache`: Cache Next.js
- `qdrant-data`: Dati del vector database

**Problemi Identificati:**

1. Tutti i volumi usano driver `local` (non adatto per multi-nodo)
2. Mancano placement constraints per servizi con volumi condivisi
3. Nessuna strategia di backup per dati critici
4. Nessun storage condiviso per dati persistenti

### docker-stack-simple.yml (Sviluppo)

**Differenze Principali:**

- Usa bind mounts per `./data_exchange` e `./config.yml.local`
- Mancano i secrets e configs esterni
- Più adatto per sviluppo su singolo nodo
- Nessuna gestione della persistenza multi-nodo

### docker-compose.yml (Non-Swarm)

**Caratteristiche:**

- Usa volumi external con naming esplicito
- Include bind mounts per sviluppo
- Gestione singolo nodo con container names
- Non adatto per deployment Swarm

## Modifiche Necessarie per docker-stack.yml

### 1. Configurazione Volumi con Storage Condiviso

```yaml
volumes:
  thoth-backend-db:
    driver: local
    driver_opts:
      type: "nfs"
      o: "addr=nfs-server,rw,nfsvers=4"
      device: ":/exports/thoth/backend-db"
  
  qdrant-data:
    driver: local
    driver_opts:
      type: "nfs"
      o: "addr=nfs-server,rw,nfsvers=4"
      device: ":/exports/thoth/qdrant"
  
  thoth-shared-data:
    driver: local
    driver_opts:
      type: "nfs"
      o: "addr=nfs-server,rw,nfsvers=4"
      device: ":/exports/thoth/shared-data"
  
  thoth-logs:
    driver: local
    driver_opts:
      type: "nfs"
      o: "addr=nfs-server,rw,nfsvers=4"
      device: ":/exports/thoth/logs"
  
  # Volumi temporanei locali
  backend-static:
    driver: local
  backend-media:
    driver: local
  frontend-cache:
    driver: local
```

Nota: l'esempio sopra usa il driver `local` con `type=nfs`, che è il pattern più comune senza installare plugin dedicati. In produzione HA vera, valuta uno storage/distributed filesystem con locking/replica migliori o un DB esterno (vedi nota su SQLite).

### 2. Placement Constraints per Servizi con Stato

```yaml
services:
  backend:
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.thoth-data == true
          # Evita di vincolare ai manager a meno che tu non lo voglia esplicitamente.
      # ... resto della configurazione

  thoth-qdrant:
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.thoth-data == true
          # Evita di vincolare ai manager a meno che tu non lo voglia esplicitamente.
      # ... resto della configurazione

  sql-generator:
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.thoth-data == true
          # Evita di vincolare ai manager a meno che tu non lo voglia esplicitamente.
      # ... resto della configurazione
```

Suggerimento: per i servizi stateful, spesso è preferibile usare worker dedicati (label) e lasciare i manager il più “puliti” possibile.

### 3. Aggiungere Servizio di Backup

```yaml
services:
  backup-service:
    image: ${REGISTRY_URL}/thoth-backup:${VERSION:-latest}
    volumes:
      - thoth-backend-db:/backup/db:ro
      - qdrant-data:/backup/qdrant:ro
      - thoth-shared-data:/backup/shared:ro
      - /mnt/backups:/output
    environment:
      - SCHEDULE=0 2 * * *
      - RETENTION_DAYS=30
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.thoth-data == true
      restart_policy:
        condition: on-failure
```

Nota:
- La variabile `SCHEDULE` funziona solo se l'immagine di backup implementa effettivamente uno scheduler/cron interno.
- Il mount `/mnt/backups:/output` è un bind mount per-node: in multi-nodo richiede placement sul nodo che ha quel path oppure uno storage condiviso.
- Per Qdrant, un semplice backup a caldo dei file potrebbe non essere consistente: preferisci snapshot/backup supportati dal servizio o una procedura di quiescenza.

## Modifiche Necessarie per docker-stack-simple.yml

### 1. Rimuovere (o Limitare) Bind Mounts Per-Node

```yaml
services:
  backend:
    volumes:
      - thoth-backend-db:/app/backend_db
      - thoth-shared-data:/app/data
      - thoth-logs:/app/logs
      - backend-static:/vol/static
      - backend-media:/vol/media
      # Rimuovere queste linee:
      # - ./config.yml.local:/app/config.yml.local:ro
      # - ./data_exchange:/app/data_exchange
    # ... resto della configurazione
```

### 2. Aggiungere Secrets e Configs

```yaml
services:
  backend:
    secrets:
      - thoth_env_config
      - thoth_config_yml
    configs:
      - source: thoth_env_docker
        target: /app/.env.docker
    # ... resto della configurazione

  frontend:
    secrets:
      - thoth_env_config
    configs:
      - source: thoth_env_docker
        target: /app/.env.docker
    # ... resto della configurazione

  sql-generator:
    secrets:
      - thoth_env_config
    configs:
      - source: thoth_env_docker
        target: /app/.env.docker
    # ... resto della configurazione
```

### 3. Aggiungere Placement Constraints

```yaml
services:
  backend:
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.thoth-data == true
    # ... resto della configurazione

  thoth-qdrant:
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.thoth-data == true
    # ... resto della configurazione
```

## Configurazione dell'Ambiente Swarm

### 1. Preparazione dei Nodi

```bash
# Su tutti i nodi manager
docker node update --label-add thoth-data=true node-1

# Installare client NFS su tutti i nodi
apt-get update && apt-get install -y nfs-common

# Creare mount points
mkdir -p /mnt/thoth-volumes/{backend-db,qdrant,shared-data,logs}
```

### 2. Configurazione Server NFS

```bash
# Sul server NFS
mkdir -p /exports/thoth/{backend-db,qdrant,shared-data,logs}
chown -R nobody:nogroup /exports/thoth

# Configurare /etc/exports
echo "/exports/thoth *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports
exportfs -a
systemctl restart nfs-kernel-server
```

Nota sicurezza: `no_root_squash` è rischioso; preferisci restringere gli host/IP autorizzati e valutare `root_squash` (o un approccio storage diverso) in produzione.

### 3. Creare Secrets e Configs

```bash
# Creare secrets
echo "contenuto_env_config" | docker secret create thoth_env_config -
echo "contenuto_config_yml" | docker secret create thoth_config_yml -

# Creare configs
echo "contenuto_env_docker" | docker config create thoth_env_docker -
```

### 4. Deploy dello Stack

```bash
# Deploy con configurazione modificata
docker stack deploy -c docker-stack.yml thoth

# Verificare lo stato
docker stack services thoth
docker service logs thoth_backend
```

## Raccomandazioni Operative

### 1. Per Produzione Multi-Nodo

1. **Storage Condiviso**: Implementare NFS o Ceph per volumi persistenti
2. **Node Labels**: Configurare labels appropriati per placement constraints
3. **Backup Strategy**: Implementare backup automatici con retention policy
4. **Monitoring**: Monitorare utilizzo storage e performance NFS

### 2. Per Sviluppo Singolo Nodo

1. **Usare docker-stack-simple.yml**: Modificato come indicato sopra
2. **Volume Local**: Mantenere driver `local` per tutti i volumi
3. **Bind Mounts**: In Swarm sono supportati, ma usali sapendo che sono per-node (quindi con placement constraints o cluster singolo nodo)
4. **Secrets Management**: Convertire file di configurazione sensibili in secrets/configs Swarm quando possibile

### 3. Migrazione Graduale

1. **Fase 1**: Testare con volumi per-node (driver `local`) + placement constraints
2. **Fase 2**: Implementare storage condiviso per dati critici
3. **Fase 3**: Aggiungere backup e monitoring
4. **Fase 4**: Testare failover e recovery procedures

Nota importante: se `thoth-backend-db` è SQLite, evitare SQLite su NFS in produzione (locking/latency/consistenza). Per produzione multi-nodo è generalmente preferibile un DB server (Postgres/MariaDB) piuttosto che un file DB condiviso.

### 4. Best Practices

1. **Separare Dati Critici**: Database e vector data su storage condiviso
2. **Cache Locale**: Mantenere cache su volumi `local` per performance
3. **Backup Regolari**: Implementare backup giornalieri con retention
4. **Monitoring**: Monitorare spazio storage e performance I/O
5. **Documentazione**: Mantenere documentata la configurazione storage

## Troubleshooting Comuni

### 1. Volumi Non Accessibili

```bash
# Verificare stato volumi
docker volume ls
docker volume inspect thoth-backend-db

# Verificare mount points sui nodi
df -h | grep nfs
mount | grep thoth
```

### 2. Placement Constraints

```bash
# Verificare node labels
docker node ls
docker node inspect node-1 --format '{{ .Spec.Labels }}'

# Verificare service placement
docker service ps thoth_backend
```

### 3. Performance NFS

```bash
# Test performance I/O
dd if=/dev/zero of=/mnt/thoth-volumes/test bs=1M count=100 oflag=direct

# Ottimizzazioni NFS
echo "Valuta rsize/wsize/timeo/retrans direttamente nelle opzioni di mount (es. o=... nel volume) o in /etc/fstab sul nodo"
```

Questa configurazione garantisce persistenza dati, scalabilità orizzontale e recovery strategy per l'ambiente di produzione Swarm, mantenendo compatibilità con l'architettura esistente del progetto Thoth.