# Demo Environment Setup Plan

## Obiettivo
Creare automaticamente un ambiente demo completo per l'utente demo durante l'inizializzazione del container Docker, permettendo di testare immediatamente il sistema ThothAI con il database California Schools.

## Sequenza di Caricamento Dati

### 1. Import Gruppi (Prerequisito)
**Comando**: `python manage.py import_groups --source docker`
- Crea i gruppi di sistema necessari (Admin, Editor, Technical User)
- Deve essere eseguito PRIMA della creazione degli utenti per permettere l'associazione

### 2. Creazione Superuser (Admin e Demo)
**Script**: Già implementato in `backend/scripts/start.sh`
- Legge configurazione da `config.yml.local`
- Crea utente admin con credenziali dal config
- Crea utente demo con credenziali dal config
- Entrambi sono superuser con accesso completo

### 3. Associazione Utenti ai Gruppi
**Nuovo Script Python**: `backend/scripts/assign_user_groups.py`
```python
# Associa admin e demo ai gruppi:
# - Admin group (ID: 1)
# - Editor group (da identificare)
# - Technical User group (da identificare)
```

### 4. Caricamento Defaults di Sistema
**Comando**: `python manage.py load_defaults --source docker`
- Importa configurazioni AI Models
- Importa Vector Databases
- Importa Agents
- Importa Settings
- Importa database structure (California Schools)
- Importa Workspaces

### 5. Associazione Demo User al Workspace California Schools
**Nuovo Script Python**: `backend/scripts/setup_demo_workspace.py`
```python
# - Identifica workspace "California Schools" (ID: 4 da workspace.csv)
# - Associa utente demo come utente abilitato
# - Imposta demo come utente default del workspace
# - Aggiorna il workspace nel database
```

### 6. Caricamento Evidence e SQL Examples per Demo
**Script Python Unificato**: `backend/scripts/load_demo_data.py`
```python
# Per il workspace California Schools:
# a) Upload Evidence
from thoth_ai_backend.preprocessing.upload_evidence import upload_evidence_to_vectordb
upload_evidence_to_vectordb(workspace_id=4)

# b) Upload SQL Examples/Questions
from thoth_ai_backend.preprocessing.upload_questions import upload_questions_to_vectordb
upload_questions_to_vectordb(workspace_id=4)

# c) Run Preprocessing
from thoth_ai_backend.async_tasks import run_preprocessing_task
run_preprocessing_task(workspace_id=4)
```

## Modifiche Necessarie

### 1. Aggiornamento `backend/scripts/start.sh`
Aggiungere dopo la creazione degli utenti (riga ~164):

```bash
# Load system defaults if in Docker environment
if [ -n "$DOCKER_ENV" ] && [ -f "/app/setup_csv/docker/groups.csv" ]; then
    echo "Loading system defaults for Docker environment..."
    
    # 1. Import groups
    echo "Importing groups..."
    /app/.venv/bin/python manage.py import_groups --source docker || echo "Groups import completed"
    
    # 2. Assign users to groups (after user creation)
    echo "Assigning users to groups..."
    /app/.venv/bin/python /app/scripts/assign_user_groups.py || echo "User group assignment completed"
    
    # 3. Load all system defaults
    echo "Loading system defaults..."
    /app/.venv/bin/python manage.py load_defaults --source docker || echo "Defaults loaded"
    
    # 4. Setup demo workspace
    echo "Setting up demo workspace..."
    /app/.venv/bin/python /app/scripts/setup_demo_workspace.py || echo "Demo workspace setup completed"
    
    # 5. Load demo data (evidence, examples, preprocessing)
    echo "Loading demo data for California Schools..."
    /app/.venv/bin/python /app/scripts/load_demo_data.py || echo "Demo data loaded"
    
    echo "Demo environment setup completed!"
fi
```

### 2. Creazione Script `backend/scripts/assign_user_groups.py`
```python
#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thoth_ai_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User, Group

def assign_user_groups():
    """Assign admin and demo users to appropriate groups."""
    
    # Get or create groups
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    editor_group, _ = Group.objects.get_or_create(name='Editor')
    tech_user_group, _ = Group.objects.get_or_create(name='Technical User')
    
    # Assign admin user to groups
    try:
        admin_user = User.objects.get(username='admin')
        admin_user.groups.add(admin_group, editor_group, tech_user_group)
        print(f"Admin user assigned to groups: Admin, Editor, Technical User")
    except User.DoesNotExist:
        print("Admin user not found")
    
    # Assign demo user to groups
    try:
        demo_user = User.objects.get(username='demo')
        demo_user.groups.add(admin_group, editor_group, tech_user_group)
        print(f"Demo user assigned to groups: Admin, Editor, Technical User")
    except User.DoesNotExist:
        print("Demo user not found")

if __name__ == "__main__":
    assign_user_groups()
```

### 3. Creazione Script `backend/scripts/setup_demo_workspace.py`
```python
#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thoth_ai_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User
from thoth_core.models import Workspace

def setup_demo_workspace():
    """Setup California Schools workspace for demo user."""
    
    try:
        # Get demo user
        demo_user = User.objects.get(username='demo')
        
        # Get California Schools workspace (ID: 4 from CSV)
        workspace = Workspace.objects.get(name='California Schools')
        
        # Add demo user to workspace users
        workspace.users.add(demo_user)
        
        # Set demo as default user for this workspace
        workspace.default_workspace.add(demo_user)
        
        workspace.save()
        
        print(f"Demo user associated with California Schools workspace")
        print(f"Workspace ID: {workspace.id}")
        print(f"SQL Database: {workspace.sql_db.name if workspace.sql_db else 'Not configured'}")
        
    except User.DoesNotExist:
        print("Demo user not found")
    except Workspace.DoesNotExist:
        print("California Schools workspace not found")
    except Exception as e:
        print(f"Error setting up demo workspace: {e}")

if __name__ == "__main__":
    setup_demo_workspace()
```

