# ThothAI - Manuale Teorico Docker e Automazione (CI/CD)

Questo documento spiega in modo semplice i concetti fondamentali dietro l'installazione e l'aggiornamento automatico di ThothAI. È pensato per chi non ha familiarità con Docker o con le pipeline di deploy.

---

## 1. I Concetti Base: Cosa stiamo usando?

Per capire come funziona il tutto, dobbiamo definire alcuni termini chiave usando delle analogie.

### 1.1 Docker: Il Container
Immagina un **Container** come una "scatola magica" che contiene tutto ciò che serve alla tua applicazione per funzionare (codice, librerie, configurazioni).
*   **Vantaggio**: Se la scatola funziona sul mio computer, funzionerà identica sul server. Niente più "ma da me funzionava!".
*   **Differenza con VM**: Una Macchina Virtuale è come costruire un'intera casa nuova per far girare un programma. Docker è come arredare solo una stanza. È molto più leggero e veloce.

### 1.2 L'Immagine (Il Progetto) vs Il Container (La Casa)
*   **Immagine Docker**: È il progetto, il "disegno tecnico". È statica, non fa nulla da sola. Viene creata (build) una volta e salvata.
*   **Container**: È la "casa costruita" seguendo quel progetto. È l'applicazione in esecuzione. Puoi distruggere e ricreare il container in secondi partendo sempre dalla stessa immagine.

