"""BES (Bireysel Emeklilik Sistemi) modülü.

Model + şema + hak ediş hesabı + endpoint'ler tek dosyada.
main.py bu modülü create_all'dan ÖNCE import eder ve router'ı ekler.
"""
from datetime import date
from typing import List, Optional

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Date, Float, Integer, String
from sqlalchemy.orm import Session

from .database import get_db
from .models import Base
from .services import today_tr

# --- KURALLAR (mevzuat değişirse sadece burayı güncelleyin) -----------------
# Devlet katkısı hak ediş kademeleri: (sistemde geçen yıl, hak edilen oran)
VESTING_TIERS = [(3, 0.15), (6, 0.35), (10, 0.60)]
# 10 yıl + 56 yaş (emeklilik hakkı) => %100
RETIREMENT_RATIO = 1.00
# Stopaj varsayımları (kontrol edip gerekirse değiştirin)
EARLY_EXIT_TAX = 0.15   # emeklilik şartı oluşmadan ayrılma
RETIREMENT_TAX = 0.05   # emeklilik şartlarıyla çıkış


# --- MODEL ------------------------------------------------------------------
class BESAccount(Base):
    __tablename__ = "bes_accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)                 # Örn: "Anadolu Hayat BES"
    company = Column(String, nullable=True)
    # Hak ediş sayacı SİSTEME İLK GİRİŞ tarihinden işler (şirket sözleşme tarihinden değil)
    system_entry_date = Column(Date)
    contract_start_date = Column(Date, nullable=True)  # bilgi amaçlı
    own_principal = Column(Float, default=0.0)         # kendi ödediğiniz toplam katkı
    own_balance = Column(Float, default=0.0)           # kendi katkı + getirisi (ekstredeki güncel)
    state_balance = Column(Float, default=0.0)         # devlet katkısı + getirisi (ekstredeki güncel)
    retirement_eligible = Column(Boolean, default=False)  # 10 yıl + 56 yaş şartı sağlandı mı
    balance_updated = Column(Date, nullable=True)


# --- ŞEMALAR ----------------------------------------------------------------
MIN_ENTRY = date(2003, 1, 1)  # BES'in başladığı yıl


class BESCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company: Optional[str] = Field(default=None, max_length=120)
    system_entry_date: date
    contract_start_date: Optional[date] = None
    own_principal: float = Field(default=0.0, ge=0)
    own_balance: float = Field(default=0.0, ge=0)
    state_balance: float = Field(default=0.0, ge=0)
    retirement_eligible: bool = False


class BESUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    company: Optional[str] = Field(default=None, max_length=120)
    system_entry_date: Optional[date] = None
    contract_start_date: Optional[date] = None
    own_principal: Optional[float] = Field(default=None, ge=0)
    own_balance: Optional[float] = Field(default=None, ge=0)
    state_balance: Optional[float] = Field(default=None, ge=0)
    retirement_eligible: Optional[bool] = None


class Milestone(BaseModel):
    years: int
    due_date: date
    ratio: float
    reached: bool


class BESItem(BaseModel):
    id: int
    name: str
    company: Optional[str] = None
    system_entry_date: date
    contract_start_date: Optional[date] = None
    years_in_system: float
    own_principal: float
    own_balance: float
    state_balance: float
    total_balance: float
    vest_ratio: float
    vested_state: float
    forfeited_state: float
    tax: float
    net_value: float
    retirement_eligible: bool
    next_milestone: Optional[Milestone] = None
    days_to_next: Optional[int] = None
    gain_at_next: Optional[float] = None
    milestones: List[Milestone] = []
    balance_updated: Optional[date] = None


# --- HESAPLAMA --------------------------------------------------------------
def vesting_ratio(entry: date, today: date, retirement_eligible: bool) -> float:
    if retirement_eligible:
        return RETIREMENT_RATIO
    ratio = 0.0
    for years, r in VESTING_TIERS:
        if today >= entry + relativedelta(years=years):
            ratio = r
    return ratio


