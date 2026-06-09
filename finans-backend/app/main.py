from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import yfinance as yf
from tefas import Crawler
from datetime import datetime, timedelta, date, timezone
from dateutil.relativedelta import relativedelta

from . import models, schemas
from .database import engine, get_db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

TR_TZ = timezone(timedelta(hours=3))

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finans API")

_last_price_update = None
MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")

def send_mail(subject: str, body: str):
    if not MAIL_USER or not MAIL_PASSWORD:
        print("Mail ayarları eksik. Mail gönderimi atlandı.")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = MAIL_USER
        msg["To"] = MAIL_USER
        msg.attach(MIMEText(body, "html"))
        
        # Kritik Düzeltme 1: timeout=10 eklendi. Ağ engellenirse sonsuza kadar beklemez, 10 saniye sonra hataya (except) düşer.
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_USER, MAIL_USER, msg.as_string())
            print("Arka plan görevi: Mail başarıyla gönderildi!")
            
    except Exception as e:
        print(f"Arka plan görevi başarısız: Mail gönderilemedi: {e}")

# Kritik Düzeltme 2: Parametrelere 'background_tasks' eklendi
@app.post("/system/daily-job")
def run_daily_job(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    update_asset_prices(db)
    usd_try = 32.20
    try:
        usd_hist = yf.Ticker("TRY=X").history(period="5d")
        if not usd_hist.empty:
            usd_try = float(usd_hist["Close"].iloc[-1])
    except:
        pass

    summary = get_portfolio_summary(db)
    total_assets = 0.0
    for item in summary:
        val = item["net_value"]
        if item["asset_type"] == "US_STOCK":
            val *= usd_try
        total_assets += val

    total_debts = 0.0
    debts = db.query(models.Debt).all()
    for d in debts:
        for inst in d.installments:
            if not inst.is_paid:
                total_debts += inst.amount

    today = datetime.now(TR_TZ).date()
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

    # Bugün vadesi gelen veya gecikmiş taksitleri bul
    bugun = datetime.now(TR_TZ).date()
    bildirim_satirlari = []

    tum_borclar = db.query(models.Debt).all()
    for d in tum_borclar:
        for inst in d.installments:
            if not inst.is_paid:
                kalan = (inst.due_date - bugun).days
                if kalan < 0:
                    bildirim_satirlari.append(
                        f"<tr style='color:#c0392b'><td>{d.name}</td><td>₺{inst.amount:,.2f}</td>"
                        f"<td>{inst.due_date}</td><td>🔴 {abs(kalan)} gün gecikmiş</td></tr>"
                    )
                elif kalan <= 3:
                    bildirim_satirlari.append(
                        f"<tr style='color:#e67e22'><td>{d.name}</td><td>₺{inst.amount:,.2f}</td>"
                        f"<td>{inst.due_date}</td><td>⚠️ {kalan} gün kaldı</td></tr>"
                    )

    if bildirim_satirlari:
        tablo = "".join(bildirim_satirlari)
        body = f"""
        <html><body>
        <h2>💰 Finans Dashboard — Günlük Borç Bildirimi</h2>
        <p>Aşağıdaki taksitler için işlem yapmanız gerekiyor:</p>
        <table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;width:100%'>
            <tr style='background:#2962FF;color:white'>
                <th>Borç Adı</th><th>Tutar</th><th>Vade Tarihi</th><th>Durum</th>
            </tr>
            {tablo}
        </table>
        <br>
        <p>Net Servet: <b>₺{net:,.2f}</b></p>
        </body></html>
        """
        # Kritik Düzeltme 3: Mail fonksiyonunu bloklayıcı şekilde çağırmak yerine kuyruğa ekliyoruz.
        background_tasks.add_task(send_mail, "🔔 Finans Dashboard — Borç Bildirimi", body)
        
    return {"message": "Gece otomasyonu tamamlandı", "net_worth": net}


@app.post("/portfolio/snapshot")
def save_snapshot(snapshot: schemas.SnapshotCreate, db: Session = Depends(get_db)):
    today = datetime.now(TR_TZ).date()
    record = db.query(models.PortfolioHistory).filter(models.PortfolioHistory.record_date == today).first()
    net = snapshot.total_assets - snapshot.total_debts

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
        txns = db.query(models.Transaction).filter(
            models.Transaction.asset_id == asset.id
        ).order_by(models.Transaction.transaction_date).all()

        buy_lots = []
        for t in txns:
            if t.quantity > 0:
                buy_lots.append({'qty': t.quantity, 'price': t.unit_price})
            elif t.quantity < 0:
                sell_qty = abs(t.quantity)
                for lot in buy_lots:
                    if sell_qty <= 0:
                        break
                    if lot['qty'] >= sell_qty:
                        lot['qty'] -= sell_qty
                        sell_qty = 0
                    else:
                        sell_qty -= lot['qty']
                        lot['qty'] = 0

        total_qty = 0.0
        total_net_value = 0.0
        total_tax = 0.0
        total_cost = 0.0
        curr_price = asset.current_price or 0.0
        is_fund = (asset.asset_type == "FUND")

        for lot in buy_lots:
            if lot['qty'] > 0:
                total_qty += lot['qty']
                cost = lot['qty'] * lot['price']
                total_cost += cost
                gross_val = lot['qty'] * curr_price
                profit = gross_val - cost
                tax = (profit * 0.175) if (is_fund and profit > 0) else 0.0
                total_tax += tax
                total_net_value += (gross_val - tax)

        # 🚀 YENİ EKLENEN MANTIK: Eğer eldeki miktar sıfırsa (veya küsurat hatası sınırındaysa), özete ekleme ve atla.
        if total_qty <= 0.0001:
            continue

        summary.append({
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "symbol": asset.symbol,
            "name": asset.name,
            "total_qty": total_qty,
            "current_price": curr_price,
            "previous_price": asset.previous_price,
            "total_cost": total_cost,
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
    global _last_price_update
    now = datetime.now(TR_TZ)

    if _last_price_update and (now - _last_price_update).seconds < 60:
        kalan = 60 - (now - _last_price_update).seconds
        raise HTTPException(
            status_code=429,
            detail=f"Çok sık istek. {kalan} saniye sonra tekrar deneyin."
        )

    _last_price_update = now
    assets = db.query(models.Asset).all()
    crawler = Crawler()
    updated_count = 0

    for asset in assets:
        try:
            if asset.asset_type == "US_STOCK":
                hist = yf.Ticker(asset.symbol).history(period="5d")
                if not hist.empty:
                    if len(hist) > 1:
                        asset.previous_price = float(hist["Close"].iloc[-2])
                    asset.current_price = float(hist["Close"].iloc[-1])
                    asset.last_updated = datetime.now(TR_TZ)
                    updated_count += 1

            elif asset.asset_type == "TR_STOCK":
                # .strip() ile yanlışlıkla girilen boşlukları temizliyoruz
                bist_symbol = asset.symbol.strip().upper()
                if not bist_symbol.endswith(".IS"):
                    bist_symbol += ".IS"
                
                # Tatilleri atlaması için 7 günlük veri çekip NaN olanları siliyoruz
                hist = yf.Ticker(bist_symbol).history(period="7d")
                if not hist.empty and "Close" in hist:
                    valid_closes = hist["Close"].dropna()
                    if not valid_closes.empty:
                        if len(valid_closes) > 1:
                            asset.previous_price = float(valid_closes.iloc[-2])
                        asset.current_price = float(valid_closes.iloc[-1])
                        asset.last_updated = datetime.now(TR_TZ)
                        updated_count += 1

            elif asset.asset_type == "FUND":
                end_date = datetime.now(TR_TZ)
                start_date = end_date - timedelta(days=5)
                data = crawler.fetch(
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    name=asset.symbol
                )
                if not data.empty:
                    data = data.sort_values(by="date", ascending=False)
                    if len(data) > 1:
                        asset.previous_price = float(data.iloc[1]['price'])
                    asset.current_price = float(data.iloc[0]['price'])
                    asset.last_updated = datetime.now(TR_TZ)
                    updated_count += 1

            elif asset.asset_type == "COMMODITY":
                usd_try_hist = yf.Ticker("TRY=X").history(period="5d")
                if not usd_try_hist.empty:
                    usd_try = float(usd_try_hist["Close"].iloc[-1])
                    if asset.symbol.upper() in ["ALTIN", "XAU", "GRAMALTIN"]:
                        xau_hist = yf.Ticker("GC=F").history(period="5d")
                        if not xau_hist.empty:
                            if len(xau_hist) > 1 and len(usd_try_hist) > 1:
                                asset.previous_price = (float(xau_hist["Close"].iloc[-2]) * float(usd_try_hist["Close"].iloc[-2])) / 31.1034768
                            asset.current_price = (float(xau_hist["Close"].iloc[-1]) * usd_try) / 31.1034768
                            asset.last_updated = datetime.now(TR_TZ)
                            updated_count += 1
                    elif asset.symbol.upper() in ["GUMUS", "XAG", "GRAMGUMUS"]:
                        xag_hist = yf.Ticker("SI=F").history(period="5d")
                        if not xag_hist.empty:
                            if len(xag_hist) > 1 and len(usd_try_hist) > 1:
                                asset.previous_price = (float(xag_hist["Close"].iloc[-2]) * float(usd_try_hist["Close"].iloc[-2])) / 31.1034768
                            asset.current_price = (float(xag_hist["Close"].iloc[-1]) * usd_try) / 31.1034768
                            asset.last_updated = datetime.now(TR_TZ)
                            updated_count += 1

            elif asset.asset_type == "FIAT":
                if asset.symbol.upper() in ["TRY", "TL"]:
                    asset.previous_price = 1.0
                    asset.current_price = 1.0
                    asset.last_updated = datetime.now(TR_TZ)
                    updated_count += 1
                elif asset.symbol.upper() in ["USD", "DOLAR"]:
                    usd_hist = yf.Ticker("TRY=X").history(period="5d")
                    if not usd_hist.empty:
                        if len(usd_hist) > 1:
                            asset.previous_price = float(usd_hist["Close"].iloc[-2])
                        asset.current_price = float(usd_hist["Close"].iloc[-1])
                        asset.last_updated = datetime.now(TR_TZ)
                        updated_count += 1
                elif asset.symbol.upper() in ["EUR", "EURO"]:
                    eur_hist = yf.Ticker("EURTRY=X").history(period="5d")
                    if not eur_hist.empty:
                        if len(eur_hist) > 1:
                            asset.previous_price = float(eur_hist["Close"].iloc[-2])
                        asset.current_price = float(eur_hist["Close"].iloc[-1])
                        asset.last_updated = datetime.now(TR_TZ)
                        updated_count += 1

        except Exception:
            continue

    db.commit()
    return {"message": f"{updated_count} adet varlığın fiyatı güncellendi."}


@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(txn: schemas.TransactionCreate, db: Session = Depends(get_db)):
    if txn.quantity < 0:
        txns = db.query(models.Transaction).filter(
            models.Transaction.asset_id == txn.asset_id
        ).order_by(models.Transaction.transaction_date).all()

        buy_lots = []
        for t in txns:
            if t.quantity > 0:
                buy_lots.append({'qty': t.quantity, 'price': t.unit_price})
            elif t.quantity < 0:
                sell_qty = abs(t.quantity)
                for lot in buy_lots:
                    if sell_qty <= 0:
                        break
                    if lot['qty'] >= sell_qty:
                        lot['qty'] -= sell_qty
                        sell_qty = 0
                    else:
                        sell_qty -= lot['qty']
                        lot['qty'] = 0

        available_qty = sum(lot['qty'] for lot in buy_lots)
        requested_sell = abs(txn.quantity)

        if requested_sell > available_qty:
            raise HTTPException(
                status_code=400,
                detail=f"Yetersiz lot: Satmaya çalıştığınız miktar ({requested_sell:.4f}) "
                       f"eldeki miktarı ({available_qty:.4f}) aşıyor."
            )

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
        due_date = schedule.start_date + relativedelta(months=i)

        if i == schedule.installments_count - 1:
            already_paid = installment_amount * (schedule.installments_count - 1)
            amount = round(schedule.total_amount - already_paid, 2)
        else:
            amount = installment_amount

        new_inst = models.DebtInstallment(
            debt_id=new_debt.id,
            amount=amount,
            due_date=due_date,
            is_paid=False
        )
        db.add(new_inst)

    db.commit()
    return {"message": f"{schedule.name} planı oluşturuldu."}