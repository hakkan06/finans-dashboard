import { useEffect, useRef } from "react";
import Icon from "./Icon.jsx";

/** Masaüstünde sağdan açılan panel, telefonda alttan açılan sayfa. */
export default function Sheet({ title, subtitle, onClose, children, footer, wide = false }) {
  const ref = useRef(null);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    // İlk girilebilir alana odaklan
    const t = setTimeout(() => ref.current?.querySelector("[data-autofocus], input:not([type=hidden]), select")?.focus({ preventScroll: true }), 60);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
      clearTimeout(t);
    };
  }, [onClose]);

  return (
    <div className="sheet-scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <section ref={ref} className={`sheet ${wide ? "sheet--wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <header className="sheet__head">
          <div className="sheet__titles">
            <h2 className="sheet__title">{title}</h2>
            {subtitle && <p className="sheet__sub">{subtitle}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Kapat">
            <Icon name="x" />
          </button>
        </header>
        <div className="sheet__body">{children}</div>
        {footer && <footer className="sheet__foot">{footer}</footer>}
      </section>
    </div>
  );
}
