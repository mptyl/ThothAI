# ThothAI Unified Project - Migration Complete

## ✅ Lavoro Completato

### 1. Struttura Directory Creata
```
/Users/mp/Thoth/
├── backend/          ✅ Copia completa di thoth_be (1.1GB)
├── frontend/         ✅ Copia completa di thoth_ui (1.5GB)
├── docker/           ✅ Dockerfiles ottimizzati
├── scripts/          ✅ Script di utilità
├── exports/          ✅ Directory I/O
├── logs/             ✅ Logs unificati
├── data/             ✅ Dati condivisi
├── thoth_be/         ✅ INTATTO (backup)
└── thoth_ui/         ✅ INTATTO (backup)
```

### 2. File di Configurazione
- `.env.local` - Configurazione sviluppo locale
- `.env.docker` - Configurazione Docker production
- `.env.template` - Template per utenti

### 3. Docker Setup
- `docker-compose.yml` - Orchestrazione servizi
- `docker/backend.Dockerfile` - Multi-stage build backend
- `docker/frontend.Dockerfile` - Multi-stage build frontend
- `docker/sql-generator.Dockerfile` - SQL generator
- `docker/proxy.Dockerfile` - Nginx proxy
- `docker/unified.Dockerfile` - Immagine singola all-in-one
- `docker/nginx.conf` - Configurazione Nginx
- `docker/supervisord.conf` - Gestione processi

### 4. Script Utilità
- `scripts/build-unified.sh` - Build e pubblicazione Docker Hub
- `scripts/test-local.sh` - Test locale
- `scripts/start.sh` - Avvio backend
- `scripts/crontab` - Scheduled tasks

### 5. Documentazione
- `README.md` - Documentazione principale
- `.gitignore` - Git ignore unificato
- `LICENSE.md` - Licenza MIT

## 🚀 Prossimi Passi

### Test Locale (Opzionale)
```bash
# Test della configurazione locale
cd /Users/mp/Thoth
./scripts/test-local.sh
```

### Build e Test Docker

#### Opzione 1: Docker Compose (Servizi Separati)
```bash
# Build di tutti i servizi
docker-compose build

# Avvio in background
docker-compose up -d

# Verifica stato
docker-compose ps

# Visualizza logs
docker-compose logs -f

# Stop
docker-compose down
```

#### Opzione 2: Immagine Unificata (per Docker Hub)
```bash
# Build immagine unificata
docker build -f docker/unified.Dockerfile -t thoth:latest .

# Test locale
docker run -d \
  --name thoth-test \
  -p 80:80 \
  -p 8040:8040 \
  -p 3001:3001 \
  -p 8005:8005 \
  -v $(pwd)/exports:/exports \
  -v $(pwd)/logs:/logs \
  -v $(pwd)/data:/data \
  --env-file .env.docker \
  thoth:latest

# Verifica
curl http://localhost/health
curl http://localhost:8040/admin/
curl http://localhost:3001/
```

### Pubblicazione su Docker Hub
```bash
# Login Docker Hub
docker login

# Tag e push
docker tag thoth:latest marcopancotti/thoth:latest
docker push marcopancotti/thoth:latest

# O usa lo script
./scripts/build-unified.sh v1.0.0
```

## 📝 Note Importanti

### Configurazione API Keys
Prima di avviare, assicurati di configurare le API keys nel file `.env.docker`:
- OPENAI_API_KEY
- GEMINI_API_KEY
- EMBEDDING_API_KEY
- LOGFIRE_TOKEN

### Porte Utilizzate
- 80: Frontend principale
- 8040: Backend API/Admin
- 3001: Frontend diretto
- 8005: SQL Generator
- 6333: Qdrant (interno)
- 5432: PostgreSQL (interno)

### Directory Persistenti
- `./exports`: File esportati
- `./logs`: Log applicazione
- `./data`: Database e dati

## 🔧 Troubleshooting

### Errore porte già in uso
```bash
# Cambia le porte nel file .env.docker
WEB_PORT=8080
BACKEND_PORT=8041
FRONTEND_PORT=3002
SQL_GENERATOR_PORT=8006
```

### Permessi file
```bash
# Fix permessi
chmod -R 755 exports logs data
chmod +x scripts/*.sh
```

### Reset completo
```bash
# Stop e rimuovi tutto
docker-compose down -v
docker system prune -a
rm -rf data/* logs/* exports/*
```

## ✨ Struttura Finale

Il progetto unificato ThothAI è ora pronto per:
1. ✅ Sviluppo locale
2. ✅ Deployment Docker
3. ✅ Pubblicazione su Docker Hub
4. ✅ Distribuzione agli utenti finali

I progetti originali `thoth_be` e `thoth_ui` sono stati preservati come backup.

## 📞 Supporto

Per problemi o domande:
- GitHub Issues: https://github.com/mptyl/ThothAI/issues
- Email: marco.pancotti@thoth.ai

---
Migration completed successfully on $(date)