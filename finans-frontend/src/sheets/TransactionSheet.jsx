import { useMemo, useState } from "react";
import Sheet from "../components/Sheet.jsx";
import { Field, NumberInput, Segmented, parseNum } from "../components/controls.jsx";
import { toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { TYPES, TYPE_HINT, TYPE_LABEL, money, plain2, qty as fmtQty, todayStr } from "../lib/format.js";
import { useData } from "../lib/store.jsx";

const NEW = "__new__";

/** Alım/satım ekleme ve düzenleme. Yeni varlık da aynı formdan tanımlanır. */
export default function TransactionSheet({ assetId = null, startNew = false, txn = null, onClose }) {
  const { items, reload } = useData();
  const editing = !!txn;

  const [sel, setSel] = useState(editing ? String(txn.asset_id) : startNew ? NEW : assetId ? String(assetId) : "");
  const [side, setSide] = useState(editing && txn.quantity < 0 ? "sell" : "buy");
  const [amount, setAmount] = useState(editing ? String(Math.abs(txn.quantity)).replace(".", ",") : "");
  const [price, setPrice] = useState(editing ? String(txn.unit_price).replace(".", ",") : "");
  const [priceTouched, setPriceTouched] = useState(editing);
  const [date, setDate] = useState(editing ? txn.transaction_date : todayStr());
  const [newType, setNewType] = useState("US_STOCK");
  const [newSym, setNewSym] = useState("");
  const [newName, setNewName] = useState("");
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [noPrice, setNoPrice] = useState(false);
  const [busy, setBusy] = useState(false);

  const isNew = sel === NEW;
  const asset = useMemo(() => items.find((i) => String(i.asset_id) === sel), [items, sel]);
  const type = isNew ? newType : asset?.asset_type;
  const currency = type === "US_STOCK" ? "USD" : "TRY";
  const sym = currency === "USD" ? "$" : "₺";

  const pickAsset = (v) => {
    setSel(v);
    setErrors({});
    setFormError("");
    if (v === NEW) {
      setSide("buy");
      if (!priceTouched) setPrice("");
      return;
    }
    const a = items.find((i) => String(i.asset_id) === v);
    if (a && !priceTouched && a.current_price) setPrice(String(a.current_price).replace(".", ","));
    if (a && !a.has_position) setSide("buy");
  };

  const q = parseNum(amount);
  const p = parseNum(price);
  const total = q > 0 && p > 0 ? q * p : null;
  const holding = asset?.total_qty ?? 0;

  function validate() {
    const e = {};
    if (!sel) e.asset = "Bir varlık seç veya yeni bir tane tanımla.";
    if (isNew && !newSym.trim()) e.sym = "Sembol gerekli.";
    if (!(q > 0)) e.amount = "Sıfırdan büyük bir miktar gir.";
    if (!(p > 0)) e.price = "Sıfırdan büyük bir fiyat gir.";
    if (!date) e.date = "Tarih seç.";
    if (side === "sell" && asset && q > holding + 1e-9) e.amount = `Elinde ${fmtQty(holding)} var.`;
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function submit({ skipPriceCheck = false, again = false } = {}) {
    setFormError("");
    setNoPrice(false);
    if (!validate()) return;
    setBusy(true);
    let createdId = null;
    try {
      let targetId = asset?.asset_id;
      if (isNew) {
        const created = await api.createAsset({ asset_type: newType, symbol: newSym.trim(), name: newName.trim() });
        createdId = created.id;
        if (created.current_price == null && !skipPriceCheck) {
          await api.deleteAsset(created.id);
          createdId = null;
          setNoPrice(true);
          setErrors({ sym: "Bu sembol için piyasa fiyatı bulunamadı." });
          return;
        }
        targetId = created.id;
      }
      const body = { quantity: side === "buy" ? q : -q, unit_price: p, transaction_date: date };
      if (editing) await api.updateTransaction(txn.id, body);
      else await api.createTransaction({ asset_id: targetId, ...body });
      await reload();
      toast(editing ? "İşlem güncellendi" : side === "buy" ? "Alış kaydedildi" : "Satış kaydedildi", { tone: "good" });
      if (again) {
        setAmount("");
        setCreatedReset(targetId);
      } else onClose();
    } catch (err) {
      if (createdId) {
        try {
          await api.deleteAsset(createdId);
        } catch {
          /* yarım kalan varlık sonra silinebilir */
        }
      }
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // "Kaydet ve yenisini ekle" sonrası: yeni varlık artık listede, onu seçili bırak
  function setCreatedReset(targetId) {
    setSel(String(targetId));
    setNewSym("");
    setNewName("");
  }

  const symbolFor = (i) => `${i.symbol} · ${i.name}`;
  const sorted = [...items].sort((a, b) => a.symbol.localeCompare(b.symbol, "tr"));

  return (
    <Sheet
      title={editing ? "İşlemi düzenle" : isNew ? "Yeni varlık al" : "Alım / satım ekle"}
      subtitle={editing && asset ? symbolFor(asset) : undefined}
      onClose={onClose}
      footer={
        <>
          {!editing && (
            <button className="btn btn--ghost" onClick={() => submit({ again: true })} disabled={busy}>
              Kaydet, yenisini ekle
            </button>
          )}
          <button className="btn btn--primary" onClick={() => submit()} disabled={busy}>
            {busy ? "Kaydediliyor…" : editing ? "Değişikliği kaydet" : side === "buy" ? "Alışı kaydet" : "Satışı kaydet"}
          </button>
        </>
      }
    >
      <form className="form" onSubmit={(e) => (e.preventDefault(), submit())}>
        {!editing && (
          <Field label="Varlık" error={errors.asset}>
            {(id) => (
              <select id={id} className="input" value={sel} onChange={(e) => pickAsset(e.target.value)} data-autofocus>
                <option value="">Seç…</option>
                {sorted.map((i) => (
                  <option key={i.asset_id} value={i.asset_id}>
                    {symbolFor(i)}
                  </option>
                ))}
                <option value={NEW}>＋ Yeni varlık tanımla…</option>
              </select>
            )}
          </Field>
        )}

        {isNew && (
          <div className="form__group">
            <Field label="Varlık türü">
              {() => (
                <div className="chips">
                  {TYPES.map((t) => (
                    <button
                      key={t}
                      type="button"
                      className={`chip ${newType === t ? "is-on" : ""}`}
                      onClick={() => {
                        setNewType(t);
                        setNoPrice(false);
                        setErrors({});
                      }}
                    >
                      {TYPE_LABEL[t]}
                    </button>
                  ))}
                </div>
              )}
            </Field>
            <div className="form__row">
              <Field label="Sembol / kod" hint={TYPE_HINT[newType]} error={errors.sym}>
                {(id) => <input id={id} className="input" value={newSym} onChange={(e) => setNewSym(e.target.value)} autoCapitalize="characters" spellCheck="false" data-autofocus />}
              </Field>
              <Field label="Ad (isteğe bağlı)">
                {(id) => <input id={id} className="input" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Boşsa sembol kullanılır" />}
              </Field>
            </div>
            {noPrice && (
              <div className="callout callout--warn">
                <p>Sembolü kontrol et. İnternet sorunu olabilir; yine de ekleyebilirsin, fiyat sonraki güncellemede gelir.</p>
                <button type="button" className="btn btn--small btn--ghost" onClick={() => submit({ skipPriceCheck: true })}>
                  Fiyatsız ekle
                </button>
              </div>
            )}
          </div>
        )}

        {!isNew && asset && !editing && (
          <p className="form__note">
            Elinde <b>{fmtQty(holding)}</b> var · güncel fiyat <b>{asset.has_price ? money(asset.current_price, { decimals: 2, currency }) : "yok"}</b>
          </p>
        )}

        {!isNew && (
          <Field label="İşlem yönü">
            {() => (
              <Segmented
                label="İşlem yönü"
                value={side}
                onChange={setSide}
                options={[
                  { value: "buy", label: "Alış", tone: "good" },
                  { value: "sell", label: "Satış", tone: "bad" },
                ]}
              />
            )}
          </Field>
        )}

        <div className="form__row">
          <Field label={type === "FIAT" ? "Tutar" : "Miktar"} error={errors.amount}>
            {(id) => (
              <>
                <NumberInput id={id} value={amount} onChange={setAmount} placeholder="0" />
                {side === "sell" && holding > 0 && (
                  <button type="button" className="linkish" onClick={() => setAmount(String(holding).replace(".", ","))}>
                    Tümünü sat ({fmtQty(holding)})
                  </button>
                )}
              </>
            )}
          </Field>
          <Field label={side === "buy" ? "Birim alış fiyatı" : "Birim satış fiyatı"} error={errors.price} hint={type === "FIAT" && currency === "TRY" ? "TL için 1 gir" : undefined}>
            {(id) => (
              <NumberInput
                id={id}
                value={price}
                prefix={sym}
                onChange={(v) => {
                  setPrice(v);
                  setPriceTouched(true);
                }}
                placeholder="0,00"
              />
            )}
          </Field>
        </div>

        <Field label="İşlem tarihi" error={errors.date}>
          {(id) => <input id={id} type="date" className="input" value={date} max={todayStr()} onChange={(e) => setDate(e.target.value)} />}
        </Field>

        <div className="summary-box" aria-live="polite">
          <span>Toplam tutar</span>
          <strong>{total ? money(total, { decimals: 2, currency }) : "–"}</strong>
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
