# Piano di Implementazione: Moderna Interfaccia Admin per Thoth Backend

## Analisi del Sistema Esistente

### Modelli Django Identificati
**Modelli Core (thoth_core/models.py)**:
- **User & Group**: Gestione utenti e gruppi Django standard
- **BasicAiModel**: Configurazioni base AI provider (OpenAI, Claude, Mistral, ecc.)
- **AiModel**: Istanze specifiche con parametri (temperature, max_tokens, ecc.)
- **Agent**: Agenti AI specializzati (SQL generation, validation, ecc.)
- **SqlDb**: Connessioni database SQL (PostgreSQL, MySQL, Oracle, ecc.)
- **SqlTable & SqlColumn**: Metadati tabelle e colonne con commenti AI
- **Relationship**: Relazioni FK/PK tra tabelle
- **VectorDb**: Configurazioni database vettoriali (Qdrant, Pinecone, ecc.)
- **Workspace**: Workspace utente con configurazione agenti complessa
- **Setting**: Impostazioni sistema e parametri LSH
- **GroupProfile**: Profili permissions per gruppi

### Stack Tecnologico Attuale
- **Backend**: Django 5.2 + DRF 3.16 + PostgreSQL
- **Frontend Esistente**: Next.js 14 + TypeScript + Tailwind CSS
- **API**: REST con serializers completi già implementati
- **Autenticazione**: Django Allauth + API key authentication

## Strategia di Implementazione

### Fase 1: Foundation & Architecture (Settimana 1-2)
**1.1 Setup Base Admin Interface**
- Creare routing `/admin` separato dal chatbot
- Implementare layout base con sidebar navigation
- Setup componenti base (DataTable, Forms, Modals)
- Integrare autenticazione esistente

**1.2 Core Components Library**
- **AdminDataTable**: Tabelle con sorting, filtering, pagination
- **AdminForm**: Form dinamiche based on model schema
- **AdminModal**: Modal per create/edit/delete operations
- **AdminLayout**: Layout consistente per tutte le sezioni

### Fase 2: User & Group Management (Settimana 3)
**2.1 User Administration**
- Lista utenti con search/filter (username, email, groups)
- Form creazione/modifica utente
- Gestione password e permissions
- Bulk operations (attiva/disattiva, assign groups)

**2.2 Group & GroupProfile Management**
- Gestione gruppi con permissions
- Form per GroupProfile settings
- Preview permissions in tempo reale
- Integrazione con workspace assignments

### Fase 3: AI Models & Agents (Settimana 4-5)
**3.1 BasicAiModel Management**
- CRUD per AI providers configuration
- Validation API keys real-time
- Template per configurazioni comuni
- Import/export configurations

**3.2 AiModel Management**
- Form dinamiche per parametri provider-specifici
- Validation ranges (temperature, tokens, ecc.)
- Test connection functionality
- Clone/duplicate models

**3.3 Agent Management**
- Form specializzate per tipo agent
- Prompt editor con syntax highlighting
- Agent testing interface
- Agent performance metrics

### Fase 4: Database Management (Settimana 6-7)
**4.1 SqlDb Administration**
- Connection manager con test connectivity
- Schema browser integration
- Database type-specific configurations
- Connection pooling settings

**4.2 Table & Column Management**
- Visual schema browser
- Bulk edit column descriptions
- AI comment generation interface
- Relationship visualization (ERD-like)

**4.3 VectorDb Management**
- Provider-specific configuration forms
- Collection/index management
- Vector search testing interface
- Performance monitoring

### Fase 5: Advanced Management (Settimana 8-9)
**5.1 Workspace Management**
- Complex form con agent assignments
- Workspace templates e cloning
- User assignment bulk operations
- Status monitoring (preprocessing, comments)

**5.2 Settings & System Config**
- Global settings management
- LSH parameters tuning interface
- System health dashboard
- Performance monitoring

### Fase 6: Advanced Features (Settimana 10-11)
**6.1 Bulk Operations**
- Import/export CSV functionality
- Batch processing interface
- Progress tracking per long operations
- Error handling e rollback

**6.2 Monitoring & Analytics**
- System usage analytics
- Performance metrics dashboard
- Error logging e debugging tools
- Audit trail per admin operations

## Architettura Tecnica

### Component Structure
```
/app/admin/
├── layout.tsx                 # Admin layout con sidebar
├── page.tsx                   # Admin dashboard
├── users/
│   ├── page.tsx              # Users list
│   ├── [id]/page.tsx         # User detail/edit
│   └── new/page.tsx          # New user form
├── groups/
├── ai-models/
├── agents/
├── databases/
├── workspaces/
└── settings/

/components/admin/
├── core/
│   ├── AdminDataTable.tsx
│   ├── AdminForm.tsx
│   ├── AdminModal.tsx
│   └── AdminLayout.tsx
├── forms/
│   ├── UserForm.tsx
│   ├── AiModelForm.tsx
│   ├── AgentForm.tsx
│   └── WorkspaceForm.tsx
└── tables/
    ├── UsersTable.tsx
    ├── ModelsTable.tsx
    └── AgentsTable.tsx
```

