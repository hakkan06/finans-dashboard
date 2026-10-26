import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api.js";
import { parseServerTime, todayStr } from "./format.js";
import { toast } from "../components/feedback.jsx";

const Ctx = createContext(null);
export const useData = () => useContext(Ctx);

export function DataProvider({ children }) {
  const [state, setState] = useState({ ready: false, error: null });
  const [data, setData] = useState({ overview: null, items: [], debts: [], groups: [], history: [] });
  const [refreshing, setRefreshing] = useState(false);
  const alive = useRef(true);

  const load = useCallback(async () => {
    try {
      const [overview, items, debts, groups, history] = await Promise.all([
        api.overview(),
        api.summary(),
        api.debts(),
        api.groups(),
        api.history(),
      ]);
      if (!alive.current) return;
      setData({ overview, items, debts, groups, history });
      setState({ ready: true, error: null });
    } catch (e) {
      if (!alive.current) return;
      setState((s) => ({ ready: s.ready, error: e.message }));
      if (state.ready) toast(e.message, { tone: "bad" });
    }
  }, [state.ready]);

  useEffect(() => {
    alive.current = true;
    load();
    return () => {
      alive.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Fiyatları sunucuda güncelle, sonra her şeyi yeniden yükle. */
  const refreshPrices = useCallback(async () => {
    setRefreshing(true);
    try {
      const r = await api.updatePrices();
      await load();
      if (r.failed?.length) {
        toast(`${r.updated} fiyat güncellendi. Alınamayanlar: ${r.failed.join(", ")}`, { tone: "warn", ms: 7000 });
      } else {
        toast(`${r.updated} fiyat güncellendi`, { tone: "good" });
      }
    } catch (e) {
      toast(e.message, { tone: e.status === 429 ? "warn" : "bad" });
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  /** Taksiti ödendi/ödenmedi olarak çevirir; arayüzü hemen günceller, hata olursa geri alır. */
  const toggleInstallment = useCallback(
    async (inst, label) => {
      const flip = (list) =>
        list.map((d) => ({ ...d, installments: d.installments.map((i) => (i.id === inst.id ? { ...i, is_paid: !i.is_paid } : i)) }));
      setData((d) => ({ ...d, debts: flip(d.debts) }));
      try {
        const r = await api.toggleInstallment(inst.id);
        await load();
        toast(r.is_paid ? `${label} ödendi olarak işaretlendi` : `${label} ödenmedi olarak işaretlendi`, {
          tone: "good",
          undo: () => toggleInstallment({ ...inst, is_paid: r.is_paid }, label),
        });
      } catch (e) {
        await load();
        toast(e.message, { tone: "bad" });
      }
    },
    [load]
  );

  const derived = useMemo(() => {
    const holdings = data.items.filter((i) => i.has_position);
    const empty = data.items.filter((i) => !i.has_position);
    const priceTime = parseServerTime(data.overview?.last_price_update);
    return { holdings, empty, priceTime };
  }, [data]);

  /** Geçmiş + bugünün canlı değeri (gece kaydı henüz yoksa da grafik güncel görünür). */
  const series = useMemo(() => {
    if (!data.overview) return [];
    const today = todayStr();
    const pts = data.history.map((h) => ({
      date: h.record_date,
      assets: h.total_assets,
      debts: h.total_debts,
      net: h.net_worth,
    }));
    const live = {
      date: today,
      assets: data.overview.total_assets,
      debts: data.overview.total_debts,
      net: data.overview.net_worth,
      live: true,
    };
    const last = pts[pts.length - 1];
    if (last && last.date === today) pts[pts.length - 1] = { ...live, saved: true };
    else if (!last || last.date < today) pts.push(live);
    return pts;
  }, [data]);

  const value = {
    ...data,
    ...derived,
    series,
    ...state,
    refreshing,
    reload: load,
    refreshPrices,
    toggleInstallment,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
