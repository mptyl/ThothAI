# PowerShell script to check Docker container logs on Windows

Write-Host "Checking Docker container status..." -ForegroundColor Green

# Get container status
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.State}}"

Write-Host "`nChecking logs for containers that may be stuck..." -ForegroundColor Yellow

# Check backend logs
Write-Host "`n=== Backend Logs ===" -ForegroundColor Cyan
docker logs thoth-backend --tail 20

# Check if start.sh is running
Write-Host "`n=== Checking processes in backend container ===" -ForegroundColor Cyan
docker exec thoth-backend ps aux | Select-String "start.sh"

Write-Host "`n=== Frontend Logs ===" -ForegroundColor Cyan
docker logs thoth-frontend --tail 20

Write-Host "`n=== SQL Generator Logs ===" -ForegroundColor Cyan
docker logs thoth-sql-generator --tail 20

Write-Host "`n=== Proxy Logs ===" -ForegroundColor Cyan
docker logs thoth-proxy --tail 20

Write-Host "`nTip: If containers are stuck, try:" -ForegroundColor Yellow
Write-Host "  docker-compose down" -ForegroundColor White
Write-Host "  docker-compose up -d" -ForegroundColor White