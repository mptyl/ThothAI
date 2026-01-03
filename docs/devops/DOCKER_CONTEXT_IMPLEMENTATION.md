# Copyright (c) 2025 Marco Pancotti
# This file is part of ThothAI and is released under Apache 2.0.
# See the LICENSE.md file in the project root for full license information.

# Miglioramento del Deploy Remoto con Docker Context

## Soluzione Ideale

Implementare **Docker Context** come metodo primario per il deployment remoto di ThothAI, sia per Docker Compose che per Docker Swarm.

**Perché Docker Context?**
- ✅ Nativo Docker (nessun codice custom necessario)
- ✅ Semplice: `docker context use` per switchare tra server
- ✅ Persistente: I context rimangono tra le sessioni
- ✅ Funziona per Compose e Swarm
- ✅ Debugging nativo: Comandi standard Docker senza SSH
- ✅ Multi-server facile: Gestione rapida tra produzione, staging, sviluppo
- ✅ Sicuro: SSH standard

---

## Implementazione per Docker Compose

### Aggiungere a [`docker_manager.py`](../../cli/thothai-cli/src/thothai_cli/core/docker_manager.py)

```python
def _use_docker_context(self, server: str) -> tuple[bool, str]:
    """Usa Docker Context per connessione remota."""
    clean_server = server.replace('ssh://', '')
    context_name = f"thothai-{self._get_server_hash(clean_server)}"
    
    console.print(f"[dim]Using Docker Context: {context_name}[/dim]")
    
    # Verifica se il context esiste
    result = subprocess.run(
        ['docker', 'context', 'ls', '--format', '{{.Name}}'],
        capture_output=True,
        text=True
    )
    
    existing_contexts = result.stdout.strip().split('\n')
    
    if context_name not in existing_contexts:
        # Crea il context
        console.print(f"[dim]Creating Docker Context for {clean_server}...[/dim]")
        
        create_cmd = [
            'docker', 'context', 'create', context_name,
            '--docker', f'host=ssh://{clean_server}'
        ]
        
        result = subprocess.run(create_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[yellow]Warning: Could not create Docker Context: {result.stderr}[/yellow]")
            return False, ""
        
        console.print(f"[green]✓ Docker Context created[/green]")
    else:
        console.print(f"[dim]Docker Context already exists[/dim]")
    
    # Salva il context corrente
    result = subprocess.run(
        ['docker', 'context', 'show', '--format', '{{.Name}}'],
        capture_output=True,
        text=True
    )
    previous_context = result.stdout.strip()
    
    # Usa il context
    result = subprocess.run(
        ['docker', 'context', 'use', context_name],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        console.print(f"[red]Error: Could not use Docker Context: {result.stderr}[/red]")
        return False, ""
    
    console.print(f"[green]✓ Using Docker Context: {context_name}[/green]")
    
    return True, previous_context


def _restore_docker_context(self, previous_context: str) -> bool:
    """Ripristina il context Docker precedente."""
    if not previous_context:
        return True
    
    console.print(f"[dim]Restoring Docker Context: {previous_context}[/dim]")
    
    result = subprocess.run(
        ['docker', 'context', 'use', previous_context],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        console.print(f"[yellow]Warning: Could not restore Docker Context: {result.stderr}[/yellow]")
        return False
    
    console.print(f"[green]✓ Docker Context restored[/green]")
    return True
```

### Modificare `up()` per Docker Compose

```python
def up(self, server: Optional[str] = None) -> bool:
    """Pull images and start containers."""
    previous_context = None
    
    try:
        # Usa Docker Context se server è specificato
        if server:
            success, previous_context = self._use_docker_context(server)
            if not success:
                console.print("[yellow]Warning: Docker Context failed, falling back to SSH Tunnel[/yellow]")
                # Fallback all'approccio SSH Tunnel attuale
                if not self.check_connection(server):
                    return False
        
        # ... resto del codice esistente per preparazione ...
        
        # Esegui docker compose (ora usa il context se impostato)
        console.print("\n[bold]Pulling images...[/bold]")
        result = self._run_cmd(
            ['docker', 'compose', '-f', str(self.base_dir / compose_file_to_use), 'pull'],
            server=None  # Non usare server se usiamo Docker Context
        )
        
        # ... resto del codice esistente ...
        
        return True
        
    finally:
        # Ripristina sempre il context precedente
        if previous_context:
            self._restore_docker_context(previous_context)
```

