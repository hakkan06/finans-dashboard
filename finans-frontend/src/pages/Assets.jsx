import { useMemo, useState } from "react";
import Icon from "../components/Icon.jsx";
import { Segmented } from "../components/controls.jsx";
import { TYPE_COLOR, TYPE_LABEL, TYPES, money, pct, qty as fmtQty } from "../lib/format.js";
import { useSheets } from "../lib/sheets.jsx";
import { useData } from "../lib/store.jsx";

const SORTS = [
  { value: "value", label: "Değer" },
  { value: "day", label: "Günlük" },
  { value: "pl", label: "Kâr/zarar" },
  { value: "name", label: "Ad" },
];

const plOf = (i) => i.value_try - i.cost_try;
const dayPct = (i) => (i.previous_price ? ((i.current_price - i.previous_price) / i.previous_price) * 100 : null);
const tone = (v) => (v > 0 ? "good" : v < 0 ? "bad" : "calm");

function AssetRow({ item, onOpen }) {
  const pl = plOf(item);
  const plPct = item.cost_try > 0 ? (pl / item.cost_try) * 100 : null;
  const d = dayPct(item);
  return (
    <li>
      <button className="arow" onClick={onOpen}>
        <span className="arow__badge" style={{ "--badge": TYPE_COLOR[item.asset_type] }} aria-hidden="true">
          {item.symbol.slice(0, 3)}
        </span>
        <span className="arow__name">
          <strong>{item.symbol}</strong>
          <small>{item.name !== item.symbol ? item.name : TYPE_LABEL[item.asset_type]}</small>
        </span>
        <span className="arow__qty">
          <span>{fmtQty(item.total_qty)}</span>
          <small>{item.has_price ? money(item.current_price, { decimals: 2, currency: item.currency }) : "Fiyat yok"}</small>
        </span>
        <span className="arow__value">
          <strong>{money(item.value_try)}</strong>
          <small className={`tone-${tone(pl)}`}>
            {money(pl, { sign: true })}
            {plPct !== null && ` · ${pct(plPct)}`}
          </small>
        </span>
        <span className={`arow__day tone-${d === null ? "calm" : tone(d)}`}>{d === null ? "–" : pct(d)}</span>
        <Icon name="chevron" size={18} className="arow__go" />
      </button>
    </li>
  );
}

export default function Assets() {
  const { holdings, empty, overview: ov } = useData();
  const { open } = useSheets();
  const [type, setType] = useState("ALL");
  const [sort, setSort] = useState("value");
  const [query, setQuery] = useState("");
  const [showEmpty, setShowEmpty] = useState(false);

  const counts = useMemo(() => {
    const c = { ALL: holdings.length };
    holdings.forEach((h) => (c[h.asset_type] = (c[h.asset_type] || 0) + 1));
    return c;
  }, [holdings]);

  const list = useMemo(() => {
    const q = query.trim().toLowerCase();
    const l = holdings.filter((h) => (type === "ALL" || h.asset_type === type) && (!q || h.symbol.toLowerCase().includes(q) || h.name.toLowerCase().includes(q)));
    const by = {
      value: (a, b) => b.value_try - a.value_try,
      day: (a, b) => (dayPct(b) ?? -Infinity) - (dayPct(a) ?? -Infinity),
      pl: (a, b) => plOf(b) - plOf(a),
      name: (a, b) => a.symbol.localeCompare(b.symbol, "tr"),
    }[sort];
    return [...l].sort(by);
  }, [holdings, type, sort, query]);

  const totalCost = holdings.reduce((a, h) => a + h.cost_try, 0);
  const totalPl = ov.total_assets - totalCost;

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Varlıklar</h1>
          <p className="page__sub">
            {money(ov.total_assets)} · <span className={`tone-${tone(totalPl)}`}>{money(totalPl, { sign: true })} kâr/zarar</span>
          </p>
        </div>
        <button className="btn btn--primary" onClick={() => open("add", {})}>
          <Icon name="plus" size={18} /> Ekle
        </button>
      </header>

      {holdings.length === 0 && empty.length === 0 ? (
        <div className="empty">
          <h2>Henüz varlık yok</h2>
          <p>Hisse, fon, altın veya döviz ekleyerek başla.</p>
          <button className="btn btn--primary" onClick={() => open("txn", { startNew: true })}>
            <Icon name="plus" size={18} /> İlk varlığını ekle
          </button>
        </div>
      ) : (
        <>
          <div className="toolbar">
            <div className="chips chips--scroll" role="group" aria-label="Tür filtresi">
              {["ALL", ...TYPES.filter((t) => counts[t])].map((t) => (
                <button key={t} className={`chip ${type === t ? "is-on" : ""}`} onClick={() => setType(t)}>
                  {t === "ALL" ? "Tümü" : TYPE_LABEL[t]} <span className="chip__n">{counts[t] ?? 0}</span>
                </button>
              ))}
            </div>
            <div className="toolbar__right">
              <label className="search">
                <Icon name="search" size={18} />
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ara" aria-label="Varlık ara" />
              </label>
              <Segmented label="Sırala" size="sm" value={sort} onChange={setSort} options={SORTS} />
            </div>
          </div>

          <div className="list-head" aria-hidden="true">
            <span />
            <span>Varlık</span>
            <span>Miktar · fiyat</span>
            <span>Değer · kâr/zarar</span>
            <span>Günlük</span>
            <span />
          </div>
          {list.length === 0 ? (
            <p className="muted panel__empty">Bu filtreyle eşleşen varlık yok.</p>
          ) : (
            <ul className="alist">
              {list.map((i) => (
                <AssetRow key={i.asset_id} item={i} onOpen={() => open("asset", { assetId: i.asset_id })} />
              ))}
            </ul>
          )}

          {empty.length > 0 && (
            <div className="empties">
              <button className="link-btn" onClick={() => setShowEmpty(!showEmpty)} aria-expanded={showEmpty}>
                Pozisyonu olmayan {empty.length} varlık <Icon name={showEmpty ? "chevronDown" : "chevron"} size={16} />
              </button>
              {showEmpty && (
                <ul className="alist alist--muted">
                  {empty.map((i) => (
                    <li key={i.asset_id}>
                      <button className="arow arow--simple" onClick={() => open("asset", { assetId: i.asset_id })}>
                        <span className="arow__badge" style={{ "--badge": TYPE_COLOR[i.asset_type] }} aria-hidden="true">
                          {i.symbol.slice(0, 3)}
                        </span>
                        <span className="arow__name">
                          <strong>{i.symbol}</strong>
                          <small>{i.name !== i.symbol ? i.name : TYPE_LABEL[i.asset_type]}</small>
                        </span>
                        <Icon name="chevron" size={18} className="arow__go" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
