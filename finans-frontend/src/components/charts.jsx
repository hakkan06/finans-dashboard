import { useEffect, useMemo, useRef, useState } from "react";
import { fmtDate, fmtDateLong, moneyCompact, money, parseDate } from "../lib/format.js";

function useWidth() {
  const ref = useRef(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

/** "Güzel" y ekseni adımları */
function niceTicks(min, max, count = 4) {
  if (min === max) {
    const pad = Math.abs(min) * 0.05 || 1;
    min -= pad;
    max += pad;
  }
  const span = max - min;
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(v);
  return { ticks, lo, hi };
}

/**
 * Zaman serisi alan/çizgi grafiği.
 * series: [{ key, label, color, dash?, area?, points: [{ date, v }] }]
 * Dokunarak/üzerine gelerek gezinilebilir; onScrub(date | null, valuesByKey) üst bileşeni bilgilendirir.
 */
export function TimeChart({ series, height = 240, onScrub, ariaLabel }) {
  const [ref, width] = useWidth();
  const [hover, setHover] = useState(null);

  const model = useMemo(() => {
    const all = series.flatMap((s) => s.points);
    if (!all.length) return null;
    const times = all.map((p) => parseDate(p.date).getTime());
    const t0 = Math.min(...times);
    const t1 = Math.max(...times);
    const vals = all.map((p) => p.v);
    const { ticks, lo, hi } = niceTicks(Math.min(...vals), Math.max(...vals), 4);
    return { t0, t1: t1 === t0 ? t0 + 86400000 : t1, ticks, lo, hi };
  }, [series]);

  if (!model) return <div ref={ref} className="chart chart--empty" style={{ height }} />;

  const padL = 4;
  const padR = 4;
  const padT = 10;
  const padB = 26;
  const W = Math.max(width, 10);
  const innerW = W - padL - padR;
  const innerH = height - padT - padB;
  const x = (date) => padL + ((parseDate(date).getTime() - model.t0) / (model.t1 - model.t0)) * innerW;
  const y = (v) => padT + (1 - (v - model.lo) / (model.hi - model.lo)) * innerH;

  const primary = series[0];
  const single = primary.points.length === 1;

  const paths = series.map((s) => {
    const pts = s.points.map((p) => [x(p.date), y(p.v)]);
    const line = pts.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)} ${py.toFixed(1)}`).join(" ");
    const area = s.area && pts.length > 1 ? `${line} L${pts[pts.length - 1][0].toFixed(1)} ${padT + innerH} L${pts[0][0].toFixed(1)} ${padT + innerH} Z` : null;
    return { s, pts, line, area };
  });

  // X ekseni etiketleri
  const xTicks = [];
  const nX = W < 420 ? 3 : 5;
  for (let i = 0; i < nX; i++) {
    const t = model.t0 + ((model.t1 - model.t0) * i) / (nX - 1);
    xTicks.push({ t, px: padL + (innerW * i) / (nX - 1), anchor: i === 0 ? "start" : i === nX - 1 ? "end" : "middle" });
  }
  const spanDays = (model.t1 - model.t0) / 86400000;
  const xLabel = (t) => {
    const d = new Date(t);
    return spanDays > 300 ? fmtDate(d, { month: "short", year: "2-digit" }) : fmtDate(d, { day: "numeric", month: "short" });
  };

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - rect.left;
    let best = 0;
    let bestD = Infinity;
    primary.points.forEach((p, i) => {
      const d = Math.abs(x(p.date) - px);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    });
    const date = primary.points[best].date;
    setHover(date);
    if (onScrub) {
      const values = {};
      series.forEach((s) => {
        const found = s.points.find((p) => p.date === date);
        if (found) values[s.key] = found.v;
      });
      onScrub(date, values);
    }
  };
  const handleLeave = () => {
    setHover(null);
    onScrub?.(null, null);
  };

  const hoverVals = hover ? series.map((s) => ({ s, p: s.points.find((p) => p.date === hover) })).filter((r) => r.p) : [];
  const hoverX = hover ? x(hover) : 0;
  const tipLeft = hoverX > W * 0.6;

  return (
    <div ref={ref} className="chart" style={{ height }}>
      {width > 0 && (
        <svg
          width={W}
          height={height}
          role="img"
          aria-label={ariaLabel}
          onPointerMove={handleMove}
          onPointerDown={handleMove}
          onPointerLeave={handleLeave}
          onPointerCancel={handleLeave}
        >
          <defs>
            {paths.map(({ s }) =>
              s.area ? (
                <linearGradient key={s.key} id={`g-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity="0.28" />
                  <stop offset="100%" stopColor={s.color} stopOpacity="0" />
                </linearGradient>
              ) : null
            )}
          </defs>
          {model.ticks.map((v) => (
            <g key={v}>
              <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} className="chart__grid" />
              <text x={padL + 2} y={y(v) - 4} className="chart__tick">
                {moneyCompact(v)}
              </text>
            </g>
          ))}
          {xTicks.map((t, i) => (
            <text key={i} x={t.px} y={height - 6} textAnchor={t.anchor} className="chart__tick">
              {xLabel(t.t)}
            </text>
          ))}
          {paths.map(({ s, line, area }) => (
            <g key={s.key}>
              {area && <path d={area} fill={`url(#g-${s.key})`} />}
              {line && s.points.length > 1 && (
                <path d={line} fill="none" stroke={s.color} strokeWidth={s.area ? 2.5 : 2} strokeDasharray={s.dash} strokeLinejoin="round" strokeLinecap="round" />
              )}
            </g>
          ))}
          {single && <circle cx={x(primary.points[0].date)} cy={y(primary.points[0].v)} r="5" fill={primary.color} />}
          {hover && (
            <g pointerEvents="none">
              <line x1={hoverX} x2={hoverX} y1={padT} y2={padT + innerH} className="chart__cursor" />
              {hoverVals.map(({ s, p }) => (
                <circle key={s.key} cx={hoverX} cy={y(p.v)} r="5" fill="var(--paper)" stroke={s.color} strokeWidth="2.5" />
              ))}
            </g>
          )}
        </svg>
      )}
      {hover && width > 0 && (
        <div className="chart__tip" style={{ left: tipLeft ? undefined : hoverX + 12, right: tipLeft ? W - hoverX + 12 : undefined }}>
          <div className="chart__tip-date">{fmtDateLong(hover)}</div>
          {hoverVals.map(({ s, p }) => (
            <div key={s.key} className="chart__tip-row">
              <i style={{ background: s.color }} />
              <span>{s.label}</span>
              <b>{money(p.v)}</b>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Yatay parçalı çubuk (varlık dağılımı) */
export function StackBar({ parts }) {
  const total = parts.reduce((a, p) => a + Math.max(p.value, 0), 0);
  if (total <= 0) return null;
  return (
    <div className="stack" role="img" aria-label="Dağılım">
      {parts.map((p) => (
        <span key={p.key} className="stack__part" style={{ flexGrow: Math.max(p.value, 0), background: p.color }} title={p.label} />
      ))}
    </div>
  );
}

export function Progress({ pct, tone = "brand", label }) {
  const v = Math.max(0, Math.min(100, pct));
  return (
    <div className={`progress progress--${tone}`} role="progressbar" aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <span style={{ width: `${v}%` }} />
    </div>
  );
}

/** 12 aylık borç yükü sütunları */
export function MonthBars({ data, height = 140 }) {
  const [active, setActive] = useState(null);
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="bars" style={{ height }}>
      {data.map((d, i) => (
        <button
          key={d.key}
          type="button"
          className={`bars__col ${d.current ? "is-current" : ""} ${active === i ? "is-active" : ""}`}
          onMouseEnter={() => setActive(i)}
          onMouseLeave={() => setActive(null)}
          onFocus={() => setActive(i)}
          onBlur={() => setActive(null)}
          onClick={() => setActive(active === i ? null : i)}
          aria-label={`${d.label}: ${money(d.value)}`}
        >
          <span className="bars__val">{d.value > 0 ? moneyCompact(d.value) : ""}</span>
          <span className="bars__bar" style={{ height: `${Math.max((d.value / max) * 100, d.value > 0 ? 4 : 0)}%` }} />
          <span className="bars__lbl">{d.short}</span>
        </button>
      ))}
    </div>
  );
}