### API Integration Strategy
- Estendere serializers esistenti per admin needs
- Aggiungere endpoints per bulk operations
- Real-time validation per forms complesse
- WebSocket per status updates su long operations

### Model-Driven Architecture
**Dynamic Form Generation**:
- Schema introspection da Django models
- Field type mapping (CharField → Input, ForeignKey → Select)
- Validation rules auto-generated
- Dynamic fieldsets basati su model structure

**Auto-generated Tables**:
- Column definitions da model fields
- Sorting/filtering auto-configurato
- Relationship display con foreign keys
- Action buttons context-aware

### Security & Permissions
- Role-based access control
- Field-level permissions
- Audit logging per admin actions
- CSRF protection e input validation

## Implementazione Modello per Modello

### Priorità di Implementazione

#### 1. User & Group (Foundation)
**Modelli**: User, Group, GroupProfile
**Complessità**: Bassa
**Funzionalità**:
- Lista utenti con filtri (attivo, gruppo, data registrazione)
- Form utente con validazione email
- Gestione gruppi e permissions
- Profile settings per gruppo

#### 2. BasicAiModel & AiModel (Core AI)
**Modelli**: BasicAiModel, AiModel
**Complessità**: Media
**Funzionalità**:
- Provider selection con configurazioni specifiche
- API key management con mascheramento
- Parameter validation (temperature, tokens)
- Test connection con provider

#### 3. Agent (AI Logic)
**Modelli**: Agent
**Complessità**: Alta
**Funzionalità**:
- Type-specific forms (SQL generation, validation, ecc.)
- Prompt editor avanzato
- Agent testing interface
- Performance metrics

#### 4. SqlDb & VectorDb (Database Config)
**Modelli**: SqlDb, VectorDb
**Complessità**: Alta
**Funzionalità**:
- Connection string builder
- Test connectivity
- Schema introspection
- Multi-database support

#### 5. SqlTable & SqlColumn (Metadata)
**Modelli**: SqlTable, SqlColumn, Relationship
**Complessità**: Media
**Funzionalità**:
- Schema visualization
- Bulk comment editing
- Relationship management
- AI comment generation

#### 6. Workspace (Complex Configuration)
**Modelli**: Workspace
**Complessità**: Molto Alta
**Funzionalità**:
- Complex agent assignments
- User management
- Status monitoring
- Template system

#### 7. Setting (System Config)
**Modelli**: Setting
**Complessità**: Media
**Funzionalità**:
- Global system settings
- LSH parameter tuning
- Model assignments
- Language settings

## Timeline Dettagliato

### Sprint 1-2: Foundation (40h)
- Admin layout e navigation
- Core components (DataTable, Form, Modal)
- Authentication integration
- User/Group basic CRUD

### Sprint 3: User Management (20h)
- Advanced user management
- Group permissions
- GroupProfile interface
- Bulk operations

### Sprint 4-5: AI Configuration (40h)
- BasicAiModel management
- AiModel complex forms
- Agent management
- Testing interfaces

### Sprint 6-7: Database Management (40h)
- SqlDb connection management
- VectorDb configuration
- Schema browsing
- Table/Column management

### Sprint 8-9: Advanced Features (40h)
- Workspace management completo
- Settings interface
- Status monitoring
- Templates system

### Sprint 10-11: Polish & Analytics (40h)
- Bulk operations
- Analytics dashboard
- Performance monitoring
- Error handling e debugging

**Totale Stimato**: ~220 ore di sviluppo

## Caratteristiche Model-Driven

### Auto-Discovery
- Scan Django models per field types
- Relationship detection automatico
- Validation rules extraction
- Help text e descriptions

### Dynamic Forms
- Field rendering basato su type
- Foreign key dropdowns
- Many-to-many selectors
- Complex nested forms

### Smart Tables
- Column auto-generation
- Sorting/filtering automatico
- Relationship links
- Action buttons context-aware

### Validation
- Client-side validation da Django constraints
- Real-time API validation
- Cross-field validation
- Error display standardizzato

## Benefits Architettura

### Maintainability
- Aggiungere nuovo modello richiede minimal code
- Consistent patterns across admin
- Centralized validation logic
- Reusable components

### User Experience
- Modern interface vs Django admin
- Responsive design
- Real-time feedback
- Intuitive navigation

### Developer Experience
- TypeScript type safety
- Component reusability
- Clear separation of concerns
- Easy testing

### Performance
- Client-side pagination
- Lazy loading
- Optimistic updates
- Efficient API calls

## Note di Implementazione

### Fase di Transizione
- Admin Django rimane disponibile during development
- Feature parity validation
- User acceptance testing
- Gradual migration

### Compatibility
- API backward compatibility
- Database schema unchanged
- Authentication integration
- Permission system alignment

### Future Extensions
- Plugin system per custom fields
- Workflow automation
- Advanced analytics
- Mobile app support

Questo piano garantisce una moderna interfaccia admin che mantiene la flessibilità model-driven di Django Admin mentre fornisce un'esperienza utente moderna e coerente con il resto dell'applicazione Thoth.