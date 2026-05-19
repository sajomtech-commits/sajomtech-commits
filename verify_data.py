"""Verify Supabase data after scan."""
import urllib.request, json

K = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3ODc4NTIwMCwiZXhwIjo0OTM0NDU4ODAwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.iDaEfe4pHMzkeff9Cu8c-YjwDAes5NY75oPD1oVmuIk'
H = {'apikey': K, 'Authorization': f'Bearer {K}', 'User-Agent': 'Mozilla/5.0'}

def g(path):
    r = urllib.request.Request(f'http://supabase.sagetech.vip{path}', headers=H)
    return json.loads(urllib.request.urlopen(r, timeout=10).read())

accts = g('/rest/v1/mt5_accounts?select=id,instance_name,login,balance,equity')
trades = g('/rest/v1/trades?select=id,ticket,symbol,profit,is_open')
syncs = g('/rest/v1/sync_log?select=id,instance_name,status,trades_found,trades_upserted&order=id.desc&limit=5')
print(f'Accounts: {len(accts)}')
for a in accts:
    print(f'  {a["instance_name"]}: balance={a["balance"]}, equity={a["equity"]}')
print(f'Trades: {len(trades)}')
open_t = sum(1 for t in trades if t['is_open'])
print(f'  Open: {open_t}, Closed: {len(trades)-open_t}')
print(f'Last syncs:')
for s in syncs:
    print(f'  {s["instance_name"]}: {s["status"]} ({s["trades_upserted"]} upserted)')
