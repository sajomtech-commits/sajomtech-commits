const SB = {
    headers: { 'apikey': CONFIG.supabaseAnonKey, 'Authorization': `Bearer ${CONFIG.supabaseAnonKey}` },
    async get(path) {
        const r = await fetch(`${CONFIG.supabaseUrl}/rest/v1/${path}`, { headers: this.headers });
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
    }
};

const $ = id => document.getElementById(id);
const fn = (n, d = 2) => (n ?? 0).toLocaleString('en', { minFrac: d, maxFrac: d });
const fp = n => `${(n ?? 0).toFixed(2)}%`;
const fd = ts => ts ? new Date(ts).toLocaleDateString('en', CONFIG.dateOpts) : '—';
const pc = v => (v ?? 0) >= 0 ? 'plus' : 'minus';

const STATE = { accounts: [], trades: [], metrics: null, dailyPnl: [], dailyGlobal: [], stats: [], lastSync: [], drawdown: [], symbols: [] };

// ─── Tabs ───
function switchTab(name) {
    document.querySelectorAll('.tab').forEach(b => b.classList.toggle('on', b.dataset.t === name));
    document.querySelectorAll('.pane').forEach(p => p.classList.toggle('on', p.id === `p-${name}`));
}

// ─── Fetch ───
async function fetchAll() {
    try {
        const [accounts, trades, metrics, dailyPnl, dailyGlobal, stats, lastSync, drawdown] = await Promise.all([
            SB.get('mt5_accounts?select=id,instance_name,login,server,balance,equity,margin,margin_free,leverage,currency,last_sync_at&order=instance_name.asc'),
            SB.get(`trades?select=id,account_id,ticket,symbol,type,volume,open_time,close_time,open_price,close_price,profit,swap,commission,magic,comment,is_open&order=open_time.desc&limit=${CONFIG.maxTradeHistory}`),
            SB.get('v_global_metrics?limit=1'),
            SB.get('v_daily_pnl_global?order=trade_date.desc&limit=60'),
            SB.get('v_daily_pnl?order=trade_date.desc&limit=200'),
            SB.get('v_trade_stats?order=total_pnl.desc'),
            SB.get('v_last_sync'),
            SB.get('v_drawdown'),
        ]);
        STATE.accounts = accounts;
        STATE.trades = trades;
        STATE.metrics = metrics[0] || null;
        STATE.dailyGlobal = dailyGlobal;
        STATE.dailyPnl = dailyPnl;
        STATE.stats = stats;
        STATE.lastSync = lastSync;
        STATE.drawdown = drawdown;
        STATE.symbols = [...new Set(trades.map(t => t.symbol).filter(Boolean))].sort();
        populateFilters();
    } catch (e) {
        console.error(e);
        showError(e.message);
    }
}

function showError(m) {
    const t = $('toast');
    t.textContent = `⚠ ${m}`; t.classList.add('on');
    setTimeout(() => t.classList.remove('on'), 5000);
}

// ─── Filters ───
let filters = { account_id: '', symbol: '', type: '', is_open: '', date_from: '', date_to: '', magic: '', search: '' };

function populateFilters() {
    document.querySelectorAll('.fb select[data-f="account_id"]').forEach(el => {
        el.innerHTML = '<option value="">Tous les comptes</option>' +
            STATE.accounts.map(a => `<option value="${a.id}">${a.instance_name}</option>`).join('');
    });
    document.querySelectorAll('.fb select[data-f="symbol"]').forEach(el => {
        el.innerHTML = '<option value="">Tous les symboles</option>' +
            STATE.symbols.map(s => `<option value="${s}">${s}</option>`).join('');
    });
    document.querySelectorAll('.fb select[data-f="type"]').forEach(el => {
        el.innerHTML = '<option value="">Tous les types</option><option value="0">Achat</option><option value="1">Vente</option>';
    });
    document.querySelectorAll('.fb select[data-f="is_open"]').forEach(el => {
        el.innerHTML = '<option value="">Tous</option><option value="true">Ouvert</option><option value="false">Fermé</option>';
    });
}