### Modificare `_run_cmd()` per supportare Docker Context

```python
def _run_cmd(self, cmd: list, server: Optional[str] = None, capture: bool = False, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run a command locally or remotely via SSH or Docker Context."""
    import os
    
    # Prepara l'ambiente
    full_env = os.environ.copy()
    
    # Load .env.docker se esiste
    env_docker_path = self.base_dir / '.env.docker'
    if env_docker_path.exists():
        try:
            from dotenv import dotenv_values
            docker_env = dotenv_values(env_docker_path)
            if docker_env:
                clean_env = {k: v for k, v in docker_env.items() if v is not None}
                full_env.update(clean_env)
        except ImportError:
            pass

    if env:
        full_env.update(env)

    # Se server è specificato, usa Docker Context (non SSH tunnel)
    if server:
        # Verifica se stiamo usando Docker Context
        result = subprocess.run(
            ['docker', 'context', 'show', '--format', '{{.Name}}'],
            capture_output=True,
            text=True
        )
        current_context = result.stdout.strip()
        
        if current_context.startswith('thothai-'):
            # Stiamo usando Docker Context, esegui localmente
            return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)
        else:
            # Fallback all'approccio SSH Tunnel attuale
            if cmd[0] == 'docker' and self._tunnel_socket:
                full_env['DOCKER_HOST'] = f"unix://{self._tunnel_socket}"
                return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)
            elif cmd[0] == 'docker':
                docker_host = server
                if not docker_host.startswith('ssh://'):
                    docker_host = f"ssh://{docker_host}"
                full_env['DOCKER_HOST'] = docker_host
                return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)
            else:
                clean_server = server.replace('ssh://', '')
                ssh_dir = Path.home() / '.ssh'
                if ssh_dir.exists() and os.access(ssh_dir, os.W_OK):
                    control_path = '~/.ssh/thothai-%C'
                else:
                    control_path = f'/tmp/thothai-{hashlib.md5(clean_server.encode()).hexdigest()[:8]}-%C'
                
                ssh_cmd = [
                    'ssh',
                    '-o', 'ControlMaster=auto',
                    '-o', 'ControlPath=' + control_path,
                    '-o', 'ControlPersist=600',
                    clean_server,
                    ' '.join(cmd)
                ]
                return subprocess.run(ssh_cmd, cwd=self.base_dir, capture_output=capture, text=True)
    else:
        return subprocess.run(cmd, cwd=self.base_dir, capture_output=capture, text=True, env=full_env)
```

---

## Implementazione per Docker Swarm

### Modificare `swarm_up()` per Docker Swarm

```python
def swarm_up(self, server: Optional[str] = None) -> bool:
    """Deploy ThothAI to Docker Swarm."""
    previous_context = None
    
    try:
        # Usa Docker Context se server è specificato
        if server:
            success, previous_context = self._use_docker_context(server)
            if success:
                console.print("[green]Using Docker Context for Swarm deployment[/green]")
            else:
                console.print("[yellow]Docker Context not available, falling back to SSH Tunnel[/yellow]")
                # Fallback all'approccio SSH Tunnel attuale
                # ... codice esistente ...
        
        # ... resto del codice esistente per preparazione stack ...
        
        # Deploy stack (ora usa il context se impostato)
        console.print(f"\n[bold]Deploying stack '{stack_name}' to Swarm...[/bold]")
        result = self._run_cmd(
            ['docker', 'stack', 'deploy', '-c', stack_file_to_deploy, stack_name],
            server=None,  # Non usare server se usiamo Docker Context
            env=swarm_env
        )
        
        if result.returncode != 0:
            console.print("[red]Failed to deploy stack[/red]")
            return False
        
        # Wait for services
        self.wait_for_swarm_services(stack_name, server=None)
        
        # Print access info
        self.print_access_info(is_swarm=True)
        
        return True
        
    finally:
        # Ripristina sempre il context precedente
        if previous_context:
            self._restore_docker_context(previous_context)
```

