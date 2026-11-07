import Icon from "./Icon.jsx";
import { fmtDateLong, money } from "../lib/format.js";
import { useSheets } from "../lib/sheets.jsx";
import { useData } from "../lib/store.jsx";

const ratioText = (r) => `%${Math.round(r * 100)}`;
const yearsText = (y) => `${y.toFixed(1).replace(".", ",")} yıl`;
const tone = (v) => (v > 0 ? "good" : v < 0 ? "bad" : "calm");

function nextLine(b) {
  if (b.retirement_eligible) return "Devlet katkısının tamamı hak edildi";
  if (b.next_milestone) {
    const m = b.next_milestone;
    return `${fmtDateLong(m.due_date)} · ${b.days_to_next} gün sonra ${ratioText(m.ratio)}`;
  }
  return "Emeklilik şartı bekleniyor";
}

/** Varlıklar sayfasının altındaki BES bölümü. BES likit olmadığı için net servete dahil edilmez. */
export default function BesPanel() {
  const { bes, besError, besNet, besTotal, besMonthly, besReturn } = useData();
  const { open } = useSheets();
  const forfeited = bes.reduce((a, b) => a + b.forfeited_state, 0);
  const missing = [...new Set(bes.flatMap((b) => b.missing_prices))];

  return (
    <section className="panel bes" aria-labelledby="bes-title">
      <header className="panel__head">
        <h2 id="bes-title" className="panel__title">
          Bireysel emeklilik (BES)
        </h2>
        <button className="link-btn" onClick={() => open("bes", {})}>
          <Icon name="plus" size={16} /> BES ekle
        </button>
      </header>

      {besError && (
        <div className="callout callout--bad" role="alert">
          <p>BES verileri alınamadı: {besError}</p>
        </div>
      )}

      {bes.length === 0 && !besError ? (
        <p className="muted panel__empty">Henüz BES hesabı yok. Fonlarını, aylık katkını ve devlet katkısı hak ediş tarihlerini buradan takip edebilirsin.</p>
      ) : bes.length === 0 ? null : (
        <>
          <dl className="kv-grid">
            <div className="kv">
              <dt>Toplam birikim</dt>
              <dd>{money(besTotal)}</dd>
            </div>
            <div className="kv">
              <dt>Bugün çıkılırsa net</dt>
              <dd>{money(besNet)}</dd>
            </div>
            <div className="kv">
              <dt>Kendi katkı getirisi</dt>
              <dd className={`tone-${tone(besReturn)}`}>{money(besReturn, { sign: true })}</dd>
            </div>
            <div className="kv">
              <dt>Aylık katkı (toplam)</dt>
              <dd>{money(besMonthly)}</dd>
            </div>
          </dl>
          <p className="bes__note">
            Likit olmadığı için net servete ve geçmiş grafiğine dahil değil.
            {forfeited > 0.5 && ` Henüz hak edilmemiş devlet katkısı: ${money(forfeited)}.`}
          </p>
          {missing.length > 0 && (
            <div className="callout callout--warn">
              <p>{missing.join(", ")} fonunun fiyatı alınamadı; bu fonlar toplamlara 0 ₺ olarak yansır. “Fiyatları güncelle” ile tekrar dene.</p>
            </div>
          )}

          <ul className="rows">
            {bes.map((b) => (
              <li key={b.id}>
                <button className="row-line bes__row" onClick={() => open("besDetail", { besId: b.id })}>
                  <div className="row-line__main">
                    <span className="tag tag--good">{ratioText(b.vest_ratio)}</span>
                    <div>
                      <div className="row-line__title">{b.name}</div>
                      <div className="row-line__sub">
                        Sistemde {yearsText(b.years_in_system)} · {b.holdings.length} fon · {nextLine(b)}
                      </div>
                    </div>
                  </div>
                  <div className="row-line__end">
                    <strong>{money(b.net_value)}</strong>
                    <Icon name="chevron" size={18} />
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
