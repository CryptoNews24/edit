const API = '/api';
let token = localStorage.getItem('cs_token') || '';
let timer = null;
let settingsCache = null;
let saveTimer = null;
let equityPts = [];
let lastDash = null;

const BOT_META = {
  scalper: ['SC', 'Anthropic expert: news + macros'],
  pump: ['PM', 'Telegram · USDT-M futures +500% from 24h low'],
  riskoff: ['RO', 'Telegram · hawkish / high macros'],
};
const BOT_NAMES = Object.keys(BOT_META);
const RING_C = 2 * Math.PI * 54;

function headers() {
  return { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, { ...opts, headers: { ...headers(), ...opts.headers } });
  if (res.status === 401) { logout(); throw new Error('Unauthorized'); }
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 2200);
}

function logout() {
  token = '';
  localStorage.removeItem('cs_token');
  document.getElementById('app').classList.add('hidden');
  document.getElementById('login').classList.remove('hidden');
  if (timer) clearInterval(timer);
}

async function doLogin() {
  const err = document.getElementById('login-err');
  err.classList.add('hidden');
  try {
    const data = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: document.getElementById('login-user').value.trim(),
        password: document.getElementById('login-pass').value,
      }),
    }).then((r) => r.json());
    if (!data.access_token) throw new Error(data.error || 'Login failed');
    token = data.access_token;
    localStorage.setItem('cs_token', token);
    document.getElementById('login').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    init();
  } catch (e) {
    err.textContent = e.message;
    err.classList.remove('hidden');
  }
}

function fmt(n, d = 2) {
  if (n == null || Number.isNaN(n)) return '—';
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
}
function pnlC(v) { return v > 0 ? 'profit' : v < 0 ? 'loss' : ''; }

const FUTURES_24H = "https://www.binance.com/fapi/v1/ticker/24hr";
const PUMP_MIN_PCT = 500;
const PUMP_COOLDOWN_MS = 6 * 60 * 60 * 1000;
let pumpCache = { t: 0, rows: [] };
let pumpLoop = null;

function pumpThreshold() {
  const raw = Number(settingsCache?.pump_threshold_pct);
  return Number.isFinite(raw) && raw >= PUMP_MIN_PCT ? raw : PUMP_MIN_PCT;
}

function loadPumpAlerts() {
  try { return JSON.parse(localStorage.getItem("cs_pump_alerts") || "{}"); } catch { return {}; }
}
function savePumpAlerts(m) { localStorage.setItem("cs_pump_alerts", JSON.stringify(m)); }

async function scanFuturesPumps(force) {
  if (!force && Date.now() - pumpCache.t < 45000 && pumpCache.rows) return pumpCache.rows;
  const th = pumpThreshold();
  const volOn = !!settingsCache?.pump_min_volume_enabled;
  const volMin = (Number(settingsCache?.pump_min_volume_m) || 0) * 1e6;
  const rows = await fetch(FUTURES_24H).then((r) => r.json());
  const hits = [];
  for (const t of rows || []) {
    const sym = t.symbol || "";
    if (!sym.endsWith("USDT") || sym.includes("_")) continue;
    const last = Number(t.lastPrice);
    const lo = Number(t.lowPrice);
    if (!(lo > 0) || !(last > 0)) continue;
    const fromLow = (last / lo - 1) * 100;
    if (fromLow < th) continue;
    const vol = Number(t.quoteVolume) || 0;
    if (volOn && vol < volMin) continue;
    hits.push({
      coin: sym.replace(/USDT$/, ""),
      symbol: sym,
      type: "pump",
      changePct: fromLow,
      change24h: Number(t.priceChangePercent) || 0,
      volume: vol,
      price: last,
      low: lo,
      market: "FUTURES",
    });
  }
  hits.sort((a, b) => b.changePct - a.changePct);
  pumpCache = { t: Date.now(), rows: hits };
  await notifyFuturesPumps(hits, th);
  return hits;
}

async function notifyFuturesPumps(hits, th) {
  if (settingsCache?.pump_enabled === false) return;
  if (settingsCache?.telegram_enabled === false) return;
  const token = settingsCache?.telegram_bot_token;
  const chat = settingsCache?.telegram_chat_id;
  if (!token || token === "••••••••" || !chat) return;
  const seen = loadPumpAlerts();
  const now = Date.now();
  for (const p of hits) {
    const prev = Number(seen[p.symbol] || 0);
    if (now - prev < PUMP_COOLDOWN_MS) continue;
    const text = [
      "FUTURES PUMP " + p.symbol,
      "+" + p.changePct.toFixed(0) + "% from 24h low (min " + th + "%)",
      "Last " + p.price + "  Low " + p.low,
      "24h " + p.change24h.toFixed(1) + "%  Vol $" + (p.volume / 1e6).toFixed(1) + "M",
      "https://www.binance.com/en/futures/" + p.symbol,
    ].join("\n");
    try {
      const r = await fetch("https://api.telegram.org/bot" + token + "/sendMessage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
      });
      if (r.ok) { seen[p.symbol] = now; savePumpAlerts(seen); }
    } catch (e) { console.warn("pump telegram", e); }
  }
}

function startFuturesPumpLoop() {
  if (pumpLoop) clearInterval(pumpLoop);
  const run = () => scanFuturesPumps().catch((e) => console.warn("futures pump scan", e));
  run();
  pumpLoop = setInterval(run, 60000);
}


function fngLabel(v) {
  if (v == null) return '—';
  if (v <= 24) return 'Extreme Fear';
  if (v <= 44) return 'Fear';
  if (v <= 55) return 'Neutral';
  if (v <= 74) return 'Greed';
  return 'Extreme Greed';
}

function setRing(id, value, colorVar) {
  const el = document.getElementById(id);
  if (!el) return;
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  el.style.strokeDasharray = String(RING_C);
  el.style.strokeDashoffset = String(RING_C * (1 - v / 100));
  if (colorVar) el.style.stroke = getComputedStyle(document.documentElement).getPropertyValue(colorVar).trim();
}

function setMeter(id, value) {
  const el = document.getElementById(id);
  if (el) el.style.width = Math.max(0, Math.min(100, Number(value) || 0)) + '%';
}

