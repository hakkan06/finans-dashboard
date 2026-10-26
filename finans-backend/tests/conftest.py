import os
import tempfile

# Uygulama import edilmeden ÖNCE: testler izole bir SQLite dosyası kullanır.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"

import pytest
from fastapi.testclient import TestClient

from app import models, prices, services
from app.database import engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    # Testler ağa çıkmasın
    monkeypatch.setattr(prices, "fetch_quote", lambda t, s: None)
    monkeypatch.setattr(services, "_fetch_usd_try", lambda: 40.0)
    services._usd_cache.update(v=None, t=0.0)
    yield


@pytest.fixture
def client():
    return TestClient(app)
