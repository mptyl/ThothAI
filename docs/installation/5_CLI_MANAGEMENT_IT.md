# Gestione e Manutenzione (CLI Management)

Questo documento descrive i comandi della CLI per la gestione quotidiana di ThothAI, inclusi il monitoraggio, la pulizia e l'aggiornamento automatico.

## 1. Monitoraggio dello Stato

Per visualizzare lo stato di salute dei container e servizi:

### Docker Compose (Single Node)
```bash
# Locale
uv run thothai status

# Remoto
uv run thothai status --server ssh://user@ip
```

### Docker Swarm
```bash
# Locale
uv run thothai swarm status

# Remoto
uv run thothai swarm status --server ssh://user@ip
```

Mostrerà l'elenco dei servizi, lo stato (Running/Stopped) e le repliche.

## 2. Aggiornamento Applicazione

Per aggiornare l'applicazione a una nuova versione specificata nel `config.yml.local`:

1.  Modificare `config.yml.local` (se necessario).
2.  Rieseguire il deploy:

```bash
# Compose
uv run thothai up [--server ...]

# Swarm
uv run thothai swarm deploy [--server ...]
```

## 3. Aggiornamenti Automatici (Watchtower)

È possibile configurare ThothAI per aggiornarsi automaticamente quando vengono pubblicate nuove immagini (es. patch di sicurezza).

Questo utilizza **Watchtower**, un servizio che monitora la presenza di nuove immagini.

### Configurazione
Consultare i file di esempio o aggiungere un servizio `watchtower` al vostro `docker-compose.yml` o stack Swarm.

Esempio comando per aggiornamento automatico su Compose (solo servizi thoth):
```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 3600 \
  --cleanup \
  thoth-backend thoth-frontend thoth-sql-generator thoth-proxy
```

## 4. Pulizia (Prune)

Nel tempo, Docker può accumulare immagini vecchie, volumi non usati e reti orfane. Il comando `prune` aiuta a liberare spazio.

### Esecuzione
```bash
# Locale
uv run thothai prune

# Remoto
uv run thothai prune --server ssh://user@ip
```

Questo comando rimuoverà:
*   Container fermi.
*   Reti non utilizzate.
*   Immagini "dangling" (senza tag).
*   (Opzionale) Volumi non utilizzati (fate attenzione ai dati!).

## 5. Visualizzazione Log

La CLI non ha (ancora) un comando `logs` nativo unificato, ma potete usare i comandi Docker standard combinati con la connessione SSH se necessario.

```bash
# Esempio manuale su remoto
ssh user@ip "docker logs -f thoth-backend"
```
