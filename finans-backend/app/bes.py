"""BES (Bireysel Emeklilik Sistemi) modülü.

Fon bazlı takip: her hesapta hangi fondan kaç pay olduğu tutulur, değer TEFAS emeklilik
fon fiyatlarıyla hesaplanır. Aylık katkı (ve devlet katkısı) tanımlanan fon dağılımına göre
payların üzerine otomatik eklenir. Hak ediş, BES'e ilk giriş tarihi ve doğum tarihinden hesaplanır.

BES likit olmadığı için net servete / geçmiş kayıtlarına dahil edilmez.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, inspect, text
from sqlalchemy.orm import Session, relationship

from .database import get_db
from .models import Base
from .services import TR_TZ, now_tr, today_tr

logger = logging.getLogger("finans-api")

# --- KURALLAR (mevzuat değişirse sadece burayı güncelleyin) -----------------
# Devlet katkısı hak ediş kademeleri: (BES'te geçen yıl, hak edilen oran)
VESTING_TIERS = [(3, 0.15), (6, 0.35), (10, 0.60)]
RETIREMENT_YEARS = 10     # emeklilik hakkı için gereken süre
RETIREMENT_AGE = 56       # emeklilik hakkı için gereken yaş
RETIREMENT_RATIO = 1.00
# Stopaj varsayımları (ekstrenizle kontrol edin)
EARLY_EXIT_TAX = 0.15     # emeklilik şartı oluşmadan ayrılma
RETIREMENT_TAX = 0.05     # emeklilik şartlarıyla çıkış
# Devlet katkısı oranı (katkı payının yüzdesi); hesap bazında değiştirilebilir
DEFAULT_STATE_RATE = float(os.getenv("BES_STATE_RATE", "0.20"))
MIN_ENTRY = date(2003, 1, 1)  # BES'in başladığı yıl
EPS = 1e-9


# --- MODEL ------------------------------------------------------------------
class BESAccount(Base):
    __tablename__ = "bes_accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)                      # Örn: "Anadolu Hayat BES"
    company = Column(String, nullable=True)
    # Hak ediş sayacı SİSTEME İLK GİRİŞ tarihinden işler (şirket sözleşme tarihinden değil)
    system_entry_date = Column(Date)
    contract_start_date = Column(Date, nullable=True)      # bilgi amaçlı
    birth_date = Column(Date, nullable=True)               # 56 yaş şartı için
    retirement_eligible = Column(Boolean, default=False)   # doğum tarihi girilmediyse elle işaret
    monthly_contribution = Column(Float, default=0.0)      # aylık kendi katkınız
    contribution_day = Column(Integer, default=1)          # ayın kaçında yatar (1-28)
    state_rate = Column(Float, default=DEFAULT_STATE_RATE)
    next_contribution = Column(Date, nullable=True)        # sıradaki otomatik katkı tarihi

    holdings = relationship("BESHolding", back_populates="account", cascade="all, delete-orphan")
    allocations = relationship("BESAllocation", back_populates="account", cascade="all, delete-orphan")
    events = relationship("BESEvent", back_populates="account", cascade="all, delete-orphan")


class BESHolding(Base):
    """Bir hesaptaki bir fonun pay adedi. Kendi katkınız ve devlet katkısı ayrı tutulur."""
    __tablename__ = "bes_holdings"
    __table_args__ = (UniqueConstraint("account_id", "fund_code", name="uq_bes_holding"),)
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("bes_accounts.id"), index=True)
    fund_code = Column(String)
    own_units = Column(Float, default=0.0)
    state_units = Column(Float, default=0.0)
    own_cost = Column(Float, default=0.0)  # bu fona giren kendi katkınızın TL toplamı (getiri hesabı)

    account = relationship("BESAccount", back_populates="holdings")


class BESAllocation(Base):
    """Aylık katkının hangi fona yüzde kaç gideceği."""
    __tablename__ = "bes_allocations"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("bes_accounts.id"), index=True)
    fund_code = Column(String)
    percent = Column(Float)

    account = relationship("BESAccount", back_populates="allocations")


class BESFund(Base):
    """TEFAS emeklilik fonu son fiyatı."""
    __tablename__ = "bes_funds"
    code = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    previous_price = Column(Float, nullable=True)
    price_date = Column(Date, nullable=True)
    last_updated = Column(DateTime, nullable=True)


class BESEvent(Base):
    """Hesap hareketleri: otomatik katkı, devlet katkısı, fon değişikliği, düzeltme."""
    __tablename__ = "bes_events"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("bes_accounts.id"), index=True)
    event_date = Column(Date)
    kind = Column(String)       # contribution | state | switch | adjust
    fund_code = Column(String, nullable=True)
    units = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    note = Column(String, nullable=True)

    account = relationship("BESAccount", back_populates="events")



def migrate(engine) -> list:
    """Var olan BES tablolarına eksik sütunları ekler.

    `create_all` yalnızca olmayan tabloları oluşturur, var olan tabloya sütun eklemez. BES'in ilk sürümünde
    oluşan `bes_accounts` tablosunu yeni şemaya yükseltmek için gerekir. Yeni sütunların hepsi boş (NULL)
    olabilir ve kod boş değerleri varsayılanla karşılar. Eklenen sütun adlarını döner; tekrar çalıştırmak zararsızdır.
    """
    added = []
    insp = inspect(engine)
    prep = engine.dialect.identifier_preparer
    for table in (BESAccount.__table__, BESHolding.__table__, BESAllocation.__table__, BESFund.__table__, BESEvent.__table__):
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            ine = "IF NOT EXISTS " if engine.dialect.name == "postgresql" else ""  # birden fazla kopya aynı anda açılırsa
            ddl = f"ALTER TABLE {prep.quote(table.name)} ADD COLUMN {ine}{prep.quote(col.name)} {col.type.compile(dialect=engine.dialect)}"
            with engine.begin() as conn:
                conn.execute(text(ddl))
            added.append(f"{table.name}.{col.name}")
    if added:
        logger.info("BES şeması güncellendi: %s", ", ".join(added))
    return added


# --- ŞEMALAR ----------------------------------------------------------------
class AllocationIn(BaseModel):
    fund_code: str = Field(min_length=2, max_length=12)
    percent: float = Field(gt=0, le=100)


class HoldingIn(BaseModel):
    fund_code: str = Field(min_length=2, max_length=12)
    own_units: float = Field(default=0.0, ge=0)
    state_units: float = Field(default=0.0, ge=0)
    own_cost: float = Field(default=0.0, ge=0)


class HoldingValues(BaseModel):
    own_units: float = Field(default=0.0, ge=0)
    state_units: float = Field(default=0.0, ge=0)
    own_cost: float = Field(default=0.0, ge=0)


class BESCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company: Optional[str] = Field(default=None, max_length=120)
    system_entry_date: date
    contract_start_date: Optional[date] = None
    birth_date: Optional[date] = None
    retirement_eligible: bool = False
    monthly_contribution: float = Field(default=0.0, ge=0)
    contribution_day: int = Field(default=1, ge=1, le=28)
    state_rate: float = Field(default=DEFAULT_STATE_RATE, ge=0, le=1)
    first_contribution_date: Optional[date] = None
    allocations: List[AllocationIn] = []
    holdings: List[HoldingIn] = []


class BESUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    company: Optional[str] = Field(default=None, max_length=120)
    system_entry_date: Optional[date] = None
    contract_start_date: Optional[date] = None
    birth_date: Optional[date] = None
    retirement_eligible: Optional[bool] = None
    monthly_contribution: Optional[float] = Field(default=None, ge=0)
    contribution_day: Optional[int] = Field(default=None, ge=1, le=28)
    state_rate: Optional[float] = Field(default=None, ge=0, le=1)
    first_contribution_date: Optional[date] = None
    allocations: Optional[List[AllocationIn]] = None


class SwitchIn(BaseModel):
    from_fund: str = Field(min_length=2, max_length=12)
    to_fund: str = Field(min_length=2, max_length=12)
    percent: float = Field(gt=0, le=100)


class ReconcileIn(BaseModel):
    own_balance: Optional[float] = Field(default=None, ge=0)
    state_balance: Optional[float] = Field(default=None, ge=0)


class Milestone(BaseModel):
    years: int
    due_date: date
    ratio: float
    reached: bool


class HoldingOut(BaseModel):
    fund_code: str
    fund_name: Optional[str] = None
    own_units: float
    state_units: float
    price: Optional[float] = None
    price_date: Optional[date] = None
    own_value: float
    state_value: float
    own_cost: float
    own_pl: float
    share_pct: float


class AllocationOut(BaseModel):
    fund_code: str
    percent: float


class EventOut(BaseModel):
    id: int
    event_date: date
    kind: str
    fund_code: Optional[str] = None
    units: Optional[float] = None
    amount: Optional[float] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True


class BESItem(BaseModel):
    id: int
    name: str
    company: Optional[str] = None
    system_entry_date: date
    contract_start_date: Optional[date] = None
    birth_date: Optional[date] = None
    age: Optional[int] = None
    years_in_system: float
    # Değerler (güncel fon fiyatıyla)
    own_principal: float          # kendi ödediğiniz toplam katkı
    own_balance: float            # kendi katkı + getirisi
    state_balance: float          # devlet katkısı + getirisi
    total_balance: float
    own_return: float             # kendi katkı getirisi (TL, eksi olabilir)
    vest_ratio: float
    vested_state: float
    forfeited_state: float
    tax: float
    net_value: float
    retirement_eligible: bool
    retirement_date: Optional[date] = None
    next_milestone: Optional[Milestone] = None
    days_to_next: Optional[int] = None
    gain_at_next: Optional[float] = None
    milestones: List[Milestone] = []
    # Fonlar ve plan
    holdings: List[HoldingOut] = []
    missing_prices: List[str] = []
    monthly_contribution: float = 0.0
    contribution_day: int = 1
    state_rate: float = DEFAULT_STATE_RATE
    next_contribution: Optional[date] = None
    allocations: List[AllocationOut] = []


# --- FON FİYATI ---------------------------------------------------------------
FundQuote = Tuple[float, Optional[float], Optional[date], Optional[str]]  # fiyat, önceki, tarih, ad


def fetch_bes_fund(code: str) -> Optional[FundQuote]:
    """TEFAS'tan emeklilik fonunun son fiyatı. Bulunamazsa None, ağ hatasında istisna."""
    from tefas import Crawler

    end = datetime.now(TR_TZ)
    start = end - timedelta(days=10)
    data = Crawler().fetch(
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), name=code, kind="EMK"
    )
    if data is None or data.empty:
        return None
    data = data.sort_values(by="date", ascending=False)
    row = data.iloc[0]
    d = row["date"]
    d = d.date() if hasattr(d, "date") and callable(d.date) else d
    prev = float(data.iloc[1]["price"]) if len(data) > 1 else None
    title = row["title"] if "title" in data.columns else None
    return float(row["price"]), prev, d, title


