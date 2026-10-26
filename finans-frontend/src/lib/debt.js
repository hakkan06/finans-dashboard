import { addMonths, todayStr } from "./format.js";

/** Backend'deki build_installments ile aynı formül (önizleme için). */
export function buildInstallments(total, count, monthlyRatePct, start) {
  if (!(total > 0) || !(count >= 1)) return [];
  let amounts;
  if (monthlyRatePct > 0) {
    const r = monthlyRatePct / 100;
    const pmt = (total * r) / (1 - Math.pow(1 + r, -count));
    amounts = Array(count).fill(Math.round(pmt * 100) / 100);
  } else {
    const a = Math.round((total / count) * 100) / 100;
    amounts = Array(count - 1).fill(a);
    amounts.push(Math.round((total - a * (count - 1)) * 100) / 100);
  }
  return amounts.map((amount, i) => ({ due: addMonths(start, i), amount }));
}

/** Bir borcun taksit özeti */
export function debtSummary(debt) {
  let paid = 0;
  let remaining = 0;
  let next = null;
  for (const i of debt.installments) {
    if (i.is_paid) paid += i.amount;
    else {
      remaining += i.amount;
      if (!next || i.due_date < next.due_date) next = i;
    }
  }
  const total = paid + remaining;
  return {
    paid,
    remaining,
    total,
    pct: total > 0 ? (paid / total) * 100 : 0,
    next,
    done: remaining === 0 && debt.installments.length > 0,
    count: debt.installments.length,
    paidCount: debt.installments.filter((i) => i.is_paid).length,
  };
}

/** Tüm ödenmemiş taksitler (borç adıyla), vade sırasıyla */
export function unpaidInstallments(debts) {
  return debts
    .flatMap((d) => d.installments.filter((i) => !i.is_paid).map((i) => ({ ...i, debtName: d.name, debtId: d.id })))
    .sort((a, b) => (a.due_date < b.due_date ? -1 : a.due_date > b.due_date ? 1 : a.id - b.id));
}

/** Önümüzdeki 12 ay için aylık yük */
export function monthlyLoad(debts, months = 12) {
  const today = todayStr();
  const [cy, cm] = today.split("-").map(Number);
  const rows = [];
  for (let k = 0; k < months; k++) {
    const d = new Date(cy, cm - 1 + k, 1);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    rows.push({
      key,
      label: new Intl.DateTimeFormat("tr-TR", { month: "long", year: "numeric" }).format(d),
      short: new Intl.DateTimeFormat("tr-TR", { month: "short" }).format(d),
      value: 0,
      current: k === 0,
    });
  }
  const idx = Object.fromEntries(rows.map((r, i) => [r.key, i]));
  for (const d of debts) {
    for (const i of d.installments) {
      if (i.is_paid) continue;
      const key = i.due_date.slice(0, 7);
      if (key in idx) rows[idx[key]].value += i.amount;
      else if (key < rows[0].key) rows[0].value += i.amount; // gecikmiş olanlar bu aya yazılır
    }
  }
  return rows;
}
