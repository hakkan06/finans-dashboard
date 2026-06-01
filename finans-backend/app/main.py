from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import yfinance as yf
from tefas import Crawler
from datetime import datetime, timedelta, date
import calendar

from . import models, schemas
from .database import engine, get_db

# Bu komut veritabanını bozmadan eksik olan PortfolioHistory tablosunu otomatik yaratacak
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finans API")

# --- YENİ: TREND VE SNAPSHOT ENDPOINT'LERİ ---
@app.post("/portfolio/snapshot")
def save_snapshot(snapshot: schemas.SnapshotCreate, db: Session = Depends(get_db)):
    today = date.today()
    record = db.query(models.PortfolioHistory).filter(models.PortfolioHistory.record_date == today).first()
    net = snapshot.total_assets - snapshot.total_debts
    
    # Eğer bugün zaten bir kayıt atıldıysa (sayfa yenilendiyse) üzerine yazar, yoksa yeni kayıt atar.
    if record:
        record.total_assets = snapshot.total_assets
        record.total_debts = snapshot.total_debts
        record.net_worth = net
    else:
        new_record = models.PortfolioHistory(
            record_date=today,
            total_assets=snapshot.total_assets,
            total_debts=snapshot.total_debts,
            net_worth=net
        )
        db.add(new_record)
    db.commit()
    return {"message": "Snapshot kaydedildi."}

@app.get("/portfolio/history", response_model=list[schemas.PortfolioHistoryResponse])
def get_portfolio_history(db: Session = Depends(get_db)):
    return db.query(models.PortfolioHistory).order_by(models.PortfolioHistory.record_date).all()


@app.get("/portfolio/summary", response_model=list[schemas.PortfolioItem])
def get_portfolio_summary(db: Session = Depends(get_db)):
    assets = db.query(models.Asset).all()
    summary = []
    for asset in assets:
        txns = db.query(models.Transaction).filter(models.Transaction.asset_id == asset.id).order_by(models.Transaction.transaction_date).all()
        buy_lots = []
        for t in txns:
            if t.quantity > 0:
                buy_lots.append({'qty': t.quantity, 'price': t.unit_price})
            elif t.quantity < 0:
                sell_qty = abs(t.quantity)
                for lot in buy_lots:
                    if sell_qty <= 0: break
                    if lot['qty'] > 0:
                        if lot['qty'] >= sell_qty:
                            lot['qty'] -= sell_qty
                            sell_qty = 0
                        else:
                            sell_qty -= lot['qty']
                            lot['qty'] = 0
                            
        total_qty = 0.0
        total_net_value = 0.0
        total_tax = 0.0
        curr_price = asset.current_price or 0.0
        is_fund = (asset.asset_type == "FUND")
        
        for lot in buy_lots:
            if lot['qty'] > 0:
                total_qty += lot['qty']
                gross_val = lot['qty'] * curr_price
                profit = gross_val - (lot['qty'] * lot['price'])
                tax = (profit * 0.175) if (is_fund and profit > 0) else 0.0
                total_tax += tax
                total_net_value += (gross_val - tax)
                
        summary.append({
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "symbol": asset.symbol,
            "name": asset.name,
            "total_qty": total_qty,
            "current_price": curr_price,
            "total_tax": total_tax,
            "net_value": total_net_value,
            "last_updated": asset.last_updated
        })
    return summary

@app.post("/assets/", response_model=schemas.AssetResponse)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    db_asset = models.Asset(**asset.dict())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@app.get("/assets/", response_model=list[schemas.AssetResponse])
def read_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).all()

@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Varlık bulunamadı")
    db.query(models.Transaction).filter(models.Transaction.asset_id == asset_id).delete()
    db.delete(asset)
    db.commit()
    return {"message": f"{asset.symbol} başarıyla silindi."}

@app.post("/assets/update-prices")
def update_asset_prices(db: Session = Depends(get_db)):
    assets = db.query(models.Asset).all()
    crawler = Crawler()
    updated_count = 0
    
    for asset in assets:
        try:
            if asset.asset_type == "US_STOCK":
                hist = yf.Ticker(asset.symbol).history(period="5d")
                if not hist.empty:
                    asset.current_price = float(hist["Close"].iloc[-1])
                    asset.last_updated = datetime.now()
                    updated_count += 1
                    
            elif asset.asset_type == "FUND":
                end_date = datetime.now()
                start_date = end_date - timedelta(days=5)
                data = crawler.fetch(start=start_date.strftime("%Y-%m-%d"),
                                     end=end_date.strftime("%Y-%m-%d"),
                                     name=asset.symbol)
                if not data.empty:
                    data = data.sort_values(by="date", ascending=False)
                    asset.current_price = float(data.iloc[0]['price'])
                    asset.last_updated = datetime.now()
                    updated_count += 1

            elif asset.asset_type == "COMMODITY":
                usd_try_hist = yf.Ticker("TRY=X").history(period="5d")
                if not usd_try_hist.empty:
                    usd_try = float(usd_try_hist["Close"].iloc[-1])
                    if asset.symbol.upper() in ["ALTIN", "XAU", "GRAMALTIN"]:
                        xau_hist = yf.Ticker("GC=F").history(period="5d")
                        if not xau_hist.empty:
                            asset.current_price = (float(xau_hist["Close"].iloc[-1]) * usd_try) / 31.1034768
                            asset.last_updated = datetime.now()
                            updated_count += 1
                    elif asset.symbol.upper() in ["GUMUS", "XAG", "GRAMGUMUS"]:
                        xag_hist = yf.Ticker("SI=F").history(period="5d")
                        if not xag_hist.empty:
                            asset.current_price = (float(xag_hist["Close"].iloc[-1]) * usd_try) / 31.1034768
                            asset.last_updated = datetime.now()
                            updated_count += 1
                            
            elif asset.asset_type == "FIAT":
                if asset.symbol.upper() in ["TRY", "TL"]:
                    asset.current_price = 1.0
                    asset.last_updated = datetime.now()
                    updated_count += 1
                elif asset.symbol.upper() in ["USD", "DOLAR"]:
                    usd_hist = yf.Ticker("TRY=X").history(period="5d")
                    if not usd_hist.empty:
                        asset.current_price = float(usd_hist["Close"].iloc[-1])
                        asset.last_updated = datetime.now()
                        updated_count += 1
                elif asset.symbol.upper() in ["EUR", "EURO"]:
                    eur_hist = yf.Ticker("EURTRY=X").history(period="5d")
                    if not eur_hist.empty:
                        asset.current_price = float(eur_hist["Close"].iloc[-1])
                        asset.last_updated = datetime.now()
                        updated_count += 1

        except Exception as e:
            continue
            
    db.commit()
    return {"message": f"{updated_count} adet varlığın fiyatı güncellendi."}

