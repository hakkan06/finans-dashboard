import { useEffect, useState } from "react";
import Sheet from "../components/Sheet.jsx";
import Icon from "../components/Icon.jsx";
import { confirmDialog, toast } from "../components/feedback.jsx";
import { api } from "../lib/api.js";
import { TYPE_LABEL, fmtDate, money, parseServerTime, ago, pct, qty as fmtQty } from "../lib/format.js";
import { useData } from "../lib/store.jsx";
import { useSheets } from "../lib/sheets.jsx";

function Stat({ label, value, tone }) {
  return (
    <div className="kv">
      <dt>{label}</dt>
      <dd className={tone ? `tone-${tone}` : ""}>{value}</dd>
    </div>
  );
}

export default function AssetSheet({ assetId, onClose }) {
  const { items, reload } = useData();
  const { open } = useSheets();
  const asset = items.find((i) => i.asset_id === assetId);
  const [txns, setTxns] = useState(null);

  const loadTxns = () => api.transactions(assetId).then(setTxns).catch((e) => toast(e.message, { tone: "bad" }));
  useEffect(() => {
    loadTxns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetId, items]);

  if (!asset) return null;
  const cur = asset.currency;
  const pl = asset.value_try - asset.cost_try;
  const plPct = asset.cost_try > 0 ? (pl / asset.cost_try) * 100 : null;
  const dayPct = asset.previous_price ? ((asset.current_price - asset.previous_price) / asset.previous_price) * 100 : null;
  const updated = parseServerTime(asset.last_updated);
  const tone = (v) => (v > 0 ? "good" : v < 0 ? "bad" : undefined);

  async function removeTxn(t) {
    const ok = await confirmDialog({
      title: "İşlemi sil?",
      body: `${fmtDate(t.transaction_date)} tarihli ${t.quantity > 0 ? "alış" : "satış"} kaydı silinecek.`,
      confirmLabel: "Sil",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteTransaction(t.id);
      await reload();
      toast("İşlem silindi", { tone: "good" });
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  async function removeAsset() {
    const n = txns?.length ?? 0;
    const ok = await confirmDialog({
      title: `${asset.symbol} silinsin mi?`,
      body: `Varlık ve ${n} işlem kaydı kalıcı olarak silinir. Bu işlem geri alınamaz.`,
      confirmLabel: "Varlığı sil",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteAsset(asset.asset_id);
      await reload();
      toast(`${asset.symbol} silindi`, { tone: "good" });
      onClose();
    } catch (e) {
      toast(e.message, { tone: "bad" });
    }
  }

  return (
    <Sheet
      title={asset.symbol}
      subtitle={`${asset.name !== asset.symbol ? asset.name + " · " : ""}${TYPE_LABEL[asset.asset_type]}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn--danger-ghost" onClick={removeAsset}>
            <Icon name="trash" size={18} /> Varlığı sil
          </button>
          <button className="btn btn--primary" onClick={() => open("txn", { assetId: asset.asset_id })}>
            <Icon name="plus" size={18} /> Alım / satım ekle
          </button>
        </>
      }
    >
      <div className="asset-price">
        <div>
          <div className="asset-price__now">{asset.has_price ? money(asset.current_price, { decimals: 2, currency: cur }) : "Fiyat yok"}</div>
          {dayPct !== null && <div className={`asset-price__day tone-${tone(dayPct)}`}>{pct(dayPct)} son güncellemeye göre</div>}
        </div>
        <div className="asset-price__time">{updated ? `${ago(updated)} güncellendi` : "Henüz güncellenmedi"}</div>
      </div>

      {!asset.has_price && (
        <div className="callout callout--warn">
          <p>Bu varlık için piyasa fiyatı alınamadı. Sembolün doğru olduğundan emin ol, sonra fiyatları güncelle.</p>
        </div>
      )}

      <dl className="kv-grid">
        <Stat label="Değer" value={money(asset.value_try)} />
        <Stat label="Maliyet" value={money(asset.cost_try)} />
        <Stat label="Kâr / zarar" value={`${money(pl, { sign: true })}${plPct !== null ? ` (${pct(plPct)})` : ""}`} tone={tone(pl)} />
        <Stat label="Miktar" value={fmtQty(asset.total_qty)} />
        {asset.total_tax > 0 && <Stat label="Kesilen stopaj" value={money(asset.total_tax * asset.fx)} />}
        {Math.abs(asset.realized_pl) > 0.005 && <Stat label="Satıştan gerçekleşen" value={money(asset.realized_pl * asset.fx, { sign: true })} tone={tone(asset.realized_pl)} />}
      </dl>

      <h3 className="sheet__section">İşlem geçmişi</h3>
      {txns === null ? (
        <p className="muted">Yükleniyor…</p>
      ) : txns.length === 0 ? (
        <p className="muted">Bu varlık için henüz işlem yok.</p>
      ) : (
        <ul className="rows">
          {txns.map((t) => (
            <li key={t.id} className="row-line">
              <div className="row-line__main">
                <span className={`tag tag--${t.quantity > 0 ? "good" : "bad"}`}>{t.quantity > 0 ? "Alış" : "Satış"}</span>
                <div>
                  <div className="row-line__title">
                    {fmtQty(Math.abs(t.quantity))} × {money(t.unit_price, { decimals: 2, currency: cur })}
                  </div>
                  <div className="row-line__sub">{fmtDate(t.transaction_date, { day: "numeric", month: "long", year: "numeric" })}</div>
                </div>
              </div>
              <div className="row-line__end">
                <strong>{money(Math.abs(t.quantity) * t.unit_price, { decimals: 2, currency: cur })}</strong>
                <button className="icon-btn" aria-label="Düzenle" onClick={() => open("txn", { txn: t })}>
                  <Icon name="edit" size={18} />
                </button>
                <button className="icon-btn icon-btn--danger" aria-label="Sil" onClick={() => removeTxn(t)}>
                  <Icon name="trash" size={18} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Sheet>
  );
}
