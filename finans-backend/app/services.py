"""Hesaplama katmanı: FIFO, portföy özeti, kur, borç istatistikleri, taksit planı.

Tüm iş mantığı burada tek yerde durur; endpoint'ler (main.py) sadece çağırır.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from . import models

logger = logging.getLogger("finans-api")

TR_TZ = timezone(timedelta(hours=3))
FUND_TAX_RATE = float(os.getenv("FUND_TAX_RATE", "0.175"))  # TEFAS fon stopajı
EPS = 1e-6


def now_tr() -> datetime:
    return datetime.now(TR_TZ)


def today_tr() -> date:
    return now_tr().date()


# ─────────────────────────────────────────────────────────────────────
# FIFO / defter
# ─────────────────────────────────────────────────────────────────────
class LedgerError(ValueError):
    """İşlem geçmişi tutarsız hale geliyorsa (eldekinden fazla satış gibi)."""


@dataclass
class Txn:
    quantity: float
    unit_price: float
    transaction_date: date
    id: Optional[int] = None


def to_txn(t) -> Txn:
    return Txn(t.quantity, t.unit_price, t.transaction_date, getattr(t, "id", None))


def _order_key(t: Txn):
    # Aynı gün: önce alışlar, sonra satışlar; sonra kayıt sırası.
    return (t.transaction_date or date.min, 0 if t.quantity > 0 else 1, t.id if t.id is not None else 10**12)


def run_fifo(txns: list[Txn], strict: bool = False):
    """FIFO uygular. (kalan_lotlar, gerçekleşmiş_kâr_zarar) döner.

    strict=True ise herhangi bir anda eldekinden fazla satış LedgerError fırlatır.
    """
    lots: list[dict] = []
    realized = 0.0
    for t in sorted(txns, key=_order_key):
        if t.quantity > 0:
            lots.append({"qty": t.quantity, "price": t.unit_price})
        elif t.quantity < 0:
            need = -t.quantity
            for lot in lots:
                if need <= EPS:
                    break
                take = min(lot["qty"], need)
                if take > 0:
                    realized += take * (t.unit_price - lot["price"])
                    lot["qty"] -= take
                    need -= take
            if need > EPS and strict:
                raise LedgerError(
                    f"{t.transaction_date} tarihli {-t.quantity:,.4f} adetlik satış, "
                    f"o tarihte eldeki miktarı ({-t.quantity - need:,.4f}) aşıyor."
                )
    return [l for l in lots if l["qty"] > EPS], realized


def ledger_ok(txns: list[Txn]) -> bool:
    try:
        run_fifo(txns, strict=True)
        return True
    except LedgerError:
        return False


def check_mutation(old: list[Txn], new: list[Txn]) -> None:
    """Yeni defter tutarsızsa hata verir; ama zaten bozuk bir defteri kilitlemez."""
    try:
        run_fifo(new, strict=True)
    except LedgerError:
        if ledger_ok(old):
            raise


# ─────────────────────────────────────────────────────────────────────
# Kur
# ─────────────────────────────────────────────────────────────────────
_USD_TTL = 600
_usd_cache: dict = {"v": None, "t": 0.0}


def _fetch_usd_try() -> Optional[float]:
    import yfinance as yf

    hist = yf.Ticker("TRY=X").history(period="7d")
    if hist.empty or "Close" not in hist:
        return None
    closes = hist["Close"].dropna()
    return float(closes.iloc[-1]) if not closes.empty else None


def get_usd_try(db: Optional[Session] = None, force: bool = False) -> Optional[float]:
    """USD/TRY. 10 dk önbellekli. Hepsi başarısız olursa DB'deki USD varlığına, o da yoksa None."""
    now = time.time()
    if not force and _usd_cache["v"] and now - _usd_cache["t"] < _USD_TTL:
        return _usd_cache["v"]
    try:
        v = _fetch_usd_try()
        if v:
            _usd_cache.update(v=v, t=now)
            return v
    except Exception as e:  # noqa: BLE001
        logger.warning("USD/TRY çekilemedi: %r", e)
    if _usd_cache["v"]:
        return _usd_cache["v"]
    if db is not None:
        usd = (
            db.query(models.Asset)
            .filter(models.Asset.asset_type == "FIAT", models.Asset.symbol.in_(["USD", "DOLAR"]))
            .first()
        )
        if usd and usd.current_price:
            return float(usd.current_price)
    return None


