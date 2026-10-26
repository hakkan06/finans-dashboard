const P = {
  home: "M3 11.5 12 4l9 7.5M5.5 10v9.5h13V10",
  wallet: "M4 7.5A2.5 2.5 0 0 1 6.5 5H18v3M4 7.5V17a2 2 0 0 0 2 2h13V8H6.5A2.5 2.5 0 0 1 4 7.5ZM16 13.5h.01",
  card: "M3.5 7A2 2 0 0 1 5.5 5h13a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V7ZM3.5 10h17M7 15h3",
  chart: "M4 19V5M4 19h16M8 15l3.5-4 3 2.5L19 8",
  plus: "M12 5v14M5 12h14",
  refresh: "M20 11a8 8 0 0 0-14.6-4M4 4v4h4M4 13a8 8 0 0 0 14.6 4M20 20v-4h-4",
  trash: "M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12M10 11v5M14 11v5",
  check: "m5 12.5 4.5 4.5L19 7.5",
  x: "M6 6l12 12M18 6 6 18",
  chevron: "m9 6 6 6-6 6",
  chevronDown: "m6 9 6 6 6-6",
  edit: "M4 20h4L19 9l-4-4L4 16v4ZM13.5 6.5l4 4",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  alert: "M12 4 2.8 19.5h18.4L12 4ZM12 10v4.5M12 17.2h.01",
  trendUp: "m4 16 6-6 4 4 6-7M15 7h5v5",
  search: "m20 20-4.2-4.2M10.5 17a6.5 6.5 0 1 1 0-13 6.5 6.5 0 0 1 0 13Z",
  calendar: "M5 7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7ZM5 10h14M9 3.5V6M15 3.5V6",
  layers: "m12 4 9 4.5-9 4.5L3 8.5 12 4ZM3 12.5l9 4.5 9-4.5M3 16.5 12 21l9-4.5",
  save: "M5 4h11l3 3v13H5V4ZM8 4v5h7V4M8 20v-6h8v6",
};

export default function Icon({ name, size = 20, stroke = 1.8, className = "" }) {
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={P[name] || ""} />
    </svg>
  );
}