def _apply_quote(db: Session, code: str, q: FundQuote) -> BESFund:
    price, prev, d, title = q
    f = db.get(BESFund, code)
    if f is None:
        f = BESFund(code=code)
        db.add(f)
    f.price, f.previous_price, f.price_date, f.last_updated = price, prev, d, now_tr().replace(tzinfo=None)
    if title:
        f.name = title
    return f


def used_fund_codes(db: Session) -> List[str]:
    codes = {h.fund_code for h in db.query(BESHolding).all()}
    codes |= {a.fund_code for a in db.query(BESAllocation).all()}
    return sorted(codes)


def refresh_all(db: Session) -> Tuple[int, List[str]]:
    """Kullanılan tüm BES fonlarının fiyatını günceller. (güncellenen, başarısız kodlar)"""
    codes = used_fund_codes(db)
    if not codes:
        return 0, []

    def work(code):
        try:
            return fetch_bes_fund(code)
        except Exception as e:  # noqa: BLE001
            logger.warning("BES fon fiyatı alınamadı | %s | %r", code, e)
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(work, codes))
    ok, failed = 0, []
    for code, q in zip(codes, results):
        if q:
            _apply_quote(db, code, q)
            ok += 1
        else:
            failed.append(code)
    db.commit()
    return ok, failed