function getFilteredTrades() {
    return STATE.trades.filter(t => {
        if (filters.account_id && t.account_id != filters.account_id) return false;
        if (filters.symbol && t.symbol !== filters.symbol) return false;
        if (filters.type !== '' && t.type != filters.type) return false;
        if (filters.is_open !== '' && t.is_open != (filters.is_open === 'true')) return false;
        if (filters.date_from && t.open_time < filters.date_from) return false;
        if (filters.date_to && t.open_time > filters.date_to + 'T23:59:59Z') return false;
        if (filters.magic && !String(t.magic).includes(filters.magic)) return false;
        if (filters.search) {
            const q = filters.search.toLowerCase();
            const c = (t.comment || '').toLowerCase();
            const s = (t.symbol || '').toLowerCase();
            if (!c.includes(q) && !s.includes(q) && !String(t.ticket).includes(q)) return false;
        }
        return true;
    });
}

function applyFilters() {
    const filtered = getFilteredTrades();
    renderOpenPositions(filtered.filter(t => t.is_open));
    renderClosedTrades(filtered.filter(t => !t.is_open));
    renderFilteredStats(filtered);
    updateCounts(filtered);
}

function resetFilters() {
    document.querySelectorAll('.fb select, .fb input').forEach(el => el.value = '');
    Object.keys(filters).forEach(k => filters[k] = '');
    applyFilters();
}

document.addEventListener('change', e => {
    if (e.target.matches('.fb select, .fb input:not([type=date])')) {
        filters[e.target.dataset.f] = e.target.value;
        applyFilters();
    }
});
document.addEventListener('input', e => {
    if (e.target.matches('.fb input[type=date]')) {
        filters[e.target.dataset.f] = e.target.value;
        applyFilters();
    }
});

// ─── Render ───
function renderMetrics() {
    const m = STATE.metrics;
    if (!m) return;
    $('m-active').textContent = m.active_accounts ?? STATE.accounts.length;
    $('m-open').textContent = m.open_positions ?? 0;
    $('m-total').textContent = (m.total_trades ?? 0).toLocaleString();
    $('m-pnl').textContent = fn(m.total_pnl);
    $('m-pnl').className = `mv ${pc(m.total_pnl)}`;
    $('m-winrate').textContent = fp(m.win_rate_pct);
    $('m-best').textContent = fn(m.best_trade);
    $('m-worst').textContent = fn(m.worst_trade);
    $('m-avgw').textContent = fn(m.avg_win);
    $('m-avgl').textContent = fn(m.avg_loss);
    $('m-avgl').className = `mv minus`;

    const dd = STATE.drawdown;
    if (dd.length) {
        const totalDD = dd.reduce((s, d) => s + (d.floating_pnl || 0), 0);
        $('m-dd').textContent = fn(totalDD);
        $('m-dd').className = `mv ${pc(totalDD)}`;
    } else {
        $('m-dd').textContent = '0.00';
    }
}

function renderAccounts() {
    $('accounts-body').innerHTML = STATE.accounts.map(a => `
        <tr>
            <td>${a.instance_name}</td>
            <td>${a.login}</td>
            <td>${a.server}</td>
            <td class="n">${fn(a.balance)}</td>
            <td class="n">${fn(a.equity)}</td>
            <td class="n">${fn(a.margin)}</td>
            <td class="n">${fn(a.margin_free)}</td>
            <td class="n">${a.leverage}</td>
            <td>${fd(a.last_sync_at)}</td>
        </tr>
    `).join('');
}

