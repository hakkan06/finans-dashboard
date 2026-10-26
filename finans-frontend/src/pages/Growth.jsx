import { useMemo, useState } from "react";
import Icon from "../components/Icon.jsx";
import { TimeChart } from "../components/charts.jsx";
import { Segmented } from "../components/controls.jsx";
import { confirmDialog, toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { fmtDate, fmtDateLong, money, pct, todayStr } from "../lib/format.js";
import { RANGES, rangeSeries } from "../lib/range.js";
import { useData } from "../lib/store.jsx";

const VIEWS = [
  { value: "net", label: "Net servet" },
  { value: "assets", label: "Varlık ve borç" },
];

export default function Growth() {
  const { series, history, reload, overview: ov } = useData();
  const [range, setRange] = useState("3M");
  const [view, setView] = useState("net");
  const [scrub, setScrub] = useState(null);
  const [showAll, setShowAll] = useState(false);

  const pts = useMemo(() => rangeSeries(series, range), [series, range]);

  const chartSeries = useMemo(
    () =>
      view === "net"
        ? [{ key: "net", label: "Net servet", color: "var(--lagoon)", area: true, points: pts.map((p) => ({ date: p.date, v: p.net })) }]
        : [
            { key: "assets", label: "Varlık", color: "var(--lagoon)", area: true, points: pts.map((p) => ({ date: p.date, v: p.assets })) },
            { key: "debts", label: "Borç", color: "var(--rose)", dash: "5 4", points: pts.map((p) => ({ date: p.date, v: p.debts })) },
          ],
    [pts, view]
  );

  const stats = useMemo(() => {
    if (pts.length < 2) return null;
    const first = pts[0];
    const last = pts[pts.length - 1];
    const best = pts.reduce((a, p, i) => (i && p.net - pts[i - 1].net > a.d ? { d: p.net - pts[i - 1].net, date: p.date } : a), { d: -Infinity, date: null });
    const worst = pts.reduce((a, p, i) => (i && p.net - pts[i - 1].net < a.d ? { d: p.net - pts[i - 1].net, date: p.date } : a), { d: Infinity, date: null });
    return {
      change: last.net - first.net,
      changePct: first.net !== 0 ? ((last.net - first.net) / Math.abs(first.net)) * 100 : null,
      from: first.date,
      best,
      worst,
    };
  }, [pts]);

  const rows = useMemo(() => {
    const recorded = [...history].sort((a, b) => (a.record_date < b.record_date ? 1 : -1));
    return recorded.map((h, i) => ({ ...h, prev: recorded[i + 1] }));
  }, [history]);
  const shownRows = showAll ? rows : rows.slice(0, 10);
  const today = todayStr();

  const hasToday = history.some((h) => h.record_date === today);

  async function removePoint(h) {
    const ok = await confirmDialog({
      title: `${fmtDateLong(h.record_date)} kaydı silinsin mi?`,
      body: "Grafikte bozuk görünen bir günü temizlemek için kullan. Bu kayıt geri getirilemez.",
      confirmLabel: "Kaydı sil",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteHistory(h.record_date);
      await reload();
      toast("Kayıt silindi", { tone: "good" });
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  async function saveToday() {
    try {
      await api.snapshot();
      await reload();
      toast("Bugünün değeri kaydedildi", { tone: "good" });
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  const shown = scrub ? scrub.values.net ?? null : null;
  const lastPt = pts[pts.length - 1];

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Günlük takip</h1>
          <p className="page__sub">Net servetin her gün 22:00'de ve fiyatları güncelleyişinde kaydedilir.</p>
        </div>
        {!hasToday && (
          <button className="btn btn--ghost" onClick={saveToday}>
            <Icon name="save" size={18} /> Bugünü kaydet
          </button>
        )}
      </header>

      <section className="panel panel--chart">
        <div className="hero__top">
          <div>
            <div className="hero__label">{scrub ? fmtDateLong(scrub.date) : view === "net" ? "Net servet" : "Güncel"}</div>
            <div className="hero__value hero__value--md">{money(shown !== null ? shown : lastPt?.net ?? ov.net_worth)}</div>
            {stats && !scrub && (
              <div className="hero__deltas">
                <span className={`delta delta--${stats.change > 0 ? "good" : stats.change < 0 ? "bad" : "calm"}`}>
                  {money(stats.change, { sign: true })}
                  {stats.changePct !== null && <small>{pct(stats.changePct)} · {fmtDate(stats.from)} tarihinden beri</small>}
                </span>
              </div>
            )}
          </div>
          <div className="stack-y stack-y--tight">
            <Segmented label="Zaman aralığı" size="sm" value={range} onChange={(v) => (setRange(v), setScrub(null))} options={RANGES.map((r) => ({ value: r.value, label: r.label }))} />
            <Segmented label="Grafik görünümü" size="sm" value={view} onChange={(v) => (setView(v), setScrub(null))} options={VIEWS} />
          </div>
        </div>

        {pts.length < 2 ? (
          <div className="hero__empty">
            <p>Grafik için en az iki günün kaydı gerekiyor. Yarın bu sayfada ilk eğriyi göreceksin.</p>
          </div>
        ) : (
          <TimeChart series={chartSeries} height={300} ariaLabel="Zaman içinde net servet grafiği" onScrub={(date, values) => setScrub(date ? { date, values } : null)} />
        )}
        {view === "assets" && pts.length > 1 && (
          <ul className="legend legend--inline">
            <li>
              <i style={{ background: "var(--lagoon)" }} />
              <span className="legend__name">Varlık</span>
            </li>
            <li>
              <i style={{ background: "var(--rose)" }} />
              <span className="legend__name">Borç</span>
            </li>
          </ul>
        )}
      </section>

      {stats && stats.best.date && (
        <div className="trio">
          <div className="stat">
            <span className="stat__label">En iyi gün</span>
            <strong className="tone-good">{money(stats.best.d, { sign: true })}</strong>
            <span className="stat__sub">{fmtDateLong(stats.best.date)}</span>
          </div>
          <div className="stat">
            <span className="stat__label">En zayıf gün</span>
            <strong className={stats.worst.d < 0 ? "tone-bad" : ""}>{money(stats.worst.d, { sign: true })}</strong>
            <span className="stat__sub">{fmtDateLong(stats.worst.date)}</span>
          </div>
          <div className="stat">
            <span className="stat__label">Kayıtlı gün</span>
            <strong>{history.length}</strong>
            <span className="stat__sub">{history.length ? `${fmtDate(history[0].record_date, { day: "numeric", month: "short", year: "numeric" })} sonrası` : ""}</span>
          </div>
        </div>
      )}

      <section className="panel" aria-labelledby="log-title">
        <header className="panel__head">
          <h2 id="log-title" className="panel__title">
            Kayıtlar
          </h2>
        </header>
        {rows.length === 0 ? (
          <p className="muted panel__empty">Henüz kayıt yok. Üstteki “Bugünü kaydet” veya fiyat güncelleme ilk kaydı oluşturur.</p>
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Tarih</th>
                    <th className="num">Varlık</th>
                    <th className="num">Borç</th>
                    <th className="num">Net servet</th>
                    <th className="num">Günlük</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {shownRows.map((h) => {
                    const d = h.prev ? h.net_worth - h.prev.net_worth : null;
                    return (
                      <tr key={h.record_date}>
                        <td>{fmtDate(h.record_date, { day: "numeric", month: "long", year: "numeric" })}</td>
                        <td className="num">{money(h.total_assets)}</td>
                        <td className="num">{money(h.total_debts)}</td>
                        <td className="num">
                          <strong>{money(h.net_worth)}</strong>
                        </td>
                        <td className={`num tone-${d === null ? "calm" : d > 0 ? "good" : d < 0 ? "bad" : "calm"}`}>{d === null ? "–" : money(d, { sign: true })}</td>
                        <td className="num">
                          <button className="icon-btn icon-btn--danger" aria-label={`${h.record_date} kaydını sil`} onClick={() => removePoint(h)}>
                            <Icon name="trash" size={16} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {rows.length > 10 && (
              <button className="link-btn link-btn--center" onClick={() => setShowAll(!showAll)}>
                {showAll ? "Daha az göster" : `Tüm ${rows.length} kaydı göster`}
              </button>
            )}
          </>
        )}
      </section>
    </div>
  );
}
