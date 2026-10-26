import html
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from typing import Optional

from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, prices, schemas, services
from .database import engine, get_db
from .services import LedgerError, today_tr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("finans-api")

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finans API")

MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")

# Elle "Fiyatları güncelle" için basit sıklık sınırı (gece görevi bunu kullanmaz).
_MANUAL_REFRESH_COOLDOWN = 20
_last_manual_refresh = None


# ─────────────────────────────────────────────────────────────────────
# Sağlık / özet
# ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/overview", response_model=schemas.OverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    """Tek çağrıda panonun üst kartları: toplamlar, günlük değişim, bu ay ödenecek, dağılım."""
    return services.build_overview(db)


# ─────────────────────────────────────────────────────────────────────
# Mail
# ─────────────────────────────────────────────────────────────────────
def send_mail(subject: str, body: str):
    if not MAIL_USER or not MAIL_PASSWORD:
        logger.info("Mail ayarları eksik, gönderim atlandı.")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = MAIL_USER
        msg["To"] = MAIL_USER
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_USER, MAIL_USER, msg.as_string())
        logger.info("Borç bildirimi maili gönderildi.")
    except Exception as e:  # noqa: BLE001
        logger.warning("Mail gönderilemedi: %r", e)


def _due_mail_rows(db: Session) -> list[str]:
    today = today_tr()
    rows: list[str] = []
    q = (
        db.query(models.DebtInstallment)
        .filter(models.DebtInstallment.is_paid.is_(False))
        .order_by(models.DebtInstallment.due_date)
        .all()
    )
    for inst in q:
        left = (inst.due_date - today).days
        name = html.escape(inst.debt.name if inst.debt else "?")
        if left < 0:
            rows.append(
                f"<tr style='color:#c0392b'><td>{name}</td><td>₺{inst.amount:,.2f}</td>"
                f"<td>{inst.due_date}</td><td>🔴 {abs(left)} gün gecikmiş</td></tr>"
            )
        elif left <= 3:
            rows.append(
                f"<tr style='color:#e67e22'><td>{name}</td><td>₺{inst.amount:,.2f}</td>"
                f"<td>{inst.due_date}</td><td>⚠️ {left} gün kaldı</td></tr>"
            )
    return rows


