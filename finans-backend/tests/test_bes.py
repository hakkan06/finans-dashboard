from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from app import bes
from app.services import today_tr

PRICES = {"AAA": 2.0, "BBB": 4.0}


@pytest.fixture(autouse=True)
def fake_tefas(monkeypatch):
    """TEFAS'a çıkmadan sabit fiyat döner; bilinmeyen kod → None."""
    def fake(code):
        p = PRICES.get(code)
        return (p, p * 0.99, date(2026, 11, 6), f"{code} Emeklilik Fonu") if p else None
    monkeypatch.setattr(bes, "fetch_bes_fund", fake)


def acct(**over):
    entry = (today_tr() - relativedelta(years=4)).isoformat()
    base = {
        "name": "Test BES",
        "system_entry_date": entry,
        "holdings": [{"fund_code": "AAA", "own_units": 1000, "state_units": 100, "own_cost": 1500}],
    }
    base.update(over)
    return base


# ── Saf hesaplar ─────────────────────────────────────────────────────
def test_vesting_tiers():
    entry = date(2020, 1, 15)
    assert bes.vesting_ratio(entry, date(2022, 12, 31), False) == 0.0
    assert bes.vesting_ratio(entry, date(2023, 1, 15), False) == 0.15
    assert bes.vesting_ratio(entry, date(2026, 1, 15), False) == 0.35
    assert bes.vesting_ratio(entry, date(2030, 1, 15), False) == 0.60
    assert bes.vesting_ratio(entry, date(2021, 1, 1), True) == 1.0


def test_age_and_retirement_date():
    class A:
        system_entry_date = date(2018, 6, 1)
        birth_date = date(1980, 3, 10)
        retirement_eligible = False

    assert bes.age_on(A.birth_date, date(2026, 3, 9)) == 45
    assert bes.age_on(A.birth_date, date(2026, 3, 10)) == 46
    # max(2018+10, 1980+56) = 2036-03-10
    assert bes.retirement_date(A) == date(2036, 3, 10)
    assert not bes.is_retirement_eligible(A, date(2036, 3, 9))
    assert bes.is_retirement_eligible(A, date(2036, 3, 10))


# ── Değer hesabı ─────────────────────────────────────────────────────
def test_value_from_units_and_price(client):
    r = client.post("/bes/", json=acct())
    assert r.status_code == 200, r.text
    b = r.json()
    # 1000 pay × 2 = 2.000 ₺ kendi, 100 × 2 = 200 ₺ devlet
    assert b["own_balance"] == 2000 and b["state_balance"] == 200
    assert b["own_principal"] == 1500 and b["own_return"] == 500
    assert b["vest_ratio"] == 0.15 and b["vested_state"] == 30
    # (500 getiri + 30 hak edilen) × %15
    assert round(b["tax"], 2) == 79.5
    assert round(b["net_value"], 2) == 2000 + 30 - 79.5
    assert b["next_milestone"]["years"] == 6
    assert b["holdings"][0]["share_pct"] == 100


def test_negative_return_has_no_tax_on_own(client):
    b = client.post("/bes/", json=acct(holdings=[{"fund_code": "AAA", "own_units": 1000, "own_cost": 3000}])).json()
    assert b["own_return"] == -1000
    assert b["tax"] == 0 and b["net_value"] == 2000


def test_unknown_fund_rejected_and_code_normalized(client):
    assert client.post("/bes/", json=acct(holdings=[{"fund_code": "ZZZ", "own_units": 1}])).status_code == 422
    b = client.post("/bes/", json=acct(holdings=[{"fund_code": " aaa ", "own_units": 1}])).json()
    assert b["holdings"][0]["fund_code"] == "AAA"


def test_same_fund_in_holdings_and_allocations(client):
    r = client.post("/bes/", json=acct(monthly_contribution=1000, allocations=[{"fund_code": "AAA", "percent": 100}]))
    assert r.status_code == 200, r.text


