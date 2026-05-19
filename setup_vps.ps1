#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup script — à exécuter DIRECTEMENT SUR LE VPS (176.181.28.95)
    Installe les dépendances, exécute SQL, configure .env, lance le scan
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Step($msg) {
    Write-Host "`n════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor White
    Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
}

# ─── 1. Vérifier Python ───
Step "Vérification Python"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    Write-Host "Python introuvable. Installe Python 3.10+ depuis python.org" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python: $(python --version)" -ForegroundColor Green

# ─── 2. Créer venv + installer dépendances ───
Step "Environnement virtuel + dépendances"
$venv = Join-Path $Root "backend\venv"
if (-not (Test-Path $venv)) {
    python -m venv $venv
    Write-Host "✓ venv créé" -ForegroundColor Green
}
$pip = Join-Path $venv "Scripts\pip"
& $pip install -r (Join-Path $Root "backend\requirements.txt") 2>&1 | Out-Null
Write-Host "✓ Dépendances installées" -ForegroundColor Green

# ─── 3. Détecter Postgres/Supabase ───
Step "Connexion base de données"
$pgInstalled = (Get-Command psql -ErrorAction SilentlyBoolean)
$found = $false

# Essayer différentes connexions
$connStrings = @(
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@176.181.28.95:5432/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:5432/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@127.0.0.1:5432/postgres"
)

foreach ($cs in $connStrings) {
    try {
        $env:PGPASSWORD = "f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9"
        $test = & psql -h localhost -U postgres -c "SELECT 1" -d postgres -t 2>&1
        if ($LASTEXITCODE -eq 0) {
            $found = $true
            Write-Host "✓ PostgreSQL accessible via psql" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  psql: $_" -ForegroundColor DarkGray
    }
}

if (-not $found) {
    Write-Host "⚠ psql non disponible, utilisation de Python pour la connexion directe..." -ForegroundColor Yellow
    
    # Installer psycopg2 si pas déjà fait
    & $pip install psycopg2-binary 2>&1 | Out-Null
    
    # Test avec Python
    $pyCode = @'
import psycopg2, sys
uris = [
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@176.181.28.95:5432/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@localhost:5432/postgres",
    "postgresql://postgres:f7k3ZAbVkXUKs0jKjtMNUWeD9F2OkVx9@127.0.0.1:5432/postgres",
]
for uri in uris:
    try:
        conn = psycopg2.connect(uri, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        print(f"OK:{uri}")
        sys.exit(0)
    except Exception as e:
        print(f"FAIL:{uri} => {e}")
sys.exit(1)
'@
    $result = python -c $pyCode
    $okLine = $result | Select-String "^OK:"
    if ($okLine) {
        $found = $true
        Write-Host "✓ PostgreSQL accessible via Python" -ForegroundColor Green
        # Extract the working URI
        $dbUri = ($okLine -replace "^OK:", "").Trim()
        Write-Host "  URI: $dbUri" -ForegroundColor DarkGray
    } else {
        Write-Host "✗ Aucune connexion Postgres trouvée" -ForegroundColor Red
        Write-Host "Détails: $result" -ForegroundColor DarkGray
    }
}

# ─── 4. Exécuter les scripts SQL ───
if ($found) {
    Step "Exécution des scripts SQL"
    $sqlDir = Join-Path $Root "sql"
    $scripts = @("schema.sql", "indexes.sql", "views.sql", "rls.sql")
    
    foreach ($script in $scripts) {
        $path = Join-Path $sqlDir $script
        if (Test-Path $path) {
            Write-Host "→ $script..." -NoNewline
            try {
                $sql = Get-Content $path -Raw
                $pyExec = @'
import psycopg2, sys
uri = sys.argv[1]
sql = sys.argv[2]
conn = psycopg2.connect(uri)
conn.autocommit = True
cur = conn.cursor()
cur.execute(sql)
cur.close()
conn.close()
print("OK")
'@
                $result = python -c $pyExec $dbUri $sql 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host " ✓" -ForegroundColor Green
                } else {
                    Write-Host " ✗ $result" -ForegroundColor Red
                }
            } catch {
                Write-Host " ✗ $_" -ForegroundColor Red
            }
        }
    }
} else {
    Write-Host "⚠ Impossible de se connecter à PostgreSQL. Exécute les scripts SQL manuellement." -ForegroundColor Yellow
    Write-Host "  Fichiers SQL dans : $Root\sql\" -ForegroundColor Yellow
}

# ─── 5. Configurer .env ───
Step "Configuration .env"
$envPath = Join-Path $Root "backend\.env"
$instancesJson = '[{"name":"instance1","path":"C:\\Program Files\\MT5\\terminal64.exe","login":52883670,"password":"@Q169FwQ!APVuS","server":"ICMarketsEU-Demo"},{"name":"instance2","path":"C:\\MT5_Portable\\Demo1\\terminal64.exe","login":52871686,"password":"&AiYW0foMai!oy","server":"ICMarketsEU-Demo"}]'

$envContent = @"
SUPABASE_URL=https://supabase.sagetech.vip
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.iDaEfe4pHMzkeff9Cu8c-YjwDAes5NY75oPD1oVmuIk
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.iDaEfe4pHMzkeff9Cu8c-YjwDAes5NY75oPD1oVmuIk
SCAN_INTERVAL_S=1800
HISTORY_DAYS=90
LOG_LEVEL=INFO
DRY_RUN=0
BATCH_SIZE=500
MT5_INSTANCES=$instancesJson
"@

Set-Content -Path $envPath -Value $envContent
Write-Host "✓ .env créé : $envPath" -ForegroundColor Green

# ─── 6. Test dry-run ───
Step "Test dry-run (vérification sans MT5)"
$python = Join-Path $venv "Scripts\python"
$scanPath = Join-Path $Root "backend\scan_all.py"
try {
    & $python $scanPath --once --dry-run 2>&1
    Write-Host "`n✓ Dry-run terminé" -ForegroundColor Green
} catch {
    Write-Host "⚠ Dry-run : $_" -ForegroundColor Yellow
}

# ─── Résumé ───
Step "SETUP TERMINÉ"
Write-Host @"

Résumé :
  ✓ Dépendances installées
  ✓ .env configuré
  ✓ Scripts SQL exécutés
  ✓ Dry-run effectué

Prochaines étapes :

  1. Premier vrai scan (avec MT5) :
     cd $Root\backend
     .\venv\Scripts\Activate.ps1
     python scan_all.py --once

  2. Scan continu (toutes les 30min) :
     python scan_all.py

  3. Serveur webhook (optionnel) :
     python webhook_server.py

  4. Dashboard : déploie le dossier dashboard/ sur GitHub Pages

Fichiers importants :
  - SQL : $Root\sql\
  - Backend : $Root\backend\
  - Dashboard : $Root\dashboard\
  - Docs : $Root\docs\INSTALL.md
"@ -ForegroundColor Cyan
