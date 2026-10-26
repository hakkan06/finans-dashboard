import Icon from "./Icon.jsx";
import { dueLabel, fmtDate, money } from "../lib/format.js";
import { useData } from "../lib/store.jsx";

/** Tek taksit satırı: soldaki daireye dokunarak ödendi/ödenmedi çevrilir. */
export default function InstallmentRow({ inst, debtName, showDebt = true, today }) {
  const { toggleInstallment } = useData();
  const due = dueLabel(inst.due_date, today);
  const label = `${debtName} · ${fmtDate(inst.due_date)}`;
  return (
    <li className={`inst ${inst.is_paid ? "is-paid" : ""}`}>
      <button
        className={`check ${inst.is_paid ? "is-on" : ""}`}
        onClick={() => toggleInstallment(inst, label)}
        aria-label={inst.is_paid ? "Ödenmedi olarak işaretle" : "Ödendi olarak işaretle"}
        aria-pressed={inst.is_paid}
      >
        {inst.is_paid && <Icon name="check" size={16} stroke={2.6} />}
      </button>
      <div className="inst__main">
        <div className="inst__title">{showDebt ? debtName : fmtDate(inst.due_date, { day: "numeric", month: "long", year: "numeric" })}</div>
        <div className={`inst__sub ${inst.is_paid ? "" : `tone-${due.tone}`}`}>
          {inst.is_paid ? (showDebt ? `${fmtDate(inst.due_date)} · ödendi` : "Ödendi") : showDebt ? due.text : due.left < 0 || due.left <= 3 ? due.text : "Bekliyor"}
        </div>
      </div>
      <div className="inst__amount">{money(inst.amount, { decimals: 2 })}</div>
    </li>
  );
}
