import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

const Ctx = createContext(null);
export const useSheets = () => useContext(Ctx);

/** Üst üste açılabilen panel yığını. registry: { tip: Bileşen } */
export function SheetProvider({ registry, children }) {
  const [stack, setStack] = useState([]);
  const idRef = useRef(0);
  const open = useCallback((type, props = {}) => setStack((s) => [...s, { id: ++idRef.current, type, props }]), []);
  const close = useCallback(() => setStack((s) => s.slice(0, -1)), []);
  const closeAll = useCallback(() => setStack([]), []);
  const api = useMemo(() => ({ open, close, closeAll }), [open, close, closeAll]);
  return (
    <Ctx.Provider value={api}>
      {children}
      {stack.map((s, i) => {
        const C = registry[s.type];
        return C ? <C key={s.id} {...s.props} onClose={i === stack.length - 1 ? close : () => {}} /> : null;
      })}
    </Ctx.Provider>
  );
}
