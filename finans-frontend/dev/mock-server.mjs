// Yerel deneme sunucusu: dist/ klasörünü sunar ve /api altında backend'in yanıt biçimini taklit eder.
// Gerçek backend gerekmeden arayüzü denemek içindir. Kullanım: npm run dev  → http://localhost:5173
import { createServer } from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";

const PORT = Number(process.env.PORT || 5173);
const EMPTY = process.env.EMPTY === "1";
const DIST = join(process.cwd(), "dist");
const USD = 41.5;
const iso = (d) => d.toISOString().slice(0, 10);
const today = new Date();
const daysAgo = (n) => iso(new Date(today.getTime() - n * 86400000));
const monthsAhead = (n, day = 28) => iso(new Date(today.getFullYear(), today.getMonth() + n, day));

let nid = 100;
const assets = EMPTY ? [] : [
  { id: 1, asset_type: "US_STOCK", symbol: "QQQM", name: "Invesco Nasdaq 100", current_price: 212.4, previous_price: 210.1, last_updated: null },
  { id: 2, asset_type: "TR_STOCK", symbol: "THYAO", name: "Türk Hava Yolları", current_price: 318.5, previous_price: 322.0, last_updated: null },
  { id: 3, asset_type: "FUND", symbol: "TTE", name: "İstanbul Portföy Teknoloji", current_price: 14.82, previous_price: 14.7, last_updated: null },
  { id: 4, asset_type: "COMMODITY", symbol: "ALTIN", name: "Gram altın", current_price: 5120, previous_price: 5088, last_updated: null },
  { id: 5, asset_type: "FIAT", symbol: "USD", name: "Dolar", current_price: USD, previous_price: 41.4, last_updated: null },
  { id: 6, asset_type: "TR_STOCK", symbol: "ASELS", name: "Aselsan", current_price: 190, previous_price: 190, last_updated: null },
];
const txns = EMPTY ? [] : [
  { id: 1, asset_id: 1, quantity: 40, unit_price: 180, transaction_date: "2026-02-10" },
  { id: 2, asset_id: 1, quantity: 15, unit_price: 200, transaction_date: "2026-06-02" },
  { id: 3, asset_id: 2, quantity: 300, unit_price: 270, transaction_date: "2026-03-15" },
  { id: 4, asset_id: 3, quantity: 12000, unit_price: 11.2, transaction_date: "2026-01-20" },
  { id: 5, asset_id: 4, quantity: 60, unit_price: 4300, transaction_date: "2026-04-01" },
  { id: 6, asset_id: 5, quantity: 3500, unit_price: 36.8, transaction_date: "2026-05-05" },
  { id: 7, asset_id: 6, quantity: 100, unit_price: 150, transaction_date: "2026-02-01" },
  { id: 8, asset_id: 6, quantity: -100, unit_price: 190, transaction_date: "2026-09-01" },
];
const mkInst = (debtId, n, amount, start, paid) =>
  Array.from({ length: n }, (_, i) => ({ id: nid++, debt_id: debtId, amount, due_date: monthsAhead(start + i), is_paid: i < paid }));
const groups = EMPTY ? [] : [{ id: 1, name: "Ev alımı", description: null, contracted_amount: 4200000 }];
const debts = EMPTY ? [] : [
  { id: 1, name: "Peşinat", total_amount: 600000, group_id: 1, installments: mkInst(1, 6, 100000, -3, 3) },
  { id: 2, name: "Konut kredisi", total_amount: 3600000, group_id: 1, installments: mkInst(2, 120, 30000, -2, 2) },
  { id: 3, name: "Telefon taksiti", total_amount: 36000, group_id: null, installments: mkInst(3, 12, 3000, -1, 1) },
  { id: 4, name: "Eski kredi kartı", total_amount: 9000, group_id: null, installments: mkInst(4, 3, 3000, -5, 3) },
];
debts[2].installments[0].due_date = daysAgo(2); // gecikmiş örnek
debts[2].installments[0].is_paid = false;
const history = EMPTY ? [] : (() => {
  const out = [];
  let a = 760000;
  for (let i = 120; i >= 1; i--) {
    a += Math.sin(i / 6) * 4800 + 1500 + (i % 7 === 0 ? -6000 : 0);
    const d = 4_240_000 - (120 - i) * 6000;
    out.push({ record_date: daysAgo(i), total_assets: Math.round(a), total_debts: d, net_worth: Math.round(a - d) });
  }
  return out;
})();

