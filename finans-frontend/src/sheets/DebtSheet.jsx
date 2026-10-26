import { useMemo, useState } from "react";
import Sheet from "../components/Sheet.jsx";
import { Field, NumberInput, Segmented, parseNum } from "../components/controls.jsx";
import { toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { buildInstallments } from "../lib/debt.js";
import { fmtDate, money, todayStr } from "../lib/format.js";
import { useData } from "../lib/store.jsx";

const NEW_GROUP = "__new__";
const COUNT_PRESETS = [3, 6, 12, 24, 36, 60];

/** Taksit planı oluşturan borç formu. Faizli kredi için anapara + aylık faiz hesaplar. */
export default function DebtSheet({ groupId = null, onClose }) {
  const { groups, reload } = useData();
  const [name, setName] = useState("");
  const [kind, setKind] = useState("plain");
  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState("");
  const [count, setCount] = useState("12");
  const [start, setStart] = useState(todayStr());
  const [group, setGroup] = useState(groupId ? String(groupId) : "");
  const [newGroup, setNewGroup] = useState("");
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  const total = parseNum(amount);
  const n = parseNum(count);
  const r = kind === "loan" ? parseNum(rate) || 0 : 0;

  const plan = useMemo(() => (total > 0 && n >= 1 && n <= 480 && start ? buildInstallments(total, Math.round(n), r, start) : []), [total, n, r, start]);
  const repayment = plan.reduce((a, p) => a + p.amount, 0);

  function validate() {
    const e = {};
    if (!name.trim()) e.name = "Borca bir ad ver.";
    if (!(total > 0)) e.amount = "Sıfırdan büyük bir tutar gir.";
    if (!(n >= 1 && n <= 480)) e.count = "Taksit sayısı 1 ile 480 arasında olmalı.";
    if (kind === "loan" && !(parseNum(rate) > 0)) e.rate = "Aylık faiz oranını gir (örn. 3,5).";
    if (group === NEW_GROUP && !newGroup.trim()) e.group = "Grup adı gerekli.";
    if (!start) e.start = "Tarih seç.";
    setErrors(e);
    return !Object.keys(e).length;
  }

  async function submit(again) {
    setFormError("");
    if (!validate()) return;
    setBusy(true);
    try {
      let gid = group && group !== NEW_GROUP ? Number(group) : null;
      if (group === NEW_GROUP) {
        const g = await api.createGroup({ name: newGroup.trim() });
        gid = g.id;
      }
      await api.createSchedule({
        name: name.trim(),
        total_amount: total,
        installments_count: Math.round(n),
        interest_rate: r,
        start_date: start,
        group_id: gid,
      });
      await reload();
      toast(`${name.trim()} eklendi`, { tone: "good" });
      if (again) {
        setName("");
        setAmount("");
        if (gid) setGroup(String(gid));
        setNewGroup("");
        setErrors({});
      } else onClose();
    } catch (e) {
      setFormError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet
      title="Yeni borç"
      subtitle="Taksit takvimi otomatik oluşturulur."
      onClose={onClose}
      footer={
        <>
          <button className="btn btn--ghost" onClick={() => submit(true)} disabled={busy}>
            Kaydet, yenisini ekle
          </button>
          <button className="btn btn--primary" onClick={() => submit(false)} disabled={busy}>
            {busy ? "Kaydediliyor…" : "Borcu kaydet"}
          </button>
        </>
      }
    >
      <form className="form" onSubmit={(e) => (e.preventDefault(), submit(false))}>
        <Field label="Borç adı" error={errors.name}>
          {(id) => <input id={id} className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Örn. Konut kredisi, Telefon taksiti" data-autofocus />}
        </Field>

        <Field label="Borç türü">
          {() => (
            <Segmented
              label="Borç türü"
              value={kind}
              onChange={setKind}
              options={[
                { value: "plain", label: "Faizsiz / toplam tutar" },
                { value: "loan", label: "Faizli kredi" },
              ]}
            />
          )}
        </Field>

        <div className="form__row">
          <Field label={kind === "loan" ? "Çekilen tutar (anapara)" : "Toplam geri ödeme"} error={errors.amount}>
            {(id) => <NumberInput id={id} value={amount} onChange={setAmount} prefix="₺" placeholder="0" />}
          </Field>
          {kind === "loan" && (
            <Field label="Aylık faiz" error={errors.rate} hint="Yıllık değil, aylık oran">
              {(id) => <NumberInput id={id} value={rate} onChange={setRate} suffix="%" placeholder="3,5" />}
            </Field>
          )}
        </div>

        <Field label="Taksit sayısı (ay)" error={errors.count}>
          {(id) => (
            <>
              <NumberInput id={id} value={count} onChange={setCount} placeholder="12" />
              <div className="chips chips--tight">
                {COUNT_PRESETS.map((c) => (
                  <button key={c} type="button" className={`chip ${String(c) === String(count) ? "is-on" : ""}`} onClick={() => setCount(String(c))}>
                    {c}
                  </button>
                ))}
              </div>
            </>
          )}
        </Field>

        <Field label="İlk taksit tarihi" error={errors.start}>
          {(id) => <input id={id} type="date" className="input" value={start} onChange={(e) => setStart(e.target.value)} />}
        </Field>

        <Field label="Grup" hint="Peşinat, taksit ve ara ödeme gibi parçaları tek çatı altında topla." error={errors.group}>
          {(id) => (
            <>
              <select id={id} className="input" value={group} onChange={(e) => setGroup(e.target.value)}>
                <option value="">Grupsuz</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
                <option value={NEW_GROUP}>＋ Yeni grup oluştur…</option>
              </select>
              {group === NEW_GROUP && <input className="input input--stack" value={newGroup} onChange={(e) => setNewGroup(e.target.value)} placeholder="Grup adı, örn. Ev alımı" data-autofocus />}
            </>
          )}
        </Field>

        <div className="summary-box summary-box--col" aria-live="polite">
          {plan.length ? (
            <>
              <div className="summary-box__line">
                <span>{plan.length} taksit × </span>
                <strong>{money(plan[0].amount, { decimals: 2 })}</strong>
              </div>
              <div className="summary-box__sub">
                Toplam geri ödeme {money(repayment, { decimals: 2 })}
                {kind === "loan" && total > 0 && ` · faiz yükü ${money(repayment - total, { decimals: 2 })}`}
              </div>
              <div className="summary-box__sub">
                {fmtDate(plan[0].due, { day: "numeric", month: "long", year: "numeric" })} – {fmtDate(plan[plan.length - 1].due, { day: "numeric", month: "long", year: "numeric" })}
              </div>
            </>
          ) : (
            <span className="muted">Tutarı ve taksit sayısını girince plan burada görünür.</span>
          )}
        </div>

        {formError && (
          <div className="callout callout--bad" role="alert">
            <p>{formError}</p>
          </div>
        )}
        <button type="submit" hidden />
      </form>
    </Sheet>
  );
}