# ─────────────────────────────────────────────────────────────────────
# Gece görevi
# ─────────────────────────────────────────────────────────────────────
@app.post("/system/daily-job")
def run_daily_job(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Fiyatları günceller, günün kaydını yazar, vadesi yaklaşan taksitler için mail atar."""
    try:
        prices.refresh_all(db)
    except Exception as e:  # noqa: BLE001  — fiyat hatası kaydı engellemesin
        logger.warning("Gece görevinde fiyat güncellemesi başarısız: %r", e)

    ov = services.build_overview(db)
    if ov["fx_missing"]:
        logger.warning("USD/TRY kuru alınamadı; bugünün kaydı yazılmadı.")
    else:
        services.save_snapshot(db, ov["total_assets"], ov["total_debts"])

    rows = _due_mail_rows(db)
    if rows:
        body = f"""
        <html><body>
        <h2>💰 Finans Dashboard — Günlük Borç Bildirimi</h2>
        <p>Aşağıdaki taksitler için işlem yapmanız gerekiyor:</p>
        <table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;width:100%'>
          <tr style='background:#2962FF;color:white'>
            <th>Borç Adı</th><th>Tutar</th><th>Vade Tarihi</th><th>Durum</th>
          </tr>
          {''.join(rows)}
        </table>
        <br><p>Net Servet: <b>₺{ov['net_worth']:,.2f}</b></p>
        </body></html>
        """
        background_tasks.add_task(send_mail, "🔔 Finans Dashboard — Borç Bildirimi", body)

    return {"message": "Gece otomasyonu tamamlandı", "net_worth": ov["net_worth"]}


# ─────────────────────────────────────────────────────────────────────
# Portföy geçmişi / özet
# ─────────────────────────────────────────────────────────────────────
@app.post("/portfolio/snapshot")
def save_snapshot(snapshot: Optional[schemas.SnapshotCreate] = Body(default=None), db: Session = Depends(get_db)):
    """Bugünün kaydını yazar. Gövde verilmezse değerler sunucuda hesaplanır (önerilen)."""
    if snapshot is None:
        ov = services.build_overview(db)
        if ov["fx_missing"]:
            raise HTTPException(status_code=503, detail="Dolar kuru şu an alınamıyor; kayıt yazılmadı. Biraz sonra tekrar dene.")
        services.save_snapshot(db, ov["total_assets"], ov["total_debts"])
    else:
        services.save_snapshot(db, snapshot.total_assets, snapshot.total_debts)
    return {"message": "Snapshot kaydedildi."}


@app.get("/portfolio/history", response_model=list[schemas.PortfolioHistoryResponse])
def get_portfolio_history(db: Session = Depends(get_db)):
    return db.query(models.PortfolioHistory).order_by(models.PortfolioHistory.record_date).all()


@app.delete("/portfolio/history/{record_date}")
def delete_history_point(record_date: date, db: Session = Depends(get_db)):
    """Yanlış kaydedilmiş bir günün noktasını siler (grafikten aykırı değeri temizlemek için)."""
    rec = db.query(models.PortfolioHistory).filter(models.PortfolioHistory.record_date == record_date).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    db.delete(rec)
    db.commit()
    return {"message": "Silindi"}


@app.get("/portfolio/summary", response_model=list[schemas.PortfolioItem])
def get_portfolio_summary(include_empty: bool = Query(False), db: Session = Depends(get_db)):
    usd = services.get_usd_try(db)
    return services.portfolio_items(db, include_empty=include_empty, usd=usd)


# ─────────────────────────────────────────────────────────────────────
# Varlıklar
# ─────────────────────────────────────────────────────────────────────
@app.post("/assets/", response_model=schemas.AssetResponse)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    """Varlığı ekler ve fiyatı hemen çekmeyi dener (current_price boş dönerse sembol bulunamadı)."""
    data = asset.model_dump()
    data["symbol"] = data["symbol"].strip().upper()
    data["name"] = data["name"].strip() or data["symbol"]
    if not data["symbol"]:
        raise HTTPException(status_code=400, detail="Sembol boş olamaz.")
    db_asset = models.Asset(**data)
    db.add(db_asset)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Bu sembole sahip varlık zaten sistemde mevcut.")
    prices.refresh_asset(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


@app.get("/assets/", response_model=list[schemas.AssetResponse])
def read_assets(db: Session = Depends(get_db)):
    return db.query(models.Asset).order_by(models.Asset.id).all()


@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Varlık bulunamadı")
    symbol = asset.symbol
    db.query(models.Transaction).filter(models.Transaction.asset_id == asset_id).delete()
    db.delete(asset)
    db.commit()
    return {"message": f"{symbol} başarıyla silindi."}


@app.post("/assets/update-prices")
def update_asset_prices(db: Session = Depends(get_db)):
    """Tüm fiyatları günceller ve bugünün kaydını sunucuda yazar."""
    global _last_manual_refresh
    now = services.now_tr()
    if _last_manual_refresh and (now - _last_manual_refresh).total_seconds() < _MANUAL_REFRESH_COOLDOWN:
        left = int(_MANUAL_REFRESH_COOLDOWN - (now - _last_manual_refresh).total_seconds()) + 1
        raise HTTPException(status_code=429, detail=f"Çok sık istek. {left} saniye sonra tekrar deneyin.")
    _last_manual_refresh = now

    updated, failed = prices.refresh_all(db)
    ov = services.build_overview(db)
    if not ov["fx_missing"]:
        services.save_snapshot(db, ov["total_assets"], ov["total_debts"])
    return {
        "message": f"{updated} adet varlığın fiyatı güncellendi.",
        "updated": updated,
        "failed": failed,
    }


# ─────────────────────────────────────────────────────────────────────
# İşlemler (alım / satım)
# ─────────────────────────────────────────────────────────────────────
def _asset_txns(db: Session, asset_id: int) -> list[services.Txn]:
    rows = db.query(models.Transaction).filter(models.Transaction.asset_id == asset_id).all()
    return [services.to_txn(t) for t in rows]


def _validate(old: list[services.Txn], new: list[services.Txn]):
    try:
        services.check_mutation(old, new)
    except LedgerError as e:
        raise HTTPException(status_code=400, detail=f"Yetersiz miktar: {e}")


@app.get("/transactions/", response_model=list[schemas.TransactionResponse])
def read_transactions(asset_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Transaction)
    if asset_id is not None:
        q = q.filter(models.Transaction.asset_id == asset_id)
    return q.order_by(models.Transaction.transaction_date.desc(), models.Transaction.id.desc()).all()


@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(txn: schemas.TransactionCreate, db: Session = Depends(get_db)):
    if not db.query(models.Asset).filter(models.Asset.id == txn.asset_id).first():
        raise HTTPException(status_code=404, detail="Varlık bulunamadı")
    if abs(txn.quantity) < 1e-9:
        raise HTTPException(status_code=400, detail="Miktar sıfır olamaz.")
    old = _asset_txns(db, txn.asset_id)
    _validate(old, old + [services.Txn(txn.quantity, txn.unit_price, txn.transaction_date)])
    db_txn = models.Transaction(**txn.model_dump())
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return db_txn


@app.put("/transactions/{txn_id}", response_model=schemas.TransactionResponse)
def update_transaction(txn_id: int, body: schemas.TransactionUpdate, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="İşlem bulunamadı")
    if abs(body.quantity) < 1e-9:
        raise HTTPException(status_code=400, detail="Miktar sıfır olamaz.")
    old = _asset_txns(db, txn.asset_id)
    new = [t for t in old if t.id != txn_id] + [
        services.Txn(body.quantity, body.unit_price, body.transaction_date, txn_id)
    ]
    _validate(old, new)
    txn.quantity, txn.unit_price, txn.transaction_date = body.quantity, body.unit_price, body.transaction_date
    db.commit()
    db.refresh(txn)
    return txn


@app.delete("/transactions/{txn_id}")
def delete_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="İşlem bulunamadı")
    old = _asset_txns(db, txn.asset_id)
    _validate(old, [t for t in old if t.id != txn_id])
    db.delete(txn)
    db.commit()
    return {"message": "İşlem silindi."}


# ─────────────────────────────────────────────────────────────────────
# Borçlar
# ─────────────────────────────────────────────────────────────────────
@app.post("/debts/", response_model=schemas.DebtResponse)
def create_debt(debt: schemas.DebtCreate, db: Session = Depends(get_db)):
    db_debt = models.Debt(**debt.model_dump())
    db.add(db_debt)
    db.commit()
    db.refresh(db_debt)
    return db_debt


@app.get("/debts/", response_model=list[schemas.DebtResponse])
def read_debts(db: Session = Depends(get_db)):
    return db.query(models.Debt).order_by(models.Debt.id).all()


@app.delete("/debts/{debt_id}")
def delete_debt(debt_id: int, db: Session = Depends(get_db)):
    debt = db.query(models.Debt).filter(models.Debt.id == debt_id).first()
    if not debt:
        raise HTTPException(status_code=404, detail="Borç bulunamadı")
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
    if schedule.total_amount <= 0:
        raise HTTPException(status_code=400, detail="Tutar sıfırdan büyük olmalı.")
    if not 1 <= schedule.installments_count <= 480:
        raise HTTPException(status_code=400, detail="Taksit sayısı 1 ile 480 arasında olmalı.")
    if schedule.interest_rate < 0:
        raise HTTPException(status_code=400, detail="Faiz oranı negatif olamaz.")
    if schedule.group_id is not None and not db.get(models.DebtGroup, schedule.group_id):
        raise HTTPException(status_code=404, detail="Grup bulunamadı")

    start = schedule.start_date or today_tr()
    plan = services.build_installments(
        schedule.total_amount, schedule.installments_count, schedule.interest_rate, start
    )
    total_repayment = round(sum(a for _, a in plan), 2)

    new_debt = models.Debt(name=schedule.name.strip(), total_amount=total_repayment, group_id=schedule.group_id)
    db.add(new_debt)
    db.flush()
    for due, amount in plan:
        db.add(models.DebtInstallment(debt_id=new_debt.id, amount=amount, due_date=due, is_paid=False))
    db.commit()
    return {
        "message": f"{new_debt.name} planı oluşturuldu.",
        "debt_id": new_debt.id,
        "total_repayment": total_repayment,
        "installment_amount": plan[0][1],
    }


# ─────────────────────────────────────────────────────────────────────
# Borç grupları
# ─────────────────────────────────────────────────────────────────────
def _compute_group_stats(group: models.DebtGroup) -> dict:
    paid = remaining = 0.0
    for debt in group.debts:
        for inst in debt.installments:
            if inst.is_paid:
                paid += inst.amount
            else:
                remaining += inst.amount
    total = paid + remaining
    return {
        "total_paid": paid,
        "total_remaining": remaining,
        "progress_pct": round(paid / total * 100, 2) if total > 0 else 0.0,
    }


def _group_response(g: models.DebtGroup) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "contracted_amount": g.contracted_amount,
        "debts": g.debts,
        **_compute_group_stats(g),
    }


@app.post("/debt-groups/", response_model=schemas.DebtGroupResponse)
def create_debt_group(group: schemas.DebtGroupCreate, db: Session = Depends(get_db)):
    db_group = models.DebtGroup(**group.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return _group_response(db_group)


@app.get("/debt-groups/", response_model=list[schemas.DebtGroupResponse])
def read_debt_groups(db: Session = Depends(get_db)):
    return [_group_response(g) for g in db.query(models.DebtGroup).order_by(models.DebtGroup.id).all()]


@app.delete("/debt-groups/{group_id}")
def delete_debt_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(models.DebtGroup).filter(models.DebtGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Grup bulunamadı")
    for debt in group.debts:  # borçları silme, sadece gruptan çıkar
        debt.group_id = None
    name = group.name
    db.delete(group)
    db.commit()
    return {"message": f"'{name}' grubu silindi, borçlar korundu."}


@app.put("/debts/{debt_id}/assign-group")
def assign_debt_to_group(debt_id: int, payload: schemas.AssignGroupRequest, db: Session = Depends(get_db)):
    debt = db.query(models.Debt).filter(models.Debt.id == debt_id).first()
    if not debt:
        raise HTTPException(status_code=404, detail="Borç bulunamadı")
    group = None
    if payload.group_id is not None:
        group = db.query(models.DebtGroup).filter(models.DebtGroup.id == payload.group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Grup bulunamadı")
    debt.group_id = payload.group_id
    db.commit()
    action = f"'{group.name}' grubuna atandı" if group else "gruptan çıkarıldı"
    return {"message": f"'{debt.name}' {action}."}
