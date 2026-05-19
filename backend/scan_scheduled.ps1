$log = "C:\Users\Administrator\Desktop\Opencode\projets\rapport trade vps\backend\scan_scheduled.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Starting scan..." | Out-File $log -Append

$env:PYTHONIOENCODING='utf-8'
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
Set-Location "C:\Users\Administrator\Desktop\Opencode\projets\rapport trade vps\backend"

& "C:\Program Files\Python312\python.exe" -u scan_all.py --once 2>&1 | Out-File $log -Append

$ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$ts2] Scan finished." | Out-File $log -Append