function fifo(list) {
  const lots = []; let realized = 0;
  for (const t of [...list].sort((a, b) => (a.transaction_date + (a.quantity > 0 ? 0 : 1) + String(a.id).padStart(6, "0")).localeCompare(b.transaction_date + (b.quantity > 0 ? 0 : 1) + String(b.id).padStart(6, "0")))) {
    if (t.quantity > 0) lots.push({ q: t.quantity, p: t.unit_price });
    else { let need = -t.quantity; for (const l of lots) { const k = Math.min(l.q, need); realized += k * (t.unit_price - l.p); l.q -= k; need -= k; if (need <= 1e-9) break; } if (need > 1e-6) return null; }
  }
  return { lots: lots.filter((l) => l.q > 1e-6), realized };
}
const stamp = () => new Date(Date.now() - 12 * 60000).toISOString().replace("Z", "").slice(0, 19);
assets.forEach((a) => (a.last_updated = EMPTY ? null : stamp()));

function summary() {
  return assets.map((a) => {
    const f = fifo(txns.filter((t) => t.asset_id === a.id)) || { lots: [], realized: 0 };
    let qty = 0, cost = 0, tax = 0, net = 0;
    for (const l of f.lots) { qty += l.q; const c = l.q * l.p; cost += c; const g = l.q * (a.current_price || 0); const pr = g - c; const t = a.asset_type === "FUND" && pr > 0 ? pr * 0.175 : 0; tax += t; net += g - t; }
    const usd = a.asset_type === "US_STOCK"; const fx = usd ? USD : 1;
    return { asset_id: a.id, asset_type: a.asset_type, symbol: a.symbol, name: a.name, total_qty: qty, current_price: a.current_price || 0, previous_price: a.previous_price,
      total_cost: cost, total_tax: tax, net_value: net, last_updated: a.last_updated, currency: usd ? "USD" : "TRY", fx, value_try: net * fx, cost_try: cost * fx,
      day_change_try: qty > 0 && a.current_price && a.previous_price ? qty * (a.current_price - a.previous_price) * fx : 0, realized_pl: f.realized,
      has_price: a.current_price != null, has_position: qty > 0.0001 };
  });
}
function overview() {
  const items = summary().filter((i) => i.has_position);
  const ta = items.reduce((s, i) => s + i.value_try, 0);
  const dc = items.reduce((s, i) => s + i.day_change_try, 0);
  const un = debts.flatMap((d) => d.installments).filter((i) => !i.is_paid);
  const td = un.reduce((s, i) => s + i.amount, 0);
  const ym = iso(today).slice(0, 7);
  const alloc = {}; items.forEach((i) => (alloc[i.asset_type] = (alloc[i.asset_type] || 0) + i.value_try));
  const od = un.filter((i) => i.due_date < iso(today));
  return { usd_try: USD, total_assets: ta, total_debts: td, net_worth: ta - td, day_change: dc, day_change_pct: ta - dc > 0 ? (dc / (ta - dc)) * 100 : 0,
    due_this_month: un.filter((i) => i.due_date.startsWith(ym)).reduce((s, i) => s + i.amount, 0), overdue_total: od.reduce((s, i) => s + i.amount, 0), overdue_count: od.length,
    last_price_update: assets.map((a) => a.last_updated).filter(Boolean).sort().pop() || null,
    allocation: Object.entries(alloc).map(([asset_type, value]) => ({ asset_type, value })).sort((a, b) => b.value - a.value) };
}
const groupOut = (g) => { const ds = debts.filter((d) => d.group_id === g.id); let p = 0, r = 0; ds.forEach((d) => d.installments.forEach((i) => (i.is_paid ? (p += i.amount) : (r += i.amount)))); return { ...g, debts: ds, total_paid: p, total_remaining: r, progress_pct: p + r ? Math.round((p / (p + r)) * 10000) / 100 : 0 }; };

