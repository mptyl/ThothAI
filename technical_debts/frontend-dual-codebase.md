# Tech Debt: Due codebase frontend non sincronizzate

## Problema

Il progetto ThothAI mantiene **due frontend Next.js distinti**:

| Codebase | Repo | Branch | Porta locale |
|----------|------|--------|-------------|
| `ThothAI/frontend/` | `ThothAI.git` (monorepo) | `main` | 3000 (prod Docker) |
| `thoth_ui/` | `ThothUi.git` | `ft02` | 3040 (dev locale) |

Essendo repository separati, **le modifiche a `ThothAI/frontend/` non si propagano automaticamente a `thoth_ui/`** e viceversa. Ogni feature o bugfix deve essere applicato manualmente in entrambi i posti.

### Esempio concreto che ha originato questo documento

Aprile 2025: l'integrazione SSO Athena → ThothAI (pagina `/auth/supabase` e route `/api/supabase-auth`) era presente e funzionante in `ThothAI/frontend/`, ma completamente assente in `thoth_ui/`. Il risultato era un errore **404** cliccando su "ThothAI" dal pannello Athena in ambiente di sviluppo locale, mentre in produzione tutto funzionava correttamente.

**File coinvolti nella discrepanza:**
- `app/auth/supabase/page.tsx` — pagina ricevitore postMessage SSO
- `app/api/config/route.ts` — endpoint per origine Athena consentita (multi-origin)
- `app/api/supabase-auth/route.ts` — proxy server-side verso Django `/api/supabase-auth`

---

## Rischio

| Impatto | Probabilità | Priorità |
|---------|-------------|----------|
| Bug silenti in dev che non compaiono in prod (o viceversa) | Alta | **Alta** |
| Regressioni difficili da diagnosticare perché i due repo divergono | Media | Alta |

---

## Soluzione a breve termine (workaround attuale)

Prima di lavorare su una feature che tocca il frontend:

1. Verificare se il file esiste in **entrambi** i frontend
2. Se manca in `thoth_ui/`, copiarlo da `ThothAI/frontend/`
3. Committare i file in `ThothAI/frontend/` e copiarli manualmente in `thoth_ui/`

Checklist file da tenere allineati:

```
app/auth/supabase/page.tsx
app/auth/callback/page.tsx
app/api/config/route.ts
app/api/supabase-auth/route.ts
```

---

## Soluzione a lungo termine

Scegliere **una** delle seguenti strategie:

### Opzione A — Unificare in un unico repo (Raccomandata)
Eliminare `thoth_ui/` come repo separato e usare solo `ThothAI/frontend/` anche per lo sviluppo locale. Adattare i `docker-compose` e gli script di avvio per puntare all'unico sorgente.

### Opzione B — Git subtree / submodule
Trasformare `ThothAI/frontend/` in un git subtree o submodule dentro `ThothUi.git`, in modo che un `git subtree pull` sincronizzi le modifiche.

### Opzione C — Script di sync automatico
Creare uno script `scripts/sync-frontend.sh` che copia selettivamente i file condivisi da `ThothAI/frontend/` a `thoth_ui/` e lo integra nei workflow CI/CD.

---

## Riferimenti

- Commit che ha introdotto la discrepanza: _da identificare_
- Issue correlata: _da aprire_
- Data rilevamento: 2026-03-02