def compute_item(acc: BESAccount, today: date) -> dict:
    own_principal = acc.own_principal or 0.0
    own_balance = acc.own_balance or 0.0
    state_balance = acc.state_balance or 0.0
    ratio = vesting_ratio(acc.system_entry_date, today, bool(acc.retirement_eligible))
    tax_rate = RETIREMENT_TAX if acc.retirement_eligible else EARLY_EXIT_TAX

    own_yield = max(own_balance - own_principal, 0.0)
    vested_state = state_balance * ratio
    forfeited = state_balance - vested_state
    tax = (own_yield + vested_state) * tax_rate
    net_value = own_balance + vested_state - tax

    milestones = []
    for years, r in VESTING_TIERS:
        d = acc.system_entry_date + relativedelta(years=years)
        milestones.append(Milestone(years=years, due_date=d, ratio=r, reached=today >= d))

    next_ms = next((m for m in milestones if not m.reached), None)
    days_to_next = (next_ms.due_date - today).days if next_ms and not acc.retirement_eligible else None
    gain_at_next = None
    if next_ms and not acc.retirement_eligible:
        gain_at_next = state_balance * (next_ms.ratio - ratio) * (1 - tax_rate)
    else:
        next_ms = None

    return dict(
        id=acc.id, name=acc.name, company=acc.company,
        system_entry_date=acc.system_entry_date, contract_start_date=acc.contract_start_date,
        years_in_system=round((today - acc.system_entry_date).days / 365.25, 2),
        own_principal=own_principal, own_balance=own_balance, state_balance=state_balance,
        total_balance=own_balance + state_balance,
        vest_ratio=ratio, vested_state=vested_state, forfeited_state=forfeited,
        tax=tax, net_value=net_value, retirement_eligible=bool(acc.retirement_eligible),
        next_milestone=next_ms, days_to_next=days_to_next, gain_at_next=gain_at_next,
        milestones=milestones, balance_updated=acc.balance_updated,
    )


# --- ENDPOINT'LER -----------------------------------------------------------
router = APIRouter(prefix="/bes", tags=["BES"])


def _check_entry(d: Optional[date], today: date):
    if d is not None and not (MIN_ENTRY <= d <= today):
        raise HTTPException(status_code=422, detail="Sisteme giriş tarihi 2003 ile bugün arasında olmalı.")


@router.get("/", response_model=List[BESItem])
def list_bes(db: Session = Depends(get_db)):
    today = today_tr()
    return [compute_item(a, today) for a in db.query(BESAccount).all()]


@router.post("/", response_model=BESItem)
def create_bes(payload: BESCreate, db: Session = Depends(get_db)):
    today = today_tr()
    _check_entry(payload.system_entry_date, today)
    acc = BESAccount(**payload.model_dump(), balance_updated=today)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return compute_item(acc, today)


@router.put("/{bes_id}", response_model=BESItem)
def update_bes(bes_id: int, payload: BESUpdate, db: Session = Depends(get_db)):
    acc = db.query(BESAccount).filter(BESAccount.id == bes_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="BES hesabı bulunamadı")
    data = payload.model_dump(exclude_unset=True)
    today = today_tr()
    _check_entry(data.get("system_entry_date"), today)
    for k, v in data.items():
        setattr(acc, k, v)
    if any(k in data for k in ("own_balance", "state_balance", "own_principal")):
        acc.balance_updated = today
    db.commit()
    db.refresh(acc)
    return compute_item(acc, today)


@router.delete("/{bes_id}")
def delete_bes(bes_id: int, db: Session = Depends(get_db)):
    acc = db.query(BESAccount).filter(BESAccount.id == bes_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="BES hesabı bulunamadı")
    db.delete(acc)
    db.commit()
    return {"message": "BES hesabı silindi."}