def test_retirement_from_birth_date(client):
    old = (today_tr() - relativedelta(years=60)).isoformat()
    entry = (today_tr() - relativedelta(years=12)).isoformat()
    b = client.post("/bes/", json=acct(birth_date=old, system_entry_date=entry)).json()
    assert b["retirement_eligible"] and b["vest_ratio"] == 1.0 and b["age"] == 60
    assert b["next_milestone"] is None and b["forfeited_state"] == 0
    young = (today_tr() - relativedelta(years=40)).isoformat()
    b2 = client.post("/bes/", json=acct(birth_date=young, system_entry_date=entry)).json()
    assert not b2["retirement_eligible"] and b2["vest_ratio"] == 0.6
    assert b2["retirement_date"] == (date.fromisoformat(young) + relativedelta(years=56)).isoformat()


# ── Aylık katkı ──────────────────────────────────────────────────────
def test_monthly_contribution_split_and_state(client):
    start_d = today_tr() - relativedelta(months=2)  # 3 vade: -2, -1, 0 ay
    start = start_d.isoformat()
    day = min(start_d.day, 28)
    r = client.post("/bes/", json=acct(
        holdings=[],
        monthly_contribution=1000, contribution_day=day, first_contribution_date=start,
        allocations=[{"fund_code": "AAA", "percent": 60}, {"fund_code": "BBB", "percent": 40}],
    ))
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    assert client.get(f"/bes/{bid}").json()["own_balance"] == 0  # henüz uygulanmadı

    assert client.post("/bes/refresh").json()["applied_months"] == 3
    b = client.get(f"/bes/{bid}").json()
    by = {h["fund_code"]: h for h in b["holdings"]}
    # 3 ay × 600 ₺ / 2 ₺ = 900 pay AAA; 3 × 400 / 4 = 300 pay BBB
    assert by["AAA"]["own_units"] == 900 and by["BBB"]["own_units"] == 300
    # devlet katkısı %20
    assert by["AAA"]["state_units"] == 180 and by["BBB"]["state_units"] == 60
    assert b["own_principal"] == 3000
    # gün, "ayın kaçında yatar" ayarına sabit kalır (29-31'e denk gelen başlangıçlarda 28'e)
    assert b["next_contribution"] == (start_d + relativedelta(months=3)).replace(day=day).isoformat()

    # Idempotent: ikinci çağrı aynı ayı tekrar eklemez
    assert client.post("/bes/refresh").json()["applied_months"] == 0
    assert client.get(f"/bes/{bid}").json()["own_principal"] == 3000
    kinds = {e["kind"] for e in client.get(f"/bes/{bid}/events").json()}
    assert kinds == {"contribution", "state"}


def test_contribution_deferred_when_price_missing(client, monkeypatch):
    start = (today_tr() - relativedelta(months=1)).isoformat()
    bid = client.post("/bes/", json=acct(
        holdings=[], monthly_contribution=1000, first_contribution_date=start,
        allocations=[{"fund_code": "AAA", "percent": 100}],
    )).json()["id"]
    from app import models
    from app.database import SessionLocal
    db = SessionLocal()
    f = db.get(bes.BESFund, "AAA")
    f.price = None
    db.commit()
    db.close()
    monkeypatch.setattr(bes, "fetch_bes_fund", lambda c: None)
    res = client.post("/bes/refresh").json()
    assert res["applied_months"] == 0 and res["failed"] == ["AAA"]
    assert client.get(f"/bes/{bid}").json()["own_principal"] == 0  # kayıp yok, sonra eklenir


def test_allocation_must_sum_to_100(client):
    r = client.post("/bes/", json=acct(monthly_contribution=500, allocations=[{"fund_code": "AAA", "percent": 70}]))
    assert r.status_code == 422
    assert client.post("/bes/", json=acct(monthly_contribution=500)).status_code == 422  # dağılım yok