def _funds(db: Session) -> Dict[str, BESFund]:
    return {f.code: f for f in db.query(BESFund).all()}


def _ensure_fund(db: Session, code: str) -> None:
    """Yeni bir fon kodu kullanılırken fiyatı çekmeyi dener; kod bulunamazsa 422 verir.

    Ağ hatasında (TEFAS ulaşılamıyorsa) kaydı engellemez, fiyat sonra güncellenir.
    """
    f = db.get(BESFund, code)
    if f is not None and f.price:
        return
    try:
        q = fetch_bes_fund(code)
    except Exception as e:  # noqa: BLE001
        logger.warning("BES fon fiyatı alınamadı | %s | %r", code, e)
        return
    if q is None:
        raise HTTPException(status_code=422, detail=f"{code} kodlu emeklilik fonu TEFAS'ta bulunamadı. Kodu kontrol et.")
    _apply_quote(db, code, q)
    db.flush()  # autoflush kapalı: aynı istekte aynı kod tekrar sorgulanırsa çift kayıt oluşmasın


# --- HESAPLAMA --------------------------------------------------------------
def age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def retirement_date(acc: BESAccount) -> Optional[date]:
    if not acc.birth_date:
        return None
    return max(
        acc.system_entry_date + relativedelta(years=RETIREMENT_YEARS),
        acc.birth_date + relativedelta(years=RETIREMENT_AGE),
    )


