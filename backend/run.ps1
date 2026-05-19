#!/usr/bin/env pwsh
param(
    [ValidateSet("scan","webhook","once")]
    [string]$Mode = "scan",
    [switch]$Once,
    [switch]$DryRun,
    [string]$Instance = ""
)

$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Dir

$envFile = Join-Path $Dir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)\s*$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            if ($val -match '^"(.*)"$' -or $val -match "^'(.*)'$") { $val = $matches[1] }
            Set-Item -Path "env:$key" -Value $val
        }
    }
    Write-Host ".env loaded" -ForegroundColor Green
}

$venv = Join-Path $Dir "venv\Scripts\Activate.ps1"
if (Test-Path $venv) { . $venv } else { Write-Host "No venv — run: python -m venv venv" -ForegroundColor Yellow }

switch ($Mode) {
    "webhook" { python webhook_server.py }
    "once" {
        $a = @("--once")
        if ($DryRun) { $a += "--dry-run" }
        if ($Instance) { $a += "--instance"; $a += $Instance }
        python scan_all.py @a
    }
    default {
        $a = @()
        if ($Once) { $a += "--once" }
        if ($DryRun) { $a += "--dry-run" }
        if ($Instance) { $a += "--instance"; $a += $Instance }
        python scan_all.py @a
    }
}
