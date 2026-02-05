# Full site build — same steps as GitHub Actions (see .github/workflows/docs.yml)
# Run from repository root:
#   .\website\build.ps1           — only build
#   .\website\build.ps1 -Serve   — build and start local server (uses serve so 404 works like on prod)

param([switch]$Serve)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Copying docs to website..." -ForegroundColor Cyan
Copy-Item -Path "$root\docs" -Destination "$root\website\docs" -Recurse -Force

Write-Host "Copying README as index..." -ForegroundColor Cyan
Copy-Item "$root\README.md" "$root\website\docs\ru\index.md" -Force
Copy-Item "$root\README_EN.md" "$root\website\docs\en\index.md" -Force

Write-Host "Building MkDocs..." -ForegroundColor Cyan
Push-Location "$root\website"
try {
    mkdocs build --clean
} finally {
    Pop-Location
}

Write-Host "Copying static files to site root..." -ForegroundColor Cyan
Copy-Item "$root\website\404.html" "$root\site\404.html" -Force
Copy-Item "$root\website\CNAME" "$root\site\CNAME" -Force
Copy-Item "$root\website\robots.txt" "$root\site\robots.txt" -Force

Write-Host "Done. Site output: $root\site\" -ForegroundColor Green

if ($Serve) {
    Write-Host "Starting local server at http://127.0.0.1:8000 (Ctrl+C to stop)" -ForegroundColor Green
    Push-Location "$root\site"
    $serve = Get-Command npx -ErrorAction SilentlyContinue
    if ($serve) {
        npx --yes serve -p 8000
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue; if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
        if ($python) {
            & $python.Source -m http.server 8000
        } else {
            Write-Host "Run from site folder: npx serve -p 8000 (for 404 support)" -ForegroundColor Yellow
        }
    }
    Pop-Location
}