### 1.3 Docker Registry (La Libreria)
Dove mettiamo i progetti (Immagini) una volta disegnati? In una libreria online chiamata **Registry** (come Docker Hub).
*   Il server non "costruisce" nulla. Il server va in libreria, prende il progetto finito (scarica l'immagine) e lo esegue.

---

## 2. Automazione: La Pipeline CI/CD

Come fa una modifica al codice sul computer di uno sviluppatore ad arrivare sul server di produzione senza intervento umano? Attraverso una "Pipeline" (tubatura).

### 2.1 Gli Attori in gioco

1.  **Lo Sviluppatore**: Scrive il codice e lo invia (Push) al deposito centrale (es. GitHub).
2.  **Il Repository (Git)**: Il deposito centrale dove sta tutto il codice.
3.  **Il Runner (L'Operaio)**: È un computer "invisibile" (fornito da GitHub o GitLab) che si sveglia solo quando c'è nuovo codice. Il suo compito è fare il "lavoro sporco": compilare e costruire.
4.  **Il Server di Produzione**: Il computer finale che ospita l'applicazione e risponde agli utenti.

### 2.2 Chi fa cosa? (Il grande equivoco)
Molti pensano che il Server di Produzione scarichi il codice e lo compili. **NO!** Sarebbe lento e rischioso.
*   **Chi Compila (Build)?** Il **Runner**. Lui prende il codice, costruisce la "scatola" (Immagine Docker) e la mette sullo scaffale (Registry).
*   **Chi Esegue?** Il **Server**. Lui si limita a prendere la scatola già pronta dallo scaffale.

---

## 3. Scenario A: Aggiornamento su Docker Singolo (VPS)

In questo scenario abbiamo un server semplice con Docker installato. Ecco cosa succede passo-passo quando un programmatore modifica una riga di codice:

1.  **Push**: Il programmatore invia la modifica a GitHub.
2.  **Build**: GitHub sveglia un **Runner**.
    *   Il Runner scarica il codice.
    *   Il Runner esegue `docker build`. Crea la nuova Immagine ("v2.0").
    *   Il Runner esegue `docker push`. Carica la nuova Immagine su Docker Hub.
3.  **Deploy (L'ordine di aggiornamento)**:
    *   Il Runner, finito il push, si collega via SSH (come un amministratore remoto) al Server di Produzione.
    *   Esegue due comandi sul Server:
        1.  `docker compose pull`: "Scarica le nuove immagini da Docker Hub".
        2.  `docker compose up -d`: "Riavvia i container usando le nuove immagini".
    *   Il Server spegne il vecchio container e accende quello nuovo in pochi secondi.

---

## 4. Scenario B: Aggiornamento su Docker Swarm (Cluster)

In questo scenario abbiamo più server collegati insieme (un Cluster). Uno comanda (Manager) e gli altri eseguono (Workers).

1.  **Push & Build**: Identico (Il Runner costruisce e pusha su Hub).
2.  **Deploy (L'orchestrazione)**:
    *   Il Runner si collega via SSH solo al **Manager Node**.
    *   Esegue il comando: `docker stack deploy` o `docker service update --image ...`.
    *   **La Magia del Rolling Update**:
        *   Il Manager non spegne tutto insieme. Dice al primo Worker: "Aggiorna questo pezzo".
        *   Il Worker scarica l'immagine, spegne il vecchio, accende il nuovo.
        *   Se il nuovo si accende correttamente, il Manager passa al secondo Worker.
        *   Se qualcosa va storto, il Manager **ferma tutto e torna indietro** (Rollback automatico).

**Vantaggio**: L'utente non si accorge di nulla perché mentre un pezzo si aggiorna, gli altri continuano a rispondere.

---

## 5. Il Dilemma dell'Utente: Come automatizzo SENZA accesso al codice?

Questa è una domanda fondamentale. Uno sviluppatore (Producer) ha la CI/CD che "spinge" (Push) gli aggiornamenti. Ma un utente normale (Consumer) che usa le immagini pubbliche non ha accesso al GitHub dello sviluppatore. Non può dire a GitHub Actions "ehi, aggiorna il mio server".

L'utente deve usare una strategia **PULL** (Tirare).

### 5.1 La soluzione semplice: Watchtower
Esiste un container speciale chiamato **Watchtower** che automatizza il processo di aggiornamento.

**Come configurarlo per ThothAI:**

ThothAI è composto da multipli servizi (backend, frontend, proxy, sql-generator). Watchtower può gestire tutto questo autonomamente.

1.  **Aggiungi Watchtower al tuo `docker-compose.yml`**:
    ```yaml
    services:
      # ... altri servizi Thoth ...
    
      watchtower:
        image: containrrr/watchtower
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock
        command: --schedule "0 0 4 * * *" --cleanup --label-enable
    ```

2.  **Come limitarlo solo a ThothAI?**
    Se il tuo server ospita anche altre applicazioni (es. un blog, un database privato) e **non** vuoi che Watchtower le aggiorni tutte, hai due strade:

    *   **Metodo A: Lista Esplicita**:
        Nel comando, aggiungi i nomi dei container che vuoi monitorare:
        `command: --schedule "0 0 4 * * *" thoth-backend thoth-frontend thoth-proxy`
    
    *   **Metodo B: Le Label (Consigliato)**:
        È il modo più elegante. Aggiungi l'opzione `--label-enable` al comando di Watchtower (come nell'esempio sopra) e poi aggiungi una "etichetta" solo ai servizi di ThothAI nel `docker-compose.yml`:
        ```yaml
        backend:
          image: thoth-backend
          labels:
            - "com.centurylinklabs.watchtower.enable=true"
        ```
        In questo modo, Watchtower ignorerà tutto ciò che non ha questa etichetta.

3.  **Watchtower e Docker Swarm**
    In un cluster Swarm, le cose cambiano leggermente perché Watchtower di base gestisce *container singoli*, non i *servizi Swarm*. 

    *   **Opzione 1 (Watchtower in Swarm)**:
        Puoi far girare Watchtower come servizio Swarm, ma deve essere in grado di parlare con il manager. Si usa l'impostazione `--unattended`:
        ```yaml
        services:
          watchtower:
            image: containrrr/watchtower
            deploy:
              placement:
                constraints: [node.role == manager]
            volumes:
              - /var/run/docker.sock:/var/run/docker.sock
            command: --unattended --cleanup --interval 3600
        ```
        *Nota: In Swarm, Watchtower deve avere accesso al socket del nodo Manager.*

    *   **Opzione 2 (L'alternativa specifica per Swarm: Shepherd)**:
        Esiste un tool chiamato **Shepherd** che fa esattamente quello che fa Watchtower ma è nato appositamente per Swarm. Invece di monitorare i singoli container, monitora i *servizi*.
        
        **Come funziona Shepherd?**
        1. Controlla periodicamente se l'immagine registrata nel servizio Swarm ha un nuovo digest (ID univoco) su Docker Hub.
        2. Se l'immagine è cambiata, invia al cluster l'ordine di aggiornamento: `docker service update --image ...`.
        
        **Esempio di configurazione Shepherd**:
        ```yaml
        services:
          shepherd:
            image: mazzolino/shepherd
            volumes:
              - /var/run/docker.sock:/var/run/docker.sock
            deploy:
              placement:
                constraints:
                  - node.role == manager
            environment:
              SLEEP_TIME: "1h" # Controlla ogni ora
              FILTER_SERVICES: "label=com.thothai.autoupdate=true" # Esempio: aggiorna solo i servizi con questa label
        ```
        In questo caso, dovrai aggiungere la label `com.thothai.autoupdate=true` a tutti i servizi di ThothAI nel tuo file `docker-stack.yml`.
        
        **Esempio Pratico: come aggiungere la label**
        Apri il tuo file `docker-stack.yml` e aggiungi la label sotto la sezione `deploy` di ogni servizio che vuoi aggiornare automaticamente:
        
        ```yaml
        services:
          backend:
            image: thoth/backend:latest
            deploy:
              labels:
                - "com.thothai.autoupdate=true"
              replicas: 2
          
          frontend:
            image: thoth/frontend:latest
            deploy:
              labels:
                - "com.thothai.autoupdate=true"
        ```
        *Nota: In Swarm è importante metterla sotto `deploy`, perché Shepherd interroga i Sevizi, non i Container.*

4.  **Spiegazione della Configurazione**:
    *   `/var/run/docker.sock`: Permette a Watchtower/Shepherd di parlare con il Docker del tuo server. È necessario per permettergli di riavviare gli altri container o servizi.
    *   `--schedule "0 0 4 * * *"`: Controlla gli aggiornamenti ogni notte alle 04:00 (valido per Docker Compose).
    *   `--cleanup`: Rimuove le vecchie immagini dopo l'aggiornamento per risparmiare spazio disco.

### 5.2 La soluzione classica: Cron Job

Se non vuoi usare un container dedicato (Watchtower/Shepherd), puoi usare un classico **Cron Job** sul server.

> **Nota Fondamentale sul contesto di esecuzione**: 
> Questi comandi **NON** vanno eseguiti sul tuo PC personale (Windows o Mac). Vanno eseguiti direttamente sul **Sistema Operativo del Server** (quello "remoto").
> 
> **Come ci si arriva?**
> 1. Devi collegarti al server tramite **SSH** (Secure Shell).
> 2. Se usi **Windows**, puoi usare il comando `ssh` dal PowerShell o dal Terminale di Windows (o tool come PuTTY).
> 3. Il comando `ssh utente@indirizzo-ip-server` ti proietta "dentro" la linea di comando del server remoto.
> 
> **Perché "solo sul nodo MANAGER"?**
> In Docker Swarm, solo il nodo Manager ha il potere di modificare lo stato del cluster. Quindi, quando ti colleghi in SSH, devi assicurarti di collegarti proprio all'indirizzo IP del server che è stato configurato come Manager. I comandi vanno lanciati sul sistema ospitante (host), non dentro un container, perché devono parlare con il "motore" Docker globale.

#### Per Docker Compose (Singolo Server)
L'utente configura un piccolo script sul suo server (ad esempio ogni notte alle 03:00):
```bash
# Esempio script utente per Compose (eseguito sul server)
cd /path/to/app
docker compose pull  # Scarica se c'è qualcosa di nuovo
docker compose up -d # Riavvia solo se l'immagine è cambiata
```

#### Per Docker Swarm (Cluster) - Guida Operativa

In Swarm il comando `pull` non basta. Ecco la procedura esatta per un operatore (es. su Windows) connesso in SSH al nodo Manager.

**Passo 1: Crea lo script di aggiornamento**
Una volta connesso in SSH, crea un file per lo script:
```bash
nano ~/update_thoth.sh
```
Incolla dentro questo codice (adattando i percorsi):
```bash
#!/bin/bash
# Definisci il nome dello stack
STACK_NAME="thoth"
# Definisci dove sta il file yaml sul server
COMPOSE_FILE="/path/to/ThothAI/docker-stack.yml"

echo "Inizio aggiornamento stack: $STACK_NAME..."
# Aggiorna lo stack forzando il re-download delle immagini (--resolve-image always)
docker stack deploy -c $COMPOSE_FILE $STACK_NAME --with-registry-auth --resolve-image always
echo "Aggiornamento inviato al cluster."
```
Salva con `CTRL+O`, Invio, ed esci `CTRL+X`.

**Passo 2: Rendilo eseguibile**
```bash
chmod +x ~/update_thoth.sh
```

**Passo 3: Configura il Cron (Pianificazione)**
Apri l'editor di cron:
```bash
crontab -e
```
(Se è la prima volta, premi 1 per scegliere nano).
Vai in fondo al file e aggiungi questa riga per eseguirlo **ogni notte alle 04:00**:
```bash
0 4 * * * /home/tuo-utente/update_thoth.sh >> /home/tuo-utente/update_log.txt 2>&1
```
*Spiegazione*: Esegue lo script e salva l'output (ed eventuali errori) nel file `update_log.txt` per debugging.

**Passo 4: Verifica**
Salva ed esci. Il sistema ti dirà `crontab: installing new crontab`. Fatto! Il Manager ora aggiornerà il cluster ogni notte.

**Differenza Chiave**:
*   **Sviluppatore (CI/CD)**: "Ho finito di scrivere, **SPINGO** il codice in produzione." (PUSH)
*   **Utente (Auto-Update)**: "Controllo periodicamente se c'è qualcosa di nuovo da **TIRARE** giù." (PULL)

---

## 6. Riassunto dei Ruoli

| Chi | Cosa Fa | Analogia |
| :--- | :--- | :--- |
| **Sviluppatore** | Scrive codice | L'Architetto |
| **Git (GitHub/GitLab)** | Conserva lo storico | L'Archivio Progetti |
| **CI Runner** | Compila, Costruisce Immagini, Ordina il Deploy | Il Capocantiere |
| **Docker Hub** | Conserva le Immagini pronte | Il Magazzino |
| **Server Reale** | Scarica ed Esegue | Il Cantiere |

In sintesi: **Il Server non sa come è fatto il tuo codice.** Sa solo che deve scaricare la scatola "versione 2.0" dal magazzino e accenderla. Questo rende il sistema estremamente robusto.

---

## 7. Riferimenti e Approfondimenti

Per chi vuole approfondire gli argomenti trattati, ecco una selezione di risorse utili:

*   **Docker & Containers**:
    *   [Docker Curriculum](https://docker-curriculum.com/) - Ottimo tutorial interattivo per principianti.
    *   [Docker Official Getting Started](https://docs.docker.com/get-started/) - La guida ufficiale.

*   **Docker Swarm**:
    *   [Swarm Mode Overview](https://docs.docker.com/engine/swarm/) - Introduzione ufficiale all'orchestrazione.
    *   [Visualizer for Docker Swarm](https://github.com/dockersamples/docker-swarm-visualizer) - Strumento utile per "vedere" il cluster.

*   **CI/CD & Automation**:
    *   [GitHub Actions Documentation](https://docs.github.com/en/actions) - Guida completa alle pipeline di GitHub.
    *   [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/) - Guida ufficiale GitLab.
    *   [Watchtower Docs](https://containrrr.dev/watchtower/) - Documentazione completa per l'auto-updater.

*   **Best Practices**:
    *   [The Twelve-Factor App](https://12factor.net/) - Metodologia standard per costruire app SaaS (molto rilevante per Container).