### Modificare altri metodi Swarm

```python
def swarm_down(self, server: Optional[str] = None) -> bool:
    """Remove ThothAI from Docker Swarm."""
    previous_context = None
    
    try:
        if server:
            success, previous_context = self._use_docker_context(server)
        
        # ... codice esistente ...
        
        result = self._run_cmd(['docker', 'stack', 'rm', stack_name], None, capture=True)
        
        return result.returncode == 0
        
    finally:
        if previous_context:
            self._restore_docker_context(previous_context)

def swarm_status(self, server: Optional[str] = None) -> None:
    """Show Swarm services status."""
    previous_context = None
    
    try:
        if server:
            success, previous_context = self._use_docker_context(server)
        
        self._run_cmd(['docker', 'stack', 'services', stack_name], None)
        
    finally:
        if previous_context:
            self._restore_docker_context(previous_context)

def swarm_update(self, server: Optional[str] = None) -> bool:
    """Update Swarm services to latest images."""
    return self.swarm_up(server)  # docker stack deploy handles updates

def swarm_rollback(self, server: Optional[str] = None) -> bool:
    """Rollback Swarm services."""
    previous_context = None
    
    try:
        if server:
            success, previous_context = self._use_docker_context(server)
        
        swarm_env = self._get_swarm_env()
        stack_name = swarm_env.get('STACK_NAME', 'thothai-swarm')
        
        services_result = self._run_cmd(
            ['docker', 'stack', 'services', '--format', '{{.Name}}', stack_name], 
            None, 
            capture=True
        )
        
        if services_result.returncode != 0:
            return False
            
        for service in services_result.stdout.strip().split('\n'):
            if service:
                console.print(f"Rolling back service {service}...")
                self._run_cmd(['docker', 'service', 'update', '--rollback', service], None)
        
        return True
        
    finally:
        if previous_context:
            self._restore_docker_context(previous_context)
```

---

## Esempi di Utilizzo

### Docker Compose

```bash
# Deploy su server remoto
thothai deploy --server user@myserver.com

# Internamente:
# 1. Crea Docker Context "thothai-abc123"
# 2. Usa il context
# 3. Esegue docker compose up -d
# 4. Ripristina context default

# Gestione multi-server
thothai deploy --server user@server1.com
thothai deploy --server user@server2.com

# Lista dei context
docker context ls

# Switch manuale
docker context use thothai-abc123
docker ps  # Mostra container su server1.com
```

### Docker Swarm

```bash
# Deploy su cluster Swarm remoto
thothai swarm deploy --server user@swarm-manager.example.com

# Gestione multi-cluster
thothai swarm deploy --server user@prod-swarm.example.com
thothai swarm deploy --server user@staging-swarm.example.com

# Verifica stato produzione
docker context use thothai-prod
docker stack services thothai

# Verifica stato staging
docker context use thothai-staging
docker stack services thothai

# Log produzione
docker service logs thothai_backend

# Log staging
docker context use thothai-staging
docker service logs thothai_backend
```

---

## Vantaggi

### Per Docker Compose

| Aspetto | Senza Docker Context | Con Docker Context |
|----------|---------------------|-------------------|
| **Configurazione** | Tunnel SSH manuale | Context una volta |
| **Comandi** | `ssh user@server "docker compose ..."` | `docker compose ...` |
| **Sintassi** | Complessa (escape quotes) | Semplice (standard) |
| **Debugging** | Difficile (via SSH) | Semplice (nativo) |
| **Multi-Server** | Difficile (più SSH) | Semplice (più context) |

### Per Docker Swarm

