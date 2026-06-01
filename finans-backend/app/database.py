from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Geliştirme ortamı (Mac) ve Kubernetes ortamı için bağlantı adresini ayarlıyoruz.
# Kubernetes içinde çalışırken DB_HOST ortam değişkenini "finans-postgres-service" yapacağız.
# Lokalimizde geliştirirken ise varsayılan olarak "localhost" kullanacak.
DB_HOST = os.getenv("DB_HOST", "localhost")

SQLALCHEMY_DATABASE_URL = f"postgresql://finans_user:finans_pass@{DB_HOST}:5432/finans_db"

# Veritabanı motorunu (engine) oluşturuyoruz
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Her istek geldiğinde veritabanı ile konuşacak bir oturum (session) fabrikası kuruyoruz
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modellerimizin miras alacağı temel sınıf
Base = declarative_base()

# FastAPI endpoint'lerinde veritabanı bağlantısı almak için kullanacağımız yardımcı fonksiyon
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
