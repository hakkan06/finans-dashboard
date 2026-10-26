import { useEffect, useState } from "react";
import Icon from "./components/Icon.jsx";
import { ConfirmHost, ToastHost } from "./components/feedback.jsx";
import { DataProvider, useData } from "./lib/store.jsx";
import { SheetProvider, useSheets } from "./lib/sheets.jsx";
import { ago } from "./lib/format.js";
import Overview from "./pages/Overview.jsx";
import Assets from "./pages/Assets.jsx";
import Debts from "./pages/Debts.jsx";
import Growth from "./pages/Growth.jsx";
import AddMenu from "./sheets/AddMenu.jsx";
import TransactionSheet from "./sheets/TransactionSheet.jsx";
import AssetSheet from "./sheets/AssetSheet.jsx";
import DebtSheet from "./sheets/DebtSheet.jsx";
import DebtDetailSheet from "./sheets/DebtDetailSheet.jsx";

const PAGES = [
  { id: "overview", label: "Özet", icon: "home" },
  { id: "assets", label: "Varlıklar", icon: "wallet" },
  { id: "debts", label: "Borçlar", icon: "card" },
  { id: "growth", label: "Günlük takip", short: "Takip", icon: "chart" },
];
const REGISTRY = { add: AddMenu, txn: TransactionSheet, asset: AssetSheet, debt: DebtSheet, debtDetail: DebtDetailSheet };

function usePage() {
  const read = () => {
    const h = window.location.hash.replace("#/", "").replace("#", "");
    return PAGES.some((p) => p.id === h) ? h : "overview";
  };
  const [page, setPage] = useState(read);
  useEffect(() => {
    const on = () => setPage(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const go = (id) => {
    window.location.hash = `#/${id}`;
    window.scrollTo({ top: 0 });
  };
  return [page, go];
}

function RefreshButton({ compact = false }) {
  const { refreshPrices, refreshing, priceTime } = useData();
  return (
    <button className={`refresh ${compact ? "refresh--compact" : ""}`} onClick={refreshPrices} disabled={refreshing} aria-label="Fiyatları güncelle">
      <Icon name="refresh" size={18} className={refreshing ? "spin" : ""} />
      <span className="refresh__text">
        <strong>{refreshing ? "Güncelleniyor…" : "Fiyatları güncelle"}</strong>
        {!compact && <small>{priceTime ? `Son: ${ago(priceTime)}` : "Henüz güncellenmedi"}</small>}
      </span>
    </button>
  );
}

function Shell() {
  const { ready, error, reload, overview, priceTime } = useData();
  const { open } = useSheets();
  const [page, go] = usePage();

  if (!ready) {
    return (
      <div className="boot">
        {error ? (
          <div className="boot__box">
            <h1>Sunucuya ulaşılamadı</h1>
            <p>{error}</p>
            <button className="btn btn--primary" onClick={reload}>
              Tekrar dene
            </button>
          </div>
        ) : (
          <div className="boot__box" role="status">
            <div className="boot__dot" />
            <p>Yükleniyor…</p>
          </div>
        )}
      </div>
    );
  }

  const Page = { overview: Overview, assets: Assets, debts: Debts, growth: Growth }[page];
  const alerts = overview.overdue_count;

  return (
    <div className="app">
      <aside className="rail" aria-label="Ana menü">
        <div className="rail__brand">
          <span className="logo" aria-hidden="true">
            <Icon name="trendUp" size={20} stroke={2.4} />
          </span>
          <span>Finans</span>
        </div>
        <nav className="rail__nav">
          {PAGES.map((p) => (
            <a key={p.id} href={`#/${p.id}`} className={`nav-item ${page === p.id ? "is-on" : ""}`} aria-current={page === p.id ? "page" : undefined}>
              <Icon name={p.icon} />
              <span>{p.label}</span>
              {p.id === "debts" && alerts > 0 && <b className="badge">{alerts}</b>}
            </a>
          ))}
        </nav>
        <div className="rail__foot">
          <button className="btn btn--primary btn--block" onClick={() => open("add", {})}>
            <Icon name="plus" size={18} /> Ekle
          </button>
          <RefreshButton />
        </div>
      </aside>

      <header className="topbar">
        <div className="rail__brand">
          <span className="logo" aria-hidden="true">
            <Icon name="trendUp" size={18} stroke={2.4} />
          </span>
          <span>{PAGES.find((p) => p.id === page).label}</span>
        </div>
        <div className="topbar__right">
          <span className="topbar__time">{priceTime ? ago(priceTime) : ""}</span>
          <RefreshButton compact />
        </div>
      </header>

      <main className="main" id="main">
        <Page go={go} />
      </main>

      <nav className="tabbar" aria-label="Ana menü">
        {PAGES.slice(0, 2).map((p) => (
          <a key={p.id} href={`#/${p.id}`} className={`tab ${page === p.id ? "is-on" : ""}`} aria-current={page === p.id ? "page" : undefined}>
            <Icon name={p.icon} size={22} />
            <span>{p.short || p.label}</span>
          </a>
        ))}
        <button className="fab" onClick={() => open("add", {})} aria-label="Ekle">
          <Icon name="plus" size={26} stroke={2.4} />
        </button>
        {PAGES.slice(2).map((p) => (
          <a key={p.id} href={`#/${p.id}`} className={`tab ${page === p.id ? "is-on" : ""}`} aria-current={page === p.id ? "page" : undefined}>
            <span className="tab__ico">
              <Icon name={p.icon} size={22} />
              {p.id === "debts" && alerts > 0 && <b className="badge badge--dot" />}
            </span>
            <span>{p.short || p.label}</span>
          </a>
        ))}
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <DataProvider>
      <SheetProvider registry={REGISTRY}>
        <Shell />
        <ConfirmHost />
        <ToastHost />
      </SheetProvider>
    </DataProvider>
  );
}