def is_retirement_eligible(acc: BESAccount, today: date) -> bool:
    rd = retirement_date(acc)
    return today >= rd if rd else bool(acc.retirement_eligible)


def vesting_ratio(entry: date, today: date, retirement_eligible: bool) -> float:
    if retirement_eligible:
        return RETIREMENT_RATIO
    ratio = 0.0
    for years, r in VESTING_TIERS:
        if today >= entry + relativedelta(years=years):
            ratio = r
    return ratio


def compute_item(acc: BESAccount, funds: Dict[str, BESFund], today: date) -> dict:
    rows, missing = [], []
    own_value = state_value = own_cost = 0.0
    for h in sorted(acc.holdings, key=lambda x: x.fund_code):
        f = funds.get(h.fund_code)
        price = f.price if f and f.price else None
        ov = (h.own_units or 0.0) * price if price else 0.0
        sv = (h.state_units or 0.0) * price if price else 0.0
        if price is None and ((h.own_units or 0) > 0 or (h.state_units or 0) > 0):
            missing.append(h.fund_code)
        own_value += ov
        state_value += sv
        own_cost += h.own_cost or 0.0
        rows.append(dict(
            fund_code=h.fund_code, fund_name=f.name if f else None,
            own_units=h.own_units or 0.0, state_units=h.state_units or 0.0,
            price=price, price_date=f.price_date if f else None,
            own_value=ov, state_value=sv, own_cost=h.own_cost or 0.0,
            own_pl=ov - (h.own_cost or 0.0) if price else 0.0, share_pct=0.0,
        ))
    total = own_value + state_value
    for r in rows:
        r["share_pct"] = (r["own_value"] + r["state_value"]) / total * 100 if total > 0 else 0.0

    eligible = is_retirement_eligible(acc, today)
    ratio = vesting_ratio(acc.system_entry_date, today, eligible)
    tax_rate = RETIREMENT_TAX if eligible else EARLY_EXIT_TAX

    own_yield = max(own_value - own_cost, 0.0)
    vested_state = state_value * ratio
    forfeited = state_value - vested_state
    tax = (own_yield + vested_state) * tax_rate
    net_value = own_value + vested_state - tax

    milestones = []
    for years, r in VESTING_TIERS:
        d = acc.system_entry_date + relativedelta(years=years)
        milestones.append(Milestone(years=years, due_date=d, ratio=r, reached=today >= d))

    next_ms = None if eligible else next((m for m in milestones if not m.reached), None)
    days_to_next = (next_ms.due_date - today).days if next_ms else None
    gain_at_next = state_value * (next_ms.ratio - ratio) * (1 - tax_rate) if next_ms else None

    return dict(
        id=acc.id, name=acc.name, company=acc.company,
        system_entry_date=acc.system_entry_date, contract_start_date=acc.contract_start_date,
        birth_date=acc.birth_date, age=age_on(acc.birth_date, today) if acc.birth_date else None,
        years_in_system=round((today - acc.system_entry_date).days / 365.25, 2),
        own_principal=own_cost, own_balance=own_value, state_balance=state_value,
        total_balance=total, own_return=own_value - own_cost if not missing else 0.0,
        vest_ratio=ratio, vested_state=vested_state, forfeited_state=forfeited,
        tax=tax, net_value=net_value, retirement_eligible=eligible,
        retirement_date=retirement_date(acc),
        next_milestone=next_ms, days_to_next=days_to_next, gain_at_next=gain_at_next,
        milestones=milestones, holdings=rows, missing_prices=missing,
        monthly_contribution=acc.monthly_contribution or 0.0,
        contribution_day=acc.contribution_day or 1,
        state_rate=acc.state_rate if acc.state_rate is not None else DEFAULT_STATE_RATE,
        next_contribution=acc.next_contribution,
        allocations=[dict(fund_code=a.fund_code, percent=a.percent)
                     for a in sorted(acc.allocations, key=lambda x: x.fund_code)],
    )


