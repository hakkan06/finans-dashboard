from datetime import date, timedelta


def mk_asset(client, symbol="QQQM", asset_type="US_STOCK"):
    r = client.post("/assets/", json={"asset_type": asset_type, "symbol": symbol, "name": symbol})
    assert r.status_code == 200, r.text
    return r.json()


def set_price(client, asset_id, cur, prev=None):
    from app import models
    from app.database import SessionLocal

    db = SessionLocal()
    a = db.get(models.Asset, asset_id)
    a.current_price, a.previous_price = cur, prev
    db.commit()
    db.close()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_duplicate_symbol_rejected_and_symbol_normalized(client):
    a = mk_asset(client, " qqqm ")
    assert a["symbol"] == "QQQM"
    r = client.post("/assets/", json={"asset_type": "US_STOCK", "symbol": "QQQM", "name": "x"})
    assert r.status_code == 400


def test_transaction_lifecycle_and_ledger_validation(client):
    a = mk_asset(client)
    base = {"asset_id": a["id"], "unit_price": 100.0, "transaction_date": "2026-01-10"}
    buy = client.post("/transactions/", json={**base, "quantity": 10})
    assert buy.status_code == 200
    # fazla satış
    assert client.post("/transactions/", json={**base, "quantity": -11}).status_code == 400
    sell = client.post("/transactions/", json={**base, "quantity": -4, "transaction_date": "2026-02-01"})
    assert sell.status_code == 200
    # alışı silmek satışı yetim bırakır → engellenmeli
    assert client.delete(f"/transactions/{buy.json()['id']}").status_code == 400
    # satışı silince alış silinebilir
    assert client.delete(f"/transactions/{sell.json()['id']}").status_code == 200
    assert client.delete(f"/transactions/{buy.json()['id']}").status_code == 200
    assert client.get("/transactions/", params={"asset_id": a["id"]}).json() == []


def test_update_transaction(client):
    a = mk_asset(client)
    t = client.post(
        "/transactions/",
        json={"asset_id": a["id"], "quantity": 5, "unit_price": 10, "transaction_date": "2026-01-01"},
    ).json()
    r = client.put(
        f"/transactions/{t['id']}", json={"quantity": 7, "unit_price": 11, "transaction_date": "2026-01-02"}
    )
    assert r.status_code == 200 and r.json()["quantity"] == 7


def test_summary_hides_empty_unless_requested_and_overview_math(client):
    usd = mk_asset(client, "QQQM")
    gold = mk_asset(client, "ALTIN", "COMMODITY")
    mk_asset(client, "EMPTY", "TR_STOCK")
    set_price(client, usd["id"], 110.0, 100.0)  # USD; kur 40
    set_price(client, gold["id"], 3000.0, 2900.0)
    for aid, q, p in [(usd["id"], 10, 100.0), (gold["id"], 2, 2500.0)]:
        client.post(
            "/transactions/",
            json={"asset_id": aid, "quantity": q, "unit_price": p, "transaction_date": "2026-01-01"},
        )
    assert len(client.get("/portfolio/summary").json()) == 2
    assert len(client.get("/portfolio/summary", params={"include_empty": True}).json()) == 3

    ov = client.get("/overview").json()
    assert ov["usd_try"] == 40.0
    assert ov["total_assets"] == 10 * 110 * 40 + 2 * 3000
    assert ov["day_change"] == 10 * 10 * 40 + 2 * 100
    assert {a["asset_type"] for a in ov["allocation"]} == {"US_STOCK", "COMMODITY"}


def test_fund_tax_applied_on_profit_only(client):
    f = mk_asset(client, "TTE", "FUND")
    set_price(client, f["id"], 12.0)
    client.post(
        "/transactions/",
        json={"asset_id": f["id"], "quantity": 100, "unit_price": 10.0, "transaction_date": "2026-01-01"},
    )
    item = client.get("/portfolio/summary").json()[0]
    assert item["total_tax"] == 200 * 0.175
    assert item["net_value"] == 1200 - 35


