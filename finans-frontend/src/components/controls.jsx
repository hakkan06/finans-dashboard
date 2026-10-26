import { useId } from "react";

export function Field({ label, hint, error, children, className = "" }) {
  const id = useId();
  return (
    <div className={`field ${error ? "field--error" : ""} ${className}`}>
      {label && (
        <label className="field__label" htmlFor={id}>
          {label}
        </label>
      )}
      {typeof children === "function" ? children(id) : children}
      {error ? <p className="field__msg field__msg--error">{error}</p> : hint ? <p className="field__msg">{hint}</p> : null}
    </div>
  );
}

/** Birden fazla seçenekten birini seçtiren segment düğmesi. */
export function Segmented({ value, onChange, options, label, size = "md" }) {
  return (
    <div className={`seg seg--${size}`} role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={`seg__opt ${value === o.value ? "is-on" : ""} ${o.tone ? `seg__opt--${o.tone}` : ""}`}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Sayısal alan: virgül/nokta fark etmeden sayı alır. */
export function parseNum(s) {
  if (typeof s === "number") return s;
  if (s === null || s === undefined || s === "") return NaN;
  let t = String(s).trim().replace(/\s/g, "");
  if (t.includes(",") && t.includes(".")) t = t.replace(/\./g, "").replace(",", ".");
  else if (t.includes(",")) t = t.replace(",", ".");
  return Number(t);
}

export function NumberInput({ value, onChange, id, placeholder, prefix, suffix, ...rest }) {
  return (
    <div className="input-wrap">
      {prefix && <span className="input-wrap__affix">{prefix}</span>}
      <input
        id={id}
        className="input input--num"
        inputMode="decimal"
        autoComplete="off"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        {...rest}
      />
      {suffix && <span className="input-wrap__affix input-wrap__affix--end">{suffix}</span>}
    </div>
  );
}
