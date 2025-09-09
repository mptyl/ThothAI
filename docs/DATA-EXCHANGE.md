# DATA-EXCHANGE.md

## CSV Import/Export System in ThothAI

ThothAI’s CSV import/export system enables data exchange between different environments (local and Docker) using CSV files. The system uses the `data_exchange` directory as a universal exchange point between the host and Docker containers.

## How Host ↔ Docker Exchange Works

### The Key Concept: Bind Mount

The `data_exchange` directory is NOT an isolated Docker volume, but a bind mount that directly links a directory on your computer (host) with a directory inside the Docker containers.

In `docker-compose.yml` the services use the following mounts:
```yaml
backend:
  volumes:
    - ./data_exchange:/app/data_exchange         # RW

frontend:
  volumes:
    - ./data_exchange:/app/data_exchange:ro     # RO (read-only)

sql-generator:
  volumes:
    - ./data_exchange:/app/data_exchange        # RW

proxy:
  volumes:
    - ./data_exchange:/vol/data_exchange:ro     # RO (not exposed via HTTP)
```

This configuration means:
- `./data_exchange` = directory on YOUR computer (relative to the ThothAI project root)
- `/app/data_exchange` = directory INSIDE application containers (backend, frontend, sql-generator)
- `/vol/data_exchange` = mount inside the Nginx proxy container, used for potential internal needs; it is NOT exposed by Nginx by default
- They are the SAME directory: any file written on one side is immediately visible on the other
- The frontend mounts in read-only mode (does not write), while the backend and sql-generator can read/write

### Export Flow (Docker → Host)

```
1. Django Admin (browser) → Click "Export to CSV" (the exact action text may vary)
   ↓
2. Django (in the container) writes: /app/data_exchange/workspace.csv
   ↓
3. File IMMEDIATELY visible on the host: ./data_exchange/workspace.csv
   ↓
4. The user can open it with Excel/VS Code/etc from their computer
```

### Import Flow (Host → Docker)

```
1. User copies a CSV file to: ./data_exchange/users.csv
   ↓
2. File IMMEDIATELY visible in the container: /app/data_exchange/users.csv
   ↓
3. Django Admin can import it with "Import from CSV"
```

## Data Exchange Directory

### Main Directory
- On your computer (host): `ThothAI/data_exchange/`
- Inside Docker: `/app/data_exchange/`
- They are the SAME directory thanks to bind mount

### Verify the Bind Mount
```bash
# Create a test file from your computer
echo "test from host" > ./data_exchange/test.txt

# Verify it’s visible in Docker
docker exec -it thoth-backend cat /app/data_exchange/test.txt
# Output: test from host

# Create a file from Docker
docker exec -it thoth-backend bash -c 'echo "test from docker" > /app/data_exchange/test2.txt'

# Verify it’s visible on your computer
cat ./data_exchange/test2.txt
# Output: test from docker
```

### Visibility via Proxy (Nginx)
- The proxy exposes only backend API, static and media (see `docker/nginx.conf`).
- The `data_exchange` directory is NOT exposed via HTTP: there is no public route to browse these files.

### Usage by SQL Generator
- The `sql-generator` service also reads/writes to the same shared directory (`/app/data_exchange`).
- This enables the backend and SQL Generator to exchange artifacts (e.g., CSV exports or diagnostic output) that are also visible on the host.

## Import/Export Behavior

### CSV Export

#### From Admin Interface
1. Access: http://localhost:8040/admin → Select model → Select record(s)
2. Action: From the “Actions” menu → “Export selected to CSV” (indicative label)
3. Result: CSV file immediately available at `./data_exchange/{model_name}.csv` on YOUR computer
4. Open: You can open the file with any program (Excel, Numbers, LibreOffice, VS Code, etc.)

### CSV Import

#### From Command Line
```bash
# First: place the file in the directory on your computer
cp ~/my_backup/workspace.csv ./data_exchange/

# Then import from Docker
docker exec -it thoth-backend python manage.py import_single_csv workspace
```

## Directory Management

### Directory Creation
The `data_exchange` directory is normally created automatically by Docker at bind mount time. However, it’s recommended to verify its existence and permissions before starting:
```bash
# Create the directory if it doesn’t exist
mkdir -p ./data_exchange

# Verify permissions (must be writable)
ls -la ./data_exchange

# If needed, adjust permissions
chmod 755 ./data_exchange
```

### Permissions
The system automatically uses the correct paths and permissions, but on some systems (especially Linux) you might need to intervene manually.

### Bind Mount Troubleshooting

If files are not visible between host and Docker:

```bash
# Verify the containers use the correct bind mount
docker inspect thoth-backend | grep -A 5 Mounts

docker inspect thoth-sql-generator | grep -A 5 Mounts
```

You should see `Type: bind` with `Source: <path>/ThothAI/data_exchange` and `Destination: /app/data_exchange`.

## Important Notes

### Advantages of Bind Mount

1. Immediate Access: No need to copy files into/out of the container
2. Direct Editing: You can modify CSVs with Excel/VS Code without Docker commands
3. Simple Backup: Files are already on your filesystem, ready for backup
4. Easy Debugging: You can immediately see what Django or the `sql-generator` wrote
5. Bidirectional: Changes from both sides are immediate

### Security

1. Sensitive Data: Do not leave files with passwords/tokens in `data_exchange`
2. Cleanup: Remove CSVs after use if they contain sensitive data
3. Gitignore: The `data_exchange/` directory is already in `.gitignore`
4. Not exposed via HTTP: The contents of `data_exchange` are not served by the proxy

## Summary

The key point: The `data_exchange` directory is a direct bridge between your computer and Docker. It is not isolated inside Docker, but is the same directory accessible by the backend, frontend (READ-ONLY), and SQL Generator. The proxy does not expose it via HTTP. This makes import/export extremely simple: write on one side, read on the other, instantly.