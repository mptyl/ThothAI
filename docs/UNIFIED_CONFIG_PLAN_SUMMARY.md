# Piano Unificazione Configurazione - Riassunto Esecutivo

## 🎯 Obiettivo
Rendere `config.yml.local` l'**unica fonte di verità** per la configurazione, sia per Docker che per la run locale.

## 📊 Situazione Attuale vs Desiderata

| Aspetto | Attuale | Desiderato |
|---------|---------|------------|
| **Docker** | `config.yml.local` → `.env.docker` | ✅ Stesso |
| **Locale** | `.env.local` manuale | `config.yml.local` → `.env.local` (auto) |
| **Manutenzione** | 2 file separati da editare | 1 solo file da editare |
| **Rischio errori** | Alto (disallineamento) | Basso (single source) |

## 🏗️ Architettura Soluzione

```
config.yml.local (SINGLE SOURCE OF TRUTH)
         ↓
    ┌────┴─────┐
    ↓          ↓
install.sh   start-all.sh
    ↓          ↓
installer.py  generate_env_local.py
    ↓          ↓
    └─→ env_generator_base.py ←─┘
         ↓          ↓
    .env.docker  .env.local
```

## 📦 Deliverables

### Nuovi File
1. **`scripts/env_generator_base.py`** - Classe base con logica condivisa
2. **`scripts/generate_env_local.py`** - Generatore per ambiente locale
3. **`scripts/migrate_env_to_config.py`** - Migrazione setup esistenti
4. **`docs/CONFIGURATION.md`** - Guida completa configurazione

### File Modificati
1. **`start-all.sh`** - Auto-genera `.env.local` da config
2. **`scripts/installer.py`** - Refactoring per usare classe base
3. **`README.md`** - Aggiornamento sezione configurazione
4. **`AGENTS.md`** - Aggiornamento workflow locale

## 🔑 Caratteristiche Chiave

### 1. Auto-Generazione Intelligente
```bash
# start-all.sh ora fa:
if config.yml.local è più recente di .env.local:
    ↳ Rigenera .env.local automaticamente
    ↳ Preserva segreti esistenti
    ↳ Backup automatico
```

### 2. Logica Condivisa (DRY)
```python
class EnvGeneratorBase:
    - generate_ai_providers_env()
    - generate_embedding_env()
    - generate_backend_ai_env()
    - generate_monitoring_env()
    - generate_ports_env(mode='docker'|'local')  # ← Adatta porte
    - generate_paths_env(mode='docker'|'local')  # ← Adatta path
    - generate_runtime_env()
    - generate_relevance_guard_env()
    - generate_security_env()
```

### 3. Mappatura Porte Automatica

| Variabile | Docker | Locale |
|-----------|--------|--------|
| `FRONTEND_PORT` | 3000 | 3200 |
| `BACKEND_PORT` | 8000 | 8200 |
| `SQL_GENERATOR_PORT` | 8001 | 8180 |
| `QDRANT_PORT` | 6333 | 6334 |

### 4. Gestione Path Automatica

| Variabile | Docker | Locale |
|-----------|--------|--------|
| `DB_ROOT_PATH` | `/app/data` | `./data` |
| `EXPORTS_DIR` | `/app/exports` | `./exports` |
| `LOGS_DIR` | `/app/logs` | `./logs` |

## ✅ Vantaggi

| Vantaggio | Impatto |
|-----------|---------|
| **Single Source of Truth** | ⭐⭐⭐ Critico |
| **Consistenza Config** | ⭐⭐⭐ Alto |
| **Manutenibilità** | ⭐⭐⭐ Alto |
| **UX Migliorata** | ⭐⭐ Medio |
| **Riduzione Errori** | ⭐⭐⭐ Alto |
| **Retrocompatibilità** | ⭐⭐ Medio |

## 🎬 Implementazione in 5 Fasi

### Fase 1: Core Logic (3-4h)
- Creare `env_generator_base.py` con logica condivisa
- Creare `generate_env_local.py` per ambiente locale
- Test generazione da config.yml.local

### Fase 2: Integration (1h)
- Modificare `start-all.sh` per auto-generazione
- Refactoring `installer.py` per usare classe base
- Test flussi Docker e locale

### Fase 3: Migration Support (1-2h)
- Script migrazione da `.env.local` esistente
- Avvisi e backup automatici
- Test migrazione

### Fase 4: Documentation (1-2h)
- Aggiornare README, AGENTS.md
- Creare guida configurazione completa
- Update templates con deprecation notice

### Fase 5: Testing (2-3h)
- Test installazione fresh (Docker + locale)
- Test migrazione setup esistenti
- Verifica tutti i servizi
- Test reload dopo modifica config

## ⏱️ Timeline

```
Totale: 7-11 ore
├─ Fase 1-2 (Core): 4-5h ████████░░
├─ Fase 3 (Migration): 1-2h ██░░
├─ Fase 4 (Docs): 1-2h ██░░
└─ Fase 5 (Testing): 2-3h ███░
```

## 🚦 Edge Cases Gestiti

✅ Config.yml.local mancante → errore chiaro con istruzioni  
✅ Config.yml.local invalido → validazione preventiva  
✅ .env.local modificato manualmente → backup + avviso  
✅ Porte in conflitto → verifica + suggerimenti  
✅ API keys mancanti → validazione + errori chiari  
✅ Segreti esistenti → preservati durante rigenerazione  

## 📝 Workflow Utente Finale

### Prima (Attuale)
```bash
1. Copia .env.local.template → .env.local
2. Edita manualmente .env.local
3. Copia config.yml → config.yml.local  
4. Edita manualmente config.yml.local
5. ./start-all.sh o ./install.sh
   ⚠️ Rischio: config disallineati!
```

### Dopo (Proposto)
```bash
1. Copia config.yml → config.yml.local
2. Edita config.yml.local (UNICO FILE)
3. ./start-all.sh o ./install.sh
   ✅ .env.local/.env.docker generati automaticamente
   ✅ Sempre allineati con config.yml.local
```

## 🎯 KPIs Successo

| Metrica | Target |
|---------|--------|
| File da editare manualmente | 1 (solo config.yml.local) |
| Tempo setup nuova istanza | -30% |
| Errori configurazione | -80% |
| Linee codice duplicate | -50% |
| Coverage test | >90% |

## 🔄 Retrocompatibilità

**✅ Garantita per utenti esistenti:**
- `.env.local` manuale continua a funzionare durante transizione
- Script migrazione automatica disponibile
- Backup automatico prima di sovrascrivere
- Avvisi chiari all'utente

## 📚 Riferimenti

- **Piano Dettagliato:** `PLANNING.md`
- **Config Template:** `config.yml`
- **Installer Attuale:** `scripts/installer.py:317-432`
- **Memoria Logging:** `fed87547-1713-4731-80c5-c38f7f56a952`

## ✋ Decision Points

Prima di procedere con l'implementazione, confermare:

- [ ] Approvo l'architettura proposta
- [ ] Approvo il workflow di auto-generazione
- [ ] Approvo la gestione retrocompatibilità
- [ ] Approvo la timeline stimata
- [ ] Pronto per implementazione Step 1

---

**Status:** 📋 Piano completato, in attesa di approvazione per implementazione
