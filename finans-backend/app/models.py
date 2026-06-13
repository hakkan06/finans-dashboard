from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Asset(Base):
    __tablename__ = "assets"
    id             = Column(Integer, primary_key=True, index=True)
    asset_type     = Column(String, index=True)
    symbol         = Column(String, unique=True, index=True)
    name           = Column(String)
    current_price  = Column(Float, nullable=True)
    previous_price = Column(Float, nullable=True)
    last_updated   = Column(DateTime, nullable=True)

    transactions = relationship("Transaction", back_populates="asset")


class Transaction(Base):
    __tablename__ = "transactions"
    id               = Column(Integer, primary_key=True, index=True)
    asset_id         = Column(Integer, ForeignKey("assets.id"))
    quantity         = Column(Float)
    unit_price       = Column(Float)
    transaction_date = Column(Date)

    asset = relationship("Asset", back_populates="transactions")


# ─── Borç Grubu (Kredi Grubu) ────────────────────────────────────────
# Birden fazla "bacağı" olan borçları (peşinat + taksit + ara ödeme
# gibi) tek çatı altında toplamak için üst seviye bir kapsayıcı.
class DebtGroup(Base):
    __tablename__ = "debt_groups"
    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String, index=True)       # "Faras İncek Evi"
    description       = Column(String, nullable=True)   # opsiyonel not
    contracted_amount = Column(Float, nullable=True)    # toplam sözleşme tutarı

    debts = relationship("Debt", back_populates="group")


class Debt(Base):
    __tablename__ = "debts"
    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String, index=True)
    total_amount = Column(Float)
    # Nullable → mevcut tekil borçlar group_id=NULL ile olduğu gibi çalışır
    group_id     = Column(Integer, ForeignKey("debt_groups.id"), nullable=True)

    group        = relationship("DebtGroup", back_populates="debts")
    installments = relationship("DebtInstallment", back_populates="debt", cascade="all, delete-orphan")


class DebtInstallment(Base):
    __tablename__ = "debt_installments"
    id       = Column(Integer, primary_key=True, index=True)
    debt_id  = Column(Integer, ForeignKey("debts.id"))
    amount   = Column(Float)
    due_date = Column(Date)
    is_paid  = Column(Boolean, default=False)

    debt = relationship("Debt", back_populates="installments")


# ─── Portföy Tarih Kaydı ─────────────────────────────────────────────
class PortfolioHistory(Base):
    __tablename__ = "portfolio_history"
    id           = Column(Integer, primary_key=True, index=True)
    record_date  = Column(Date, unique=True, index=True)
    total_assets = Column(Float)
    total_debts  = Column(Float)
    net_worth    = Column(Float)