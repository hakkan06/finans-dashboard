import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";

// ── Toast ────────────────────────────────────────────────────────────
let toastListener = null;
let nextId = 1;

/** toast("Kaydedildi", { tone: "good" | "warn" | "bad", undo: fn, ms }) */
export function toast(message, opts = {}) {
  toastListener?.({ id: nextId++, message, tone: "neutral", ms: opts.undo ? 6000 : 3800, ...opts });
}

export function ToastHost() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    toastListener = (t) => {
      setItems((cur) => [...cur.slice(-2), t]);
      setTimeout(() => setItems((cur) => cur.filter((x) => x.id !== t.id)), t.ms);
    };
    return () => {
      toastListener = null;
    };
  }, []);
  const dismiss = (id) => setItems((cur) => cur.filter((x) => x.id !== id));
  return (
    <div className="toasts" role="status" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className={`toast toast--${t.tone}`}>
          <span className="toast__msg">{t.message}</span>
          {t.undo && (
            <button
              className="toast__undo"
              onClick={() => {
                dismiss(t.id);
                t.undo();
              }}
            >
              Geri al
            </button>
          )}
          <button className="toast__x" onClick={() => dismiss(t.id)} aria-label="Kapat">
            <Icon name="x" size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Onay penceresi ───────────────────────────────────────────────────
let confirmListener = null;

/** await confirmDialog({ title, body, confirmLabel, danger }) → true/false */
export function confirmDialog(opts) {
  return new Promise((resolve) => {
    if (!confirmListener) return resolve(false);
    confirmListener({ ...opts, resolve });
  });
}

export function ConfirmHost() {
  const [req, setReq] = useState(null);
  const okRef = useRef(null);
  useEffect(() => {
    confirmListener = setReq;
    return () => {
      confirmListener = null;
    };
  }, []);
  useEffect(() => {
    if (req) okRef.current?.focus();
  }, [req]);
  useEffect(() => {
    if (!req) return;
    const onKey = (e) => e.key === "Escape" && done(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  const done = (v) => {
    req.resolve(v);
    setReq(null);
  };
  if (!req) return null;
  return (
    <div className="modal-scrim" onMouseDown={(e) => e.target === e.currentTarget && done(false)}>
      <div className="modal" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title">
        <h2 id="confirm-title" className="modal__title">
          {req.title}
        </h2>
        {req.body && <p className="modal__body">{req.body}</p>}
        <div className="modal__actions">
          <button className="btn btn--ghost" onClick={() => done(false)}>
            Vazgeç
          </button>
          <button ref={okRef} className={`btn ${req.danger ? "btn--danger" : "btn--primary"}`} onClick={() => done(true)}>
            {req.confirmLabel || "Onayla"}
          </button>
        </div>
      </div>
    </div>
  );
}