@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(txn: schemas.TransactionCreate, db: Session = Depends(get_db)):
    db_txn = models.Transaction(**txn.dict())
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return db_txn

@app.post("/debts/", response_model=schemas.DebtResponse)
def create_debt(debt: schemas.DebtCreate, db: Session = Depends(get_db)):
    db_debt = models.Debt(**debt.dict())
    db.add(db_debt)
    db.commit()
    db.refresh(db_debt)
    return db_debt

@app.get("/debts/", response_model=list[schemas.DebtResponse])
def read_debts(db: Session = Depends(get_db)):
    return db.query(models.Debt).all()

@app.delete("/debts/{debt_id}")
def delete_debt(debt_id: int, db: Session = Depends(get_db)):
    debt = db.query(models.Debt).filter(models.Debt.id == debt_id).first()
    if debt:
        db.delete(debt)
        db.commit()
    return {"message": "Silindi"}

@app.put("/installments/{inst_id}/toggle")
def toggle_installment(inst_id: int, db: Session = Depends(get_db)):
    inst = db.query(models.DebtInstallment).filter(models.DebtInstallment.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Taksit bulunamadı")
    inst.is_paid = not inst.is_paid
    db.commit()
    return {"message": "Durum güncellendi", "is_paid": inst.is_paid}

@app.post("/debts/schedules/")
def create_debt_schedule(schedule: schemas.DebtScheduleCreate, db: Session = Depends(get_db)):
    new_debt = models.Debt(name=schedule.name, total_amount=schedule.total_amount)
    db.add(new_debt)
    db.commit()
    db.refresh(new_debt)
    
    installment_amount = round(schedule.total_amount / schedule.installments_count, 2)
    
    for i in range(schedule.installments_count):
        month = schedule.start_date.month - 1 + i
        year = schedule.start_date.year + month // 12
        month = month % 12 + 1
        
        last_day_of_month = calendar.monthrange(year, month)[1]
        day = min(schedule.start_date.day, last_day_of_month)
        
        new_inst = models.DebtInstallment(
            debt_id=new_debt.id,
            amount=installment_amount,
            due_date=date(year, month, day),
            is_paid=False
        )
        db.add(new_inst)
        
    db.commit()
    return {"message": f"{schedule.name} planı oluşturuldu."}
# --- YENİ EKLENEN: KUBERNETES CRONJOB İÇİN GECE OTOMASYON ENDPOINT'İ ---
@app.post("/system/daily-job")
def run_daily_job(db: Session = Depends(get_db)):
    # 1. Önce tüm piyasa fiyatlarını en güncel haliyle çek
    update_asset_prices(db)
    
    # 2. Canlı Dolar Kurunu Çek (US_STOCK varlıklarını TL'ye çevirmek için)
    usd_try = 32.20
    try:
        usd_hist = yf.Ticker("TRY=X").history(period="5d")
        if not usd_hist.empty:
            usd_try = float(usd_hist["Close"].iloc[-1])
    except:
        pass
        
    # 3. Toplam Varlıkları TL Cinsinden Hesapla
    summary = get_portfolio_summary(db)
    total_assets = 0.0
    for item in summary:
        val = item["net_value"]
        if item["asset_type"] == "US_STOCK":
            val *= usd_try
        total_assets += val
        
    # 4. Toplam Borçları Hesapla (Sadece ödenmemiş taksitler)
    total_debts = 0.0
    debts = db.query(models.Debt).all()
    for d in debts:
        for inst in d.installments:
            if not inst.is_paid:
                total_debts += inst.amount
                
    # 5. Gece Yarısı Snapshot'ını Veritabanına Yaz
    today = date.today()
    record = db.query(models.PortfolioHistory).filter(models.PortfolioHistory.record_date == today).first()
    net = total_assets - total_debts
    
    if record:
        record.total_assets = total_assets
        record.total_debts = total_debts
        record.net_worth = net
    else:
        new_record = models.PortfolioHistory(
            record_date=today,
            total_assets=total_assets,
            total_debts=total_debts,
            net_worth=net
        )
        db.add(new_record)
    db.commit()
    
    return {"message": "Gece otomasyonu tamamlandı", "net_worth": net}