# --- AYLIK KATKI ------------------------------------------------------------
def first_due(day: int, today: date, start: Optional[date] = None) -> date:
    if start:
        return start
    d = date(today.year, today.month, min(day, 28))
    return d if d >= today else d + relativedelta(months=1)


def next_month_due(current: date, day: int) -> date:
    """Bir sonraki ayın katkı tarihi. Gün her zaman 'ayın kaçında yatar' ayarına sabitlenir (kayma olmaz)."""
    d = current + relativedelta(months=1)
    return date(d.year, d.month, min(day or 1, 28))


def _holding(db: Session, acc: BESAccount, code: str) -> BESHolding:
    h = next((x for x in acc.holdings if x.fund_code == code), None)
    if h is None:
        h = BESHolding(account_id=acc.id, fund_code=code, own_units=0.0, state_units=0.0, own_cost=0.0)
        acc.holdings.append(h)
    return h


def _apply_one(db: Session, acc: BESAccount, funds: Dict[str, BESFund], due: date) -> bool:
    """Tek ayın katkısını fon dağılımına göre paylara ekler. Fiyat eksikse hiçbir şey yapmaz."""
    if any(not (funds.get(a.fund_code) and funds[a.fund_code].price) for a in acc.allocations):
        return False
    for a in acc.allocations:
        price = funds[a.fund_code].price
        amount = acc.monthly_contribution * a.percent / 100.0
        h = _holding(db, acc, a.fund_code)
        units = amount / price
        h.own_units = (h.own_units or 0.0) + units
        h.own_cost = (h.own_cost or 0.0) + amount
        db.add(BESEvent(account_id=acc.id, event_date=due, kind="contribution", fund_code=a.fund_code,
                        units=units, amount=amount, note="Aylık katkı (güncel fiyatla)"))
        rate = acc.state_rate if acc.state_rate is not None else DEFAULT_STATE_RATE
        if rate > 0:
            s_amount = amount * rate
            s_units = s_amount / price
            h.state_units = (h.state_units or 0.0) + s_units
            db.add(BESEvent(account_id=acc.id, event_date=due, kind="state", fund_code=a.fund_code,
                            units=s_units, amount=s_amount, note=f"Devlet katkısı %{rate * 100:g}"))
    return True


