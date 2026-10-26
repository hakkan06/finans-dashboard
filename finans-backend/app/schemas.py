from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional


# ─── Transaction ─────────────────────────────────────────────────────
class TransactionBase(BaseModel):
    quantity: float
    unit_price: float
    transaction_date: date

class TransactionCreate(TransactionBase):
    asset_id: int

class TransactionResponse(TransactionBase):
    id: int
    asset_id: int
    class Config:
        from_attributes = True


# ─── Asset ───────────────────────────────────────────────────────────
class AssetBase(BaseModel):
    asset_type: str
    symbol: str
    name: str

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    current_price:  Optional[float]   = None
    previous_price: Optional[float]   = None
    last_updated:   Optional[datetime] = None
    class Config:
        from_attributes = True


# ─── Portfolio ────────────────────────────────────────────────────────
class PortfolioItem(BaseModel):
    asset_id:       int
    asset_type:     str
    symbol:         str
    name:           str
    total_qty:      float
    current_price:  float
    previous_price: Optional[float]   = None
    total_cost:     float
    total_tax:      float
    net_value:      float
    last_updated:   Optional[datetime] = None
    # --- Arayüzün kur hesabı yapmaması için sunucuda hazırlanan alanlar ---
    currency:       str   = "TRY"      # fiyatın para birimi (US_STOCK → USD)
    fx:             float = 1.0        # 1 birim fiyat = fx TRY
    value_try:      float = 0.0        # net değer (TRY)
    cost_try:       float = 0.0        # maliyet (TRY)
    day_change_try: float = 0.0        # son fiyat güncellemesine göre günlük değişim (TRY)
    realized_pl:    float = 0.0        # satışlardan gerçekleşmiş kâr/zarar (FIFO, vergi öncesi, yerel para)
    has_price:      bool  = True
    has_position:   bool  = True


# ─── Installment ─────────────────────────────────────────────────────
class InstallmentBase(BaseModel):
    amount:   float
    due_date: date
    is_paid:  bool = False

class InstallmentCreate(InstallmentBase):
    pass

class InstallmentResponse(InstallmentBase):
    id:      int
    debt_id: int
    class Config:
        from_attributes = True


# ─── Debt ─────────────────────────────────────────────────────────────
class DebtBase(BaseModel):
    name:         str
    total_amount: float

class DebtCreate(DebtBase):
    pass

class DebtResponse(DebtBase):
    id:           int
    group_id:     Optional[int]                  = None
    installments: List[InstallmentResponse]      = []
    class Config:
        from_attributes = True


# ─── DebtGroup ────────────────────────────────────────────────────────
class DebtGroupCreate(BaseModel):
    name:               str
    description:        Optional[str]   = None
    contracted_amount:  Optional[float] = None

class DebtGroupResponse(BaseModel):
    id:                 int
    name:               str
    description:        Optional[str]   = None
    contracted_amount:  Optional[float] = None
    debts:              List[DebtResponse] = []
    # Computed alanlar — endpoint'te hesaplanır, modelden gelmez
    total_paid:         float = 0.0
    total_remaining:    float = 0.0
    progress_pct:       float = 0.0
    class Config:
        from_attributes = True

class AssignGroupRequest(BaseModel):
    group_id: Optional[int] = None   # None → gruptan çıkar


# ─── Debt Schedule ────────────────────────────────────────────────────
class DebtScheduleCreate(BaseModel):
    name:               str
    total_amount:       float            # faiz 0 ise toplam geri ödeme; faiz > 0 ise anapara
    installments_count: int
    interest_rate:      float = 0.0      # AYLIK faiz yüzdesi (örn. 3.5); 0 = faizsiz eşit bölme
    start_date:         Optional[date] = None   # boşsa bugün (TR saati)
    group_id:           Optional[int]  = None

class DebtScheduleResponse(BaseModel):
    message: str


# ─── Snapshot ────────────────────────────────────────────────────────
class SnapshotCreate(BaseModel):
    total_assets: float
    total_debts:  float


class TransactionUpdate(TransactionBase):
    pass


class AllocationItem(BaseModel):
    asset_type: str
    value:      float


class OverviewResponse(BaseModel):
    usd_try:          Optional[float] = None
    total_assets:     float
    total_debts:      float
    net_worth:        float
    day_change:       float
    day_change_pct:   float
    due_this_month:   float
    overdue_total:    float
    overdue_count:    int
    last_price_update: Optional[datetime] = None
    allocation:       List[AllocationItem] = []

class PortfolioHistoryResponse(BaseModel):
    record_date:  date
    total_assets: float
    total_debts:  float
    net_worth:    float
    class Config:
        from_attributes = True