from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    asset_type = Column(String, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    current_price = Column(Float, nullable=True)
    previous_price = Column(Float, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    
    transactions = relationship("Transaction", back_populates="asset")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    quantity = Column(Float)
    unit_price = Column(Float)
    transaction_date = Column(Date)
    
    asset = relationship("Asset", back_populates="transactions")

class Debt(Base):
    __tablename__ = "debts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    total_amount = Column(Float)
    
    installments = relationship("DebtInstallment", back_populates="debt", cascade="all, delete-orphan")
    schedules = relationship("DebtSchedule", back_populates="debt", cascade="all, delete-orphan")

class DebtInstallment(Base):
    __tablename__ = "debt_installments"
    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"))
    amount = Column(Float)
    due_date = Column(Date)
    is_paid = Column(Boolean, default=False)
    
    debt = relationship("Debt", back_populates="installments")

class DebtSchedule(Base):
    __tablename__ = "debt_schedules"
    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"))
    
    debt = relationship("Debt", back_populates="schedules")

# --- YENİ: ZAMAN ÇİZELGESİ (TREND) TABLOSU ---
class PortfolioHistory(Base):
    __tablename__ = "portfolio_history"
    id = Column(Integer, primary_key=True, index=True)
    record_date = Column(Date, unique=True, index=True) # Her güne 1 kayıt
    total_assets = Column(Float)
    total_debts = Column(Float)
    net_worth = Column(Float)