def apply_due_contributions(db: Session, today: Optional[date] = None) -> int:
    """Vadesi gelmiş aylık katkıları uygular (idempotent: her ay bir kez). Uygulanan ay sayısını döner."""
    today = today or today_tr()
    funds = _funds(db)
    applied = 0
    for acc in db.query(BESAccount).all():
        if not acc.monthly_contribution or not acc.allocations or not acc.next_contribution:
            continue
        guard = 0
        while acc.next_contribution <= today and guard < 36:
            if not _apply_one(db, acc, funds, acc.next_contribution):
                logger.warning("BES katkısı ertelendi (fon fiyatı yok) | %s", acc.name)
                break
            acc.next_contribution = next_month_due(acc.next_contribution, acc.contribution_day)
            applied += 1
            guard += 1
    db.commit()
    return applied


# --- ENDPOINT'LER -----------------------------------------------------------
router = APIRouter(prefix="/bes", tags=["BES"])


def _norm(code: str) -> str:
    return code.strip().upper()


def _get(db: Session, bes_id: int) -> BESAccount:
    acc = db.get(BESAccount, bes_id)
    if not acc:
        raise HTTPException(status_code=404, detail="BES hesabı bulunamadı")
    return acc


def _out(db: Session, acc: BESAccount) -> dict:
    return compute_item(acc, _funds(db), today_tr())


def _check_entry(d: Optional[date], today: date):
    if d is not None and not (MIN_ENTRY <= d <= today):
        raise HTTPException(status_code=422, detail="Sisteme giriş tarihi 2003 ile bugün arasında olmalı.")


def _check_birth(d: Optional[date], today: date):
    if d is not None and not (date(1920, 1, 1) <= d <= today):
        raise HTTPException(status_code=422, detail="Doğum tarihi geçerli değil.")


def _set_allocations(db: Session, acc: BESAccount, items: List[AllocationIn]):
    merged: Dict[str, float] = {}
    for a in items:
        code = _norm(a.fund_code)
        merged[code] = merged.get(code, 0.0) + a.percent
    if merged and abs(sum(merged.values()) - 100.0) > 0.01:
        raise HTTPException(status_code=422, detail="Fon dağılımı yüzdelerinin toplamı %100 olmalı.")
    for code in merged:
        _ensure_fund(db, code)
    acc.allocations.clear()
    db.flush()
    for code, pct in merged.items():
        acc.allocations.append(BESAllocation(fund_code=code, percent=pct))


def _schedule(acc: BESAccount, today: date, start: Optional[date], day_changed: bool):
    if not acc.monthly_contribution:
        acc.next_contribution = None
    elif start or acc.next_contribution is None or day_changed:
        acc.next_contribution = first_due(acc.contribution_day or 1, today, start)


@router.get("/", response_model=List[BESItem])
def list_bes(db: Session = Depends(get_db)):
    funds, today = _funds(db), today_tr()
    return [compute_item(a, funds, today) for a in db.query(BESAccount).order_by(BESAccount.id).all()]


@router.post("/refresh")
def refresh_bes(db: Session = Depends(get_db)):
    """Fon fiyatlarını günceller ve vadesi gelen aylık katkıları ekler."""
    updated, failed = refresh_all(db)
    applied = apply_due_contributions(db)
    return {"updated": updated, "failed": failed, "applied_months": applied}


