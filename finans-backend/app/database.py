import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Kubernetes'te DB_* değişkenleri Secret'tan gelir; lokalde varsayılanlar kullanılır.
# Testler/yerel deneme için tek parça DATABASE_URL de verilebilir (örn. sqlite:///./dev.db).
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "finans_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "finans_pass")
DB_NAME = os.getenv("DB_NAME", "finans_db")

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
)

_connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
