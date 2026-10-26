import { useMemo, useState } from "react";
import Icon from "../components/Icon.jsx";
import InstallmentRow from "../components/InstallmentRow.jsx";
import { MonthBars, Progress } from "../components/charts.jsx";
import { Segmented } from "../components/controls.jsx";
import { confirmDialog, toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { debtSummary, monthlyLoad, unpaidInstallments } from "../lib/debt.js";
import { dueLabel, money, pct, todayStr } from "../lib/format.js";
import { useSheets } from "../lib/sheets.jsx";
import { useData } from "../lib/store.jsx";

function DebtCard({ debt, onOpen, today }) {
  const s = debtSummary(debt);
  const due = s.next ? dueLabel(s.next.due_date, today) : null;
  return (
    <button className={`dcard ${s.done ? "is-done" : ""}`} onClick={onOpen}>
      <div className="dcard__top">
        <strong className="dcard__name">{debt.name}</strong>
        <span className="dcard__remaining">{s.done ? "Bitti" : money(s.remaining)}</span>
      </div>
      <Progress pct={s.pct} tone={s.done ? "good" : "brand"} label={`${debt.name} ilerleme`} />
      <div className="dcard__bottom">
        <span>
          {s.paidCount}/{s.count} taksit
        </span>
        {due && (
          <span className={`tone-${due.tone}`}>
            Sıradaki: {money(s.next.amount)} · {due.text}
          </span>
        )}
      </div>
    </button>
  );
}

export default function Debts() {
  const { debts, groups, reload, overview: ov } = useData();
  const { open } = useSheets();
  const [tab, setTab] = useState("active");
  const today = todayStr();

  const load = useMemo(() => monthlyLoad(debts), [debts]);
  const unpaid = useMemo(() => unpaidInstallments(debts), [debts]);
  const visible = (d) => (tab === "done" ? debtSummary(d).done : !debtSummary(d).done);

  const groupBlocks = groups
    .map((g) => ({ g, debts: debts.filter((d) => d.group_id === g.id && visible(d)) }))
    .filter((b) => b.debts.length > 0 || (tab === "active" && debts.every((d) => d.group_id !== b.g.id)));
  const loose = debts.filter((d) => d.group_id === null && visible(d));
  const doneCount = debts.filter((d) => debtSummary(d).done).length;

  async function removeGroup(g) {
    const ok = await confirmDialog({
      title: `${g.name} grubu silinsin mi?`,
      body: "Gruptaki borçlar silinmez, grupsuz olarak kalır.",
      confirmLabel: "Grubu sil",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteGroup(g.id);
      await reload();
      toast("Grup silindi, borçlar korundu", { tone: "good" });
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  if (debts.length === 0 && groups.length === 0) {
    return (
      <div className="page">
        <header className="page__head">
          <h1 className="page__title">Borçlar</h1>
        </header>
        <div className="empty">
          <h2>Kayıtlı borç yok</h2>
          <p>Kredi veya taksitli alışveriş eklersen vade günlerini burada takip edersin.</p>
          <button className="btn btn--primary" onClick={() => open("debt", {})}>
            <Icon name="plus" size={18} /> Borç ekle
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Borçlar</h1>
          <p className="page__sub">
            {money(ov.total_debts)} kalan
            {ov.overdue_count > 0 && <span className="tone-bad"> · {ov.overdue_count} gecikmiş taksit</span>}
          </p>
        </div>
        <button className="btn btn--primary" onClick={() => open("debt", {})}>
          <Icon name="plus" size={18} /> Borç ekle
        </button>
      </header>

      <section className="panel" aria-labelledby="load-title">
        <header className="panel__head">
          <h2 id="load-title" className="panel__title">
            Önümüzdeki 12 ay
          </h2>
          <span className="muted small">Gecikenler bu aya dahildir</span>
        </header>
        <MonthBars data={load} />
      </section>

      <div className="cols cols--debts">
        <div className="stack-y">
          <div className="toolbar toolbar--tight">
            <Segmented
              label="Borç durumu"
              value={tab}
              onChange={setTab}
              options={[
                { value: "active", label: "Devam eden" },
                { value: "done", label: `Biten (${doneCount})` },
              ]}
            />
          </div>

          {groupBlocks.map(({ g, debts: ds }) => {
            const gs = debts.filter((d) => d.group_id === g.id);
            const all = g.total_paid + g.total_remaining;
            return (
              <section key={g.id} className="panel group" aria-label={g.name}>
                <header className="panel__head">
                  <div>
                    <h2 className="panel__title">{g.name}</h2>
                    <p className="muted small">
                      {money(g.total_remaining)} kalan · {pct(g.progress_pct, { sign: false })} ödendi
                      {g.contracted_amount ? ` · sözleşme ${money(g.contracted_amount)}` : ""}
                    </p>
                  </div>
                  <div className="panel__tools">
                    <button className="icon-btn" aria-label={`${g.name} grubuna borç ekle`} onClick={() => open("debt", { groupId: g.id })}>
                      <Icon name="plus" size={18} />
                    </button>
                    <button className="icon-btn icon-btn--danger" aria-label={`${g.name} grubunu sil`} onClick={() => removeGroup(g)}>
                      <Icon name="trash" size={18} />
                    </button>
                  </div>
                </header>
                {all > 0 && <Progress pct={g.progress_pct} label={`${g.name} ilerleme`} />}
                <div className="dcards">
                  {ds.map((d) => (
                    <DebtCard key={d.id} debt={d} today={today} onOpen={() => open("debtDetail", { debtId: d.id })} />
                  ))}
                  {ds.length === 0 && <p className="muted small">{gs.length ? "Bu grupta bu görünümde borç yok." : "Bu gruba henüz borç eklenmedi."}</p>}
                </div>
              </section>
            );
          })}

          {loose.length > 0 && (
            <section className="panel" aria-label="Grupsuz borçlar">
              {groupBlocks.length > 0 && (
                <header className="panel__head">
                  <h2 className="panel__title">Grupsuz</h2>
                </header>
              )}
              <div className="dcards">
                {loose.map((d) => (
                  <DebtCard key={d.id} debt={d} today={today} onOpen={() => open("debtDetail", { debtId: d.id })} />
                ))}
              </div>
            </section>
          )}

          {groupBlocks.length === 0 && loose.length === 0 && <p className="muted panel__empty">{tab === "done" ? "Henüz biten borç yok." : "Devam eden borç yok."}</p>}
        </div>

        <section className="panel panel--sticky" aria-labelledby="next-title">
          <header className="panel__head">
            <h2 id="next-title" className="panel__title">
              Sıradaki ödemeler
            </h2>
          </header>
          {unpaid.length === 0 ? (
            <p className="muted panel__empty">Ödenecek taksit kalmadı.</p>
          ) : (
            <ul className="insts">
              {unpaid.slice(0, 10).map((i) => (
                <InstallmentRow key={i.id} inst={i} debtName={i.debtName} today={today} />
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