@router.post("/", response_model=BESItem)
def create_bes(payload: BESCreate, db: Session = Depends(get_db)):
    today = today_tr()
    _check_entry(payload.system_entry_date, today)
    _check_birth(payload.birth_date, today)
    acc = BESAccount(
        name=payload.name.strip(), company=payload.company,
        system_entry_date=payload.system_entry_date, contract_start_date=payload.contract_start_date,
        birth_date=payload.birth_date, retirement_eligible=payload.retirement_eligible,
        monthly_contribution=payload.monthly_contribution, contribution_day=payload.contribution_day,
        state_rate=payload.state_rate,
    )
    db.add(acc)
    db.flush()
    seen = set()
    for h in payload.holdings:
        code = _norm(h.fund_code)
        if code in seen:
            raise HTTPException(status_code=422, detail=f"{code} birden fazla kez girilmiş.")
        seen.add(code)
        _ensure_fund(db, code)
        acc.holdings.append(BESHolding(fund_code=code, own_units=h.own_units, state_units=h.state_units, own_cost=h.own_cost))
    if payload.allocations:
        _set_allocations(db, acc, payload.allocations)
    elif payload.monthly_contribution > 0:
        raise HTTPException(status_code=422, detail="Aylık katkı için fon dağılımı gerekli.")
    _schedule(acc, today, payload.first_contribution_date, True)
    db.commit()
    db.refresh(acc)
    return _out(db, acc)


@router.get("/{bes_id}", response_model=BESItem)
def get_bes(bes_id: int, db: Session = Depends(get_db)):
    return _out(db, _get(db, bes_id))


@router.put("/{bes_id}", response_model=BESItem)
def update_bes(bes_id: int, payload: BESUpdate, db: Session = Depends(get_db)):
    acc = _get(db, bes_id)
    data = payload.model_dump(exclude_unset=True)
    today = today_tr()
    _check_entry(data.get("system_entry_date"), today)
    _check_birth(data.get("birth_date"), today)
    allocations = data.pop("allocations", None)
    first = data.pop("first_contribution_date", None)
    old_day = acc.contribution_day
    for k, v in data.items():
        setattr(acc, k, v)
    if allocations is not None:
        _set_allocations(db, acc, payload.allocations)
    if (acc.monthly_contribution or 0) > 0 and not acc.allocations:
        raise HTTPException(status_code=422, detail="Aylık katkı için fon dağılımı gerekli.")
    _schedule(acc, today, first, "contribution_day" in data and acc.contribution_day != old_day)
    db.commit()
    db.refresh(acc)
    return _out(db, acc)


@router.delete("/{bes_id}")
def delete_bes(bes_id: int, db: Session = Depends(get_db)):
    acc = _get(db, bes_id)
    db.delete(acc)
    db.commit()
    return {"message": "BES hesabı silindi."}


@router.put("/{bes_id}/holdings/{fund_code}", response_model=BESItem)
def put_holding(bes_id: int, fund_code: str, body: HoldingValues, db: Session = Depends(get_db)):
    """Bir fonun pay adedini elle ayarlar (yoksa ekler)."""
    acc = _get(db, bes_id)
    code = _norm(fund_code)
    _ensure_fund(db, code)
    h = _holding(db, acc, code)
    h.own_units, h.state_units, h.own_cost = body.own_units, body.state_units, body.own_cost
    db.add(BESEvent(account_id=acc.id, event_date=today_tr(), kind="adjust", fund_code=code,
                    units=body.own_units + body.state_units, note="Pay adedi elle girildi"))
    db.commit()
    db.refresh(acc)
    return _out(db, acc)


@router.delete("/{bes_id}/holdings/{fund_code}", response_model=BESItem)
def delete_holding(bes_id: int, fund_code: str, db: Session = Depends(get_db)):
    acc = _get(db, bes_id)
    code = _norm(fund_code)
    h = next((x for x in acc.holdings if x.fund_code == code), None)
    if h is None:
        raise HTTPException(status_code=404, detail="Bu hesapta böyle bir fon yok")
    acc.holdings.remove(h)
    db.add(BESEvent(account_id=acc.id, event_date=today_tr(), kind="adjust", fund_code=code, note="Fon hesaptan kaldırıldı"))
    db.commit()
    db.refresh(acc)
    return _out(db, acc)