| Aspetto | Senza Docker Context | Con Docker Context |
|----------|---------------------|-------------------|
| **Configurazione** | SSH manuale per ogni comando | Context una volta |
| **Comandi** | `ssh user@server "docker stack deploy ..."` | `docker stack deploy ...` |
| **Sintassi** | Complessa (escape quotes) | Semplice (standard) |
| **Debugging** | Difficile (via SSH) | Semplice (nativo) |
| **Multi-Cluster** | Difficile (più SSH) | Semplice (più context) |

---

## Implementazione Graduale

### Fase 1: Aggiungere Supporto Docker Context (Non Breaking)

Aggiungere i metodi `_use_docker_context()` e `_restore_docker_context()` a [`docker_manager.py`](../../cli/thothai-cli/src/thothai_cli/core/docker_manager.py).

Modificare i metodi esistenti per usare Docker Context:
- `up()` per Docker Compose
- `swarm_up()` per Docker Swarm
- `swarm_down()` per Docker Swarm
- `swarm_status()` per Docker Swarm
- `swarm_update()` per Docker Swarm
- `swarm_rollback()` per Docker Swarm
- `_run_cmd()` per supportare Docker Context

### Fase 2: Test e Validazione

1. Test con Docker >= 19.03
2. Verifica fallback con Docker < 19.03
3. Test con più server (Compose)
4. Test con più cluster (Swarm)
5. Test di cleanup

### Fase 3: Rendere Docker Context Default (Opzionale)

Aggiungere a `config.yml.local`:
```yaml
docker:
  use_docker_context: true  # Default: true per Docker >= 19.03
```

---

## Troubleshooting

### Problema: Docker Context non funziona

**Sintomo:**
```
Error: Could not create Docker Context
```

**Soluzione:**
```bash
# Verifica versione Docker
docker --version
# Deve essere >= 19.03

# Verifica connessione SSH
ssh user@server

# Crea context manualmente
docker context create test --docker "host=ssh://user@server"
docker context use test
docker ps
```

### Problema: Swarm: Stack non viene deployato

**Sintomo:**
```
Error: This node is not a swarm manager
```

**Soluzione:**
```bash
# Verifica che il context punti al manager node
docker context inspect thothai-prod

# Output deve mostrare:
# "Host": "ssh://user@manager-node.example.com"

# Non al worker node!
```

### Problema: Comandi eseguiti localmente invece che remotamente

**Sintomo:**
```
docker ps mostra container locali invece che remoti
```

**Soluzione:**
```bash
# Verifica context corrente
docker context show

# Se non è thothai-*, usa il context corretto
docker context use thothai-abc123

# Verifica connessione
docker version
# Server version dovrebbe essere quella del server remoto
```

---

## Riferimenti

### Documentazione Ufficiale Docker
- [Docker Context Documentation](https://docs.docker.com/engine/context/working-with-contexts/)
- [Docker Context CLI Reference](https://docs.docker.com/engine/reference/commandline/context/)

### Codice di Riferimento
- [`docker_manager.py`](../../cli/thothai-cli/src/thothai_cli/core/docker_manager.py) - Implementazione attuale
- [`deploy.py`](../../cli/thothai-cli/src/thothai_cli/commands/deploy.py) - Comandi di deployment
- [`swarm.py`](../../cli/thothai-cli/src/thothai_cli/commands/swarm.py) - Comandi Swarm

---

## Conclusione

Docker Context è la **soluzione ideale** per migliorare il deployment remoto di ThothAI:

✅ **Nativo Docker**: Nessun codice custom necessario per la gestione delle connessioni
✅ **Semplice**: `docker context use` per switchare tra server
✅ **Persistente**: I context rimangono tra le sessioni
✅ **Funziona per Compose e Swarm**: Unico approccio per entrambi
✅ **Debugging Nativo**: Comandi standard Docker senza SSH
✅ **Multi-Server Facile**: Gestione rapida tra produzione, staging, sviluppo
✅ **Sicuro**: SSH standard
✅ **Performante**: Nessun overhead

**Raccomandazione**: Implementare Docker Context come metodo primario per il deployment remoto, con fallback all'approccio SSH Tunnel attuale per compatibilità con versioni vecchie di Docker (< 19.03).
