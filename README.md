# 💰 Finans ve Varlık Yönetim Paneli

Bu proje, kişisel varlıkları (Hisse, Fon, Emtia, Döviz) ve borçları tek bir merkezden, gerçek zamanlı piyasa verileriyle takip etmeyi sağlayan, Kubernetes üzerinde çalışan tam otonom bir finansal gösterge panelidir.

## ✨ Temel Özellikler

- **Gerçek Zamanlı Fiyatlama:** Amerikan Borsası (Yahoo Finance), Borsa İstanbul (TR_STOCK), TEFAS Yatırım Fonları, Döviz ve Altın piyasaları otomatik olarak taranır.
- **Akıllı FIFO Algoritması:** Varlıkların kâr/zarar ve stopaj (vergi) hesaplamaları Backend üzerinde otomatik yapılır.
- **Borç ve Likidite Yönetimi:** Otomatik taksit planlayıcı ile borçlar takip edilir. Ay sonu likidite projeksiyonu ile borç-varlık dengesi analiz edilir.
- **Otonom Trend Analizi:** Kubernetes CronJob sayesinde sistem her gece (23:59) sessizce piyasa kapanış değerlerini ve net serveti veritabanına işler.
- **Profesyonel Görselleştirme:** Plotly destekli, interaktif "Investing.com" stili finansal büyüme grafikleri sunar.

## 🏗️ Mimari ve Teknoloji Yığını

Proje iki ana mikroservisten ve bir veritabanından oluşmaktadır:

- **Backend:** `FastAPI` (Python) - İş mantığı, muhasebe hesaplamaları, API endpoint'leri ve dış veri kaynakları (yfinance, tefas) entegrasyonu.
- **Frontend:** `Streamlit` (Python) - Reaktif, hızlı ve kullanıcı dostu arayüz.
- **Veritabanı:** `PostgreSQL` / `SQLite` (SQLAlchemy ORM ile) - Kalıcı veri saklama.
- **Dağıtım:** `Docker` & `Kubernetes` (K8s) - Konteyner mimarisi ve orkestrasyon.
- **CI/CD:** `GitLab CI/CD` - Koda yapılan her *push* işleminde imajları derleyen ve Kubernetes kümesini *Rolling Update* ile kesintisiz güncelleyen otonom boru hattı.

## 🚀 Kurulum ve Dağıtım

Sistem tamamen CI/CD boru hattı üzerinden yönetilmektedir. Manuel müdahaleye gerek kalmadan K8s üzerine deploy edilir.

1. **Gereksinimler:** Çalışır durumda bir Kubernetes Cluster'ı, yapılandırılmış GitLab Runner (`shell` executor) ve `kubectl` yetkileri.
2. **Değişikliklerin Canlıya Alınması:**
   Projeye yeni bir özellik eklendiğinde standart git komutlarıyla ana dala gönderilir:
   ```bash
   git add .
   git commit -m "feat: yeni özellik eklendi"
   git push origin main
