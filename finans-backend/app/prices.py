"""Piyasa fiyatı çekme (yfinance + TEFAS). Ağ çağrıları thread'lerde paralel yapılır."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from . import models
from .services import TR_TZ

logger = logging.getLogger("finans-api")

GOLD = {"ALTIN", "XAU", "GRAMALTIN", "GOLD", "GRAM-ALTIN", "GLD"}
SILVER = {"GUMUS", "XAG", "GRAMGUMUS", "SILVER", "GRAM-GUMUS", "SLV"}
OUNCE_GRAMS = 31.1034768

Quote = tuple[float, Optional[float]]  # (güncel, önceki)


def normalize(asset: models.Asset) -> None:
    """Altın/gümüş sembollerini otomatik olarak COMMODITY yapar."""
    sym = asset.symbol.strip().upper()
    if sym in GOLD or sym in SILVER:
        asset.asset_type = "COMMODITY"


def _closes(symbol: str) -> list[float]:
    import yfinance as yf

    hist = yf.Ticker(symbol).history(period="7d")
    if hist.empty or "Close" not in hist:
        return []
    return [float(x) for x in hist["Close"].dropna()]


def _last_two(values: list[float]) -> Optional[Quote]:
    if not values:
        return None
    return values[-1], (values[-2] if len(values) > 1 else None)


def _ounce_to_gram_try(symbol: str) -> Optional[Quote]:
    metal, usd = _closes(symbol), _closes("TRY=X")
    if not metal or not usd:
        return None
    cur = metal[-1] * usd[-1] / OUNCE_GRAMS
    prev = metal[-2] * usd[-2] / OUNCE_GRAMS if len(metal) > 1 and len(usd) > 1 else None
    return cur, prev


def _fund(symbol: str) -> Optional[Quote]:
    from tefas import Crawler

    end = datetime.now(TR_TZ)
    start = end - timedelta(days=7)
    data = Crawler().fetch(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), name=symbol)
    if data is None or data.empty:
        return None
    data = data.sort_values(by="date", ascending=False)
    cur = float(data.iloc[0]["price"])
    prev = float(data.iloc[1]["price"]) if len(data) > 1 else None
    return cur, prev


def fetch_quote(asset_type: str, symbol: str) -> Optional[Quote]:
    """Tek varlık için (güncel, önceki) fiyat. Bulunamazsa None, ağ hatasında istisna."""
    sym = symbol.strip().upper()
    if asset_type == "US_STOCK":
        return _last_two(_closes(sym))
    if asset_type == "TR_STOCK":
        return _last_two(_closes(sym if sym.endswith(".IS") else sym + ".IS"))
    if asset_type == "FUND":
        return _fund(sym)
    if asset_type == "COMMODITY":
        if sym in GOLD:
            return _ounce_to_gram_try("GC=F")
        if sym in SILVER:
            return _ounce_to_gram_try("SI=F")
        return None
    if asset_type == "FIAT":
        if sym in ("TRY", "TL"):
            return 1.0, 1.0
        if sym in ("USD", "DOLAR"):
            return _last_two(_closes("TRY=X"))
        if sym in ("EUR", "EURO"):
            return _last_two(_closes("EURTRY=X"))
    return None


def _apply(asset: models.Asset, quote: Quote) -> None:
    cur, prev = quote
    asset.current_price = cur
    if prev is not None:
        asset.previous_price = prev
    asset.last_updated = datetime.now(TR_TZ)


def refresh_asset(asset: models.Asset) -> bool:
    """Tek varlığın fiyatını çeker (yeni varlık eklenirken sembolü doğrulamak için de kullanılır)."""
    normalize(asset)
    try:
        quote = fetch_quote(asset.asset_type, asset.symbol)
    except Exception as e:  # noqa: BLE001
        logger.warning("Fiyat çekilemedi | %s (%s) | %r", asset.symbol, asset.asset_type, e)
        return False
    if not quote:
        return False
    _apply(asset, quote)
    return True


def refresh_all(db: Session) -> tuple[int, list[str]]:
    """Tüm varlıkları paralel günceller. (güncellenen_sayı, başarısız_semboller)"""
    assets = db.query(models.Asset).all()
    for a in assets:
        normalize(a)
    jobs = [(a, a.asset_type, a.symbol) for a in assets]

    def work(job):
        _, atype, sym = job
        try:
            return fetch_quote(atype, sym)
        except Exception as e:  # noqa: BLE001
            logger.warning("Fiyat güncellenemedi | %s (%s) | %r", sym, atype, e)
            return None

    updated, failed = 0, []
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(work, jobs))
    for (asset, _, sym), quote in zip(jobs, results):
        if quote:
            _apply(asset, quote)
            updated += 1
        else:
            failed.append(sym)
    db.commit()
    logger.info("Fiyat güncellemesi bitti: %d güncellendi, başarısız: %s", updated, failed)
    return updated, failed
