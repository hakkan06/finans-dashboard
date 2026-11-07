import { useEffect, useState } from "react";
import Sheet from "../components/Sheet.jsx";
import Icon from "../components/Icon.jsx";
import { confirmDialog, toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { fmtDate, fmtDateLong, money, qty } from "../lib/format.js";
import { useData } from "../lib/store.jsx";
import { useSheets } from "../lib/sheets.jsx";

const ratioText = (r) => `%${Math.round(r * 100)}`;
const tone = (v) => (v > 0 ? "good" : v < 0 ? "bad" : undefined);
const KIND = { contribution: "Aylık katkı", state: "Devlet katkısı", switch: "Fon değişikliği", adjust: "Düzeltme" };

function Timeline({ b }) {
  return (
    <>
      <h3 className="sheet__section">Devlet katkısı hak ediş takvimi</h3>
      <ul className="rows">
        {b.milestones.map((m) => (
          <li key={m.years} className="row-line">
            <div className="row-line__main">
              <span className={`tag ${m.reached ? "tag--good" : ""}`}>{ratioText(m.ratio)}</span>
              <div>
                <div className="row-line__title">{m.years}. yıl</div>
                <div className="row-line__sub">{fmtDateLong(m.due_date)}</div>
              </div>
            </div>
            <div className="row-line__end">
              <span className={m.reached ? "tone-good" : "muted"}>{m.reached ? "Hak edildi" : "Bekleniyor"}</span>
            </div>
          </li>
        ))}
        <li className="row-line">
          <div className="row-line__main">
            <span className={`tag ${b.retirement_eligible ? "tag--good" : ""}`}>%100</span>
            <div>
              <div className="row-line__title">Emeklilik hakkı</div>
              <div className="row-line__sub">
                {b.retirement_date ? `${fmtDateLong(b.retirement_date)} (10 yıl + 56 yaş)` : "10 yıl dolması ve 56 yaşın tamamlanması · doğum tarihi girilmedi"}
              </div>
            </div>
          </div>
          <div className="row-line__end">
            <span className={b.retirement_eligible ? "tone-good" : "muted"}>{b.retirement_eligible ? "Sağlandı" : "Bekleniyor"}</span>
          </div>
        </li>
      </ul>
    </>
  );
}

export default function BesDetailSheet({ besId, onClose }) {
  const { bes, reload } = useData();
  const { open } = useSheets();
  const b = bes.find((x) => x.id === besId);
  const [events, setEvents] = useState(null);

  useEffect(() => {
    api.besEvents(besId).then(setEvents).catch(() => setEvents([]));
  }, [besId, bes]);

  if (!b) return null;

  async function remove() {
    const ok = await confirmDialog({
      title: `${b.name} silinsin mi?`,
      body: "Hesap, fonları ve hareket geçmişi kalıcı olarak silinir. Gerçek sözleşmeniz etkilenmez, sadece bu panodaki kayıt kalkar.",
      confirmLabel: "Hesabı sil",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteBes(b.id);
      await reload();
      toast("BES hesabı silindi", { tone: "good" });
      onClose();
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  const sub = [b.company, b.age != null ? `${b.age} yaşında` : null, `BES'e giriş ${fmtDateLong(b.system_entry_date)}`].filter(Boolean).join(" · ");

  return (
    <Sheet
      title={b.name}
      subtitle={sub}
      onClose={onClose}
      wide
      footer={
        <>
          <button className="btn btn--danger-ghost" onClick={remove}>
            <Icon name="trash" size={18} /> Hesabı sil
          </button>
          <button className="btn btn--primary" onClick={() => open("bes", { besId: b.id })}>
            <Icon name="edit" size={18} /> Hesabı ve planı düzenle
          </button>
        </>
      }
    >
      {b.missing_prices.length > 0 && (
        <div className="callout callout--warn">
          <p>{b.missing_prices.join(", ")} fonunun fiyatı alınamadı; değerler eksik görünebilir. “Fiyatları güncelle” ile tekrar dene.</p>
        </div>
      )}

      <dl className="kv-grid">
        <div className="kv">
          <dt>Toplam birikim</dt>
          <dd>{money(b.total_balance)}</dd>
        </div>
        <div className="kv">
          <dt>Bugün çıkılırsa net</dt>
          <dd>{money(b.net_value)}</dd>
        </div>
        <div className="kv">
          <dt>Kendi katkı + getirisi</dt>
          <dd>
            {money(b.own_balance)} <small className={`tone-${tone(b.own_return) || "calm"}`}>{money(b.own_return, { sign: true })}</small>
          </dd>
        </div>
        <div className="kv">
          <dt>Devlet katkısı + getirisi</dt>
          <dd>
            {money(b.state_balance)} <small className="muted">hak edilen {ratioText(b.vest_ratio)}</small>
          </dd>
        </div>
        <div className="kv">
          <dt>Hak edilen devlet katkısı</dt>
          <dd>{money(b.vested_state)}</dd>
        </div>
        <div className="kv">
          <dt>Tahmini stopaj</dt>
          <dd>{money(b.tax)}</dd>
        </div>
      </dl>
      {b.gain_at_next > 0 && b.next_milestone && (
        <p className="bes__note">
          {fmtDateLong(b.next_milestone.due_date)} tarihinde {ratioText(b.next_milestone.ratio)} kademesine geçince net değer yaklaşık {money(b.gain_at_next)} artar.
        </p>
      )}

      <Timeline b={b} />

      <h3 className="sheet__section">Fonlar</h3>
      {b.holdings.length === 0 ? (
        <p className="muted">Bu hesapta henüz fon yok. Ekstrendeki pay adedini girerek başla.</p>
      ) : (
        <ul className="rows">
          {b.holdings.map((h) => (
            <li key={h.fund_code}>
              <button className="row-line bes__row" onClick={() => open("besFund", { besId: b.id, fundCode: h.fund_code })}>
                <div className="row-line__main">
                  <span className="tag">{h.fund_code}</span>
                  <div>
                    <div className="row-line__title">{h.fund_name || h.fund_code}</div>
                    <div className="row-line__sub">
                      {qty(h.own_units)} pay + {qty(h.state_units)} devlet payı ·{" "}
                      {h.price ? `fiyat ${money(h.price, { decimals: 4 })}${h.price_date ? ` (${fmtDate(h.price_date)})` : ""}` : "fiyat yok"} · %{h.share_pct.toFixed(0)}
                    </div>
                  </div>
                </div>
                <div className="row-line__end">
                  <span className="bes__fundval">
                    <strong>{money(h.own_value + h.state_value)}</strong>
                    <small className={`tone-${tone(h.own_pl) || "calm"}`}>{h.price ? money(h.own_pl, { sign: true }) : "–"}</small>
                  </span>
                  <Icon name="chevron" size={18} />
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="bes__actions">
        <button className="btn btn--ghost btn--small" onClick={() => open("besFund", { besId: b.id })}>
          <Icon name="plus" size={16} /> Fon ekle
        </button>
        <button className="btn btn--ghost btn--small" onClick={() => open("besSwitch", { besId: b.id })} disabled={b.holdings.length === 0}>
          Fon değiştir
        </button>
        <button className="btn btn--ghost btn--small" onClick={() => open("besReconcile", { besId: b.id })} disabled={b.holdings.length === 0}>
          Ekstreyle düzelt
        </button>
      </div>

      <h3 className="sheet__section">Aylık katkı planı</h3>
      {b.monthly_contribution > 0 ? (
        <dl className="kv-grid">
          <div className="kv">
            <dt>Aylık katkı</dt>
            <dd>{money(b.monthly_contribution)}</dd>
          </div>
          <div className="kv">
            <dt>Sıradaki katkı</dt>
            <dd>{b.next_contribution ? fmtDateLong(b.next_contribution) : "–"}</dd>
          </div>
          <div className="kv">
            <dt>Devlet katkısı oranı</dt>
            <dd>%{(b.state_rate * 100).toFixed(0)}</dd>
          </div>
          <div className="kv">
            <dt>Fon dağılımı</dt>
            <dd>{b.allocations.map((a) => `${a.fund_code} %${a.percent}`).join(" · ")}</dd>
          </div>
        </dl>
      ) : (
        <p className="muted">Aylık katkı tanımlı değil. “Hesabı ve planı düzenle” ile ekleyebilirsin.</p>
      )}

      <h3 className="sheet__section">Son hareketler</h3>
      {events === null ? (
        <p className="muted">Yükleniyor…</p>
      ) : events.length === 0 ? (
        <p className="muted">Henüz hareket yok. Aylık katkılar ve fon değişiklikleri burada listelenir.</p>
      ) : (
        <ul className="rows">
          {events.slice(0, 12).map((e) => (
            <li key={e.id} className="row-line">
              <div className="row-line__main">
                <span className="tag">{KIND[e.kind] || e.kind}</span>
                <div>
                  <div className="row-line__title">{e.fund_code || "—"}</div>
                  <div className="row-line__sub">{[fmtDate(e.event_date, { day: "numeric", month: "short", year: "numeric" }), e.note].filter(Boolean).join(" · ")}</div>
                </div>
              </div>
              <div className="row-line__end">
                {e.amount != null && <strong>{money(e.amount, { decimals: 2 })}</strong>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Sheet>
  );
}