const err = (res, code, detail) => json(res, { detail }, code);
const json = (res, data, code = 200) => { res.writeHead(code, { "Content-Type": "application/json" }); res.end(JSON.stringify(data)); };

async function api(req, res, path, q) {
  const body = await new Promise((r) => { let s = ""; req.on("data", (c) => (s += c)); req.on("end", () => r(s ? JSON.parse(s) : null)); });
  const m = req.method; let x;
  if (m === "GET" && path === "/overview") return json(res, overview());
  if (m === "GET" && path === "/portfolio/summary") return json(res, summary().filter((i) => q.get("include_empty") === "true" || i.has_position));
  if (m === "GET" && path === "/debts/") return json(res, debts);
  if (m === "GET" && path === "/debt-groups/") return json(res, groups.map(groupOut));
  if (m === "GET" && path === "/portfolio/history") return json(res, history);
  if (m === "GET" && path === "/assets/") return json(res, assets);
  if (m === "GET" && path === "/transactions/") return json(res, txns.filter((t) => !q.get("asset_id") || t.asset_id === +q.get("asset_id")).sort((a, b) => b.transaction_date.localeCompare(a.transaction_date)));
  if (m === "POST" && path === "/assets/") {
    const sym = body.symbol.trim().toUpperCase();
    if (assets.some((a) => a.symbol === sym)) return err(res, 400, "Bu sembole sahip varlık zaten sistemde mevcut.");
    const known = ["AAPL", "VOO", "THYAO", "EUR", "TRY", "GUMUS"].includes(sym);
    const a = { id: nid++, asset_type: body.asset_type, symbol: sym, name: body.name || sym, current_price: known ? 100 : null, previous_price: null, last_updated: known ? stamp() : null };
    assets.push(a); return json(res, a);
  }
  if (m === "DELETE" && (x = path.match(/^\/assets\/(\d+)$/))) { const i = assets.findIndex((a) => a.id === +x[1]); if (i < 0) return err(res, 404, "Varlık bulunamadı"); assets.splice(i, 1); for (let k = txns.length - 1; k >= 0; k--) if (txns[k].asset_id === +x[1]) txns.splice(k, 1); return json(res, { message: "ok" }); }
  if (m === "POST" && path === "/assets/update-prices") { assets.forEach((a) => (a.last_updated = stamp())); return json(res, { message: "ok", updated: assets.length, failed: [] }); }
  if (m === "POST" && path === "/transactions/") { const list = txns.filter((t) => t.asset_id === body.asset_id).concat({ ...body, id: 1e9 }); if (!fifo(list)) return err(res, 400, "Yetersiz miktar: satış, o tarihte eldeki miktarı aşıyor."); const t = { id: nid++, ...body }; txns.push(t); return json(res, t); }
  if (m === "PUT" && (x = path.match(/^\/transactions\/(\d+)$/))) { const t = txns.find((t) => t.id === +x[1]); if (!t) return err(res, 404, "İşlem bulunamadı"); const list = txns.filter((k) => k.asset_id === t.asset_id && k.id !== t.id).concat({ ...t, ...body }); if (!fifo(list)) return err(res, 400, "Yetersiz miktar."); Object.assign(t, body); return json(res, t); }
  if (m === "DELETE" && (x = path.match(/^\/transactions\/(\d+)$/))) { const t = txns.find((t) => t.id === +x[1]); if (!t) return err(res, 404, "İşlem bulunamadı"); if (!fifo(txns.filter((k) => k.asset_id === t.asset_id && k.id !== t.id))) return err(res, 400, "Yetersiz miktar: bu alış silinirse satışlar açıkta kalır."); txns.splice(txns.indexOf(t), 1); return json(res, { message: "ok" }); }
  if (m === "POST" && path === "/debts/schedules/") {
    const id = nid++; const n = body.installments_count; const r = body.interest_rate / 100;
    const pmt = r > 0 ? Math.round((body.total_amount * r / (1 - Math.pow(1 + r, -n))) * 100) / 100 : Math.round((body.total_amount / n) * 100) / 100;
    const [yy, mm, dd] = (body.start_date || iso(today)).split("-").map(Number);
    const insts = Array.from({ length: n }, (_, i) => ({ id: nid++, debt_id: id, amount: pmt, due_date: iso(new Date(Date.UTC(yy, mm - 1 + i, dd))), is_paid: false }));
    debts.push({ id, name: body.name, total_amount: pmt * n, group_id: body.group_id ?? null, installments: insts });
    return json(res, { message: "ok", debt_id: id, total_repayment: pmt * n, installment_amount: pmt });
  }
  if (m === "PUT" && (x = path.match(/^\/installments\/(\d+)\/toggle$/))) { for (const d of debts) for (const i of d.installments) if (i.id === +x[1]) { i.is_paid = !i.is_paid; return json(res, { message: "ok", is_paid: i.is_paid }); } return err(res, 404, "Taksit bulunamadı"); }
  if (m === "DELETE" && (x = path.match(/^\/debts\/(\d+)$/))) { const i = debts.findIndex((d) => d.id === +x[1]); if (i < 0) return err(res, 404, "Borç bulunamadı"); debts.splice(i, 1); return json(res, { message: "ok" }); }
  if (m === "POST" && path === "/debt-groups/") { const g = { id: nid++, name: body.name, description: null, contracted_amount: null }; groups.push(g); return json(res, groupOut(g)); }
  if (m === "DELETE" && (x = path.match(/^\/debt-groups\/(\d+)$/))) { debts.forEach((d) => d.group_id === +x[1] && (d.group_id = null)); const i = groups.findIndex((g) => g.id === +x[1]); if (i >= 0) groups.splice(i, 1); return json(res, { message: "ok" }); }
  if (m === "PUT" && (x = path.match(/^\/debts\/(\d+)\/assign-group$/))) { const d = debts.find((d) => d.id === +x[1]); d.group_id = body.group_id; return json(res, { message: "ok" }); }
  if (m === "POST" && path === "/portfolio/snapshot") { const o = overview(); const rec = { record_date: iso(today), total_assets: o.total_assets, total_debts: o.total_debts, net_worth: o.net_worth }; const i = history.findIndex((h) => h.record_date === rec.record_date); i >= 0 ? (history[i] = rec) : history.push(rec); return json(res, { message: "ok" }); }
  if (m === "DELETE" && (x = path.match(/^\/portfolio\/history\/(.+)$/))) { const i = history.findIndex((h) => h.record_date === x[1]); if (i < 0) return err(res, 404, "Kayıt bulunamadı"); history.splice(i, 1); return json(res, { message: "ok" }); }
  return err(res, 404, "Bulunamadı");
}

const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json" };
createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  if (url.pathname.startsWith("/api/")) return api(req, res, url.pathname.slice(4), url.searchParams).catch((e) => err(res, 500, String(e)));
  let file = normalize(join(DIST, url.pathname === "/" ? "index.html" : url.pathname));
  if (!file.startsWith(DIST) || !existsSync(file) || statSync(file).isDirectory()) file = join(DIST, "index.html");
  res.writeHead(200, { "Content-Type": MIME[extname(file)] || "application/octet-stream" });
  res.end(readFileSync(file));
}).listen(PORT, () => console.log(`Deneme sunucusu: http://localhost:${PORT}`));
