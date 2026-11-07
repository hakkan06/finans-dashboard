import { useState } from "react";
import Sheet from "../components/Sheet.jsx";
import Icon from "../components/Icon.jsx";
import { Field, NumberInput, parseNum } from "../components/controls.jsx";
import { confirmDialog, toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { fmtDateLong, money, todayStr } from "../lib/format.js";
import { useData } from "../lib/store.jsx";

const MIN_ENTRY = "2003-01-01";
const num = (s) => (s === "" || s === null || s === undefined ? 0 : parseNum(s));
const ratioText = (r) => `%${Math.round(r * 100)}`;

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
              <div className="row-line__sub">10 yıl dolması ve 56 yaşın tamamlanması</div>
            </div>
          </div>
          <div className="row-line__end">
            <span className={b.retirement_eligible ? "tone-good" : "muted"}>{b.retirement_eligible ? "Sağlandı" : "Bekleniyor"}</span>
          </div>
        </li>
      </ul>
      <dl className="kv-grid">
        <div className="kv">
          <dt>Hak edilen devlet katkısı</dt>
          <dd>{money(b.vested_state)}</dd>
        </div>
        <div className="kv">
          <dt>Henüz hak edilmeyen</dt>
          <dd>{money(b.forfeited_state)}</dd>
        </div>
        <div className="kv">
          <dt>Tahmini stopaj</dt>
          <dd>{money(b.tax)}</dd>
        </div>
        <div className="kv">
          <dt>Bugün çıkılırsa net</dt>
          <dd>{money(b.net_value)}</dd>
        </div>
      </dl>
      {b.gain_at_next > 0 && b.next_milestone && (
        <p className="bes__note">
          {fmtDateLong(b.next_milestone.due_date)} tarihinde {ratioText(b.next_milestone.ratio)} kademesine geçince net değer yaklaşık {money(b.gain_at_next)} artar.
        </p>
      )}
    </>
  );
}

/** BES hesabı ekleme ve düzenleme. besId verilirse düzenleme modundadır. */
export default function BesSheet({ besId = null, onClose }) {
  const { bes, reload } = useData();
  const cur = besId ? bes.find((b) => b.id === besId) : null;
  const [name, setName] = useState(cur?.name ?? "");
  const [company, setCompany] = useState(cur?.company ?? "");
  const [entry, setEntry] = useState(cur?.system_entry_date ?? "");
  const [contract, setContract] = useState(cur?.contract_start_date ?? "");
  const [principal, setPrincipal] = useState(cur ? String(cur.own_principal) : "");
  const [ownBal, setOwnBal] = useState(cur ? String(cur.own_balance) : "");
  const [stateBal, setStateBal] = useState(cur ? String(cur.state_balance) : "");
  const [retire, setRetire] = useState(cur?.retirement_eligible ?? false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  if (besId && !cur) return null;

  function validate() {
    const e = {};
    if (!name.trim()) e.name = "Hesaba bir ad ver.";
    if (!entry) e.entry = "Sisteme ilk giriş tarihini seç.";
    else if (entry < MIN_ENTRY || entry > todayStr()) e.entry = "Tarih 2003 ile bugün arasında olmalı.";
    if (contract && contract < MIN_ENTRY) e.contract = "Geçersiz tarih.";
    for (const [k, v] of [["principal", principal], ["ownBal", ownBal], ["stateBal", stateBal]]) {
      const n = num(v);
      if (Number.isNaN(n) || n < 0) e[k] = "Sıfır veya daha büyük bir tutar gir.";
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
      own_principal: num(principal),
      own_balance: num(ownBal),
      state_balance: num(stateBal),
      retirement_eligible: retire,
    };
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

  async function remove() {
    const ok = await confirmDialog({
      title: `${cur.name} silinsin mi?`,
      body: "BES hesabı kaydı kalıcı olarak silinir. Gerçek sözleşmeniz etkilenmez, sadece bu panodaki kayıt kalkar.",
      confirmLabel: "Hesabı sil",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteBes(cur.id);
      await reload();
      toast("BES hesabı silindi", { tone: "good" });
      onClose();
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  return (
    <Sheet
      title={cur ? cur.name : "Yeni BES hesabı"}
      subtitle={cur ? `Bakiyeler en son ${cur.balance_updated ? fmtDateLong(cur.balance_updated) : "–"} tarihinde güncellendi.` : "Tutarları güncel BES ekstrenizden girin."}
      onClose={onClose}
      footer={
        <>
          {cur && (
            <button className="btn btn--danger-ghost" onClick={remove} disabled={busy}>
              <Icon name="trash" size={18} /> Hesabı sil
            </button>
          )}
          <button className="btn btn--primary" onClick={submit} disabled={busy}>
            {busy ? "Kaydediliyor…" : cur ? "Güncelle" : "Kaydet"}
          </button>
        </>
      }
    >
      {cur && <Timeline b={cur} />}

      <h3 className="sheet__section">{cur ? "Bilgileri güncelle" : "Hesap bilgileri"}</h3>
      <form className="form" onSubmit={(e) => (e.preventDefault(), submit())}>
        <Field label="Hesap adı" error={errors.name}>
          {(id) => <input id={id} className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Örn. Anadolu Hayat BES" data-autofocus={cur ? undefined : true} />}
        </Field>
        <Field label="Şirket (isteğe bağlı)">{(id) => <input id={id} className="input" value={company} onChange={(e) => setCompany(e.target.value)} />}</Field>

        <div className="form__row">
          <Field label="BES sistemine ilk giriş" error={errors.entry} hint="Hak ediş süresi buradan işler. Birden fazla sözleşmen varsa en eski girişin geçerlidir.">
            {(id) => <input id={id} type="date" className="input" value={entry} min={MIN_ENTRY} max={todayStr()} onChange={(e) => setEntry(e.target.value)} />}
          </Field>
          <Field label="Bu sözleşmenin başlangıcı" error={errors.contract} hint="Bilgi amaçlı, hesabı etkilemez.">
            {(id) => <input id={id} type="date" className="input" value={contract} min={MIN_ENTRY} onChange={(e) => setContract(e.target.value)} />}
          </Field>
        </div>

        <Field label="Kendi ödediğin toplam katkı" error={errors.principal} hint="Getiri hesabı için kullanılır.">
          {(id) => <NumberInput id={id} value={principal} onChange={setPrincipal} prefix="₺" placeholder="0" />}
        </Field>
        <div className="form__row">
          <Field label="Kendi katkın + getirisi" error={errors.ownBal}>
            {(id) => <NumberInput id={id} value={ownBal} onChange={setOwnBal} prefix="₺" placeholder="0" />}
          </Field>
          <Field label="Devlet katkısı + getirisi" error={errors.stateBal}>
            {(id) => <NumberInput id={id} value={stateBal} onChange={setStateBal} prefix="₺" placeholder="0" />}
          </Field>
        </div>

        <label className="bes__check">
          <input type="checkbox" checked={retire} onChange={(e) => setRetire(e.target.checked)} />
          <span>10 yıl + 56 yaş emeklilik şartını sağladım</span>
        </label>

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
