# Resoconto Installazione e Analisi Fallimenti ThothAI (Swarm)

## 1. Stato Attuale
L'installazione dello stack `thothai-swarm` è stata completata con successo sul server di test `docker-test-m1.uni.com`. Tutti i servizi sono operativi e raggiungibili.

### URL di Accesso (Test)
- **Main App (Gateway)**: [http://docker-test-m1.uni.com:7410](http://docker-test-m1.uni.com:7410)
- **Frontend UI**: [http://docker-test-m1.uni.com:7401](http://docker-test-m1.uni.com:7401)
- **Django Admin**: [http://docker-test-m1.uni.com:7410/admin](http://docker-test-m1.uni.com:7410/admin)

---

## 2. Analisi Comparativa Fallimento Produzione
Il tentativo di deploy su `docker-prod-m1.uni.com` non ha avuto esito positivo. L'analisi dei due contesti ha evidenziato differenze critiche nella distribuzione dei carichi e nella gestione delle risorse.

### Matrice Comparativa degli Ambienti

| Caratteristica | docker-test-m1 (Test) | docker-prod-m1 (Produzione) |
| :--- | :--- | :--- |
| **Nodi Totali** | 5 (3 Manager, 2 Worker) | 5 (3 Manager, 2 Worker) |
| **RAM Totale (Manager)** | ~16 GB | ~12 GB |
| **Versione Docker Engine** | 26.1.3 / 28.0.4 | 26.1.3 (omogenea) |
| **Carico Preesistente** | Basso (stack di test) | Elevato (14+ stack attivi) |
| **Placement Servizi** | Concentrato (prevalenza su `m2`) | Distribuito (mix `m1`, `m2`, `m3`) |
| **Esito Deploy** | **SUCCESSO** | **FALLIMENTO** (Exit 137 / Unhealthy) |

### Ipotesi sul fallimento in Produzione:

#### Ipotesi 1: Volumi Locali in Cluster Multi-Nodo (Causa Principale)
Lo stack utilizza driver `local` per i volumi (es. `thoth-shared-data`, `thoth-secrets`). In Docker Swarm, un volume `local` è confinato al nodo fisico su cui viene creato.
- **Nel Test**: Quasi tutti i servizi sono stati pianificati sullo stesso nodo (`docker-test-m2`), permettendo la condivisione "accidentale" dei file.
- **In Produzione**: Lo Swarm ha distribuito i servizi su nodi diversi (`m1`, `m2`, `m3`). Il `frontend` su `m2` non può vedere i file di configurazione inizializzati dal `backend` su `m1`, restando in attesa infinita.

#### Ipotesi 2: Health Check e Timeout (Exit Code 137)
Molti servizi in produzione mostrano l'errore `task: non-zero exit (137): dockerexec: unhealthy container`.
- Poiché i servizi restano bloccati in attesa dei segreti/volumi (Ipotesi 1), non riescono a rispondere agli health check entro il `start_period`.
- Docker interviene con un `SIGKILL` (137) per tentare di riavviare il container, entrando in un loop di fallimento.

#### Ipotesi 3: Saturazione Risorse di Memoria (OOM)
I nodi di produzione hanno circa 12GB di RAM (contro i 16GB del test) e ospitano numerosi altri stack attivi.
- L'exit code 137 è spesso associato a eventi di Out Of Memory (OOM). 
- La partenza simultanea dei microservizi ThothAI, unita al carico preesistente sul cluster, potrebbe saturare la memoria fisica disponibile sui nodi di produzione.

#### Ipotesi 4: Latenza Propagazione Secrets
I log indicano *"Secrets not ready yet"*. In cluster Swarm remoti o con elevato carico, la propagazione dei segreti tramite la rete overlay può subire ritardi. Se la gestione del piano di controllo è rallentata, i container partono ma non trovano il mount del segreto pronto.

---

## 3. Raccomandazioni per la Produzione
Per garantire un deploy stabile in ambiente di produzione multi-nodo, si consiglia di:

1.  **Storage Condiviso**: Configurare i volumi utilizzando un driver di rete (es. NFS o GlusterFS) in modo che i dati siano accessibili da tutti i nodi del cluster.
2.  **Placement Constraints**: Qualora non sia possibile usare storage condiviso, aggiungere vincoli di posizionamento nel `docker-stack.yml` per forzare i servizi critici a girare sullo stesso nodo (es. `node.hostname == docker-prod-m1`).
3.  **Ottimizzazione Risorse**: Verificare i limiti di memoria (`deploy.resources.limits.memory`) per assicurarsi che non eccedano la capacità residua dei nodi di produzione.
