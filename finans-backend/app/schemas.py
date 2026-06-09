from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional

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

class AssetBase(BaseModel):
    asset_type: str
    symbol: str
    name: str

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    current_price: Optional[float] = None
    last_updated: Optional[datetime] = None
    class Config:
        from_attributes = True

class PortfolioItem(BaseModel):
    asset_id: int
    asset_type: str
    symbol: str
    name: str
    total_qty: float
    current_price: float
    total_cost: float
    total_tax: float
    net_value: float
    last_updated: Optional[datetime] = None

class InstallmentBase(BaseModel):
    amount: float
    due_date: date
    is_paid: bool = False

class InstallmentCreate(InstallmentBase):
    pass

class InstallmentResponse(InstallmentBase):
    id: int
    debt_id: int
    class Config:
        from_attributes = True

class DebtBase(BaseModel):
    name: str
    total_amount: float

class DebtCreate(DebtBase):
    pass

class DebtResponse(DebtBase):
    id: int
    installments: List[InstallmentResponse] = []
    class Config:
        from_attributes = True

class DebtScheduleCreate(BaseModel):
    name: str
    total_amount: float
    installments_count: int
    interest_rate: float = 0.0
    start_date: date = date.today()

class DebtScheduleResponse(BaseModel):
    message: str
    class Config:
        from_attributes = True

# --- YENİ: SNAPSHOT ŞEMALARI ---
class SnapshotCreate(BaseModel):
    total_assets: float
    total_debts: float

class PortfolioHistoryResponse(BaseModel):
    record_date: date
    total_assets: float
    total_debts: float
    net_worth: float
    class Config:
        from_attributes = True