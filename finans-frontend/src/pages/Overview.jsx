import { useMemo, useState } from "react";
import Icon from "../components/Icon.jsx";
import InstallmentRow from "../components/InstallmentRow.jsx";
import { StackBar, TimeChart } from "../components/charts.jsx";
import { Segmented } from "../components/controls.jsx";
import { RANGES, rangeSeries } from "../lib/range.js";
import { TYPE_COLOR, TYPE_LABEL, fmtDateLong, money, pct, todayStr } from "../lib/format.js";
import { unpaidInstallments } from "../lib/debt.js";
import { useSheets } from "../lib/sheets.jsx";
import { useData } from "../lib/store.jsx";

const BES_KEY = "finans.showBes";

/** BES gösterimi cihaz başına hatırlanır; depolama kullanılamıyorsa kapalı başlar. */
function useShowBes() {
  const [on, setOn] = useState(() => {
    try {
      return localStorage.getItem(BES_KEY) === "1";
    } catch {
      return false;
    }
  });
  const set = (v) => {
    setOn(v);
    try {
      localStorage.setItem(BES_KEY, v ? "1" : "0");
    } catch {
      /* depolama yok: yalnızca bu oturumda geçerli */
    }
  };
  return [on, set];
}

export default function Overview({ go }) {
  const { overview: ov, series, holdings, debts, bes, besNet } = useData();
  const [showBes, setShowBes] = useShowBes();
  const hasBes = bes.length > 0;
  const { open } = useSheets();
  const [range, setRange] = useState("3M");
  const [scrub, setScrub] = useState(null);
  const today = todayStr();

  const pts = useMemo(() => rangeSeries(series, range), [series, range]);
  const chartSeries = useMemo(() => [{ key: "net", label: "Net servet", color: "var(--lagoon)", area: true, points: pts.map((p) => ({ date: p.date, v: p.net })) }], [pts]);

  const upcoming = useMemo(() => unpaidInstallments(debts).slice(0, 6), [debts]);
  const empty = holdings.length === 0 && debts.length === 0;

  const first = pts[0];
  const last = pts[pts.length - 1];
  const shown = scrub ? { date: scrub.date, net: scrub.values.net } : { date: null, net: ov.net_worth };
  const base = first ? first.net : null;
  const delta = base !== null && shown.net !== undefined ? shown.net - base : null;

  const alloc = ov.allocation.map((a) => ({ key: a.asset_type, label: TYPE_LABEL[a.asset_type], value: a.value, color: TYPE_COLOR[a.asset_type] }));
  if (hasBes && showBes && besNet > 0) alloc.push({ key: "BES", label: "BES (net)", value: besNet, color: "var(--ink-3)" });
  const allocTotal = alloc.reduce((a, p) => a + p.value, 0);

  if (empty) {
    return (
      <div className="page">
        <div className="onboard">
          <h1 className="onboard__title">Finans panelin hazır</h1>
          <p className="onboard__text">İlk varlığını veya borcunu ekle; net servetin burada her gün takip edilir.</p>
          <div className="onboard__actions">
            <button className="btn btn--primary btn--lg" onClick={() => open("txn", { startNew: true })}>
              <Icon name="plus" size={18} /> İlk varlığını ekle
            </button>
            <button className="btn btn--ghost btn--lg" onClick={() => open("debt", {})}>
              Borç ekle
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <section className="hero" aria-label="Net servet">
        <div className="hero__top">
          <div>
            <div className="hero__label">{scrub ? fmtDateLong(scrub.date) : "Net servet"}</div>
            <div className="hero__value">
              {money(shown.net)}
              {/* Geçmiş bir güne bakarken o günün kuru bilinmediği için dolar karşılığı yalnızca güncel değerde gösterilir. */}
              {!scrub && ov.usd_try > 0 && (
                <span className="hero__usd" title={`Güncel kur: ${ov.usd_try.toFixed(2).replace(".", ",")} ₺`}>
                  ({money(shown.net / ov.usd_try, { currency: "USD" })})
                </span>
              )}
            </div>
            <div className="hero__deltas">
              {!scrub && (
                <span className={`delta delta--${ov.day_change > 0 ? "good" : ov.day_change < 0 ? "bad" : "calm"}`}>
                  {money(ov.day_change, { sign: true })} <small>{pct(ov.day_change_pct)} bugün</small>
                </span>
              )}
              {delta !== null && pts.length > 1 && (
                <span className={`delta delta--${delta > 0 ? "good" : delta < 0 ? "bad" : "calm"}`}>
                  {money(delta, { sign: true })} <small>{RANGES.find((r) => r.value === range).long}</small>
                </span>
              )}
            </div>
          </div>
          <Segmented label="Zaman aralığı" size="sm" value={range} onChange={(v) => (setRange(v), setScrub(null))} options={RANGES.filter((r) => r.value !== "ALL" || true).map((r) => ({ value: r.value, label: r.label }))} />
        </div>

        {pts.length < 2 ? (
          <div className="hero__empty">
            <p>Grafik, ikinci günün kaydıyla çizilmeye başlar. Değerler her gece 22:00'de ve fiyatları her güncelleyişinde kaydedilir.</p>
            <button className="btn btn--ghost btn--small" onClick={() => go("growth")}>
              Günlük kayıtları gör
            </button>
          </div>
        ) : (
          <TimeChart
            series={chartSeries}
            height={260}
            ariaLabel={`Net servet ${money(first.net)} değerinden ${money(last.net)} değerine`}
            onScrub={(date, values) => setScrub(date ? { date, values } : null)}
          />
        )}

        <dl className="strip">
          <div className="strip__cell">
            <dt>Toplam varlık</dt>
            <dd>{money(ov.total_assets)}</dd>
          </div>
          <div className="strip__cell">
            <dt>Kalan borç</dt>
            <dd>{money(ov.total_debts)}</dd>
          </div>
          <div className={`strip__cell ${ov.overdue_count ? "strip__cell--bad" : ""}`}>
            <dt>{ov.overdue_count ? "Gecikmiş ödeme" : "Bu ay ödenecek"}</dt>
            <dd>{money(ov.overdue_count ? ov.overdue_total : ov.due_this_month)}</dd>
          </div>
        </dl>

        {hasBes && (
          <div className="bes-line">
            <button type="button" role="switch" aria-checked={showBes} className={`chip ${showBes ? "is-on" : ""}`} onClick={() => setShowBes(!showBes)}>
              {showBes ? "BES gösteriliyor" : "BES'i göster"}
            </button>
            {showBes && (
              <span className="bes-line__vals" aria-live="polite">
                <span>
                  BES (bugün çıkılırsa net) <strong>{money(besNet)}</strong>
                </span>
                <span>
                  BES dahil net servet <strong>{money(ov.net_worth + besNet)}</strong>
                </span>
              </span>
            )}
          </div>
        )}
      </section>

      <div className="cols">
        <section className="panel" aria-labelledby="up-title">
          <header className="panel__head">
            <h2 id="up-title" className="panel__title">
              Yaklaşan ödemeler
            </h2>
            <button className="link-btn" onClick={() => go("debts")}>
              Tüm borçlar <Icon name="chevron" size={16} />
            </button>
          </header>
          {upcoming.length === 0 ? (
            <p className="muted panel__empty">Ödenecek taksit yok.</p>
          ) : (
            <ul className="insts">
              {upcoming.map((i) => (
                <InstallmentRow key={i.id} inst={i} debtName={i.debtName} today={today} />
              ))}
            </ul>
          )}
        </section>

        <section className="panel" aria-labelledby="alloc-title">
          <header className="panel__head">
            <h2 id="alloc-title" className="panel__title">
              Varlık dağılımı
            </h2>
            <button className="link-btn" onClick={() => go("assets")}>
              Varlıklar <Icon name="chevron" size={16} />
            </button>
          </header>
          {alloc.length === 0 ? (
            <p className="muted panel__empty">Henüz varlık yok.</p>
          ) : (
            <>
              <StackBar parts={alloc} />
              <ul className="legend">
                {alloc.map((a) => (
                  <li key={a.key}>
                    <i style={{ background: a.color }} />
                    <span className="legend__name">{a.label}</span>
                    <span className="legend__pct">{pct((a.value / allocTotal) * 100, { sign: false })}</span>
                    <strong>{money(a.value)}</strong>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