function renderOpenPositions(open) {
    $('pos-body').innerHTML = open.map(t => `
        <tr>
            <td>${t.ticket}</td>
            <td>${an(t.account_id)}</td>
            <td>${t.symbol}</td>
            <td>${tl(t.type)}</td>
            <td class="n">${fn(t.volume)}</td>
            <td class="n">${fn(t.open_price, 5)}</td>
            <td>${fd(t.open_time)}</td>
            <td class="n">${fn(t.sl, 1)}</td>
            <td class="n">${fn(t.tp, 1)}</td>
            <td class="n ${pc(t.profit)}">${fn(t.profit)}</td>
            <td>${t.comment || ''}</td>
        </tr>
    `).join('');
    $('pos-count').textContent = open.length;
}

function renderClosedTrades(closed) {
    const slice = closed.slice(0, 200);
    $('hist-body').innerHTML = slice.map(t => `
        <tr>
            <td>${t.ticket}</td>
            <td>${an(t.account_id)}</td>
            <td>${t.symbol}</td>
            <td>${tl(t.type)}</td>
            <td class="n">${fn(t.volume)}</td>
            <td class="n">${fn(t.open_price, 5)}</td>
            <td class="n">${fn(t.close_price, 5)}</td>
            <td>${fd(t.open_time)}</td>
            <td>${fd(t.close_time)}</td>
            <td class="n ${pc(t.profit)}">${fn(t.profit)}</td>
            <td>${t.comment || ''}</td>
        </tr>
    `).join('');
    $('hist-count').textContent = closed.length;
    $('hist-total').textContent = `Affichage de ${Math.min(200, closed.length)} sur ${closed.length}`;
}

function renderDailyPnl() {
    $('dp-body').innerHTML = STATE.dailyPnl.map(d => `
        <tr>
            <td>${d.trade_date}</td>
            <td>${an(d.account_id)}</td>
            <td class="n">${d.trade_count}</td>
            <td class="n ${pc(d.pnl)}">${fn(d.pnl)}</td>
            <td class="n">${fn(d.total_swap)}</td>
            <td class="n">${fn(d.total_commission)}</td>
        </tr>
    `).join('');
}

function renderDailyGlobal() {
    $('dpg-body').innerHTML = STATE.dailyGlobal.map(d => `
        <tr>
            <td>${d.trade_date}</td>
            <td class="n">${d.active_accounts}</td>
            <td class="n">${d.total_trades}</td>
            <td class="n ${pc(d.total_pnl)}">${fn(d.total_pnl)}</td>
            <td class="n">${fn(d.total_swap)}</td>
            <td class="n">${fn(d.total_commission)}</td>
        </tr>
    `).join('');
}

function renderStats() {
    $('stats-body').innerHTML = STATE.stats.map(s => `
        <tr>
            <td>${s.instance_name}</td>
            <td>${s.symbol}</td>
            <td class="n">${s.total_trades}</td>
            <td class="n">${s.wins}</td>
            <td class="n">${s.losses}</td>
            <td class="n">${fp(s.win_rate_pct)}</td>
            <td class="n ${pc(s.total_pnl)}">${fn(s.total_pnl)}</td>
            <td class="n">${fn(s.avg_pnl)}</td>
            <td class="n plus">${fn(s.best_trade)}</td>
            <td class="n minus">${fn(s.worst_trade)}</td>
        </tr>
    `).join('');
}

function renderFilteredStats(trades) {
    const groups = {};
    trades.forEach(t => {
        const key = `${an(t.account_id)}|${t.symbol}`;
        if (!groups[key]) groups[key] = { instance: an(t.account_id), symbol: t.symbol, total: 0, wins: 0, losses: 0, pnl: 0 };
        const g = groups[key];
        g.total++;
        if (!t.is_open) {
            if (t.profit > 0) g.wins++;
            if (t.profit < 0) g.losses++;
        }
        g.pnl += (t.profit || 0);
    });
    const arr = Object.values(groups).sort((a, b) => b.pnl - a.pnl);
    $('stats-body').innerHTML = arr.map(s => `
        <tr>
            <td>${s.instance}</td>
            <td>${s.symbol}</td>
            <td class="n">${s.total}</td>
            <td class="n">${s.wins}</td>
            <td class="n">${s.losses}</td>
            <td class="n">${fp(s.total ? (100 * s.wins / (s.wins + s.losses || 1)) : 0)}</td>
            <td class="n ${pc(s.pnl)}">${fn(s.pnl)}</td>
            <td class="n">${fn(s.total ? s.pnl / s.total : 0)}</td>
            <td class="n plus">—</td>
            <td class="n minus">—</td>
        </tr>
    `).join('');
}