### 4. Creazione Script `backend/scripts/load_demo_data.py`
```python
#!/usr/bin/env python
# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the Apache License 2.0.

import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'thoth_ai_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from thoth_core.models import Workspace
from thoth_ai_backend.preprocessing.upload_evidence import upload_evidence_to_vectordb
from thoth_ai_backend.preprocessing.upload_questions import upload_questions_to_vectordb
from thoth_ai_backend.async_tasks import run_preprocessing_task

def load_demo_data():
    """Load evidence, SQL examples and run preprocessing for California Schools workspace."""
    
    try:
        # Get California Schools workspace
        workspace = Workspace.objects.get(name='California Schools')
        workspace_id = workspace.id
        
        print(f"Loading data for workspace: {workspace.name} (ID: {workspace_id})")
        
        # 1. Upload evidence
        print("Uploading evidence...")
        try:
            successful_uploads, total_items = upload_evidence_to_vectordb(workspace_id)
            print(f"Evidence uploaded: {successful_uploads}/{total_items} items")
        except Exception as e:
            print(f"Error uploading evidence: {e}")
        
        # 2. Upload SQL examples/questions
        print("Uploading SQL examples...")
        try:
            successful_uploads, total_items = upload_questions_to_vectordb(workspace_id)
            print(f"SQL examples uploaded: {successful_uploads}/{total_items} items")
        except Exception as e:
            print(f"Error uploading SQL examples: {e}")
        
        # 3. Run preprocessing
        print("Running preprocessing...")
        try:
            # Run preprocessing synchronously for initial setup
            run_preprocessing_task(workspace_id)
            print("Preprocessing completed")
        except Exception as e:
            print(f"Error during preprocessing: {e}")
        
        print("Demo data loading completed successfully!")
        
    except Workspace.DoesNotExist:
        print("California Schools workspace not found - skipping demo data load")
    except Exception as e:
        print(f"Error loading demo data: {e}")

if __name__ == "__main__":
    load_demo_data()
```

## File di Configurazione Richiesti

### 1. `/app/setup_csv/docker/groups.csv`
- Deve contenere almeno: Admin, Editor, Technical User

### 2. `/app/data/dev_databases/dev.json`
- Deve contenere evidence e SQL examples per california_schools

### 3. `config.yml.local`
- Configurazione admin e demo users (già implementato)

## Dipendenze e Prerequisiti

1. **Database SQLite California Schools**
   - Deve essere presente in `/app/data/dev_databases/california_schools/california_schools.sqlite`
   
2. **Vector Database (Qdrant)**
   - Deve essere in esecuzione e accessibile
   - Collection `california_schools` verrà creata automaticamente

3. **File dev.json**
   - Deve contenere dati di esempio per california_schools

## Test del Setup

Per verificare che il setup sia completato correttamente:

1. **Verifica Utenti**:
   ```bash
   python manage.py shell -c "
   from django.contrib.auth.models import User
   demo = User.objects.get(username='demo')
   print(f'Demo user exists: {demo.is_superuser}')
   print(f'Groups: {list(demo.groups.values_list('name', flat=True))}')
   "
   ```

2. **Verifica Workspace**:
   ```bash
   python manage.py shell -c "
   from thoth_core.models import Workspace
   ws = Workspace.objects.get(name='California Schools')
   print(f'Workspace: {ws.name}')
   print(f'Users: {list(ws.users.values_list('username', flat=True))}')
   print(f'Default for: {list(ws.default_workspace.values_list('username', flat=True))}')
   "
   ```

3. **Verifica Vector Database**:
   - Controllare che esistano documenti nella collection california_schools
   - Verificare presenza di evidence e SQL examples

## Note Importanti

1. **Idempotenza**: Tutti gli script devono essere idempotenti (possono essere eseguiti più volte senza errori)

2. **Error Handling**: Ogni step deve gestire errori gracefully e continuare con gli step successivi

3. **Logging**: Ogni operazione deve loggare il suo stato per debugging

4. **Performance**: Il preprocessing può richiedere tempo, considerare l'esecuzione asincrona dopo il primo setup

5. **Sicurezza**: Le password degli utenti demo/admin sono configurabili tramite config.yml.local

## Timeline Implementazione

1. **Fase 1**: Creazione degli script Python (assign_user_groups.py, setup_demo_workspace.py, load_demo_data.py)
2. **Fase 2**: Modifica di start.sh per orchestrare il setup
3. **Fase 3**: Test locale del flusso completo
4. **Fase 4**: Test in ambiente Docker
5. **Fase 5**: Documentazione per l'utente finale

## Risultato Atteso

Dopo l'avvio del container Docker, l'utente demo potrà:
1. Fare login con username: demo, password: demo1234
2. Accedere al workspace California Schools
3. Eseguire query in linguaggio naturale sul database
4. Vedere esempi di query già caricate
5. Utilizzare tutte le funzionalità del sistema

Questo setup automatico ridurrà drasticamente il tempo necessario per avere un ambiente demo funzionante.