# Copyright (c) 2025 Marco Pancotti
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

# PowerShell script to fix line endings for .sh files on Windows

Write-Host "Fixing line endings for all .sh files..." -ForegroundColor Green
Write-Host ""

# Find all .sh files and convert to Unix line endings
$shFiles = Get-ChildItem -Path . -Filter *.sh -Recurse -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -notmatch "\\node_modules\\" -and 
                   $_.FullName -notmatch "\\venv\\" -and
                   $_.FullName -notmatch "\\.venv\\" }

$count = 0
foreach ($file in $shFiles) {
    $relativePath = $file.FullName.Replace($PWD.Path + "\", "")
    
    # Read file and convert CRLF to LF
    $content = [System.IO.File]::ReadAllText($file.FullName)
    $unixContent = $content -replace "`r`n", "`n"
    [System.IO.File]::WriteAllText($file.FullName, $unixContent)
    
    Write-Host "  Fixed: $relativePath" -ForegroundColor Green
    $count++
}

Write-Host ""
Write-Host "Total files converted: $count" -ForegroundColor Green
Write-Host ""
Write-Host "Now rebuild Docker containers with:" -ForegroundColor Yellow
Write-Host "  docker-compose build --no-cache" -ForegroundColor Cyan
Write-Host "  docker-compose up" -ForegroundColor Cyan