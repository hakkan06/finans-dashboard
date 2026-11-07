import { useMemo, useState } from "react";
import Sheet from "../components/Sheet.jsx";
import Icon from "../components/Icon.jsx";
import { Field, NumberInput, parseNum } from "../components/controls.jsx";
import { toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { todayStr } from "../lib/format.js";
import { useData } from "../lib/store.jsx";

const MIN_ENTRY = "2003-01-01";
const num = (s) => (s === "" || s === null || s === undefined ? 0 : parseNum(s));
const bad = (n) => Number.isNaN(n) || n < 0;
const str = (v) => (v ? String(v).replace(".", ",") : "");

/** BES hesabı ekleme ve düzenleme: hesap bilgisi, aylık katkı planı ve (yeni hesapta) başlangıç fonları. */
export default function BesSheet({ besId = null, onClose }) {
  const { bes, reload } = useData();
  const cur = besId ? bes.find((b) => b.id === besId) : null;
  const [name, setName] = useState(cur?.name ?? "");
  const [company, setCompany] = useState(cur?.company ?? "");
  const [entry, setEntry] = useState(cur?.system_entry_date ?? "");
  const [contract, setContract] = useState(cur?.contract_start_date ?? "");
  const [birth, setBirth] = useState(cur?.birth_date ?? "");
  const [retire, setRetire] = useState(cur?.retirement_eligible ?? false);
  const [monthly, setMonthly] = useState(cur ? str(cur.monthly_contribution) : "");
  const [day, setDay] = useState(cur ? String(cur.contribution_day) : "1");
  const [stateRate, setStateRate] = useState(cur ? String(Math.round(cur.state_rate * 1000) / 10).replace(".", ",") : "20");
  const [firstDate, setFirstDate] = useState(cur?.next_contribution ?? "");
  const [allocs, setAllocs] = useState(cur?.allocations.length ? cur.allocations.map((a) => ({ code: a.fund_code, pct: String(a.percent).replace(".", ",") })) : [{ code: "", pct: "100" }]);
  const [funds, setFunds] = useState([{ code: "", own: "", state: "", cost: "" }]);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  const monthlyN = num(monthly);
  const pctSum = useMemo(() => allocs.reduce((a, r) => a + (num(r.pct) || 0), 0), [allocs]);

  if (besId && !cur) return null;

  const setAlloc = (i, patch) => setAllocs((l) => l.map((r, k) => (k === i ? { ...r, ...patch } : r)));
  const setFund = (i, patch) => setFunds((l) => l.map((r, k) => (k === i ? { ...r, ...patch } : r)));

  function validate() {
    const e = {};
    if (!name.trim()) e.name = "Hesaba bir ad ver.";
    if (!entry) e.entry = "BES sistemine ilk giriş tarihini seç.";
    else if (entry < MIN_ENTRY || entry > todayStr()) e.entry = "Tarih 2003 ile bugün arasında olmalı.";
    if (birth && (birth > todayStr() || birth < "1920-01-01")) e.birth = "Geçerli bir doğum tarihi gir.";
    if (bad(monthlyN)) e.monthly = "Sıfır veya daha büyük bir tutar gir.";
    const d = Math.round(num(day));
    if (!(d >= 1 && d <= 28)) e.day = "Günü 1 ile 28 arasında gir.";
    const sr = num(stateRate);
    if (Number.isNaN(sr) || sr < 0 || sr > 100) e.stateRate = "0 ile 100 arasında bir oran gir.";
    if (monthlyN > 0) {
      const filled = allocs.filter((r) => r.code.trim() || r.pct);
      if (!filled.length || filled.some((r) => r.code.trim().length < 2)) e.allocs = "Her satır için fon kodu gir.";
      else if (Math.abs(pctSum - 100) > 0.01) e.allocs = "Yüzdelerin toplamı %100 olmalı.";
    }
    if (!cur) {
      for (const f of funds) {
        if (!f.code.trim() && !f.own && !f.state) continue;
        if (f.code.trim().length < 2) e.funds = "Pay girdiğin her satır için fon kodu gir.";
        else if ([f.own, f.state, f.cost].some((v) => bad(num(v)))) e.funds = "Pay ve tutarlar sıfır veya daha büyük olmalı.";
      }
    }
    setErrors(e);
    return !Object.keys(e).length;
  }

  async function submit() {
    setFormError("");
    if (!validate()) return;
    setBusy(true);
    const body = {
      name: name.trim(),
      company: company.trim() || null,
      system_entry_date: entry,
      contract_start_date: contract || null,
      birth_date: birth || null,
      retirement_eligible: retire,
      monthly_contribution: monthlyN || 0,
      contribution_day: Math.round(num(day)) || 1,
      state_rate: num(stateRate) / 100,
      allocations: monthlyN > 0 ? allocs.filter((r) => r.code.trim()).map((r) => ({ fund_code: r.code.trim().toUpperCase(), percent: num(r.pct) })) : [],
    };
    if (firstDate && firstDate !== cur?.next_contribution) body.first_contribution_date = firstDate;
    if (!cur) {
      body.holdings = funds
        .filter((f) => f.code.trim())
        .map((f) => ({ fund_code: f.code.trim().toUpperCase(), own_units: num(f.own), state_units: num(f.state), own_cost: num(f.cost) }));
    }
    try {
      if (cur) await api.updateBes(cur.id, body);
      else await api.createBes(body);
      await reload();
      toast(cur ? "BES hesabı güncellendi" : "BES hesabı eklendi", { tone: "good" });
      onClose();
    } catch (e) {
      setFormError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet
      title={cur ? "Hesabı ve planı düzenle" : "Yeni BES hesabı"}
      subtitle={cur ? cur.name : "Bilgileri güncel BES ekstrenizden girin."}
      onClose={onClose}
      wide
      footer={
        <button className="btn btn--primary" onClick={submit} disabled={busy}>
          {busy ? "Kaydediliyor…" : cur ? "Güncelle" : "Kaydet"}
        </button>
      }
    >
      <form className="form" onSubmit={(e) => (e.preventDefault(), submit())}>
        <h3 className="sheet__section">Hesap</h3>
        <Field label="Hesap adı" error={errors.name}>
          {(id) => <input id={id} className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Örn. Anadolu Hayat BES" data-autofocus={cur ? undefined : true} />}
        </Field>
        <Field label="Şirket (isteğe bağlı)">{(id) => <input id={id} className="input" value={company} onChange={(e) => setCompany(e.target.value)} />}</Field>
        <div className="form__row">
          <Field label="BES sistemine ilk giriş" error={errors.entry} hint="Hak ediş süresi buradan işler. Birden fazla sözleşmen varsa en eski girişin geçerlidir.">
            {(id) => <input id={id} type="date" className="input" value={entry} min={MIN_ENTRY} max={todayStr()} onChange={(e) => setEntry(e.target.value)} />}
          </Field>
          <Field label="Bu sözleşmenin başlangıcı" hint="Bilgi amaçlı, hesabı etkilemez.">
            {(id) => <input id={id} type="date" className="input" value={contract} min={MIN_ENTRY} onChange={(e) => setContract(e.target.value)} />}
          </Field>
        </div>
        <Field label="Doğum tarihi" error={errors.birth} hint="Girersen 56 yaş ve 10 yıl şartı otomatik hesaplanır.">
          {(id) => <input id={id} type="date" className="input" value={birth} max={todayStr()} onChange={(e) => setBirth(e.target.value)} />}
        </Field>
        {!birth && (
          <label className="bes__check">
            <input type="checkbox" checked={retire} onChange={(e) => setRetire(e.target.checked)} />
            <span>10 yıl + 56 yaş emeklilik şartını sağladım</span>
          </label>
        )}

        <h3 className="sheet__section">Aylık katkı planı</h3>
        <div className="form__row">
          <Field label="Aylık katkı (kendi payın)" error={errors.monthly} hint="Boş bırakırsan otomatik katkı eklenmez.">
            {(id) => <NumberInput id={id} value={monthly} onChange={setMonthly} prefix="₺" placeholder="0" />}
          </Field>
          <Field label="Ayın kaçında yatar" error={errors.day}>
            {(id) => <NumberInput id={id} value={day} onChange={setDay} placeholder="1" />}
          </Field>
        </div>
        {monthlyN > 0 && (
          <>
            <Field label="Katkının fon dağılımı" error={errors.allocs} hint={`Toplam %${String(Math.round(pctSum * 100) / 100).replace(".", ",")}`}>
              {() => (
                <div className="bes__rows">
                  {allocs.map((r, i) => (
                    <div key={i} className="bes__rowfields">
                      <input className="input" value={r.code} onChange={(e) => setAlloc(i, { code: e.target.value })} placeholder="Fon kodu" aria-label="Fon kodu" />
                      <NumberInput value={r.pct} onChange={(v) => setAlloc(i, { pct: v })} suffix="%" aria-label="Yüzde" />
                      <button type="button" className="icon-btn" aria-label="Satırı sil" disabled={allocs.length === 1} onClick={() => setAllocs((l) => l.filter((_, k) => k !== i))}>
                        <Icon name="x" size={18} />
                      </button>
                    </div>
                  ))}
                  <button type="button" className="link-btn" onClick={() => setAllocs((l) => [...l, { code: "", pct: "" }])}>
                    <Icon name="plus" size={16} /> Fon ekle
                  </button>
                </div>
              )}
            </Field>
            <div className="form__row">
              <Field label="Devlet katkısı oranı" error={errors.stateRate} hint="Katkı payının yüzdesi; mevzuat değişirse güncelle.">
                {(id) => <NumberInput id={id} value={stateRate} onChange={setStateRate} suffix="%" placeholder="20" />}
              </Field>
              <Field label="Sıradaki otomatik katkı" hint="Bu tarihten önceki katkıların pay adedine zaten dahil olduğu varsayılır. Boşsa ayın seçilen gününe göre belirlenir.">
                {(id) => <input id={id} type="date" className="input" value={firstDate} onChange={(e) => setFirstDate(e.target.value)} />}
              </Field>
            </div>
          </>
        )}

        {!cur && (
          <>
            <h3 className="sheet__section">Şu anki fonların</h3>
            <Field label="Fon, pay adedi ve katkı" error={errors.funds} hint="Ekstrendeki güncel pay adetlerini gir; sonradan Fon ekle ve Ekstreyle düzelt ile değiştirebilirsin.">
              {() => (
                <div className="bes__rows">
                  {funds.map((f, i) => (
                    <div key={i} className="bes__fundfields">
                      <input className="input" value={f.code} onChange={(e) => setFund(i, { code: e.target.value })} placeholder="Fon kodu" aria-label="Fon kodu" />
                      <NumberInput value={f.own} onChange={(v) => setFund(i, { own: v })} placeholder="Kendi pay" aria-label="Kendi katkı payı adedi" />
                      <NumberInput value={f.state} onChange={(v) => setFund(i, { state: v })} placeholder="Devlet pay" aria-label="Devlet katkısı payı adedi" />
                      <NumberInput value={f.cost} onChange={(v) => setFund(i, { cost: v })} prefix="₺" placeholder="Ödenen" aria-label="Bu fona giren kendi katkın" />
                      <button type="button" className="icon-btn" aria-label="Satırı sil" disabled={funds.length === 1} onClick={() => setFunds((l) => l.filter((_, k) => k !== i))}>
                        <Icon name="x" size={18} />
                      </button>
                    </div>
                  ))}
                  <button type="button" className="link-btn" onClick={() => setFunds((l) => [...l, { code: "", own: "", state: "", cost: "" }])}>
                    <Icon name="plus" size={16} /> Fon ekle
                  </button>
                </div>
              )}
            </Field>
          </>
        )}

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
