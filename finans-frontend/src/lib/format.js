// Biçimlendirme yardımcıları (tr-TR)
const nf0 = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nfQty = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 4 });
const nfCompact = new Intl.NumberFormat("tr-TR", { notation: "compact", maximumFractionDigits: 1 });
const nfPct = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

const SYMBOL = { TRY: "₺", USD: "$" };

/** ₺1.234 veya ₺1.234,56 — eksi işaret başta. sign=true ise artıya + koyar. */
export function money(v, { decimals = 0, sign = false, currency = "TRY" } = {}) {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const abs = Math.abs(v);
  const body = (decimals ? nf2 : nf0).format(abs);
  const s = v < 0 && abs >= (decimals ? 0.005 : 0.5) ? "−" : sign && v > 0 ? "+" : "";
  return `${s}${SYMBOL[currency] || ""}${body}`;
}

export const moneyCompact = (v) => (v < 0 ? "−" : "") + "₺" + nfCompact.format(Math.abs(v));
export const qty = (v) => nfQty.format(v ?? 0);
export const pct = (v, { sign = true } = {}) => {
  if (v === null || v === undefined || !Number.isFinite(v)) return "–";
  const s = v < 0 ? "−" : sign && v > 0 ? "+" : "";
  return `${s}%${nfPct.format(Math.abs(v))}`;
};
export const plain2 = (v) => nf2.format(v);

// ── Tarih ────────────────────────────────────────────────────────────
const IST = "Europe/Istanbul";
const ymdFmt = new Intl.DateTimeFormat("en-CA", { timeZone: IST, year: "numeric", month: "2-digit", day: "2-digit" });

/** Bugünün tarihi (İstanbul) → "YYYY-MM-DD" */
export const todayStr = () => ymdFmt.format(new Date());
/** "YYYY-MM-DD" → yerel gün başlangıcı */
export const parseDate = (s) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};
export const dateStr = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const daysBetween = (a, b) => Math.round((parseDate(b) - parseDate(a)) / 86400000);
export const addMonths = (s, n) => {
  const d = parseDate(s);
  const day = d.getDate();
  d.setDate(1);
  d.setMonth(d.getMonth() + n);
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  d.setDate(Math.min(day, last));
  return dateStr(d);
};

export const fmtDate = (s, opts = { day: "numeric", month: "short" }) =>
  new Intl.DateTimeFormat("tr-TR", opts).format(typeof s === "string" ? parseDate(s) : s);
export const fmtDateLong = (s) => fmtDate(s, { day: "numeric", month: "long", year: "numeric" });
export const fmtMonth = (s) => fmtDate(s, { month: "long", year: "numeric" });

/** Sunucudan gelen saat dilimsiz zaman damgası İstanbul saatidir. */
export const parseServerTime = (s) => (s ? new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s + "+03:00") : null);

export function ago(date) {
  if (!date) return "hiç";
  const mins = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (mins < 1) return "az önce";
  if (mins < 60) return `${mins} dk önce`;
  const h = Math.floor(mins / 60);
  if (h < 24) return `${h} sa önce`;
  return `${Math.floor(h / 24)} gün önce`;
}

/** Vadeye göre kısa ifade: "3 gün gecikti", "Bugün", "Yarın", "12 Kas" */
export function dueLabel(dueStr, today = todayStr()) {
  const left = daysBetween(today, dueStr);
  if (left < 0) return { text: `${-left} gün gecikti`, tone: "bad", left };
  if (left === 0) return { text: "Bugün", tone: "warn", left };
  if (left === 1) return { text: "Yarın", tone: "warn", left };
  if (left <= 3) return { text: `${left} gün kaldı`, tone: "warn", left };
  return { text: fmtDate(dueStr), tone: "calm", left };
}

export const TYPE_LABEL = {
  US_STOCK: "ABD hissesi",
  TR_STOCK: "BIST hissesi",
  FUND: "Yatırım fonu",
  COMMODITY: "Altın / gümüş",
  FIAT: "Döviz / nakit",
};
export const TYPE_HINT = {
  US_STOCK: "Örn. QQQM, AAPL, VOO",
  TR_STOCK: "Örn. THYAO, ASELS, TUPRS",
  FUND: "TEFAS fon kodu, örn. TTE, AFT",
  COMMODITY: "ALTIN (gram altın) veya GUMUS (gram gümüş)",
  FIAT: "TRY, USD veya EUR",
};
export const TYPE_COLOR = {
  US_STOCK: "var(--c-indigo)",
  TR_STOCK: "var(--c-rose)",
  FUND: "var(--c-lagoon)",
  COMMODITY: "var(--c-amber)",
  FIAT: "var(--c-slate)",
};
export const TYPES = Object.keys(TYPE_LABEL);
