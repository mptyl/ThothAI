# Guida Build e Pubblicazione (Sviluppatore)

Questa guida è destinata allo **Sviluppatore** o **Release Manager** che deve creare le immagini Docker di ThothAI e pubblicarle su Docker Hub affinché gli utenti possano installarle.

## 1. Prerequisiti

*   Account Docker Hub.
*   Accesso di scrittura al repository (es. `tylconsulting/thoth-backend`).
*   Login effettuato:
    ```bash
    docker login
    ```

## 2. Script di Pubblicazione

Abbiamo predisposto lo script `push.sh` che automatizza l'intero processo di compilazione (build), tagging e upload (push).

### Utilizzo

```bash
./push.sh <REGISTRY_URL> <VERSION> [OPTIONS]
```

*   `REGISTRY_URL`: Il tuo username o URL del registry (es. `tylconsulting`).
*   `VERSION`: Il tag della versione (es. `1.0.2` o `beta`). Lo script taggherà anche come `latest`.

### Esempio Rapido

```bash
# Compila e pubblica la versione 0.5.0 sul namespace tylconsulting
./push.sh tylconsulting 0.5.0
```

## 3. Workflow Tipico di Rilascio

1.  **Test Locale:** Verifica che tutto funzioni con `docker-compose-local.yml` o build locale.
2.  **Commit & Tag Git:**
    ```bash
    git commit -m "Release 0.5.0"
    git tag v0.5.0
    git push origin --tags
    ```
3.  **Build & Push Docker:**
    ```bash
    ./push.sh tylconsulting 0.5.0 --no-cache
    ```
4.  **Verifica:** Controlla su Docker Hub che le immagini siano aggiornate.
5.  **Annuncio:** Gli utenti possono ora aggiornare eseguendo il loro `install.sh`.

```mermaid
graph LR
    subgraph Dev Machine
        Code[Codice Sorgente]
        Build[Docker Build]
    end
    
    subgraph Registry
        Hub[Docker Hub]
    end
    
    subgraph Users
        UserA[Utente Docker]
        UserB[Utente Swarm]
    end

    Code --> Build
    Build -- "./push.sh" --> Hub
    Hub -- "./install.sh" --> UserA
    Hub -- "docker stack deploy" --> UserB
    
    style Dev Machine fill:#e0f2f1,stroke:#00695c
    style Registry fill:#fff3e0,stroke:#ef6c00
    style Users fill:#f3e5f5,stroke:#8e24aa
    linkStyle default stroke:#fff,stroke-width:1px;
```

## 4. Dettagli sullo Script

Lo script `push.sh`:
*   Legge i `Dockerfile` predefiniti.
*   Costruisce le immagini per: `backend`, `frontend`, `sql-generator`, `proxy`, `mermaid-service`.
*   Esegue il `docker push` sia del tag specifico che di `latest`.
*   Gestisce il re-tagging dell'immagine `qdrant` ufficiale per coerenza (opzionale).
