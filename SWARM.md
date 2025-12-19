# Deploy ThothAI con Docker Swarm (Windows build → Linux server)

Questa guida copre il percorso completo:

1) Windows: aggiornare repo, configurare, buildare le immagini.
2) Windows: push delle immagini sul registry.
3) Linux (server Swarm): deploy dello stack.

## Prerequisiti

- Docker installato su Windows (per build) e su Linux (per Swarm).
- Accesso al registry `registry.uni.com` con credenziali valide.
- File già presenti nel repo: `buildswarm.ps1`, `deployswarm.ps1`, `docker-stack-simple.yml`, `stackswarm.sh`, `.env.docker`, `config.yml.local`.

## Passo 1: Windows – aggiornare e configurare

```powershell
git pull
# aggiorna config.yml.local se necessario
```

## Passo 2: Windows – build immagini

```powershell
.\buildswarm.ps1
# opzionale: senza cache
# .\buildswarm.ps1 -NoCache
```

## Passo 3: Windows – push immagini al registry

```powershell
docker login registry.uni.com

# imposta il tag versione usato in build
$VER="0.1"   # cambia se usi un altro tag
.\deployswarm.ps1 -Version $VER
# opzionale: aggiungi -PushLatest se vuoi pushare anche :latest
```

## Passo 4: Copiare i file sul server Linux

Crea/scegli una cartella sul server (es. `/opt/thoth`) e copia lì:

- `docker-stack-simple.yml`
- `stackswarm.sh`
- `.env.docker`
- `config.yml.local`
- `data_exchange/` (se serve)

## Passo 5: Linux (server Swarm) – deploy

Sul server, dentro la cartella dove hai copiato i file:

```bash
docker login registry.uni.com
chmod +x stackswarm.sh

# variabili di default già nel file; puoi sovrascrivere al volo
export VERSION="0.1"                          # tag pushato
export REGISTRY_URL="registry.uni.com/tylconsulting/thothai"
export FRONTEND_PORT=3040 BACKEND_PORT=8040 SQL_GENERATOR_PORT=8020 WEB_PORT=8040

# se vuoi usare lo stack semplice (env_file .env.docker)
./stackswarm.sh

# se vuoi usare lo stack completo con secrets/config esterni:
# export STACK_FILE="docker-stack.yml"
# ./stackswarm.sh
```

Verifica:

```bash
docker stack services thoth
docker stack ps thoth
```

## Note rapide

- Lo stack “semplice” (`docker-stack-simple.yml`) non richiede secrets/config esterni, ma usa `.env.docker` e `config.yml.local` copiati localmente.
- Per cambiare porte o tag, esporta le variabili prima di lanciare `stackswarm.sh`.
- Assicurati di pushare con lo stesso tag che poi imposti in `VERSION` sul server.
