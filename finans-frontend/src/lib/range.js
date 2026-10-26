import { addMonths, parseDate, todayStr } from "./format.js";

export const RANGES = [
  { value: "1M", label: "1A", months: 1, long: "son 1 ay" },
  { value: "3M", label: "3A", months: 3, long: "son 3 ay" },
  { value: "6M", label: "6A", months: 6, long: "son 6 ay" },
  { value: "1Y", label: "1Y", months: 12, long: "son 1 yıl" },
  { value: "ALL", label: "Tümü", months: null, long: "başlangıçtan beri" },
];

/** Seçilen aralığa düşen günlük kayıtlar (en az iki nokta kalacak şekilde). */
export function rangeSeries(series, range) {
  const r = RANGES.find((x) => x.value === range);
  if (!r || r.months === null) return series;
  const from = addMonths(todayStr(), -r.months);
  const inRange = series.filter((p) => p.date >= from);
  if (inRange.length >= 2) return inRange;
  return series.slice(-2);
}

export const dayMs = (s) => parseDate(s).getTime();