function drawEquity(canvasId, points) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const parent = canvas.parentElement;
  const w = parent.clientWidth || 600;
  const h = parent.clientHeight || 220;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + 'px';
  canvas.style.height = h + 'px';
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const pts = (points && points.length) ? points : [{ t: 0, equity: 10000 }, { t: 1, equity: 10000 }];
  const vals = pts.map((p) => p.equity);
  let min = Math.min(...vals);
  let max = Math.max(...vals);
  if (min === max) { min -= 50; max += 50; }
  const pad = 14;
  const xs = (i) => pad + (i / Math.max(pts.length - 1, 1)) * (w - pad * 2);
  const ys = (v) => pad + (1 - (v - min) / (max - min)) * (h - pad * 2);

  const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#22d3ee';
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(34,211,238,0.3)');
  grad.addColorStop(0.55, 'rgba(167,139,250,0.12)');
  grad.addColorStop(1, 'rgba(167,139,250,0)');

  ctx.beginPath();
  pts.forEach((p, i) => {
    const x = xs(i), y = ys(p.equity);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.lineTo(xs(pts.length - 1), h - pad);
  ctx.lineTo(xs(0), h - pad);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.beginPath();
  pts.forEach((p, i) => {
    const x = xs(i), y = ys(p.equity);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = accent;
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--mute').trim() || '#8f877a';
  ctx.font = '11px IBM Plex Mono, monospace';
  ctx.fillText('$' + fmt(vals[vals.length - 1], 0), pad, 12);
}

function showPage(id) {
  document.querySelectorAll('.page').forEach((p) => p.classList.remove('active'));
  document.getElementById('page-' + id)?.classList.add('active');
  document.querySelectorAll('.icon-rail a, .mobile-nav a').forEach((a) => {
    a.classList.toggle('active', a.dataset.page === id);
  });
  const loaders = {
    dashboard: loadDash,
    portfolio: loadPortfolio,
    risk: loadRisk,
    signals: loadSignals,
    macro: loadMacro,
    pumps: loadPumps,
    ong: () => {},
    whales: loadWhales,
    'auto-trades': loadAuto,
    trades: loadTrades,
    history: loadHistory,
    backtest: () => {},
    settings: loadSettings,
    logs: loadLogs,
  };
  loaders[id]?.();
}

function setBotStatus(d) {
  const on = !!d.bot_enabled;
  document.getElementById('bot-dot')?.classList.toggle('on', on);
  document.getElementById('bot-label').textContent = on ? 'Bots On' : 'Bots Off';
  document.getElementById('btn-toggle').textContent = on ? 'Pause bots' : 'Start bots';
  const ops = document.getElementById('btn-ops-toggle');
  if (ops) ops.textContent = on ? 'Pause bots' : 'Start bots';
  document.getElementById('badge-paper').textContent = d.paper_mode ? 'PAPER' : 'LIVE';
  document.getElementById('badge-paper').className = 'mode-tag ' + (d.paper_mode ? 'badge-yellow' : 'badge-red');
  const hm = document.getElementById('hero-mode');
  if (hm) hm.textContent = d.paper_mode ? 'PAPER' : 'LIVE';
}

function renderBotMatrix(d) {
  const enabled = new Set(d.enabled_bots || []);
  const stats = {};
  (d.bots || []).forEach((b) => { stats[b.bot_name] = b; });
  document.getElementById('bot-matrix').innerHTML = BOT_NAMES.map((n) => {
    const m = BOT_META[n];
    const s = stats[n] || {};
    const on = enabled.has(n);
    return `<button type="button" class="bot-tile ${on ? 'on' : ''}" onclick="toggleBot('${n}')">
      <div class="code">${m[0]} · ${on ? 'ON' : 'OFF'}</div>
      <div class="name">${n}</div>
      <div class="stats"><span>${s.total_trades || 0} tr</span><span class="${pnlC(s.total_pnl)}">$${fmt(s.total_pnl || 0, 0)}</span></div>
    </button>`;
  }).join('');
}

function renderExposure(d) {
  const bots = d.bots || [];
  const max = Math.max(1, ...bots.map((b) => Math.abs(b.total_pnl || 0)));
  document.getElementById('exposure-bars').innerHTML = bots.map((b) => {
    const pnl = b.total_pnl || 0;
    const pct = Math.abs(pnl) / max * 100;
    return `<div class="bar-row">
      <span class="nm">${b.bot_name}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${pnl >= 0 ? 'var(--mint)' : 'var(--rose)'}"></div></div>
      <span class="amt ${pnlC(pnl)}">$${fmt(pnl, 0)}</span>
    </div>`;
  }).join('') || '<div class="empty">No bot P&amp;L yet</div>';
}

function renderWatchlist(d) {
  const coins = (settingsCache?.tracked_coins || 'BTC,ETH,SOL,BNB').split(',').map((c) => c.trim()).filter(Boolean).slice(0, 8);
  const pumps = {};
  (d.pump_opportunities || []).forEach((p) => { pumps[p.coin] = p; });
  document.getElementById('watchlist').innerHTML = coins.map((c) => {
    const p = pumps[c];
    return `<div class="bar-row">
      <span class="nm">${c}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${p ? Math.min(100, Math.abs(p.changePct)) : 8}%"></div></div>
      <span class="amt ${p ? pnlC(p.changePct) : ''}">${p ? fmt(p.changePct, 1) + '%' : '—'}</span>
    </div>`;
  }).join('');
}

function renderOpsFeed(d) {
  const items = [];
  (d.recent_signals || []).forEach((s) => {
    items.push({
      t: s.timestamp || 0,
      html: `<div class="feed-item">
        <div class="feed-top"><span class="feed-coin">${s.coin}</span><span class="badge ${String(s.signal).toUpperCase().includes('BUY') || s.signal === 'long' ? 'badge-green' : 'badge-red'}">${s.signal}</span></div>
        <div class="feed-body">${(s.reasoning || 'Signal').slice(0, 90)} · ${s.confidence || '—'}%</div>
        <div class="feed-time">${s.timestamp ? new Date(s.timestamp).toLocaleTimeString() : ''}</div>
      </div>`,
    });
  });
  (d.pump_opportunities || []).forEach((p) => {
    items.push({
      t: Date.now(),
      html: `<div class="feed-item">
        <div class="feed-top"><span class="feed-coin">${p.coin}</span><span class="badge ${p.type === 'pump' ? 'badge-green' : 'badge-red'}">${p.type}</span></div>
        <div class="feed-body">${fmt(p.changePct, 1)}% · vol $${fmt((p.volume || 0) / 1e6, 1)}M</div>
      </div>`,
    });
  });
  (d.recent_whales || []).forEach((w) => {
    items.push({
      t: w.timestamp || 0,
      html: `<div class="feed-item">
        <div class="feed-top"><span class="feed-coin">${w.coin}</span><span class="badge badge-blue">whale</span></div>
        <div class="feed-body">${w.sentiment} · $${fmt((w.amount || 0) / 1e6, 1)}M · ${w.source || ''}</div>
        <div class="feed-time">${w.timestamp ? new Date(w.timestamp).toLocaleTimeString() : ''}</div>
      </div>`,
    });
  });
  items.sort((a, b) => new Date(b.t) - new Date(a.t));
  document.getElementById('ops-feed').innerHTML = items.slice(0, 12).map((x) => x.html).join('')
    || '<div class="empty">Quiet — scan to populate feed</div>';
}

async function loadDash() {
  try {
    if (!settingsCache) settingsCache = await api('/settings').catch(() => ({}));
    const d = await api('/dashboard');
    try {
      d.pump_opportunities = await scanFuturesPumps();
    } catch (e) { console.warn('futures pumps', e); }
    lastDash = d;

    document.getElementById('k-pv').textContent = '$' + fmt(d.portfolio_value);
    document.getElementById('k-bal').textContent = '$' + fmt(d.balance);
    document.getElementById('k-upnl').textContent = '$' + fmt(d.unrealized_pnl);
    document.getElementById('k-upnl').className = 'v ' + pnlC(d.unrealized_pnl);
    document.getElementById('k-tpnl').textContent = '$' + fmt(d.total_pnl);
    document.getElementById('k-tpnl').className = 'v ' + pnlC(d.total_pnl);
    document.getElementById('k-ppct').textContent = fmt(d.pnl_pct, 1) + '%';
    document.getElementById('k-ppct').className = 'v ' + pnlC(d.pnl_pct);
    document.getElementById('k-wr').textContent = fmt(d.win_rate, 1) + '%';
    document.getElementById('k-sh').textContent = fmt(d.sharpe_ratio);
    document.getElementById('k-dd').textContent = fmt(d.max_drawdown, 1) + '%';
    document.getElementById('k-pf').textContent = fmt(d.profit_factor);
    document.getElementById('k-open').textContent = String(d.open_trades || 0);
    document.getElementById('k-sig').textContent = String(d.signals_total || 0);
    document.getElementById('k-safety').textContent = (d.safety_score || 0) + '/6';

    const fng = d.fear_greed?.value ?? d.fear_greed;
    document.getElementById('k-fng').textContent = fng ?? '—';
    document.getElementById('k-fng-lbl').textContent = d.fear_greed?.classification || fngLabel(fng);

    const sent = d.sentiment?.score ?? 50;
    document.getElementById('sent-score').textContent = sent;
    document.getElementById('sent-rec').textContent = d.sentiment?.recommendation || 'Hold';
    setMeter('sent-bar', sent);
    setRing('sent-ring', sent, sent >= 55 ? '--mint' : sent <= 40 ? '--rose' : '--copper');

    const fv = Number(fng) || 50;
    const fngCls = d.fear_greed?.classification || fngLabel(fv);
    document.getElementById('fng-score').textContent = fv;
    document.getElementById('fng-lbl').textContent = fngCls;
    setMeter('fng-bar', fv);
    setRing('fng-ring', fv, fv >= 55 ? '--mint' : fv <= 44 ? '--rose' : '--copper');

    // Fear = red, Greed = green
    const moodEl = document.getElementById('flag-mood');
    const fngBar = document.getElementById('fng-bar')?.parentElement;
    let moodClass = 'neutral';
    let moodLabel = 'NEUTRAL';
    if (fv <= 44) { moodClass = 'fear'; moodLabel = fv <= 24 ? 'EXTREME FEAR' : 'FEAR'; }
    else if (fv >= 56) { moodClass = 'greed'; moodLabel = fv >= 75 ? 'EXTREME GREED' : 'GREED'; }
    moodEl.className = 'rflag mood ' + moodClass;
    document.getElementById('flag-mood-v').textContent = moodLabel;
    document.getElementById('flag-mood-s').textContent = 'F&G ' + fv + ' · ' + fngCls;
    if (fngBar) fngBar.className = 'meter ' + (moodClass === 'fear' ? 'fear' : moodClass === 'greed' ? 'greed' : '');

    // Bullish / Bearish from sentiment + F&G
    const trendEl = document.getElementById('flag-trend');
    let trend = 'MIXED';
    let trendClass = 'neutral';
    if (sent >= 58 || (sent >= 52 && fv >= 60)) { trend = 'BULLISH'; trendClass = 'bull'; }
    else if (sent <= 42 || (sent <= 48 && fv <= 40)) { trend = 'BEARISH'; trendClass = 'bear'; }
    trendEl.className = 'rflag trend ' + trendClass;
    document.getElementById('flag-trend-v').textContent = trend;
    document.getElementById('flag-trend-s').textContent = 'Sentiment ' + sent;

    // BUY / SELL / HOLD flag
    const actionEl = document.getElementById('flag-action');
    let action = 'HOLD';
    let actionClass = 'hold';
    let actionHint = 'No clear edge — wait';
    if (trend === 'BULLISH' && moodClass !== 'fear') {
      action = 'BUY'; actionClass = 'buy';
      actionHint = 'Risk-on bias — favor longs';
    } else if (trend === 'BEARISH' || moodClass === 'fear') {
      action = 'SELL'; actionClass = 'sell';
      actionHint = 'Risk-off bias — favor shorts';
    } else if (moodClass === 'greed' && sent >= 50) {
      action = 'BUY'; actionClass = 'buy';
      actionHint = 'Greed supporting longs';
    }
    const rec = (d.sentiment?.recommendation || '').toLowerCase();
    if (rec.includes('strong buy') || rec === 'buy') {
      action = 'BUY'; actionClass = 'buy'; actionHint = d.sentiment.recommendation;
    } else if (rec.includes('strong sell') || rec === 'sell') {
      action = 'SELL'; actionClass = 'sell'; actionHint = d.sentiment.recommendation;
    }
    actionEl.className = 'rflag action ' + actionClass;
    document.getElementById('flag-action-v').textContent = action;
    document.getElementById('flag-action-s').textContent = actionHint;

    const regime = document.getElementById('regime-text');
    const hint = document.getElementById('regime-hint');
    const sub = document.getElementById('regime-sub');
    if (moodClass === 'fear') {
      regime.textContent = 'Risk-off · Fear regime';
      regime.className = 'regime-pill fear';
      hint.textContent = 'Fear is elevated — market leans bearish. Prefer SELL / short bias until sentiment recovers.';
    } else if (moodClass === 'greed') {
      regime.textContent = 'Risk-on · Greed regime';
      regime.className = 'regime-pill greed';
      hint.textContent = 'Greed is elevated — market leans bullish. Prefer BUY / long bias; watch for late-cycle reversals.';
    } else {
      regime.textContent = 'Mixed · Range regime';
      regime.className = 'regime-pill mixed';
      hint.textContent = 'Fear & Greed near neutral — wait for a clearer bullish or bearish flag before sizing up.';
    }
    if (sub) sub.textContent = action + ' · ' + trend;

    setBotStatus(d);
    document.getElementById('clock').textContent = new Date().toUTCString();
    document.getElementById('ops-clock').textContent = new Date().toLocaleTimeString();

    const r = d.risk || {};
    ['daily', 'weekly', 'monthly'].forEach((k) => {
      const v = r[k + '_pnl'];
      const el = document.getElementById('r-' + k);
      const ops = document.getElementById('ops-' + k);
      if (el) { el.textContent = '$' + fmt(v); el.className = 'v ' + pnlC(v); }
      if (ops) { ops.textContent = '$' + fmt(v); ops.className = 'v ' + pnlC(v); }
    });

    const alert = document.getElementById('risk-alert');
    const cb = document.getElementById('cb-label');
    if (d.circuit_breaker) {
      alert.textContent = 'Circuit breaker ACTIVE — trading halted.';
      alert.classList.remove('hidden');
      if (cb) cb.textContent = 'breaker on';
    } else {
      alert.classList.add('hidden');
      if (cb) cb.textContent = 'breaker off';
    }

    equityPts = d.equity_curve || [];
    drawEquity('equity-chart', equityPts);
    renderBotMatrix(d);
    renderExposure(d);
    renderWatchlist(d);
    renderOpsFeed(d);
    renderHighMacros(d.high_macros || []);

    document.getElementById('dash-signals').innerHTML = (d.recent_signals || []).slice(0, 4).map((s) => `
      <div class="feed-item">
        <div class="feed-top"><span class="feed-coin">${s.coin}</span><span class="badge badge-blue">${s.confidence || '—'}%</span></div>
        <div class="feed-body">${s.signal} — ${(s.reasoning || '').slice(0, 70)}</div>
      </div>`).join('') || '<div class="empty">No signals</div>';

    document.getElementById('dash-pulse').innerHTML = (d.pump_opportunities || []).slice(0, 5).map((p) => `
      <div class="feed-item">
        <div class="feed-top"><span class="feed-coin">${p.coin}</span><span class="badge ${p.type === 'pump' ? 'badge-green' : 'badge-red'}">${p.type}</span></div>
        <div class="feed-body ${pnlC(p.changePct)}">${fmt(p.changePct, 1)}%</div>
      </div>`).join('') || '<div class="empty">No pumps</div>';

    const ai = await api('/ai-analysis').catch(() => null);
    const brief = d.desk_brief || await api('/desk-brief').catch(() => null);
    let box = '';
    if (brief) {
      box += `<div style="margin-bottom:10px"><strong style="color:var(--accent)">Desk bias: ${(brief.bias || '—').toUpperCase()}</strong>
        <span class="badge badge-blue" style="margin-left:6px">news ${brief.news_score ?? '—'}</span>
        ${brief.eventBlackout ? '<span class="badge badge-red" style="margin-left:4px">EVENT WINDOW</span>' : ''}
        <div style="margin-top:6px;font-size:12px">${(brief.notes || []).join(' · ') || 'Waiting for first scan…'}</div></div>`;
    }
    if (ai && (ai.summary || ai.trend)) {
      box += `<strong style="color:var(--text)">${(ai.trend || '—').toUpperCase()}</strong> — ${ai.summary || ''}
        <div style="margin-top:8px;font-family:var(--mono);font-size:11px">Support $${fmt(ai.support)} · Resistance $${fmt(ai.resistance)} · Risk ${ai.riskLevel || '—'}${ai.desk_bias ? ' · Bias ' + ai.desk_bias : ''}</div>`;
    }
    if (!box) {
      box = settingsCache?.has_anthropic
        ? 'Anthropic expert desk ready. Enable Scalper + Start bots, then Scan — Claude picks scalps from news + macros.'
        : 'Add your Anthropic API key in Settings → API Keys, enable Scalper (Anthropic expert desk), Start bots, then Scan.';
    }
    document.getElementById('ai-box').innerHTML = box;

    if (!(d.high_macros || []).length) loadOpsMacro();
  } catch (e) { console.error(e); }
}

async function loadPortfolio() {
  const d = await api('/portfolio');
  document.getElementById('pf-bal').textContent = '$' + fmt(d.balance);
  document.getElementById('pf-count').textContent = (d.holdings || []).length;
  document.getElementById('pf-body').innerHTML = (d.holdings || []).map((t) => `
    <tr>
      <td>${t.coin}</td><td><span class="badge badge-blue">${t.bot_name}</span></td>
      <td><span class="badge ${t.signal === 'long' ? 'badge-green' : 'badge-red'}">${t.signal}</span></td>
      <td>$${fmt(t.entry_price)}</td><td>$${fmt(t.current_price)}</td><td>$${fmt(t.size_usd)}</td>
      <td class="${pnlC(t.unrealized_pnl)}">$${fmt(t.unrealized_pnl)}</td>
      <td>${t.confidence != null ? t.confidence + '%' : '—'}</td>
      <td><button class="btn btn-danger btn-sm" onclick="closeTrade(${t.id})">Close</button></td>
    </tr>`).join('') || '<tr><td colspan="9" class="empty">No open positions</td></tr>';
}

async function closeTrade(id) {
  try {
    await api('/trades/close', { method: 'POST', body: JSON.stringify({ id: Number(id) }) });
    toast('Trade closed');
    const page = document.querySelector('.page.active')?.id?.replace('page-', '');
    if (page === 'trades') loadTrades();
    else if (page === 'auto-trades') loadAuto();
    else if (page === 'portfolio') loadPortfolio();
    else {
      loadTrades().catch(() => {});
      loadPortfolio().catch(() => {});
      loadDash().catch(() => {});
    }
  } catch (e) {
    toast(e.message || 'Close failed');
  }
}

async function loadTrades() {
  const rows = await api('/trades?limit=100');
  document.getElementById('trades-body').innerHTML = (rows || []).map((t) => {
    const open = t.status === 'open';
    return `<tr>
      <td><span class="badge badge-blue">${t.bot_name}</span></td>
      <td>${t.coin}</td>
      <td><span class="badge ${t.signal === 'long' ? 'badge-green' : 'badge-red'}">${t.signal}</span></td>
      <td>$${fmt(t.entry_price)}</td>
      <td>${t.exit_price != null ? '$' + fmt(t.exit_price) : '—'}</td>
      <td class="${pnlC(t.pnl_usd)}">${t.pnl_usd != null ? '$' + fmt(t.pnl_usd) : '—'}</td>
      <td>${t.reason || '—'}</td>
      <td><span class="badge ${t.status === 'win' ? 'badge-green' : t.status === 'loss' ? 'badge-red' : 'badge-blue'}">${t.status}</span></td>
      <td>${open
        ? `<button type="button" class="btn btn-danger btn-sm" onclick="closeTrade(${t.id})">Close</button>`
        : '<span style="color:var(--mute);font-size:11px">—</span>'}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="9" class="empty">No trades</td></tr>';
}

async function loadRisk() {
  const r = await api('/risk');
  document.getElementById('risk-kpis').innerHTML = `
    <div class="kpi"><div class="kpi-label">Balance</div><div class="kpi-value">$${fmt(r.balance)}</div></div>
    <div class="kpi"><div class="kpi-label">Daily</div><div class="kpi-value ${pnlC(r.daily_pnl)}">$${fmt(r.daily_pnl)}</div></div>
    <div class="kpi"><div class="kpi-label">Weekly</div><div class="kpi-value ${pnlC(r.weekly_pnl)}">$${fmt(r.weekly_pnl)}</div></div>
    <div class="kpi"><div class="kpi-label">Monthly</div><div class="kpi-value ${pnlC(r.monthly_pnl)}">$${fmt(r.monthly_pnl)}</div></div>
    <div class="kpi"><div class="kpi-label">Open</div><div class="kpi-value">${r.open_trades}</div></div>
    <div class="kpi"><div class="kpi-label">Consec. losses</div><div class="kpi-value">${r.consecutive_losses}</div></div>
    <div class="kpi"><div class="kpi-label">Breaker</div><div class="kpi-value ${r.circuit_breaker ? 'loss' : 'profit'}">${r.circuit_breaker ? 'ON' : 'OFF'}</div></div>`;
  const L = r.limits || {};
  document.getElementById('risk-limits').innerHTML = `
    Daily ≤ $${fmt(L.daily ?? L.daily_loss_limit, 0)} · Weekly ≤ $${fmt(L.weekly ?? L.weekly_loss_limit, 0)} · Monthly ≤ $${fmt(L.monthly ?? L.monthly_loss_limit, 0)}<br>
    Min bal $${fmt(L.minBal ?? L.min_account_balance, 0)} · Max pos ${fmt(L.maxPos ?? L.max_position_pct, 0)}%<br>
    Max open ${L.maxOpen ?? L.max_open_trades ?? '—'} · Max consecutive ${L.maxConsec ?? L.max_consecutive_losses ?? '—'}`;
}

function macroNewsMeta(e) {
  const ban = e.banner || (e.tone === 'hawkish' ? 'danger' : e.tone === 'dovish' ? 'soft' : 'watch');
  const label = String(e.banner_label || '').toUpperCase().includes('BAD')
    ? 'BAD NEWS'
    : String(e.banner_label || '').toUpperCase().includes('GOOD')
      ? 'GOOD NEWS'
      : (ban === 'danger' ? 'BAD NEWS' : ban === 'soft' ? 'GOOD NEWS' : 'WATCH');
  const emoji = label === 'BAD NEWS' ? '🔴' : label === 'GOOD NEWS' ? '🟢' : '🟡';
  return { ban, label, emoji, flag: `${emoji} ${label}` };
}

function renderHighMacros(items) {
  const el = document.getElementById('ops-macros');
  if (!el) return;
  const list = items || [];
  el.innerHTML = list.length ? list.map((e) => {
    const title = e.code ? `${e.title} (${e.code})` : (e.label || e.title);
    const { ban, flag } = macroNewsMeta(e);
    const cur = e.current || e.actual || '—';
    return `<div class="macro-card">
      <div class="macro-banner ${ban}">${flag}</div>
      <div class="body">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
          <div style="font-weight:600;color:var(--text);font-size:12px;line-height:1.35">${title}</div>
          <span class="feed-time">${e.country || ''}</span>
        </div>
        <div style="color:var(--accent);font-weight:600;font-size:11px;margin-top:6px">${e.time_left || '—'}</div>
        <div style="font-size:10px;color:var(--mute);margin-top:4px;line-height:1.4">${e.meaning || ''}</div>
        <div class="macro-stats">
          <div class="s"><div class="l">Forecast</div><div class="v">${e.forecast || '—'}</div></div>
          <div class="s"><div class="l">Current</div><div class="v">${cur}</div></div>
          <div class="s"><div class="l">Previous</div><div class="v">${e.previous || '—'}</div></div>
        </div>
        <div class="feed-time" style="margin-top:6px">${e.banner_hint || ''}</div>
      </div>
    </div>`;
  }).join('') : '<div class="empty">No high-impact events in the next 7 days</div>';
}

async function loadOpsMacro() {
  try {
    const ev = await api('/macro');
    renderHighMacros(ev);
  } catch (_) {
    const el = document.getElementById('ops-macros');
    if (el) el.innerHTML = '<div class="empty">Macro unavailable</div>';
  }
}

async function loadSignals() {
  const sigs = await api('/signals');
  document.getElementById('sig-list').innerHTML = (sigs || []).slice(0, 25).map((s) => `
    <div class="panel">
      <div class="signal-card">
        <div>
          <strong style="font-family:var(--mono)">${s.coin}</strong>
          <span class="badge ${String(s.signal).toUpperCase().includes('BUY') || s.signal === 'long' ? 'badge-green' : 'badge-red'}" style="margin-left:8px">${s.signal}</span>
          <div style="font-size:12px;color:var(--mute);margin-top:8px">${s.reasoning || ''}</div>
          <div style="font-size:11px;font-family:var(--mono);color:var(--mute);margin-top:8px">
            Entry $${fmt(s.entry)} · TP1 $${fmt(s.tp1)} · TP2 $${fmt(s.tp2)} · SL $${fmt(s.sl)}
          </div>
        </div>
        <div class="conf-big">${s.confidence || '—'}<small>conf</small></div>
      </div>
    </div>`).join('') || '<div class="panel empty">No signals — Start bots + Scan</div>';
}

async function loadHistory() {
  const sigs = await api('/signals');
  document.getElementById('hist-list').innerHTML = (sigs || []).map((s) => `
    <div class="panel signal-card">
      <div><strong>${s.coin}</strong> <span class="badge badge-blue">${s.signal}</span>
        <div style="font-size:11px;color:var(--mute);margin-top:6px">${s.reasoning || ''}</div></div>
      <div style="font-size:11px;color:var(--mute)">${s.timestamp ? new Date(s.timestamp).toLocaleString() : '—'}</div>
    </div>`).join('') || '<div class="panel empty">Empty</div>';
}

async function loadMacro() {
  const ev = await api('/macro');
  document.getElementById('macro-body').innerHTML = (ev || []).map((e) => {
    const title = e.code ? `${e.title} (${e.code})` : e.title;
    const { ban, label, flag } = macroNewsMeta(e);
    const badge = ban === 'danger' ? 'badge-red' : ban === 'soft' ? 'badge-green' : 'badge-yellow';
    const cur = e.current || e.actual || '—';
    return `<tr>
      <td>
        <div>${title}</div>
        <div style="font-size:10px;color:var(--mute);margin-top:4px;max-width:320px">${e.meaning || ''}</div>
      </td>
      <td>${e.country || '—'}</td>
      <td>
        <span class="macro-flag ${ban}" title="${label}">${flag}</span>
        <div style="font-size:9px;color:var(--mute);margin-top:4px">HIGH IMPACT</div>
      </td>
      <td><div style="color:var(--accent);font-weight:600">${e.time_left || '—'}</div>
        <div style="font-size:10px;color:var(--mute)">${e.datetime ? new Date(e.datetime).toUTCString().slice(0, 22) : '—'}</div></td>
      <td>${e.forecast || '—'}</td>
      <td>${cur}</td>
      <td>${e.previous || '—'}</td></tr>`;
  }).join('') || '<tr><td colspan="7" class="empty">No high-impact events</td></tr>';
}

async function loadPumps() {
  let rows = [];
  try { rows = await scanFuturesPumps(true); } catch (e) { rows = await api('/pumps').catch(() => []); }
  document.getElementById('pump-body').innerHTML = (rows || []).map((p) => `
    <tr><td>${p.coin}</td>
    <td><span class="badge badge-blue">${p.market || 'FUTURES'}</span></td>
    <td><span class="badge ${p.type === 'pump' ? 'badge-green' : 'badge-red'}">${p.type}</span></td>
    <td class="${pnlC(p.changePct)}">${fmt(p.changePct, 1)}% from low</td>
    <td>$${fmt((p.volume || 0) / 1e6, 1)}M</td>
    <td>$${fmt(p.price)}</td></tr>`).join('') || '<tr><td colspan="6" class="empty">No USDT-M futures ≥ ' + pumpThreshold() + '% from 24h low</td></tr>';
}

async function loadWhales() {
  const w = await api('/whales?hours=48');
  document.getElementById('whale-list').innerHTML = (w || []).map((x) => `
    <div class="panel signal-card">
      <div><strong>${x.coin}</strong>
        <span class="badge badge-blue" style="margin-left:6px">${x.source}</span>
        <span class="badge ${x.sentiment === 'bullish' ? 'badge-green' : 'badge-red'}">${x.sentiment}</span>
        <div style="font-size:12px;color:var(--mute);margin-top:6px">${x.type} · $${fmt((x.amount || 0) / 1e6, 1)}M</div>
      </div>
      <div style="font-size:11px;color:var(--mute)">${x.timestamp ? new Date(x.timestamp).toLocaleString() : '—'}</div>
    </div>`).join('') || '<div class="panel empty">No whale alerts</div>';
}

async function loadAuto() {
  const d = await api('/auto-trades');
  document.getElementById('bots-grid').innerHTML = (d.bots || []).map((b) => {
    const on = d.settings?.[`${b.bot_name}_enabled`];
    const m = BOT_META[b.bot_name] || ['BT', ''];
    return `<div class="panel">
      <div style="display:flex;justify-content:space-between;margin-bottom:10px">
        <div><strong style="font-family:var(--mono)">${m[0]} · ${b.bot_name.toUpperCase()}</strong>
          <div style="font-size:11px;color:var(--mute)">${m[1]}</div></div>
        <span class="badge ${on ? 'badge-green' : 'badge-yellow'}">${on ? 'ON' : 'OFF'}</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px">
        <div>Trades: <b>${b.total_trades}</b></div><div>Open: <b>${b.open_trades || 0}</b></div>
        <div>Win: <b class="${b.win_rate >= 50 ? 'profit' : 'loss'}">${fmt(b.win_rate, 1)}%</b></div>
        <div>P&L: <b class="${pnlC(b.total_pnl)}">$${fmt(b.total_pnl)}</b></div>
      </div>
      <button class="btn btn-ghost" style="width:100%;margin-top:10px" onclick="toggleBot('${b.bot_name}')">${on ? 'Disable' : 'Enable'}</button>
    </div>`;
  }).join('');

  document.getElementById('at-body').innerHTML = (d.recent_trades || []).map((t) => {
    const open = t.status === 'open';
    return `<tr>
      <td><span class="badge badge-blue">${t.bot_name}</span></td>
      <td>${t.coin}</td>
      <td><span class="badge ${t.signal === 'long' ? 'badge-green' : 'badge-red'}">${t.signal}</span></td>
      <td>$${fmt(t.entry_price)}</td>
      <td>${t.exit_price ? '$' + fmt(t.exit_price) : '—'}</td>
      <td class="${pnlC(t.pnl_usd)}">${t.pnl_usd != null ? '$' + fmt(t.pnl_usd) : '—'}</td>
      <td>${t.duration_hours != null ? t.duration_hours + 'h' : '—'}</td>
      <td><span class="badge ${t.status === 'win' ? 'badge-green' : t.status === 'loss' ? 'badge-red' : 'badge-blue'}">${t.status}</span></td>
      <td>${open
        ? `<button type="button" class="btn btn-danger btn-sm" onclick="closeTrade(${t.id})">Close</button>`
        : '—'}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="9" class="empty">No trades yet</td></tr>';
}

async function toggleBot(name) {
  await api(`/bots/${name}/toggle`, { method: 'POST' });
  toast(name + ' toggled');
  const page = document.querySelector('.page.active')?.id?.replace('page-', '');
  if (page === 'dashboard') loadDash();
  if (page === 'auto-trades') loadAuto();
}

async function loadLogs() {
  const logs = await api('/logs?limit=100');
  document.getElementById('log-list').innerHTML = (logs || []).map((l) =>
    `<div>[${l.ts}] <span style="color:${l.level === 'error' ? 'var(--rose)' : 'var(--mute)'}">${l.level}</span> ${l.msg}</div>`
  ).join('') || 'No logs';
}

const SETTINGS_TABS = [
  ['api', 'API Keys'], ['markets', 'Markets'], ['signals', 'Signals'],
  ['scalper', 'Scalper'], ['pump', 'Pump Alerts'], ['riskoff', 'Risk-Off Alerts'],
  ['risk', 'Risk Control'], ['advanced', 'Advanced'],
];

function field(key, label, hint, type = 'number') {
  const v = settingsCache?.[key];
  if (typeof v === 'boolean' || type === 'toggle') {
    return `<div class="toggle-row"><div><div>${label}</div>${hint ? `<div class="hint">${hint}</div>` : ''}</div>
      <button type="button" class="toggle ${v ? 'on' : ''}" data-key="${key}" onclick="flip(this)"></button></div>`;
  }
  return `<div class="form-group"><label>${label}</label>
    <input type="${type}" data-key="${key}" value="${v ?? ''}" onchange="queueSave()" oninput="queueSave()">
    ${hint ? `<div class="hint">${hint}</div>` : ''}</div>`;
}

/** Binance-style % stick + typed value */
function pctSlider(key, label, opts = {}) {
  const { min = 0.1, max = 50, step = 0.1, hint = '', tone = '', unit = '%' } = opts;
  const raw = Number(settingsCache?.[key]);
  const v = Number.isFinite(raw) ? raw : min;
  const pct = Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
  const mid = (min + max) / 2;
  const fmtM = (n) => {
    const s = Number.isInteger(n) ? String(n) : (Math.round(n * 100) / 100).toString();
    return unit === '%' ? s + '%' : s + unit;
  };
  return `<div class="bn-field" data-bn="${key}">
    <div class="bn-head">
      <label>${label}</label>
      <div class="bn-input-wrap">
        <input type="number" data-key="${key}" data-bn-num="${key}" value="${v}" min="${min}" max="${max}" step="${step}"
          oninput="bnSync('${key}', this.value, 'num')" onchange="queueSave()">
        <span class="bn-unit">${unit}</span>
      </div>
    </div>
    <input type="range" class="bn-range ${tone}" data-bn-range="${key}" min="${min}" max="${max}" step="${step}" value="${v}"
      style="--bn-pct:${pct}%" oninput="bnSync('${key}', this.value, 'range')">
    <div class="bn-marks"><span>${fmtM(min)}</span><span>${fmtM(mid)}</span><span>${fmtM(max)}</span></div>
    ${hint ? `<div class="bn-hint">${hint}</div>` : ''}
  </div>`;
}

/** Entry amount: USDT input + balance % stick */
function amountSlider(key, label, opts = {}) {
  const { hint = '', maxCap = 10000 } = opts;
  const bal = Number(lastDash?.balance ?? lastDash?.portfolio_value ?? 10000) || 10000;
  const raw = Number(settingsCache?.[key]);
  const v = Number.isFinite(raw) ? raw : 50;
  const pctOfBal = Math.max(0, Math.min(100, (v / bal) * 100));
  return `<div class="bn-field bn-amount" data-bn="${key}" data-bal="${bal}">
    <div class="bn-head">
      <label>${label}</label>
      <div class="bn-input-wrap">
        <input type="number" data-key="${key}" data-bn-num="${key}" value="${v}" min="1" max="${maxCap}" step="1"
          oninput="bnAmountSync('${key}', this.value, 'num')" onchange="queueSave()">
        <span class="bn-unit">USDT</span>
      </div>
    </div>
    <div class="bn-amount-meta"><span>Available ≈ $${fmt(bal, 0)}</span><span id="bn-amt-pct-${key}">${fmt(pctOfBal, 1)}% of balance</span></div>
    <input type="range" class="bn-range" data-bn-range="${key}" min="0" max="100" step="1" value="${Math.round(pctOfBal)}"
      style="--bn-pct:${pctOfBal}%" oninput="bnAmountSync('${key}', this.value, 'pct')">
    <div class="bn-marks"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
    <div class="bn-pct-btns">
      ${[25, 50, 75, 100].map((p) => `<button type="button" data-pct="${p}" onclick="bnAmountPreset('${key}', ${p})">${p}%</button>`).join('')}
    </div>
    ${hint ? `<div class="bn-hint">${hint}</div>` : ''}
  </div>`;
}

function bnSync(key, value, from) {
  const wrap = document.querySelector(`.bn-field[data-bn="${key}"]`);
  if (!wrap) return;
  const num = wrap.querySelector(`[data-bn-num="${key}"]`);
  const range = wrap.querySelector(`[data-bn-range="${key}"]`);
  if (!num || !range) return;
  let v = parseFloat(value);
  if (!Number.isFinite(v)) return;
  const min = parseFloat(range.min);
  const max = parseFloat(range.max);
  v = Math.max(min, Math.min(max, v));
  if (from !== 'num') num.value = String(v);
  if (from !== 'range') range.value = String(v);
  range.style.setProperty('--bn-pct', ((v - min) / (max - min)) * 100 + '%');
  queueSave();
}

function bnAmountSync(key, value, from) {
  const wrap = document.querySelector(`.bn-field[data-bn="${key}"]`);
  if (!wrap) return;
  const bal = parseFloat(wrap.dataset.bal) || 10000;
  const num = wrap.querySelector(`[data-bn-num="${key}"]`);
  const range = wrap.querySelector(`[data-bn-range="${key}"]`);
  const label = document.getElementById('bn-amt-pct-' + key);
  if (!num || !range) return;
  let usd;
  let pct;
  if (from === 'pct') {
    pct = Math.max(0, Math.min(100, parseFloat(value) || 0));
    usd = Math.max(1, Math.round((bal * pct) / 100));
    num.value = String(usd);
  } else {
    usd = Math.max(1, parseFloat(value) || 0);
    pct = Math.max(0, Math.min(100, (usd / bal) * 100));
    range.value = String(Math.round(pct));
  }
  range.style.setProperty('--bn-pct', pct + '%');
  if (label) label.textContent = fmt(pct, 1) + '% of balance';
  wrap.querySelectorAll('.bn-pct-btns button').forEach((b) => {
    b.classList.toggle('active', Math.abs(parseFloat(b.dataset.pct) - pct) < 1);
  });
  queueSave();
}

function bnAmountPreset(key, pct) {
  bnAmountSync(key, pct, 'pct');
}

function renderSettingsSection(tab) {
  const f = field;
  if (tab === 'api') return [
    f('binance_api_key', 'Binance API Key', '', 'password'),
    f('binance_api_secret', 'Binance API Secret', '', 'password'),
    f('anthropic_api_key', 'Anthropic API Key', 'Required for expert scalper (Claude picks winning sides from news + macros)', 'password'),
    f('cursor_api_key', 'Cursor API Key (optional alias)', 'If set and Anthropic is empty, used as Anthropic key', 'password'),
    f('telegram_bot_token', 'Telegram Bot Token', '', 'password'),
    f('telegram_chat_id', 'Telegram Chat ID', '', 'text'),
    `<div class="form-group" style="margin-top:8px">
      <button type="button" class="btn btn-primary" onclick="testTelegram()">Send Telegram test message</button>
      <div class="hint" id="tg-test-status" style="margin-top:8px">Saves settings first, then sends a test ping to your chat.</div>
    </div>`,
    f('grok_api_key', 'Grok API Key', 'Optional', 'password'),
    f('etherscan_api_key', 'Etherscan API Key', 'Optional', 'password'),
    f('discord_webhook_url', 'Discord Webhook', 'Optional', 'text'),
  ].join('');
  if (tab === 'markets') return [
    f('tracked_coins', 'Tracked Coins', 'Comma-separated', 'text'),
    f('base_currency', 'Base Currency', '', 'text'),
    f('refresh_rate_sec', 'UI Refresh (sec)'),
    f('paper_mode', 'Paper Mode', '', 'toggle'),
  ].join('');
  if (tab === 'signals') return [
    pctSlider('min_confidence', 'Min Confidence', { min: 0, max: 100, step: 1, hint: 'Only take signals at or above this confidence' }),
    f('max_signals_per_hour', 'Max Signals / Hour'),
    f('signal_timeout_hours', 'Signal Timeout (hours)'),
    f('signals_ai', 'AI Signals', '', 'toggle'),
    f('signals_news', 'News for scalping', 'RSS tone feeds the scalper — not shown in UI', 'toggle'),
    f('signals_macro', 'Macro Signals', '', 'toggle'),
    f('signals_whale', 'Whale Signals', '', 'toggle'),
  ].join('');
  if (tab === 'scalper') return [
    '<div class="bn-section-title">Scalper · entry &amp; exits</div>',
    f('scalper_enabled', 'Enable Scalper', '', 'toggle'),
    f('scalper_ai_managed', 'Anthropic expert desk', 'Claude analyzes news + high macros and opens the best scalp', 'toggle'),
    f('scalper_respect_macros', 'Respect macro calendar', 'Hold / require higher confidence near High events', 'toggle'),
    f('scalper_block_long_hawkish', 'Block longs when hawkish', 'Force short bias on rate hikes / hot CPI windows', 'toggle'),
    f('scalper_hold_near_events', 'Hold near events', 'Avoid weak entries within ~90 minutes of High prints', 'toggle'),
    f('scalper_paper', 'Paper', '', 'toggle'),
    amountSlider('scalper_position_usd', 'Entry amount', { hint: 'How much USDT to enter with each scalp. Drag % of balance or type exact size.' }),
    pctSlider('scalper_tp_long_pct', 'Take profit · Long', { min: 0.2, max: 30, step: 0.1, tone: 'tp-tone' }),
    pctSlider('scalper_tp_short_pct', 'Take profit · Short', { min: 0.2, max: 30, step: 0.1, tone: 'tp-tone' }),
    pctSlider('scalper_sl_pct', 'Stop loss', { min: 0.2, max: 20, step: 0.1, tone: 'sl-tone' }),
    pctSlider('scalper_event_min_confidence', 'Min confidence near events', { min: 50, max: 95, step: 1 }),
    pctSlider('scalper_event_size_mult', 'Size near events', { min: 0.1, max: 1, step: 0.05, unit: '×', hint: '1.0 = full size · 0.6 = 60% size when macros are near' }),
    f('scalper_tp_enabled', 'TP On', '', 'toggle'),
    f('scalper_sl_enabled', 'SL On', '', 'toggle'),
    f('scalper_max_hold_hours', 'Max Hold Hours'),
    f('scalper_max_open', 'Max Open'),
  ].join('');
  if (tab === 'pump') return [
    '<div class="bn-section-title">Pump · USDT-M futures only · Telegram (no trades)</div>',
    f('pump_enabled', 'Enable Pump alerts', 'USDT-M futures only. Telegram when +500% from the 24h low — does not open positions', 'toggle'),
    pctSlider('pump_threshold_pct', 'Min pump % from 24h low', { min: 500, max: 2000, step: 50, hint: 'Futures only. Default 500 = 6x from the session low. Spot is ignored.' }),
    f('pump_min_volume_enabled', 'Min volume filter On', 'Off = ignore volume', 'toggle'),
    f('pump_min_volume_m', 'Min Volume M', 'Skip illiquid pumps (quote volume in millions USDT)'),
    '<div class="bn-hint" style="margin-top:8px">Requires Settings → API Keys → Telegram token + chat ID, and Advanced → Telegram ON.</div>',
  ].join('');
  if (tab === 'riskoff') return [
    '<div class="bn-section-title">Risk-Off · Telegram alerts only (no trades)</div>',
    f('riskoff_enabled', 'Enable Risk-Off alerts', 'Telegram when hawkish macros / extreme fear / bearish news — no auto shorts', 'toggle'),
    f('riskoff_coins', 'Coins to watch', 'Shown in the alert message', 'text'),
    pctSlider('riskoff_fear_max', 'F&G max to alert', { min: 5, max: 50, step: 1, hint: 'Alert if Fear & Greed ≤ this', tone: 'sl-tone' }),
    pctSlider('riskoff_news_max', 'News score max', { min: 10, max: 50, step: 1, hint: 'Alert if news score ≤ this and bearish' }),
    f('riskoff_window_hours', 'Macro window (hours)', 'Look ahead for hawkish High events'),
    '<div class="bn-section-title" style="margin-top:16px">High-impact macros · Telegram</div>',
    f('macro_alerts_enabled', 'High-impact macro alerts', 'Always send when Telegram token+chat set — 2h → 30m → 5m → 30s · BAD/GOOD NEWS label', 'toggle'),
    f('macro_alert_hours', 'Look-ahead (hours)', 'Only alerts inside the last 2h window (default 2)'),
    '<div class="bn-hint" style="margin-top:8px">Sends whenever bot token + chat ID are saved (even if Advanced → Telegram is off). Labels: BAD NEWS / GOOD NEWS / WATCH.</div>',
  ].join('');
  if (tab === 'risk') return [
    f('daily_loss_limit', 'Daily Loss Limit $'), f('weekly_loss_limit', 'Weekly Loss Limit $'),
    f('monthly_loss_limit', 'Monthly Loss Limit $'), f('min_account_balance', 'Min Balance $'),
    pctSlider('max_position_pct', 'Max Position', { min: 1, max: 100, step: 1, hint: 'Cap any single entry as % of account' }),
    pctSlider('max_stop_loss_pct', 'Max Stop Loss', { min: 0.5, max: 25, step: 0.1, tone: 'sl-tone' }),
    f('max_open_trades', 'Max Open Trades'), f('max_consecutive_losses', 'Max Consecutive Losses'),
    f('whale_confirmations', 'Whale Confirmations'),
    '<h3 style="margin:14px 0 8px;font-size:11px;color:var(--mute)">Safety checklist</h3>',
    f('safety_verified_keys', 'API keys verified', '', 'toggle'),
    f('safety_paper_first', 'Paper tested first', '', 'toggle'),
    f('safety_limits_set', 'Limits configured', '', 'toggle'),
    f('safety_sl_enabled', 'Stop losses on', '', 'toggle'),
    f('safety_telegram_ok', 'Telegram working', '', 'toggle'),
    f('safety_understand_risk', 'I understand risk', '', 'toggle'),
    `<div class="panel" style="margin-top:10px">Safety: <strong id="safety-score">${settingsCache?.safety_score || 0}/6</strong>
      <button class="btn btn-ghost btn-sm" style="margin-left:8px" onclick="resetRisk()">Reset defaults</button>
      <button class="btn btn-danger btn-sm" style="margin-left:6px" onclick="resetBreaker()">Reset breaker</button></div>`,
  ].join('');
  return [
    f('bot_master_enabled', 'Master Bot Switch', '', 'toggle'),
    f('telegram_enabled', 'Telegram', 'ON for pump / risk-off / macros / trade open+close alerts', 'toggle'),
    `<div class="form-group" style="margin-top:4px;margin-bottom:12px">
      <button type="button" class="btn btn-ghost" onclick="testTelegram()">Send Telegram test message</button>
      <div class="hint" id="tg-test-status-adv" style="margin-top:6px"></div>
    </div>`,
    f('discord_enabled', 'Discord', '', 'toggle'),
    f('email_enabled', 'Email', '', 'toggle'),
    f('logging_enabled', 'Logging', '', 'toggle'),
    f('caching_enabled', 'Caching', '', 'toggle'),
    f('debug_mode', 'Debug', '', 'toggle'),
    f('smtp_host', 'SMTP Host', '', 'text'),
    f('smtp_user', 'SMTP User', '', 'text'),
    f('smtp_pass', 'SMTP Pass', '', 'password'),
  ].join('');
}

async function testTelegram() {
  const status = document.getElementById('tg-test-status') || document.getElementById('tg-test-status-adv');
  if (status) status.textContent = 'Sending test…';
  try {
    await saveSettingsNow();
    const body = {};
    const tokenEl = document.querySelector('#settings-body [data-key="telegram_bot_token"]');
    const chatEl = document.querySelector('#settings-body [data-key="telegram_chat_id"]');
    if (tokenEl?.value && tokenEl.value !== '••••••••') body.telegram_bot_token = tokenEl.value;
    if (chatEl?.value) body.telegram_chat_id = chatEl.value;
    const r = await api('/telegram/test', { method: 'POST', body: JSON.stringify(body) });
    const msg = r.message || 'Test message sent';
    if (status) status.textContent = msg;
    toast(msg);
  } catch (e) {
    if (status) status.textContent = e.message || 'Telegram test failed';
    toast(e.message || 'Telegram test failed');
  }
}

function flip(el) { el.classList.toggle('on'); queueSave(); }
function queueSave() { clearTimeout(saveTimer); saveTimer = setTimeout(saveSettingsNow, 400); }

async function saveSettingsNow() {
  const data = {};
  document.querySelectorAll('#settings-body [data-key]').forEach((el) => {
    const k = el.dataset.key;
    if (el.classList.contains('toggle')) data[k] = el.classList.contains('on');
    else if (el.type === 'number') data[k] = parseFloat(el.value);
    else if (el.value && el.value !== '••••••••') data[k] = el.value;
  });
  try {
    const r = await api('/settings', { method: 'PUT', body: JSON.stringify(data) });
    settingsCache = r.settings;
    const sc = document.getElementById('safety-score');
    if (sc) {
      const s = settingsCache;
      sc.textContent = [
        s.safety_verified_keys, s.safety_paper_first, s.safety_limits_set,
        s.safety_sl_enabled, s.safety_telegram_ok, s.safety_understand_risk,
      ].filter(Boolean).length + '/6';
    }
    toast('Settings saved');
  } catch (e) { toast(e.message); }
}

async function loadSettings() {
  settingsCache = await api('/settings');
  const tabs = document.getElementById('settings-tabs');
  tabs.innerHTML = SETTINGS_TABS.map(([id, label], i) =>
    `<button class="tab ${i === 0 ? 'active' : ''}" data-tab="${id}">${label}</button>`).join('');
  tabs.querySelectorAll('.tab').forEach((t) => {
    t.onclick = () => {
      tabs.querySelectorAll('.tab').forEach((x) => x.classList.remove('active'));
      t.classList.add('active');
      document.getElementById('settings-body').innerHTML = renderSettingsSection(t.dataset.tab);
    };
  });
  document.getElementById('settings-body').innerHTML = renderSettingsSection('api');
}

async function resetRisk() {
  await api('/settings', {
    method: 'PUT',
    body: JSON.stringify({
      daily_loss_limit: 100, weekly_loss_limit: 400, monthly_loss_limit: 1000,
      min_account_balance: 100, max_position_pct: 10, max_stop_loss_pct: 8,
    }),
  });
  toast('Risk defaults restored');
  loadSettings();
}

async function resetBreaker() {
  await api('/risk/reset-breaker', { method: 'POST' });
  toast('Circuit breaker reset');
  loadDash();
}

async function runBt() {
  toast('Running backtest…');
  const result = await api('/backtest', {
    method: 'POST',
    body: JSON.stringify({
      symbol: document.getElementById('bt-sym').value,
      strategy: document.getElementById('bt-strat').value,
      days: +document.getElementById('bt-days').value,
      capital: +document.getElementById('bt-cap').value,
    }),
  });
  document.getElementById('bt-out').innerHTML = `
    <div class="kpi-grid">
      <div class="kpi"><div class="kpi-label">Trades</div><div class="kpi-value">${result.total_trades}</div></div>
      <div class="kpi"><div class="kpi-label">Win Rate</div><div class="kpi-value">${result.win_rate}%</div></div>
      <div class="kpi"><div class="kpi-label">Return</div><div class="kpi-value ${pnlC(result.net_profit)}">$${fmt(result.net_profit)}</div></div>
      <div class="kpi"><div class="kpi-label">Max DD</div><div class="kpi-value loss">${result.max_drawdown_pct}%</div></div>
      <div class="kpi"><div class="kpi-label">Sharpe</div><div class="kpi-value">${result.sharpe_ratio}</div></div>
      <div class="kpi"><div class="kpi-label">PF</div><div class="kpi-value">${result.profit_factor}</div></div>
    </div>
    <div class="panel">Monte Carlo median $${fmt(result.monte_carlo?.median)} · P5 $${fmt(result.monte_carlo?.p5)} · P95 $${fmt(result.monte_carlo?.p95)}</div>`;
  drawEquity('bt-chart', (result.equity_curve || []).map((p) => ({ t: p.step, equity: p.equity })));
}

function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('cs_theme', next);
  drawEquity('equity-chart', equityPts);
}

async function toggleMaster() {
  await api('/bot/toggle', { method: 'POST' });
  loadDash();
  toast('Master bot toggled');
}

async function runScan() {
  toast('Scanning…');
  await api('/trigger', { method: 'POST' });
  loadDash();
  toast('Scan done');
}

function init() {
  const theme = localStorage.getItem('cs_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', theme);
  showPage('dashboard');
  startFuturesPumpLoop();
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    const id = document.querySelector('.page.active')?.id?.replace('page-', '');
    if (id === 'dashboard') loadDash();
    if (id === 'portfolio') loadPortfolio();
    if (id === 'auto-trades') loadAuto();
    if (id === 'pumps') loadPumps().catch(() => {});
    document.getElementById('clock').textContent = new Date().toUTCString();
  }, 5000);
  window.addEventListener('resize', () => drawEquity('equity-chart', equityPts));
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.icon-rail a[data-page], .mobile-nav a').forEach((a) => {
    a.addEventListener('click', (e) => { e.preventDefault(); showPage(a.dataset.page); });
  });
  document.getElementById('login-btn').onclick = doLogin;
  document.getElementById('login-pass').onkeydown = (e) => { if (e.key === 'Enter') doLogin(); };
  document.getElementById('btn-logout').onclick = logout;
  document.getElementById('btn-theme').onclick = toggleTheme;
  document.getElementById('btn-toggle').onclick = toggleMaster;
  document.getElementById('btn-scan').onclick = () => runScan().catch((e) => toast(e.message));
  document.getElementById('btn-ops-toggle').onclick = toggleMaster;
  document.getElementById('btn-ops-scan').onclick = () => runScan().catch((e) => toast(e.message));
  document.getElementById('btn-ops-risk').onclick = () => showPage('risk');
  document.getElementById('btn-bt').onclick = () => runBt().catch((e) => toast(e.message));
  document.getElementById('btn-reset-breaker').onclick = () => resetBreaker().catch((e) => toast(e.message));
  if (token) {
    document.getElementById('login').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    init();
  }
});

window.closeTrade = closeTrade;
window.toggleBot = toggleBot;
window.flip = flip;
window.queueSave = queueSave;
window.bnSync = bnSync;
window.bnAmountSync = bnAmountSync;
window.bnAmountPreset = bnAmountPreset;
window.testTelegram = testTelegram;
window.resetRisk = resetRisk;
window.resetBreaker = resetBreaker;
