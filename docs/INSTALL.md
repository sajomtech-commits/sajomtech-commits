# MT5 Trade Dashboard — Installation Guide

## Architecture

```
MT5 Instance 1 (Program Files)  ─┐
MT5 Instance 2 (Portable Demo1) ─┤
                                  │
    Python scan_all.py (30min)    │
    batch upsert 500              │
                                  ▼
                          ┌──────────────┐
                          │   Supabase   │
                          │ REST API     │
                          └──────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
           GitHub Pages                Webhook Server
           Dashboard JS                FastAPI :8450
           (anon key, RLS)             (service_role key)
```

---

## 1. Prérequis

- Windows VPS
- Python 3.10+
- MetaTrader 5 installé
- Accès Supabase auto-hébergé (Coolify)

---

## 2. Installation Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

1. Copier `.env.example` vers `.env`
2. Éditer `.env` avec les credentials réels :

```ini
SUPABASE_URL=https://supabase.sagetech.vip
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
SCAN_INTERVAL_S=1800
HISTORY_DAYS=90
MT5_INSTANCES=[{"name":"instance1","path":"C:\\Program Files\\MT5\\terminal64.exe","login":52883670,"password":"@Q169FwQ!APVuS","server":"ICMarketsEU-Demo"},{"name":"instance2","path":"C:\\MT5_Portable\\Demo1\\terminal64.exe","login":52871686,"password":"&AiYW0foMai!oy","server":"ICMarketsEU-Demo"}]
```

---

## 3. Base de données

Exécuter les scripts SQL dans l'ordre via l'éditeur SQL Supabase :

```sql
-- 1. Tables
-- Copier-coller le contenu de sql/schema.sql

-- 2. Indexes
-- Copier-coller le contenu de sql/indexes.sql

-- 3. Vues
-- Copier-coller le contenu de sql/views.sql

-- 4. Sécurité RLS
-- Copier-coller le contenu de sql/rls.sql
```

---

## 4. Configuration CORS Supabase

Dans Supabase Studio → Authentication → Settings :

```
Allowed Origins:
  https://sajomtech-commits.github.io
  http://localhost:8080
  http://localhost:5500
```

---

## 5. Lancement

### Scan unique (test)

```powershell
cd backend
.\venv\Scripts\activate
python scan_all.py --once
```

### Scan continu (toutes les 30 min)

```powershell
python scan_all.py
```

### Test sans MT5

```powershell
python scan_all.py --dry-run --once
```

### Serveur webhook (optionnel)

```powershell
python webhook_server.py
```

### Tâche planifiée Windows (alternative à la boucle)

```powershell
$action = New-ScheduledTaskAction -Execute "C:\chemin\backend\venv\Scripts\python.exe" `
    -Argument "C:\chemin\backend\scan_all.py --once" `
    -WorkingDirectory "C:\chemin\backend"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -At (Get-Date) -RepetitionDuration (New-TimeSpan -Days 365)
Register-ScheduledTask -TaskName "MT5-Sync" -Action $action -Trigger $trigger -RunLevel Highest
```

---

## 6. Dashboard GitHub Pages

1. Pusher le dossier `dashboard/` vers un repo GitHub
2. Activer GitHub Pages : Settings → Pages → Source: `main branch /root`
3. Accéder à `https://sajomtech-commits.github.io/mt5-dashboard/dashboard/`

### Test en local

```powershell
cd dashboard
python -m http.server 8080
# http://localhost:8080
```

---

## 7. Dépannage

| Problème | Cause | Solution |
|----------|-------|----------|
| MT5 init fail | Mauvais chemin ou login | Vérifier `MT5_INSTANCES` dans `.env` |
| Aucun trade trouvé | Compte vide ou jours insuffisants | Ajouter `--days 365` ou vérifier connexion broker |
| Supabase 401 | Mauvaise clé | Vérifier `SUPABASE_SERVICE_ROLE_KEY` |
| Dashboard vide | CORS ou anon key | Vérifier CORS dans Supabase + `supabaseAnonKey` dans `config.js` |
| Positions non fermées | Stale positions | Relancer un scan complet |

---

## 8. Fichiers du projet

```
project/
├── backend/
│   ├── config.py              # Configuration (JSON instances dans .env)
│   ├── logger.py              # Logs console + fichier
│   ├── scan_to_supabase.py    # Scanner MT5 + sync Supabase
│   ├── scan_all.py            # Orchestrateur (--once, --instance)
│   ├── webhook_server.py      # API FastAPI (optionnel)
│   ├── requirements.txt
│   ├── run.ps1                # Lanceur PowerShell
│   ├── .env.example
│   └── logs/
├── sql/
│   ├── schema.sql             # 6 tables
│   ├── indexes.sql            # 15 indexes
│   ├── views.sql              # 8 vues
│   └── rls.sql                # Sécurité RLS
├── dashboard/
│   ├── index.html             # 7 onglets
│   ├── app.js                 # Fetch + filtres + export CSV
│   ├── style.css              # Dark theme
│   └── config.js              # Anon key uniquement
└── docs/
    └── INSTALL.md
```
