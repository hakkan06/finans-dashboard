import Sheet from "../components/Sheet.jsx";
import Icon from "../components/Icon.jsx";
import InstallmentRow from "../components/InstallmentRow.jsx";
import { Progress } from "../components/charts.jsx";
import { confirmDialog, toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { debtSummary } from "../lib/debt.js";
import { money, pct, todayStr } from "../lib/format.js";
import { useData } from "../lib/store.jsx";

export default function DebtDetailSheet({ debtId, onClose }) {
  const { debts, groups, reload } = useData();
  const debt = debts.find((d) => d.id === debtId);
  if (!debt) return null;
  const s = debtSummary(debt);
  const today = todayStr();
  const sorted = [...debt.installments].sort((a, b) => (a.due_date < b.due_date ? -1 : 1));

  async function move(e) {
    const v = e.target.value;
    try {
      await api.assignGroup(debt.id, v === "" ? null : Number(v));
      await reload();
      toast("Grup güncellendi", { tone: "good" });
    } catch (err) {
      toast(err.message, { tone: "bad" });
    }
  }

  async function remove() {
    const ok = await confirmDialog({
      title: `${debt.name} silinsin mi?`,
      body: `${s.count} taksitlik plan ve ödeme kayıtları kalıcı olarak silinir.`,
      confirmLabel: "Borcu sil",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteDebt(debt.id);
      await reload();
      toast(`${debt.name} silindi`, { tone: "good" });
      onClose();
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  return (
    <Sheet
      title={debt.name}
      subtitle={`${s.paidCount} / ${s.count} taksit ödendi`}
      onClose={onClose}
      footer={
        <button className="btn btn--danger-ghost" onClick={remove}>
          <Icon name="trash" size={18} /> Borcu sil
        </button>
      }
    >
      <div className="debt-hero">
        <div>
          <div className="debt-hero__label">Kalan</div>
          <div className="debt-hero__value">{money(s.remaining, { decimals: 2 })}</div>
        </div>
        <div className="debt-hero__side">
          {pct(s.pct, { sign: false })} ödendi
          <br />
          Toplam {money(s.total, { decimals: 2 })}
        </div>
      </div>
      <Progress pct={s.pct} label="Ödeme ilerlemesi" />

      <div className="form" style={{ marginTop: 20 }}>
        <label className="field">
          <span className="field__label">Grup</span>
          <select className="input" value={debt.group_id ?? ""} onChange={move}>
            <option value="">Grupsuz</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <h3 className="sheet__section">Taksitler</h3>
      <ul className="insts">
        {sorted.map((i) => (
          <InstallmentRow key={i.id} inst={i} debtName={debt.name} showDebt={false} today={today} />
        ))}
      </ul>
    </Sheet>
  );
}
