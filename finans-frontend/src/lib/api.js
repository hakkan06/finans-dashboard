// Backend'e nginx üzerinden /api altında ulaşılır.
const BASE = "/api";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function detailText(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return "Girilen bilgilerde eksik veya hatalı alan var.";
  if (status === 0) return "Sunucuya ulaşılamıyor. Bağlantını kontrol et.";
  return `Beklenmeyen hata (${status}).`;
}

async function req(method, path, body) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(detailText(null, 0), 0);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* gövde yok */
  }
  if (!res.ok) throw new ApiError(detailText(data?.detail, res.status), res.status);
  return data;
}

export const api = {
  overview: () => req("GET", "/overview"),
  summary: () => req("GET", "/portfolio/summary?include_empty=true"),
  debts: () => req("GET", "/debts/"),
  groups: () => req("GET", "/debt-groups/"),
  history: () => req("GET", "/portfolio/history"),
  transactions: (assetId) => req("GET", `/transactions/?asset_id=${assetId}`),

  createAsset: (a) => req("POST", "/assets/", a),
  deleteAsset: (id) => req("DELETE", `/assets/${id}`),
  updatePrices: () => req("POST", "/assets/update-prices"),

  createTransaction: (t) => req("POST", "/transactions/", t),
  updateTransaction: (id, t) => req("PUT", `/transactions/${id}`, t),
  deleteTransaction: (id) => req("DELETE", `/transactions/${id}`),

  createSchedule: (s) => req("POST", "/debts/schedules/", s),
  toggleInstallment: (id) => req("PUT", `/installments/${id}/toggle`),
  deleteDebt: (id) => req("DELETE", `/debts/${id}`),
  createGroup: (g) => req("POST", "/debt-groups/", g),
  deleteGroup: (id) => req("DELETE", `/debt-groups/${id}`),
  assignGroup: (debtId, groupId) => req("PUT", `/debts/${debtId}/assign-group`, { group_id: groupId }),

  snapshot: () => req("POST", "/portfolio/snapshot"),
  deleteHistory: (date) => req("DELETE", `/portfolio/history/${date}`),
};
