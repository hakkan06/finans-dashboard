import { useState } from "react";
import Sheet from "../components/Sheet.jsx";
import Icon from "../components/Icon.jsx";
import { Field, NumberInput, parseNum } from "../components/controls.jsx";
import { confirmDialog, toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { money } from "../lib/format.js";
import { useData } from "../lib/store.jsx";

const num = (s) => (s === "" || s === null || s === undefined ? 0 : parseNum(s));
const bad = (n) => Number.isNaN(n) || n < 0;
const str = (v) => (v ? String(v).replace(".", ",") : "");

function useAccount(besId) {
  const { bes, reload } = useData();
  return { acc: bes.find((b) => b.id === besId), reload };
}

/** Fon ekleme / pay adedi düzenleme. fundCode verilirse düzenleme modundadır. */
export function BesFundSheet({ besId, fundCode = null, onClose }) {
  const { acc, reload } = useAccount(besId);
  const cur = fundCode ? acc?.holdings.find((h) => h.fund_code === fundCode) : null;
  const [code, setCode] = useState(cur?.fund_code ?? "");
  const [own, setOwn] = useState(str(cur?.own_units));
  const [state, setState] = useState(str(cur?.state_units));
  const [cost, setCost] = useState(str(cur?.own_cost));
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!acc || (fundCode && !cur)) return null;

  async function submit() {
    setFormError("");
    const e = {};
    const c = code.trim().toUpperCase();
    if (c.length < 2) e.code = "Fon kodunu gir (örn. TEFAS emeklilik fon kodu).";
    else if (!cur && acc.holdings.some((h) => h.fund_code === c)) e.code = "Bu fon hesapta zaten var; listeden seçip düzenle.";
    for (const [k, v] of [["own", own], ["state", state], ["cost", cost]]) if (bad(num(v))) e[k] = "Sıfır veya daha büyük bir sayı gir.";
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      await api.putBesHolding(besId, c, { own_units: num(own), state_units: num(state), own_cost: num(cost) });
      await reload();
      toast(cur ? "Fon güncellendi" : "Fon eklendi", { tone: "good" });
      onClose();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    const ok = await confirmDialog({
      title: `${cur.fund_code} hesaptan kaldırılsın mı?`,
      body: "Fondaki pay kaydı silinir. Fonu başka bir fona aktardıysan bunun yerine “Fon değiştir”i kullan.",
      confirmLabel: "Kaldır",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteBesHolding(besId, cur.fund_code);
      await reload();
      toast("Fon kaldırıldı", { tone: "good" });
      onClose();
    } catch (err) {
      toast(err.message, { tone: "bad" });
    }
  }

  return (
    <Sheet
      title={cur ? cur.fund_code : "Fon ekle"}
      subtitle={cur ? cur.fund_name || acc.name : `${acc.name} hesabına`}
      onClose={onClose}
      footer={
        <>
          {cur && (
            <button className="btn btn--danger-ghost" onClick={remove} disabled={busy}>
              <Icon name="trash" size={18} /> Fonu kaldır
            </button>
          )}
          <button className="btn btn--primary" onClick={submit} disabled={busy}>
            {busy ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </>
      }
    >
      <form className="form" onSubmit={(e) => (e.preventDefault(), submit())}>
        <Field label="Fon kodu" error={errors.code} hint="Fiyat TEFAS emeklilik fonlarından çekilir; kod bulunamazsa kaydedilmez.">
          {(id) => <input id={id} className="input" value={code} disabled={!!cur} onChange={(e) => setCode(e.target.value)} placeholder="Fon kodu" data-autofocus />}
        </Field>
        <div className="form__row">
          <Field label="Kendi katkı payı adedi" error={errors.own} hint="Ekstrendeki pay adedi">
            {(id) => <NumberInput id={id} value={own} onChange={setOwn} placeholder="0" />}
          </Field>
          <Field label="Devlet katkısı payı adedi" error={errors.state}>
            {(id) => <NumberInput id={id} value={state} onChange={setState} placeholder="0" />}
          </Field>
        </div>
        <Field label="Bu fona giren kendi katkın (₺)" error={errors.cost} hint="Getiriyi hesaplamak için. Bilmiyorsan o günkü değere eşit gir; getiri bundan sonrası için hesaplanır.">
          {(id) => <NumberInput id={id} value={cost} onChange={setCost} prefix="₺" placeholder="0" />}
        </Field>
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

/** Bir fondaki payın belirli oranını başka fona aktarır. */
export function BesSwitchSheet({ besId, onClose }) {
  const { acc, reload } = useAccount(besId);
  const [from, setFrom] = useState(acc?.holdings[0]?.fund_code ?? "");
  const [to, setTo] = useState("");
  const [percent, setPercent] = useState("100");
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!acc) return null;
  const src = acc.holdings.find((h) => h.fund_code === from);

  async function submit() {
    setFormError("");
    const e = {};
    const t = to.trim().toUpperCase();
    const p = num(percent);
    if (!from) e.from = "Kaynak fonu seç.";
    if (t.length < 2) e.to = "Hedef fon kodunu gir.";
    else if (t === from) e.to = "Hedef fon kaynakla aynı olamaz.";
    if (!(p > 0 && p <= 100)) e.percent = "1 ile 100 arasında bir oran gir.";
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      await api.switchBes(besId, { from_fund: from, to_fund: t, percent: p });
      await reload();
      toast(`${from} → ${t} aktarıldı`, { tone: "good" });
      onClose();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet
      title="Fon değiştir"
      subtitle="Değer korunur; adet, iki fonun güncel fiyatına göre yeniden hesaplanır."
      onClose={onClose}
      footer={
        <button className="btn btn--primary" onClick={submit} disabled={busy}>
          {busy ? "Aktarılıyor…" : "Aktar"}
        </button>
      }
    >
      <form className="form" onSubmit={(e) => (e.preventDefault(), submit())}>
        <Field label="Kaynak fon" error={errors.from} hint={src ? `Mevcut değer ${money(src.own_value + src.state_value)}` : undefined}>
          {(id) => (
            <select id={id} className="input" value={from} onChange={(e) => setFrom(e.target.value)}>
              {acc.holdings.map((h) => (
                <option key={h.fund_code} value={h.fund_code}>
                  {h.fund_code}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="Hedef fon kodu" error={errors.to}>
          {(id) => <input id={id} className="input" value={to} onChange={(e) => setTo(e.target.value)} placeholder="Fon kodu" data-autofocus />}
        </Field>
        <Field label="Aktarılacak oran" error={errors.percent}>
          {(id) => (
            <>
              <NumberInput id={id} value={percent} onChange={setPercent} suffix="%" placeholder="100" />
              <div className="chips chips--tight">
                {[25, 50, 75, 100].map((c) => (
                  <button key={c} type="button" className={`chip ${String(c) === percent ? "is-on" : ""}`} onClick={() => setPercent(String(c))}>
                    %{c}
                  </button>
                ))}
              </div>
            </>
          )}
        </Field>
        <p className="bes__note">Aylık katkı dağılımını da değiştirmek istiyorsan “Hesabı ve planı düzenle”den güncelle.</p>
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

/** Ekstredeki toplam bakiyelerle eşitler (paylar oranlı ölçeklenir). */
export function BesReconcileSheet({ besId, onClose }) {
  const { acc, reload } = useAccount(besId);
  const round2 = (v) => (Math.round(v * 100) / 100).toString().replace(".", ",");
  const [own, setOwn] = useState(acc ? round2(acc.own_balance) : "");
  const [state, setState] = useState(acc ? round2(acc.state_balance) : "");
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!acc) return null;

  async function submit() {
    setFormError("");
    const o = num(own);
    const s = num(state);
    if (bad(o) || bad(s)) return setFormError("Tutarlar sıfır veya daha büyük olmalı.");
    const body = {};
    if (Math.abs(o - acc.own_balance) > 0.005) body.own_balance = o;
    if (Math.abs(s - acc.state_balance) > 0.005) body.state_balance = s;
    if (!Object.keys(body).length) return onClose();
    setBusy(true);
    try {
      await api.reconcileBes(besId, body);
      await reload();
      toast("Bakiyeler ekstreyle eşitlendi", { tone: "good" });
      onClose();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet
      title="Ekstreyle düzelt"
      subtitle="Şirket giriş aidatı, yönetim gideri ve fiyat gecikmesi küçük farklar yaratır."
      onClose={onClose}
      footer={
        <button className="btn btn--primary" onClick={submit} disabled={busy}>
          {busy ? "Kaydediliyor…" : "Eşitle"}
        </button>
      }
    >
      <form className="form" onSubmit={(e) => (e.preventDefault(), submit())}>
        <Field label="Kendi katkı + getirisi (ekstre)" hint={`Panoda şu an ${money(acc.own_balance, { decimals: 2 })}`}>
          {(id) => <NumberInput id={id} value={own} onChange={setOwn} prefix="₺" data-autofocus />}
        </Field>
        <Field label="Devlet katkısı + getirisi (ekstre)" hint={`Panoda şu an ${money(acc.state_balance, { decimals: 2 })}`}>
          {(id) => <NumberInput id={id} value={state} onChange={setState} prefix="₺" />}
        </Field>
        <p className="bes__note">Tüm fonların payları aynı oranda ölçeklenir; ödenen katkı toplamı değişmez. Fon bazında doğru dağılım için pay adetlerini fon fon girmek daha isabetlidir.</p>
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
