import Icon from "./Icon.jsx";
import { fmtDateLong, money } from "../lib/format.js";
import { useSheets } from "../lib/sheets.jsx";
import { useData } from "../lib/store.jsx";

const ratioText = (r) => `%${Math.round(r * 100)}`;
const yearsText = (y) => `${y.toFixed(1).replace(".", ",")} yıl`;

function nextLine(b) {
  if (b.retirement_eligible) return "Devlet katkısının tamamı hak edildi";
  if (b.next_milestone) {
    const m = b.next_milestone;
    return `${fmtDateLong(m.due_date)} · ${b.days_to_next} gün sonra ${ratioText(m.ratio)} hak edilir`;
  }
  return "Kalan kısım için 10 yıl + 56 yaş emeklilik şartı bekleniyor";
}

/** Varlıklar sayfasının altındaki BES bölümü. BES likit olmadığı için net servete dahil edilmez. */
export default function BesPanel() {
  const { bes, besNet, besTotal } = useData();
  const { open } = useSheets();
  const forfeited = bes.reduce((a, b) => a + b.forfeited_state, 0);

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

      {bes.length === 0 ? (
        <p className="muted panel__empty">Henüz BES hesabı yok. Birikimini ve devlet katkısı hak ediş tarihlerini buradan takip edebilirsin.</p>
      ) : (
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
          </dl>
          <p className="bes__note">
            Likit olmadığı için net servete ve geçmiş grafiğine dahil değil.
            {forfeited > 0.5 && ` Henüz hak edilmemiş devlet katkısı: ${money(forfeited)}.`}
          </p>

          <ul className="rows">
            {bes.map((b) => (
              <li key={b.id}>
                <button className="row-line bes__row" onClick={() => open("bes", { besId: b.id })}>
                  <div className="row-line__main">
                    <span className="tag tag--good">{ratioText(b.vest_ratio)}</span>
                    <div>
                      <div className="row-line__title">{b.name}</div>
                      <div className="row-line__sub">
                        Sistemde {yearsText(b.years_in_system)} · {nextLine(b)}
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