# ── Fon değiştirme, düzeltme, CRUD ───────────────────────────────────
def test_switch_preserves_value(client):
    bid = client.post("/bes/", json=acct()).json()["id"]
    b = client.post(f"/bes/{bid}/switch", json={"from_fund": "AAA", "to_fund": "BBB", "percent": 50}).json()
    by = {h["fund_code"]: h for h in b["holdings"]}
    assert by["AAA"]["own_units"] == 500 and by["BBB"]["own_units"] == 250  # 500×2/4
    assert by["AAA"]["own_cost"] == 750 and by["BBB"]["own_cost"] == 750
    assert b["own_balance"] == 2000 and b["state_balance"] == 200  # değer değişmez
    full = client.post(f"/bes/{bid}/switch", json={"from_fund": "AAA", "to_fund": "BBB", "percent": 100}).json()
    assert [h["fund_code"] for h in full["holdings"]] == ["BBB"]  # boşalan fon kalkar
    assert client.post(f"/bes/{bid}/switch", json={"from_fund": "BBB", "to_fund": "BBB", "percent": 10}).status_code == 422
    assert client.post(f"/bes/{bid}/switch", json={"from_fund": "AAA", "to_fund": "BBB", "percent": 10}).status_code == 404


def test_reconcile_scales_units(client):
    bid = client.post("/bes/", json=acct()).json()["id"]
    b = client.post(f"/bes/{bid}/reconcile", json={"own_balance": 1900, "state_balance": 210}).json()
    assert round(b["own_balance"], 2) == 1900 and round(b["state_balance"], 2) == 210
    assert b["own_principal"] == 1500  # ödenen katkı toplamı değişmez


def test_holding_crud_and_update(client):
    bid = client.post("/bes/", json=acct()).json()["id"]
    b = client.put(f"/bes/{bid}/holdings/bbb", json={"own_units": 10, "state_units": 1, "own_cost": 30}).json()
    assert {h["fund_code"] for h in b["holdings"]} == {"AAA", "BBB"}
    b = client.delete(f"/bes/{bid}/holdings/BBB").json()
    assert {h["fund_code"] for h in b["holdings"]} == {"AAA"}
    up = client.put(f"/bes/{bid}", json={"name": "Yeni ad"}).json()
    assert up["name"] == "Yeni ad" and up["own_balance"] == 2000
    assert client.delete(f"/bes/{bid}").status_code == 200
    assert client.get("/bes/").json() == []
    assert client.get("/bes/999").status_code == 404


def test_validation(client):
    future = (today_tr() + relativedelta(days=2)).isoformat()
    assert client.post("/bes/", json=acct(system_entry_date=future)).status_code == 422
    assert client.post("/bes/", json=acct(system_entry_date="1999-01-01")).status_code == 422
    assert client.post("/bes/", json=acct(holdings=[{"fund_code": "AAA", "own_units": -1}])).status_code == 422


def test_bes_not_part_of_liquid_assets(client):
    client.post("/bes/", json=acct())
    ov = client.get("/overview").json()
    assert ov["total_assets"] == 0 and ov["net_worth"] == 0


def test_next_month_due_does_not_drift():
    assert bes.next_month_due(date(2026, 1, 28), 28) == date(2026, 2, 28)
    assert bes.next_month_due(date(2026, 2, 28), 28) == date(2026, 3, 28)
    assert bes.next_month_due(date(2026, 1, 31), 5) == date(2026, 2, 5)
    assert bes.next_month_due(date(2026, 12, 5), 5) == date(2027, 1, 5)


def test_migrate_upgrades_legacy_table():
    """BES'in ilk sürümünden kalan bes_accounts tablosuna yeni sütunlar eklenir (create_all eklemez)."""
    from sqlalchemy import create_engine, inspect, text

    eng = create_engine("sqlite://")
    with eng.begin() as c:
        c.execute(text(
            "CREATE TABLE bes_accounts (id INTEGER PRIMARY KEY, name VARCHAR, company VARCHAR, system_entry_date DATE, "
            "contract_start_date DATE, own_principal FLOAT, own_balance FLOAT, state_balance FLOAT, "
            "retirement_eligible BOOLEAN, balance_updated DATE)"
        ))
        c.execute(text("INSERT INTO bes_accounts (id, name, system_entry_date) VALUES (1, 'Eski', '2022-03-01')"))
    added = bes.migrate(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("bes_accounts")}
    assert {"birth_date", "monthly_contribution", "contribution_day", "state_rate", "next_contribution"} <= cols
    assert "bes_accounts.birth_date" in added
    assert bes.migrate(eng) == []  # ikinci çalıştırma bir şey yapmaz
    with eng.begin() as c:  # eski kayıt korunur
        assert c.execute(text("SELECT name FROM bes_accounts")).scalar() == "Eski"