@router.post("/{bes_id}/switch", response_model=BESItem)
def switch_fund(bes_id: int, body: SwitchIn, db: Session = Depends(get_db)):
    """Bir fondaki payın yüzde kadarını başka fona aktarır (değer korunur, adet yeni fiyata göre hesaplanır)."""
    acc = _get(db, bes_id)
    src_code, dst_code = _norm(body.from_fund), _norm(body.to_fund)
    if src_code == dst_code:
        raise HTTPException(status_code=422, detail="Kaynak ve hedef fon aynı olamaz.")
    src = next((x for x in acc.holdings if x.fund_code == src_code), None)
    if src is None:
        raise HTTPException(status_code=404, detail=f"{src_code} bu hesapta yok.")
    _ensure_fund(db, dst_code)
    db.flush()
    funds = _funds(db)
    p_src = funds.get(src_code).price if funds.get(src_code) else None
    p_dst = funds.get(dst_code).price if funds.get(dst_code) else None
    if not p_src or not p_dst:
        raise HTTPException(status_code=422, detail="Fon fiyatı alınamadığı için değişiklik yapılamadı. Fiyatları güncelleyip tekrar dene.")
    frac = body.percent / 100.0
    own_u, st_u, cost = src.own_units * frac, src.state_units * frac, src.own_cost * frac
    dst = _holding(db, acc, dst_code)
    dst.own_units = (dst.own_units or 0.0) + own_u * p_src / p_dst
    dst.state_units = (dst.state_units or 0.0) + st_u * p_src / p_dst
    dst.own_cost = (dst.own_cost or 0.0) + cost
    src.own_units -= own_u
    src.state_units -= st_u
    src.own_cost -= cost
    if src.own_units < EPS and src.state_units < EPS:
        acc.holdings.remove(src)
    db.add(BESEvent(account_id=acc.id, event_date=today_tr(), kind="switch", fund_code=dst_code,
                    amount=(own_u + st_u) * p_src, note=f"{src_code} → {dst_code} (%{body.percent:g})"))
    db.commit()
    db.refresh(acc)
    return _out(db, acc)


@router.post("/{bes_id}/reconcile", response_model=BESItem)
def reconcile(bes_id: int, body: ReconcileIn, db: Session = Depends(get_db)):
    """Ekstredeki bakiyelerle eşitler: payları oranlı olarak ölçekler (katkı toplamı değişmez)."""
    acc = _get(db, bes_id)
    item = compute_item(acc, _funds(db), today_tr())
    if item["missing_prices"]:
        raise HTTPException(status_code=422, detail=f"Fiyatı olmayan fon var ({', '.join(item['missing_prices'])}). Önce fiyatları güncelle.")
    notes = []
    if body.own_balance is not None:
        if item["own_balance"] <= 0:
            raise HTTPException(status_code=422, detail="Kendi katkı bakiyesi sıfır, oranla düzeltilemez. Fon pay adedini elle gir.")
        k = body.own_balance / item["own_balance"]
        for h in acc.holdings:
            h.own_units *= k
        notes.append(f"kendi katkı ×{k:.4f}")
    if body.state_balance is not None:
        if item["state_balance"] <= 0:
            raise HTTPException(status_code=422, detail="Devlet katkısı bakiyesi sıfır, oranla düzeltilemez. Fon pay adedini elle gir.")
        k = body.state_balance / item["state_balance"]
        for h in acc.holdings:
            h.state_units *= k
        notes.append(f"devlet katkısı ×{k:.4f}")
    if notes:
        db.add(BESEvent(account_id=acc.id, event_date=today_tr(), kind="adjust", note="Ekstreyle düzeltildi: " + ", ".join(notes)))
    db.commit()
    db.refresh(acc)
    return _out(db, acc)


@router.get("/{bes_id}/events", response_model=List[EventOut])
def list_events(bes_id: int, db: Session = Depends(get_db)):
    _get(db, bes_id)
    return (
        db.query(BESEvent).filter(BESEvent.account_id == bes_id)
        .order_by(BESEvent.event_date.desc(), BESEvent.id.desc()).limit(100).all()
    )