# ─────────────────────────────────────────────────────────────────────
# Portföy
# ─────────────────────────────────────────────────────────────────────
def portfolio_items(db: Session, include_empty: bool = False, usd: Optional[float] = None) -> list[dict]:
    assets = db.query(models.Asset).order_by(models.Asset.id).all()
    by_asset: dict[int, list[Txn]] = defaultdict(list)
    for t in db.query(models.Transaction).all():
        by_asset[t.asset_id].append(to_txn(t))

    items: list[dict] = []
    for a in assets:
        lots, realized = run_fifo(by_asset.get(a.id, []))
        price = a.current_price or 0.0
        is_fund = a.asset_type == "FUND"
        qty = cost = tax = net = 0.0
        for lot in lots:
            qty += lot["qty"]
            lot_cost = lot["qty"] * lot["price"]
            cost += lot_cost
            gross = lot["qty"] * price
            profit = gross - lot_cost
            lot_tax = profit * FUND_TAX_RATE if (is_fund and profit > 0) else 0.0
            tax += lot_tax
            net += gross - lot_tax

        has_position = qty > 0.0001
        if not has_position and not include_empty:
            continue

        is_usd = a.asset_type == "US_STOCK"
        fx = (usd or 0.0) if is_usd else 1.0
        day = 0.0
        if has_position and a.current_price and a.previous_price:
            day = qty * (a.current_price - a.previous_price) * fx

        items.append(
            {
                "asset_id": a.id,
                "asset_type": a.asset_type,
                "symbol": a.symbol,
                "name": a.name,
                "total_qty": qty,
                "current_price": price,
                "previous_price": a.previous_price,
                "total_cost": cost,
                "total_tax": tax,
                "net_value": net,
                "last_updated": a.last_updated,
                "currency": "USD" if is_usd else "TRY",
                "fx": fx,
                "value_try": net * fx,
                "cost_try": cost * fx,
                "day_change_try": day,
                "realized_pl": realized,
                "has_price": a.current_price is not None,
                "has_position": has_position,
            }
        )
    return items


# ─────────────────────────────────────────────────────────────────────
# Borçlar
# ─────────────────────────────────────────────────────────────────────
def debt_stats(db: Session, today: Optional[date] = None) -> dict:
    today = today or today_tr()
    unpaid = db.query(models.DebtInstallment).filter(models.DebtInstallment.is_paid.is_(False)).all()
    total = due_month = overdue_total = 0.0
    overdue_count = 0
    for i in unpaid:
        total += i.amount
        if i.due_date < today:
            overdue_total += i.amount
            overdue_count += 1
        if i.due_date.year == today.year and i.due_date.month == today.month:
            due_month += i.amount
    return {
        "total_debts": total,
        "due_this_month": due_month,
        "overdue_total": overdue_total,
        "overdue_count": overdue_count,
    }


def build_overview(db: Session) -> dict:
    usd = get_usd_try(db)
    items = portfolio_items(db, usd=usd)
    total_assets = sum(i["value_try"] for i in items)
    day_change = sum(i["day_change_try"] for i in items)
    base = total_assets - day_change
    alloc: dict[str, float] = defaultdict(float)
    for i in items:
        alloc[i["asset_type"]] += i["value_try"]
    last = [i["last_updated"] for i in items if i["last_updated"]]
    d = debt_stats(db)
    # Kur alınamadıysa ABD hisseleri 0 TL sayılır; böyle bir değer kaydedilmemeli.
    fx_missing = usd is None and any(i["asset_type"] == "US_STOCK" for i in items)
    return {
        "fx_missing": fx_missing,
        "usd_try": usd,
        "total_assets": total_assets,
        "total_debts": d["total_debts"],
        "net_worth": total_assets - d["total_debts"],
        "day_change": day_change,
        "day_change_pct": (day_change / base * 100) if base > 0 else 0.0,
        "due_this_month": d["due_this_month"],
        "overdue_total": d["overdue_total"],
        "overdue_count": d["overdue_count"],
        "last_price_update": max(last) if last else None,
        "allocation": [{"asset_type": k, "value": v} for k, v in sorted(alloc.items(), key=lambda kv: -kv[1])],
    }


def save_snapshot(db: Session, total_assets: float, total_debts: float) -> models.PortfolioHistory:
    today = today_tr()
    rec = db.query(models.PortfolioHistory).filter(models.PortfolioHistory.record_date == today).first()
    net = total_assets - total_debts
    if rec:
        rec.total_assets, rec.total_debts, rec.net_worth = total_assets, total_debts, net
    else:
        rec = models.PortfolioHistory(
            record_date=today, total_assets=total_assets, total_debts=total_debts, net_worth=net
        )
        db.add(rec)
    db.commit()
    return rec


# ─────────────────────────────────────────────────────────────────────
# Taksit planı
# ─────────────────────────────────────────────────────────────────────
def build_installments(total: float, count: int, monthly_rate_pct: float, start: date) -> list[tuple[date, float]]:
    """Taksit listesi (vade, tutar).

    monthly_rate_pct == 0 → `total` toplam geri ödemedir, eşit bölünür (kuruş farkı son taksitte).
    monthly_rate_pct  > 0 → `total` anapara, aylık bileşik faizle eşit taksitli (annüite) plan.
    """
    if count < 1:
        raise ValueError("Taksit sayısı en az 1 olmalı.")
    if monthly_rate_pct and monthly_rate_pct > 0:
        r = monthly_rate_pct / 100.0
        pmt = total * r / (1 - (1 + r) ** (-count))
        amount = round(pmt, 2)
        amounts = [amount] * count
    else:
        amount = round(total / count, 2)
        amounts = [amount] * (count - 1) + [round(total - amount * (count - 1), 2)]
    return [(start + relativedelta(months=i), a) for i, a in enumerate(amounts)]