function renderLastSync() {
    $('sync-body').innerHTML = STATE.lastSync.map(s => `
        <tr>
            <td>${s.instance_name}</td>
            <td>${s.login ?? '—'}</td>
            <td><span class="badge badge-${s.status}">${s.status}</span></td>
            <td class="n">${s.trades_found}</td>
            <td class="n">${s.trades_upserted}</td>
            <td class="n">${s.duration_ms}ms</td>
            <td>${fd(s.started_at)}</td>
        </tr>
    `).join('');
}

function updateCounts(filtered) {
    $('pos-count').textContent = filtered.filter(t => t.is_open).length;
    $('hist-count').textContent = filtered.filter(t => !t.is_open).length;
}

// ─── Helpers ───
const an = id => { const a = STATE.accounts.find(x => x.id === id); return a ? a.instance_name : `#${id}`; };
const tl = t => ({ 0: 'Buy', 1: 'Sell', 2: 'Buy Limit', 3: 'Sell Limit', 4: 'Buy Stop', 5: 'Sell Stop' }[t] ?? `T${t}`);

// ─── Sort ───
let sortDir = {};
function sortTable(th, idx, tableId) {
    const key = `${tableId}-${idx}`;
    sortDir[key] = !(sortDir[key]);
    const dir = sortDir[key] ? 1 : -1;
    const tbody = $(`${tableId}-body`);
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
        const va = a.cells[idx]?.textContent.trim() || '';
        const vb = b.cells[idx]?.textContent.trim() || '';
        const na = parseFloat(va.replace(/[,$]/g, ''));
        const nb = parseFloat(vb.replace(/[,$]/g, ''));
        if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
        return va.localeCompare(vb) * dir;
    });
    rows.forEach(r => tbody.appendChild(r));
}

// ─── CSV Export ───
function exportCSV(tableId, filename) {
    const tbody = $(`${tableId}-body`);
    if (!tbody) return;
    const rows = tbody.querySelectorAll('tr');
    if (!rows.length) return;
    const lines = [];
    const header = rows[0].parentElement.previousElementSibling;
    if (header) {
        lines.push(Array.from(header.querySelectorAll('th')).map(th => `"${th.textContent.trim()}"`).join(','));
    }
    rows.forEach(row => {
        lines.push(Array.from(row.querySelectorAll('td')).map(td => `"${td.textContent.trim()}"`).join(','));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
}

// ─── Init ───
document.addEventListener('DOMContentLoaded', async () => {
    document.querySelectorAll('.tab').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.t)));
    document.querySelectorAll('[data-export]').forEach(b => b.addEventListener('click', () => exportCSV(b.dataset.export, b.dataset.filename || 'export')));
    document.querySelectorAll('[data-reset]').forEach(b => b.addEventListener('click', resetFilters));
    document.querySelectorAll('th[data-col]').forEach(th => th.addEventListener('click', () => sortTable(th, parseInt(th.dataset.col), th.dataset.table)));

    const updateTime = () => { $('cur-time').textContent = new Date().toLocaleString('en', CONFIG.dateOpts); };
    updateTime(); setInterval(updateTime, 1000);

    await fetchAll();
    renderMetrics();
    renderAccounts();
    applyFilters();
    renderDailyPnl();
    renderDailyGlobal();
    renderLastSync();
    $('stats-filtered').textContent = '';

    setInterval(async () => {
        await fetchAll();
        renderMetrics();
        renderAccounts();
        applyFilters();
        renderDailyPnl();
        renderDailyGlobal();
        renderLastSync();
        updateTime();
    }, CONFIG.refreshIntervalMs);
});
