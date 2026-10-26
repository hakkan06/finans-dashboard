# Finans paneli

Kişisel varlıkları (hisse, fon, altın, döviz) ve borçları tek yerden takip eden panel. Net servetin her gün otomatik kaydedilir ve grafikte izlenir.

## Ekranlar

- **Özet:** net servet, günlük değişim, yaklaşan ödemeler, varlık dağılımı
- **Varlıklar:** ekle, sat, düzenle, sil; her varlığın işlem geçmişi ve kâr/zarar durumu
- **Borçlar:** faizli veya faizsiz taksit planı, gruplar, taksiti tek dokunuşla ödendi işaretleme, 12 aylık yük
- **Günlük takip:** net servet ve varlık/borç grafiği, günlük kayıtlar

Telefonda alt menü ve ortadaki **+** düğmesiyle, bilgisayarda sol menüyle kullanılır. Koyu tema sistem ayarına uyar.

## Yapı

| Parça | Teknoloji | Klasör |
|---|---|---|
| Arayüz | React (esbuild ile derlenir), nginx ile sunulur | `finans-frontend/` |
| API | FastAPI + SQLAlchemy | `finans-backend/` |
| Veritabanı | PostgreSQL | `k8s/postgres.yaml` |
| Yedek | Her gece 03:00 `pg_dump` → Google Drive | `db-backup/`, `k8s/backup-cronjob.yaml` |
| Dağıtım | k3s + GitHub Actions (VPS üzerindeki runner) | `.github/workflows/deploy.yml` |

Arayüz, API'ye aynı alan adı altında `/api/...` yoluyla ulaşır (nginx iletir); ayrı bir API adresi yoktur.

### Hesaplamalar nerede?

Tüm hesaplar backend'dedir (`finans-backend/app/services.py`): FIFO maliyet ve gerçekleşen kâr, fon stopajı (%17,5), dolar kuru, net servet, taksit planı. Arayüz sadece gösterir. Her gece 22:00'de (TR) ve fiyatlar elle güncellendiğinde günün kaydı sunucuda yazılır.

Faizli kredide girilen tutar anaparadır; **aylık** faiz oranıyla eşit taksitli (annüite) plan çıkarılır.

## Yerelde deneme

Arayüzü gerçek veritabanı olmadan görmek için:

```bash
cd finans-frontend
npm install
npm run dev        # http://localhost:5173 (örnek verili sahte API ile)
```

Backend testleri:

```bash
cd finans-backend
pip install -r requirements.txt -r requirements-dev.txt
DATABASE_URL=sqlite:///./test.db python -m pytest -q
```

## Canlıya alma

`main` dalına push edilince runner imajları derler ve k3s'e uygular. Gizli bilgiler (`finans-db-secret`, `finans-mail-secret`, `rclone-config`) repoda yoktur; `k8s/db-secret.example.yaml` örnektir.
