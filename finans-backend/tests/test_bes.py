from datetime import date

from dateutil.relativedelta import relativedelta

from app import bes
from app.services import today_tr


def payload(**over):
    base = {
        "name": "Test BES",
        "system_entry_date": "2022-03-01",
        "own_principal": 100000,
        "own_balance": 130000,
        "state_balance": 20000,
    }
    base.update(over)
    return base


def test_vesting_tiers():
    entry = date(2020, 1, 15)
    assert bes.vesting_ratio(entry, date(2022, 12, 31), False) == 0.0
    assert bes.vesting_ratio(entry, date(2023, 1, 15), False) == 0.15
    assert bes.vesting_ratio(entry, date(2026, 1, 15), False) == 0.35
    assert bes.vesting_ratio(entry, date(2030, 1, 15), False) == 0.60
    # emeklilik şartı sağlanmışsa tam hak
    assert bes.vesting_ratio(entry, date(2021, 1, 1), True) == 1.0


def test_net_value_and_next_milestone(client):
    entry = today_tr() - relativedelta(years=4)
    r = client.post("/bes/", json=payload(system_entry_date=entry.isoformat()))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["vest_ratio"] == 0.15
    assert b["vested_state"] == 3000
    assert b["forfeited_state"] == 17000
    # (30.000 getiri + 3.000 hak edilen devlet katkısı) × %15 stopaj
    assert round(b["tax"], 2) == 4950
    assert round(b["net_value"], 2) == 128050
    assert b["next_milestone"]["years"] == 6
    assert b["next_milestone"]["due_date"] == (entry + relativedelta(years=6)).isoformat()
    assert round(b["gain_at_next"], 2) == 3400  # 20.000 × (0,35−0,15) × 0,85


def test_retirement_eligible_has_no_next_milestone(client):
    r = client.post("/bes/", json=payload(retirement_eligible=True))
    b = r.json()
    assert b["vest_ratio"] == 1.0
    assert b["next_milestone"] is None
    assert b["forfeited_state"] == 0


def test_crud_and_validation(client):
    assert client.post("/bes/", json=payload(own_balance=-1)).status_code == 422
    future = (today_tr() + relativedelta(days=2)).isoformat()
    assert client.post("/bes/", json=payload(system_entry_date=future)).status_code == 422
    assert client.post("/bes/", json=payload(system_entry_date="1999-01-01")).status_code == 422

    bid = client.post("/bes/", json=payload()).json()["id"]
    up = client.put(f"/bes/{bid}", json={"state_balance": 25000})
    assert up.status_code == 200 and up.json()["state_balance"] == 25000
    assert up.json()["own_balance"] == 130000  # dokunulmayan alan korunur
    assert len(client.get("/bes/").json()) == 1
    assert client.delete(f"/bes/{bid}").status_code == 200
    assert client.get("/bes/").json() == []
    assert client.put("/bes/999", json={"name": "x"}).status_code == 404


def test_bes_not_part_of_liquid_assets(client):
    client.post("/bes/", json=payload())
    ov = client.get("/overview").json()
    assert ov["total_assets"] == 0
    assert ov["net_worth"] == 0
