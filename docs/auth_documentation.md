# Documentazione Sistema di Autenticazione ThothAI

Questo documento fornisce una panoramica tecnica dettagliata di come è gestita l'autenticazione all'interno dell'ecosistema ThothAI.

## 1. Panoramica Architetturale

ThothAI utilizza un approccio **ibrido e centralizzato** per la gestione dell'identità, progettato per supportare sia l'autenticazione locale che la federazione con Identity Provider (IdP) esterni, in particolare Microsoft Entra ID.

Il sistema si basa su due componenti principali:
1.  **ThothAI Auth Hub (Backend Django)**: Agisce come *Identity Provider* e *Service Provider* centrale. Gestisce la logica OIDC, la validazione dei token, la gestione delle sessioni e la sincronizzazione di ruoli e gruppi.
2.  **Athena Frontend (Next.js)**: Fornisce l'interfaccia utente unificata per il login e gestisce lo stato dell'autenticazione lato client tramite token e cookie di sessione condivisi.

### Caratteristiche Chiave
*   **Supporto Multi-Mode**: Configurabile come *Native* (solo DB locale), *Single IdP* (redirect automatico a Entra ID), o *Multi* (scelta utente).
*   **Unified Login Bridge**: Un'unica interfaccia di login (Next.js) gestisce l'accesso a tutti i servizi, incluso l'Admin Panel di Django.
*   **Gestione Ruoli Dinamica**: I ruoli (Roles) di Microsoft Entra ID vengono mappati automaticamente ai Gruppi (Groups) di Django al login.
*   **Sessione Condivisa**: Utilizza cookie di sessione (`thoth_sessionid`) con policy `SameSite=Lax` per permettere la comunicazione trasparente tra Frontend e Backend su porte diverse.

---

## 2. Flusso di Autenticazione

### 2.1. Login OIDC (Microsoft Entra ID)
Il flusso principale per gli utenti aziendali sfrutta OpenID Connect.

1.  **Inizio**: L'utente clicca su "Accedi con Microsoft" nel frontend Next.js.
2.  **Redirect**: Il frontend invoca `loginWithOIDC` (`frontend/lib/auth-context.tsx`), che reindirizza l'utente all'endpoint di `django-allauth`:
    ```
    {BACKEND_URL}/accounts/openid_connect/login/?process=login&provider_id=microsoft&next={FRONTEND_URL}
    ```
3.  **Auth Esterna**: L'utente si autentica su Microsoft Entra ID.
4.  **Callback & Adattamento**:
    *   Entra ID reindirizza al Backend Django.
    *   Django valida il token ID.
    *   Viene eseguito `ThothSocialAccountAdapter.pre_social_login`:
        *   Cerca un utente locale esistente con la stessa email.
        *   Se trovato, collega l'account social all'utente locale (Account Linking).
        *   Se non trovato, crea un nuovo utente.
    *   Viene eseguito `ThothSocialAccountAdapter.save_user`:
        *   Sincronizza i dati anagrafici (Nome, Cognome, Email).
        *   Sincronizza i Ruoli e i Gruppi da Entra ID ai Gruppi Django (vedi *Gestione Ruoli*).
5.  **Creazione Sessione**: Django crea una sessione server-side e imposta il cookie `thoth_sessionid`.
6.  **Ritorno al Frontend**: L'utente viene reindirizzato al Frontend autenticato.

### 2.2. Login Nativo (Username/Password)
Per amministratori locali o ambienti senza IdP esterno.

1.  L'utente inserisce le credenziali nel form Next.js.
2.  Il frontend chiama `POST /api/login` sul Backend.
3.  Il Backend valida le credenziali.
4.  Ritorna un Token di autenticazione e imposta il cookie di sessione.
5.  Il frontend memorizza il token (localStorage) e aggiorna lo stato dell'AuthContext.

### 2.3. SSO per Django Admin
Il sistema inibisce l'accesso diretto alla pagina di login standard di Django (`/admin/login`).

1.  Il middleware `UnifiedLoginMiddleware` intercetta le richieste a `/accounts/login/` o `/admin/login`.
2.  Reindirizza l'utente alla pagina di login unificata del Frontend (`UNIFIED_LOGIN_URL`).
3.  Dopo l'autenticazione sul frontend, se l'utente deve accedere all'admin, viene passato un token one-time o utilizzata la sessione condivisa per garantire l'accesso trasparente (`AdminCallbackView`).

---

## 3. Configurazione e Codice

La configurazione è centralizzata in `config.yml.local` e propagata via variabili d'ambiente.

### 3.1. Variabili Chiave (`backend/Thoth/settings.py`)
```python
# Modalità Autenticazione
AUTH_MODE = os.environ.get("AUTH_MODE", "native") # native | single_idp | multi

# Mapping Ruoli (Definito in config.yml.local)
IDP_ROLE_MAPPING = { "EntraRole": "DjangoGroup", ... }

# Provider OIDC (Configurazione dinamica)
SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": "microsoft",
                "name": "Microsoft Entra ID",
                "client_id": "...",
                "secret": "...",
                "settings": { "server_url": "..." }
            }
        ]
    }
}
```

### 3.2. Adattatore Social (`backend/thoth_core/adapters.py`)
La classe `ThothSocialAccountAdapter` è il cuore della logica di sincronizzazione:

*   **Linking Automatico**: Evita duplicati controllando l'email prima di creare un nuovo utente.
*   **Normalizzazione Claims**: Gestisce le differenze tra i vari IdP per estrarre email e username (spesso basato sull'UPN).
*   **Sync Ruoli**:
    ```python
    def _sync_roles(self, user, sociallogin):
        roles = self._get_roles(sociallogin) # Estrae 'roles' dal token
        role_mapping = getattr(settings, 'IDP_ROLE_MAPPING', {})
        for role in roles:
            # Mappa il ruolo Entra nel gruppo Django corrispondente
            group_name = role_mapping.get(role, role)
            user.groups.add(Group.objects.get_or_create(name=group_name)[0])
    ```

### 3.3. Frontend Context (`frontend/lib/auth-context.tsx`)
Gestisce lo stato lato client:
*   Chiede la configurazione al backend (`/api/auth-config`) all'avvio per decidere se mostrare il form nativo o i bottoni social.
*   Gestisce il ciclo di vita del token e la persistenza della sessione.

---

## 4. API Security

Per le chiamate API Programmatiche o Service-to-Service:

1.  **Token Authentication**: Header `Authorization: Token <token_key>`. Usato dal frontend per chiamate API protette.
2.  **API Key**: Header `X-API-KEY`. Usato per integrazioni system-to-system, validato da `ApiKeyAuthentication` (`backend/thoth_core/authentication.py`).
3.  **Session Authentication**: Fallback per chiamate browser-based (es. download file, admin panel).

## 5. Troubleshooting Comune

*   **Redirect Loop**: Spesso causato da `UNIFIED_LOGIN_URL` errato o mancata corrispondenza del dominio dei cookie. Verificare `SESSION_COOKIE_DOMAIN` e `ALLOWED_HOSTS`.
*   **Ruoli non sincronizzati**: Verificare che il claim `roles` sia presente nel token ID di Entra (richiede configurazione lato App Registration su Azure/Entra).
*   **Login Admin fallito**: Assicurarsi che l'utente abbia `is_staff=True`. Gli utenti creati via OIDC non sono staff di default a meno che un gruppo mappato non dia permessi specifici o lo si assegni manualmente.
