# ThothAI - Automazione CI/CD per il Deploy

Questo documento descrive come configurare pipeline di Continuous Integration e Continuous Deployment per ThothAI, supportando sia **GitHub** che **GitLab**.

---

## 1. Strategie di Deploy

Ci sono due strategie principali per il deploy automatico:
1.  **Docker Singolo (VPS)**: Aggiornamento tramite Docker Compose su un singolo server.
2.  **Docker Swarm (Cluster)**: Aggiornamento tramite `docker stack deploy` su un cluster di nodi.

---

## 2. GitHub Actions (Repository Pubblico/Privato)

Se il codice risiede su GitHub, si possono utilizzare le GitHub Actions per triggerare il deploy al push sul branch `main`.

### 2.1 Pipeline per Docker Singolo (Simple VPS)

Il workflow tipico è:
1.  Checkout del codice.
2.  Copia dei file sul server (tramite SCP o rsync).
3.  Esecuzione script remoto per rebuild.

**Esempio Workflow (`.github/workflows/deploy-compose.yml`):**
```yaml
name: Deploy to VPS
on:
  push:
    branches: [ main ]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Deploy to Server
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.SERVER_HOST }}
        username: ${{ secrets.SERVER_USER }}
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script: |
          cd /path/to/ThothAI
          git pull origin main
          cp config.yml.production config.yml.local # Assicura config corretta
          # Setup ambiente (generazione .env.docker)
          python3 scripts/installer.py --generate-env-only
          # Pull e Riavvio
          docker compose pull
          docker compose up -d --force-recreate
```

### 2.2 Pipeline per Docker Swarm

Il workflow Swarm richiede un passaggio intermedio: il push delle immagini su Docker Hub.

**Prerequisiti Secrets:**
*   `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
*   `SSH_PRIVATE_KEY`, `SERVER_HOST`, `SERVER_USER`

**Esempio Workflow (`.github/workflows/deploy-swarm.yml`):**
```yaml
name: Deploy Swarm
on:
  push:
    branches: [ main ]
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Build and Push Images
        run: |
          # Esegue build e push manuale o tramite script custom
          docker build -t ${{ secrets.DOCKERHUB_USERNAME }}/thoth-backend:latest -f docker/backend.Dockerfile .
          docker push ${{ secrets.DOCKERHUB_USERNAME }}/thoth-backend:latest
          # Ripetere per frontend, proxy, etc...

  deploy-stack:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Remote Deploy
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            docker service update --image ${{ secrets.DOCKERHUB_USERNAME }}/thoth-backend:latest thoth_backend
            # Oppure rieseguire install-swarm.sh se presente sul server
```

---

## 3. GitLab CI (Repository Privato - UNI)

Per l'ambiente aziendale (UNI) su GitLab privato, si usa `.gitlab-ci.yml`.

### 3.1 Pipeline Esempio

```yaml
stages:
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2

build_images:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $CI_REGISTRY_IMAGE/backend:latest -f docker/backend.Dockerfile .
    - docker push $CI_REGISTRY_IMAGE/backend:latest
  only:
    - main

deploy_swarm:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
    - mkdir -p ~/.ssh
    - chmod 700 ~/.ssh
  script:
    - ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "docker service update --image $CI_REGISTRY_IMAGE/backend:latest thoth_backend --with-registry-auth"
  only:
    - main
```

---

## 4. Dettagli Aggiuntivi

### 4.1 Gestione delle Variabili d'Ambiente
Per la CI/CD è fondamentale non committare mai file con password (`config.yml.local`, `.env`).
*   **GitHub**: Usa i "Repository Secrets".
*   **GitLab**: Usa "Settings > CI/CD > Variables".

### 4.2 Rollback Automatico
Docker Swarm supporta il rollback nativo se l'aggiornamento fallisce:
```bash
docker service update --rollback-on-failure ...
```
Assicurati di includere questo flag nei tuoi script di deploy CI/CD per garantire la stabilità della produzione.