def test_debt_schedule_group_progress_and_toggle(client):
    g = client.post("/debt-groups/", json={"name": "Ev"}).json()
    start = (date.today() - timedelta(days=40)).isoformat()
    r = client.post(
        "/debts/schedules/",
        json={"name": "Peşinat", "total_amount": 1000, "installments_count": 4, "start_date": start, "group_id": g["id"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_repayment"] == 1000.0
    debts = client.get("/debts/").json()
    assert debts[0]["group_id"] == g["id"] and len(debts[0]["installments"]) == 4

    inst_id = debts[0]["installments"][0]["id"]
    assert client.put(f"/installments/{inst_id}/toggle").json()["is_paid"] is True
    group = client.get("/debt-groups/").json()[0]
    assert group["total_paid"] == 250.0 and group["total_remaining"] == 750.0 and group["progress_pct"] == 25.0

    ov = client.get("/overview").json()
    assert ov["total_debts"] == 750.0
    assert ov["overdue_count"] >= 1  # 40 gün önce başlayan plan


def test_snapshot_computed_server_side_and_history(client):
    a = mk_asset(client, "USD", "FIAT")
    set_price(client, a["id"], 40.0)
    client.post(
        "/transactions/",
        json={"asset_id": a["id"], "quantity": 100, "unit_price": 30.0, "transaction_date": "2026-01-01"},
    )
    assert client.post("/portfolio/snapshot").status_code == 200
    assert client.post("/portfolio/snapshot").status_code == 200  # aynı gün upsert
    hist = client.get("/portfolio/history").json()
    assert len(hist) == 1 and hist[0]["total_assets"] == 4000.0 and hist[0]["net_worth"] == 4000.0
    assert client.delete(f"/portfolio/history/{hist[0]['record_date']}").status_code == 200


def test_delete_asset_removes_transactions(client):
    a = mk_asset(client)
    client.post(
        "/transactions/",
        json={"asset_id": a["id"], "quantity": 1, "unit_price": 1, "transaction_date": "2026-01-01"},
    )
    assert client.delete(f"/assets/{a['id']}").status_code == 200
    assert client.get("/transactions/").json() == []
    assert client.delete(f"/assets/{a['id']}").status_code == 404


# ── Satışla borç ödeme ───────────────────────────────────────────────
def _setup_sale(client):
    a = mk_asset(client, "TRY", "FIAT")
    set_price(client, a["id"], 1.0)
    base = {"asset_id": a["id"], "unit_price": 1.0, "transaction_date": "2026-03-01"}
    assert client.post("/transactions/", json={**base, "quantity": 5000}).status_code == 200
    r = client.post("/debts/schedules/", json={"name": "Kredi", "total_amount": 3000, "installments_count": 3, "start_date": "2026-01-01"})
    assert r.status_code == 200, r.text
    insts = client.get("/debts/").json()[0]["installments"]
    return a, base, insts


def test_settle_sale_pays_installments_and_creates_debts(client):
    a, base, insts = _setup_sale(client)
    r = client.post("/transactions/settle", json={
        "transaction": {**base, "quantity": -1500},
        "pay_installment_ids": [insts[0]["id"], insts[1]["id"]],
        "new_debts": [
            {"name": " Aidat ", "amount": 400, "paid": True},
            {"name": "Kira", "amount": 250, "due_date": "2026-04-01", "paid": False},
        ],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["paid_installments"] == 2 and body["created_debts"] == 2
    assert body["transaction"]["quantity"] == -1500

    debts = {d["name"]: d for d in client.get("/debts/").json()}
    assert [i["is_paid"] for i in debts["Kredi"]["installments"]] == [True, True, False]
    aidat = debts["Aidat"]["installments"][0]  # ad kırpıldı, vade = satış tarihi, ödenmiş
    assert aidat["is_paid"] and aidat["due_date"] == "2026-03-01" and aidat["amount"] == 400
    kira = debts["Kira"]["installments"][0]
    assert not kira["is_paid"] and kira["due_date"] == "2026-04-01"

    ov = client.get("/overview").json()
    assert ov["total_debts"] == 1250  # kalan kredi taksiti 1000 + ödenmemiş kira 250
    assert ov["total_assets"] == 3500  # 5000 - 1500


def test_settle_sale_is_atomic_on_ledger_error(client):
    a, base, insts = _setup_sale(client)
    r = client.post("/transactions/settle", json={
        "transaction": {**base, "quantity": -9999},  # eldekinden fazla
        "pay_installment_ids": [insts[0]["id"]],
        "new_debts": [{"name": "Aidat", "amount": 400}],
    })
    assert r.status_code == 400
    debts = client.get("/debts/").json()
    assert len(debts) == 1 and not any(i["is_paid"] for i in debts[0]["installments"])
    assert len(client.get("/transactions/", params={"asset_id": a["id"]}).json()) == 1


def test_settle_sale_rejects_bad_input(client):
    a, base, insts = _setup_sale(client)
    sell = {**base, "quantity": -100}
    # alış ile olmaz
    assert client.post("/transactions/settle", json={"transaction": {**base, "quantity": 100}}).status_code == 400
    # aynı taksit iki kez
    assert client.post("/transactions/settle", json={"transaction": sell, "pay_installment_ids": [insts[0]["id"]] * 2}).status_code == 400
    # olmayan taksit
    assert client.post("/transactions/settle", json={"transaction": sell, "pay_installment_ids": [99999]}).status_code == 404
    # geçersiz yeni borç
    assert client.post("/transactions/settle", json={"transaction": sell, "new_debts": [{"name": "  ", "amount": 5}]}).status_code == 400
    assert client.post("/transactions/settle", json={"transaction": sell, "new_debts": [{"name": "X", "amount": 0}]}).status_code == 400
    # hiçbiri kaydedilmedi
    assert len(client.get("/transactions/", params={"asset_id": a["id"]}).json()) == 1


def test_settle_sale_rejects_already_paid_installment(client):
    a, base, insts = _setup_sale(client)
    client.put(f"/installments/{insts[0]['id']}/toggle")
    r = client.post("/transactions/settle", json={"transaction": {**base, "quantity": -100}, "pay_installment_ids": [insts[0]["id"]]})
    assert r.status_code == 400 and "zaten ödenmiş" in r.json()["detail"]
    assert len(client.get("/transactions/", params={"asset_id": a["id"]}).json()) == 1
