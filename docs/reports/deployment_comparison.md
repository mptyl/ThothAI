# Confronto Processi di Deployment: ThothAI CLI vs Processo Cliente

Documento di analisi delle differenze e potenziali incompatibilità tra la gestione automatizzata di `thothai-cli` e la procedura manuale del cliente descritta in `docs/briefings/Instalazione su docker swarm.md`.

## Riepilogo Esecutivo

Il processo del cliente, sebbene titolato "Instalazione su docker swarm", descrive in realtà una **gestione manuale di container standalone** tramite `docker run`, non un vero deployment orchestrato su Swarm (che richiederebbe `docker stack deploy`).

La CLI `thothai` utilizza invece un approccio moderno e orchestrato (sia per Docker Compose che per Swarm), gestendo automaticamente reti, volumi, dipendenze e configurazioni.

## Analisi Dettagliata

### 1. Modalità di Esecuzione (Swarm vs Standalone)

| Caratteristica | Processo Cliente (Manuale) | ThothAI CLI (Automated) |
| :--- | :--- | :--- |
| **Comando** | `docker run ...` | `docker stack deploy` (Swarm) o `docker compose up` |
| **Modalità** | Container singoli (Standalone) | Orchestrazione (Stack/Compose) |
| **Riavvio** | Non specificato (manuale) | `restart: always` (garantito da Swarm/Compose) |
| **Scaling** | Manuale (`docker run` multipli) | Comandi di scala (`docker service scale`) |
| **Networking** | Non specificato (default bridge?) | Rete dedicata `thoth-network` (overlay su Swarm) |

**Incompatibilità:** L'attuale procedura cliente non sfrutta le funzionalità di cluster di Swarm. Se i loro server sono configurati come nodi Swarm, lanciare container con `docker run` bypassa l'orchestratore, rendendo impossibile service discovery, scaling e rolling updates gestiti da Swarm.

### 2. Gestione Immagini e Registry

| Caratteristica | Processo Cliente (Manuale) | ThothAI CLI (Automated) |
| :--- | :--- | :--- |
| **Registry** | `registry.uni.com` (Privato) | `tylconsulting` (Docker Hub) o custom tramite Config |
| **Build** | Manuale (`docker build .`) locale | Pull automatico da registry o build locale (Compose) |
| **Versioning** | Tag manuale esplicito | Gestito tramite var `VERSION` in `.env.docker` |

**Azione Richiesta:**
- È necessario configurare `config.yml.local` per puntare al registry del cliente (`registry.uni.com`) se si intende usare le loro immagini o spingere le nostre lì.
- La CLI attuale è ottimizzata per eseguire il *pull* sul server remoto. Il cliente esegue *build* locale + *push*.

### 3. Persistenza e Volumi

Il documento del cliente **non menziona la gestione dei volumi**. Gli esempi `docker run` mostrati non montano volumi.

**Criticità:** ThothAI richiede volumi persistenti per:
- Database (`thoth-backend-db`)
- Vector DB (`thoth-qdrant-data`)
- File statici/media (`backend-static`, `backend-media`)
- Segreti (`thoth-secrets`)

Lanciare l'applicazione come nel documento cliente comporterebbe la **perdita di tutti i dati** al riavvio del container.

### 4. Configurazione e Segreti

- **Cliente:** Non specifica come vengono passate le variabili d'ambiente (probabilmente hardcoded o file env non citato).
- **ThothAI CLI:** Sincronizza automaticamente `.env.docker`, `config.yml.local` e crea Docker Secrets/Configs su Swarm.

## Conclusioni e Raccomandazioni

Il processo descritto dal cliente è **insufficiente** per un'applicazione complessa come ThothAI in produzione. È imperativo **non** seguire la procedura `docker run` manuale.

### Piano di Mitigazione

1.  **Chierimento Registry:** Confermare se dobbiamo usare il loro registry `registry.uni.com`. In tal caso, dovremmo aggiungere una fase di `tag` & `push` delle nostre immagini verso il loro registry prima del deploy.
2.  **Adozione CLI:** Convincere il cliente a utilizzare `thothai swarm deploy` (o `thothai up --server ...`) invece dei comandi manuali. Questo garantisce:
    - Creazione corretta dei volumi.
    - Gestione della rete interna tra i servizi.
    - Configurazione automatica di Nginx (proxy) e variabili d'ambiente.
3.  **Fallback "Stack File":** Se il cliente rifiuta di usare la CLI Python, possiamo generare per loro il file `docker-stack.yml` finale (tramite `thothai swarm deploy --dry-run` se implementassimo tale flag, o prendendolo da un deploy di test) e fornire loro il comando standard:
    ```bash
    docker stack deploy -c docker-stack.yml thothai
    ```
