import { useMemo, useState } from "react";
import Icon from "./Icon.jsx";
import { NumberInput, parseNum } from "./controls.jsx";
import { dueLabel, money } from "../lib/format.js";
import { unpaidInstallments } from "../lib/debt.js";

const MAX_ALL = 60;

/** Toplam ödenecek tutar: seçilen taksitler + "bu satıştan öde" işaretli yeni borçlar. */
export function saleDebtTotal(debts, payIds, newDebts) {
  const sel = new Set(payIds);
  let t = 0;
  for (const d of debts) for (const i of d.installments) if (sel.has(i.id) && !i.is_paid) t += i.amount;
  for (const n of newDebts) if (n.paid) t += parseNum(n.amount) > 0 ? parseNum(n.amount) : 0;
  return t;
}

/**
 * Satış ekranına gömülen bölüm: bu satıştan ödenecek mevcut taksitleri seç, istersen daha önce girilmemiş
 * küçük bir borcu (örn. aidat) da oradan ekle. Hiçbir şey seçilmezse satış her zamanki gibi kaydolur.
 */
export default function SaleDebts({ debts, date, proceeds, payIds, setPayIds, newDebts, setNewDebts, error }) {
  const [showAll, setShowAll] = useState(false);
  const all = useMemo(() => unpaidInstallments(debts), [debts]);

  const rows = useMemo(() => {
    if (showAll) return all.slice(0, MAX_ALL);
    // Her borcun sıradaki taksiti; seçili olanlar (başka taksitler dahil) gizlenmesin
    const seen = new Set();
    return all.filter((i) => {
      const first = !seen.has(i.debtId);
      seen.add(i.debtId);
      return first || payIds.includes(i.id);
    });
  }, [all, showAll, payIds]);

  const total = saleDebtTotal(debts, payIds, newDebts);
  const left = proceeds != null ? proceeds - total : null;
  const toggle = (id) => setPayIds(payIds.includes(id) ? payIds.filter((x) => x !== id) : [...payIds, id]);
  const addNew = () => setNewDebts([...newDebts, { key: Date.now() + Math.random(), name: "", amount: "", due: date, paid: true }]);
  const patchNew = (key, patch) => setNewDebts(newDebts.map((n) => (n.key === key ? { ...n, ...patch } : n)));
  const hasAny = payIds.length > 0 || newDebts.length > 0;

  return (
    <section className="sale-debts" aria-labelledby="sale-debts-title">
      <h3 id="sale-debts-title" className="sheet__section">
        Bu satışla borç öde <small className="muted">isteğe bağlı</small>
      </h3>

      {all.length === 0 ? (
        <p className="muted">Ödenmemiş taksit yok.</p>
      ) : (
        <ul className="sale-debts__list">
          {rows.map((i) => {
            const due = dueLabel(i.due_date);
            const on = payIds.includes(i.id);
            return (
              <li key={i.id}>
                <label className={`sale-debts__row ${on ? "is-on" : ""}`}>
                  <input type="checkbox" checked={on} onChange={() => toggle(i.id)} />
                  <span className="sale-debts__name">
                    <strong>{i.debtName}</strong>
                    <small className={`tone-${due.tone === "calm" ? "calm" : due.tone}`}>{due.text}</small>
                  </span>
                  <span className="sale-debts__amt">{money(i.amount, { decimals: 2 })}</span>
                </label>
              </li>
            );
          })}
        </ul>
      )}
      {all.length > rows.length || showAll ? (
        <button type="button" className="link-btn" onClick={() => setShowAll(!showAll)}>
          {showAll ? "Yalnızca sıradaki taksitleri göster" : `Tüm taksitleri göster (${all.length})`}
        </button>
      ) : null}
      {showAll && all.length > MAX_ALL && <p className="bes__note">İlk {MAX_ALL} taksit gösteriliyor (vade sırasıyla).</p>}

      {newDebts.map((n) => (
        <div key={n.key} className="sale-debts__new">
          <div className="form__row">
            <input className="input" value={n.name} onChange={(e) => patchNew(n.key, { name: e.target.value })} placeholder="Borç adı, örn. Aidat" aria-label="Yeni borç adı" />
            <NumberInput value={n.amount} onChange={(v) => patchNew(n.key, { amount: v })} prefix="₺" placeholder="Tutar" aria-label="Yeni borç tutarı" />
          </div>
          <div className="sale-debts__newfoot">
            <input type="date" className="input" value={n.due} onChange={(e) => patchNew(n.key, { due: e.target.value })} aria-label="Vade tarihi" />
            <label className="bes__check">
              <input type="checkbox" checked={n.paid} onChange={(e) => patchNew(n.key, { paid: e.target.checked })} />
              <span>Bu satıştan öde</span>
            </label>
            <button type="button" className="icon-btn icon-btn--danger" aria-label="Yeni borcu kaldır" onClick={() => setNewDebts(newDebts.filter((x) => x.key !== n.key))}>
              <Icon name="trash" size={18} />
            </button>
          </div>
        </div>
      ))}
      <button type="button" className="link-btn" onClick={addNew}>
        <Icon name="plus" size={16} /> Yeni borç ekle
      </button>
      {error && <p className="field__msg field__msg--error">{error}</p>}

      {hasAny && (
        <div className="summary-box summary-box--col" aria-live="polite">
          <div className="summary-box__line">
            <span>Ödenecek borç</span>
            <strong>{money(total, { decimals: 2 })}</strong>
          </div>
          {left !== null && (
            <div className={`summary-box__sub ${left < -0.005 ? "tone-warn" : ""}`}>
              {left < -0.005
                ? `Satış tutarı ${money(-left, { decimals: 2 })} yetmiyor; kalanı başka bir kaynaktan ödemiş olmalısın.`
                : `Satıştan geriye ${money(left, { decimals: 2 })} kalır.`}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
