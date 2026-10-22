import streamlit as st
import requests
import pandas as pd
import os
import time
from datetime import date, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
import datetime as dt_module

API_URL = os.getenv("API_URL", "http://localhost:8000")

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(page_title="Finans Dashboard", layout="wide", page_icon="💰", initial_sidebar_state="expanded")

# =====================================================================
# GLOBAL CSS — Temiz, Modern, Kullanıcı Dostu
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ─── Genel ─────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 1.5rem !important;
    max-width: 1400px;
}
#MainMenu, footer, header { visibility: hidden; }

/* ─── Sidebar ────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(128,128,128,0.03);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 13px;
}
/* Sidebar toggle butonunu her zaman göster */
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] button,
section[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}
/* Sidebar genişliğini sabitle, tamamen kaybolmasın */
[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 40px !important;
    width: 40px !important;
    overflow: visible !important;
}

/* ─── KPI Kartları ───────────────────────────────── */
.kpi-grid {
    display: grid;
    gap: 14px;
    margin-bottom: 1.4rem;
}
.kpi-card {
    padding: 18px 20px;
    border-radius: 14px;
    border: 1px solid rgba(128,128,128,0.12);
    background: rgba(128,128,128,0.03);
    transition: border-color 0.2s, transform 0.15s;
}
.kpi-card:hover {
    border-color: rgba(128,128,128,0.25);
    transform: translateY(-1px);
}
.kpi-card-accent {
    background: linear-gradient(135deg, rgba(41,98,255,0.08), rgba(0,188,212,0.04));
    border-color: rgba(41,98,255,0.25) !important;
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    opacity: 0.5;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    line-height: 1.15;
}
.kpi-sub {
    font-size: 11.5px;
    opacity: 0.45;
    margin-top: 5px;
    font-weight: 400;
}
.kpi-positive { color: #26A69A; }
.kpi-negative { color: #EF5350; }

/* ─── Section Title ──────────────────────────────── */
.section-title {
    font-size: 13px;
    font-weight: 600;
    opacity: 0.45;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    margin: 1.2rem 0 0.6rem;
}

/* ─── Butonlar ───────────────────────────────────── */
.stButton > button {
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    transition: all 0.15s !important;
    border: 1px solid rgba(128,128,128,0.18) !important;
}
.stButton > button:hover {
    border-color: rgba(41,98,255,0.45) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(41,98,255,0.12) !important;
}

/* ─── Input/Form ─────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    border-radius: 8px !important;
    font-size: 13px !important;
}
.stForm {
    border-radius: 12px !important;
    border: 1px solid rgba(128,128,128,0.1) !important;
    padding: 16px !important;
}
[data-testid="stExpander"] {
    border-radius: 12px !important;
    border: 1px solid rgba(128,128,128,0.1) !important;
}
[data-testid="stExpander"] summary {
    font-size: 13px !important;
    font-weight: 500 !important;
}

/* ─── Tablo ──────────────────────────────────────── */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    font-size: 13px !important;
}

/* ─── Metric ─────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(128,128,128,0.03);
    border: 1px solid rgba(128,128,128,0.1);
    border-radius: 12px;
    padding: 14px 18px;
}
[data-testid="stMetricValue"] { font-size: 1.25rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { font-size: 11px !important; opacity: 0.5; font-weight: 500 !important; }

/* ─── Alert ──────────────────────────────────────── */
.alert-compact {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    border-radius: 10px;
    font-size: 12.5px;
    font-weight: 500;
    margin-bottom: 10px;
    flex-wrap: wrap;
}
.alert-compact-danger {
    background: rgba(239,83,80,0.08);
    border: 1px solid rgba(239,83,80,0.22);
    color: #EF5350;
}
.alert-compact-warning {
    background: rgba(255,167,38,0.08);
    border: 1px solid rgba(255,167,38,0.22);
    color: #FFA726;
}

/* ─── Tabs ───────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(128,128,128,0.05);
    padding: 4px;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,0.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 500;
    border: none !important;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    background: rgba(41, 98, 255, 0.15) !important;
    color: #2962FF !important;
}

/* ─── Progress Bar ───────────────────────────────── */
.progress-track {
    height: 8px;
    border-radius: 99px;
    background: rgba(128,128,128,0.1);
    overflow: hidden;
    margin: 6px 0 4px;
}
.progress-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #2962FF, #26A69A);
    transition: width 0.5s ease;
}

/* ─── Divider ────────────────────────────────────── */
hr { opacity: 0.1; margin: 0.8rem 0 !important; }

/* ─── Group Card & Quick Pay ─────────────────────── */
.group-card {
    border: 1px solid rgba(128,128,128,0.12);
    border-radius: 14px;
    padding: 18px 20px 14px;
    margin-bottom: 14px;
    background: rgba(128,128,128,0.02);
}
.quick-pay-container {
    background: rgba(41,98,255,0.03);
    border: 1px solid rgba(41,98,255,0.15);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 1.2rem;
}
.quick-pay-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid rgba(128,128,128,0.08);
}
.quick-pay-row:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# YARDIMCI FONKSİYONLAR & TİPLER
# =====================================================================
VARLIK_TURLERI = {
    "US_STOCK":  "🇺🇸 ABD Hissesi",
    "TR_STOCK":  "🇹🇷 BIST Hissesi",
    "FUND":      "📊 Fon / TEFAS",
    "COMMODITY": "🥇 Emtia (Altın/Gümüş)",
    "FIAT":      "💵 Döviz / Nakit",
}
VARLIK_TURLERI_TERS = {v: k for k, v in VARLIK_TURLERI.items()}

VARLIK_IPUCLARI = {
    "🇺🇸 ABD Hissesi": "Örnek: AAPL, MSFT, NVDA, QQQ, SPY",
    "🇹🇷 BIST Hissesi": "Örnek: THYAO, EREGL, ASELS, BIMAS (.IS uzantısı otomatik eklenir)",
    "📊 Fon / TEFAS": "Örnek: TTE, MAC, TI2, TSK",
    "🥇 Emtia (Altın/Gümüş)": "Gram Altın için ALTIN, Gram Gümüş için GUMUS (ONS/Dolar paritesiyle hesaplanır)",
    "💵 Döviz / Nakit": "Örnek: USD, EUR, GBP",
}

def tur_etiketi(api_type: str) -> str:
    return VARLIK_TURLERI.get(api_type, api_type)


@st.cache_data(ttl=3600)
def get_cached_usd_rate():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/TRY=X?interval=1d&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        return float(res.json()['chart']['result'][0]['meta']['regularMarketPrice'])
    except:
        try:
            res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3)
            return float(res.json().get("rates", {}).get("TRY", 32.20))
        except:
            return 32.20

usd_try_rate = get_cached_usd_rate()


# =====================================================================
# ÖN VERİ ÇEKİMİ
# =====================================================================
global_total_assets = 0.0
global_total_debts  = 0.0
summary_data = []
all_assets   = []
debts        = []
groups       = []

try:
    res_all = requests.get(f"{API_URL}/assets/", timeout=5)
    if res_all.status_code == 200:
        all_assets = res_all.json()

    res_assets = requests.get(f"{API_URL}/portfolio/summary", timeout=5)
    if res_assets.status_code == 200:
        summary_data = res_assets.json()
        for item in summary_data:
            net_val = item.get('net_value') or 0.0
            if item.get('asset_type') == 'US_STOCK':
                net_val *= usd_try_rate
            global_total_assets += net_val

    res_debts = requests.get(f"{API_URL}/debts/", timeout=5)
    if res_debts.status_code == 200:
        debts = res_debts.json()
        for d in debts:
            for inst in d.get('installments', []):
                if not inst['is_paid']:
                    global_total_debts += inst['amount']

    res_groups = requests.get(f"{API_URL}/debt-groups/", timeout=5)
    if res_groups.status_code == 200:
        groups = res_groups.json()

except requests.exceptions.ConnectionError:
    st.error("⚡ Backend servisine bağlanılamıyor. API sunucusu çalışıyor mu?")
except requests.exceptions.Timeout:
    st.error("⏱️ Backend yanıt vermedi (zaman aşımı).")
except Exception as e:
    st.error(f"Veri yüklenirken hata oluştu: {repr(e)}")


# Gecikmiş / Yaklaşan hesapları
gecikmis_list = []
yaklasan_list = []
urgent_installments = []
bugun = date.today()

for d in debts:
    for inst in d.get('installments', []):
        if not inst['is_paid']:
            vade  = pd.to_datetime(inst['due_date']).date()
            kalan = (vade - bugun).days
            item_info = {
                "id": inst['id'],
                "debt_name": d['name'],
                "amount": inst['amount'],
                "due_date": inst['due_date'],
                "kalan": kalan
            }
            if kalan < 0:
                gecikmis_list.append(f"{d['name']} ₺{inst['amount']:,.0f} ({abs(kalan)}g gecikti)")
                urgent_installments.append(item_info)
            elif kalan <= 7:
                if kalan <= 3:
                    yaklasan_list.append(f"{d['name']} ₺{inst['amount']:,.0f} ({kalan}g kaldı)")
                urgent_installments.append(item_info)

urgent_installments.sort(key=lambda x: x['kalan'])
net_worth = global_total_assets - global_total_debts


# =====================================================================
# SIDEBAR — Menü & Hızlı İşlemler
# =====================================================================
# Sayfa seçimini session_state ile koru — sidebar kapansa bile kaybolmaz
if "sayfa" not in st.session_state:
    st.session_state["sayfa"] = "📊 Genel Bakış"

with st.sidebar:
    st.markdown("### 💰 Finans Portföyü")
    st.caption(f"USD/TRY: **₺{usd_try_rate:,.2f}** · {bugun.strftime('%d.%m.%Y')}")

    if gecikmis_list:
        st.error(f"🔴 {len(gecikmis_list)} Gecikmiş Taksit!")
    if yaklasan_list:
        st.warning(f"⚠️ {len(yaklasan_list)} Yaklaşan Ödeme")

    st.divider()

    st.session_state["sayfa"] = st.radio(
        "Menü",
        ["📊 Genel Bakış", "💼 Varlık Yönetimi", "💳 Borç Takibi", "📈 Trend Analizi"],
        index=["📊 Genel Bakış", "💼 Varlık Yönetimi", "💳 Borç Takibi", "📈 Trend Analizi"].index(st.session_state["sayfa"]),
        label_visibility="collapsed",
        key="_sayfa_radio",
    )

    st.divider()

    # Fiyat güncelleme butonu
    if st.button("🔄 Piyasa Fiyatlarını Güncelle", use_container_width=True):
        with st.spinner("Piyasa verileri taranıyor..."):
            res = requests.post(f"{API_URL}/assets/update-prices")
            if res.status_code == 200:
                requests.post(f"{API_URL}/portfolio/snapshot", json={
                    "total_assets": global_total_assets,
                    "total_debts":  global_total_debts
                }, timeout=3)
                st.toast("📈 Fiyatlar başarıyla güncellendi!")
                time.sleep(0.8)
                st.rerun()
            elif res.status_code == 429:
                st.warning(res.json().get("detail", "Çok sık istek yapıldı. Lütfen biraz bekleyin."))
            else:
                st.error("Fiyatlar güncellenemedi.")

    # Son güncelleme zamanı
    son_guncelleme = None
    for item in summary_data:
        if item.get('last_updated'):
            gt = pd.to_datetime(item['last_updated'])
            if son_guncelleme is None or gt > son_guncelleme:
                son_guncelleme = gt

    if son_guncelleme:
        simdi = pd.Timestamp.now(tz='Europe/Istanbul')
        if son_guncelleme.tzinfo is None:
            son_guncelleme = son_guncelleme.tz_localize('UTC').tz_convert('Europe/Istanbul')
        else:
            son_guncelleme = son_guncelleme.tz_convert('Europe/Istanbul')
        fark_dk = int((simdi - son_guncelleme).total_seconds() / 60)
        if fark_dk < 1:
            fark_str = "az önce"
        elif fark_dk < 60:
            fark_str = f"{fark_dk} dk önce"
        else:
            fark_str = f"{fark_dk // 60} saat önce"
        st.caption(f"🕐 Son Güncelleme: {fark_str}")

sayfa = st.session_state["sayfa"]


# =====================================================================
# SAYFA: GENEL BAKIŞ
# =====================================================================
if sayfa == "📊 Genel Bakış":

    net_color = "kpi-positive" if net_worth >= 0 else "kpi-negative"
    net_sign  = "+" if net_worth >= 0 else ""
    varlik_cnt = len(summary_data)
    borc_cnt   = len(debts)

    st.markdown(f"""
    <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr);">
        <div class="kpi-card">
            <div class="kpi-label">💼 Toplam Varlık</div>
            <div class="kpi-value">₺ {global_total_assets:,.0f}</div>
            <div class="kpi-sub">{varlik_cnt} aktif portföy varlığı</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">💳 Toplam Borç</div>
            <div class="kpi-value">₺ {global_total_debts:,.0f}</div>
            <div class="kpi-sub">{borc_cnt} borç kalemi</div>
        </div>
        <div class="kpi-card kpi-card-accent">
            <div class="kpi-label">📈 Net Servet</div>
            <div class="kpi-value {net_color}">₺ {net_worth:,.0f}</div>
            <div class="kpi-sub">{net_sign}{(net_worth/global_total_assets*100) if global_total_assets else 0:.1f}% servet oranı</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bildirimler
    if gecikmis_list:
        items = " &nbsp;·&nbsp; ".join(gecikmis_list)
        st.markdown(f'<div class="alert-compact alert-compact-danger">🔴 <b>Gecikmiş Ödemeler:</b> {items}</div>', unsafe_allow_html=True)
    if yaklasan_list:
        items = " &nbsp;·&nbsp; ".join(yaklasan_list)
        st.markdown(f'<div class="alert-compact alert-compact-warning">⚠️ <b>Yaklaşan Ödemeler:</b> {items}</div>', unsafe_allow_html=True)

    # Portföy tablosu & Dağılım Pastası
    if summary_data:
        col_tablo, col_pasta = st.columns([3, 1])

        with col_tablo:
            st.markdown('<div class="section-title">Portföy Varlıkları</div>', unsafe_allow_html=True)
            portfolio_table = []
            for item in summary_data:
                net_val    = item.get('net_value') or 0.0
                curr_price = item.get('current_price') or 0.0
                prev_price = item.get('previous_price')

                if item.get('asset_type') == 'US_STOCK':
                    net_val_try   = net_val * usd_try_rate
                    display_price = f"$ {curr_price:,.2f}"
                else:
                    net_val_try   = net_val
                    display_price = f"₺ {curr_price:,.2f}"

                if prev_price and prev_price > 0:
                    daily_pct = ((curr_price - prev_price) / prev_price) * 100
                    if daily_pct > 0:
                        change_str = f"🟢 +{daily_pct:.2f}%"
                    elif daily_pct < 0:
                        change_str = f"🔴 {daily_pct:.2f}%"
                    else:
                        change_str = "—"
                else:
                    change_str = "—"

                portfolio_table.append({
                    "Tür":           tur_etiketi(item.get('asset_type', '—')),
                    "Sembol":        item.get('symbol', '—'),
                    "Ad":            item.get('name', '—'),
                    "Miktar":        item.get('total_qty') or 0.0,
                    "Fiyat":         display_price,
                    "Günlük":        change_str,
                    "Net Değer (₺)": net_val_try,
                })

            df = pd.DataFrame(portfolio_table)
            st.dataframe(
                df.style.format({"Net Değer (₺)": "{:,.0f}", "Miktar": "{:,.4f}"}),
                use_container_width=True,
                height=min(36 * (len(df) + 1) + 3, 400),
                hide_index=True,
            )

        with col_pasta:
            st.markdown('<div class="section-title">Varlık Dağılımı</div>', unsafe_allow_html=True)
            pie_data = {}
            for item in summary_data:
                a_type  = tur_etiketi(item.get('asset_type', 'DİĞER'))
                net_val = item.get('net_value') or 0.0
                if item.get('asset_type') == 'US_STOCK':
                    net_val *= usd_try_rate
                if net_val > 0:
                    pie_data[a_type] = pie_data.get(a_type, 0) + net_val

            if pie_data:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=list(pie_data.keys()),
                    values=list(pie_data.values()),
                    hole=0.58,
                    textinfo='percent',
                    textfont=dict(size=11, family='Inter'),
                    hovertemplate='<b>%{label}</b><br>₺%{value:,.0f}<br>%{percent}<extra></extra>',
                    marker=dict(colors=['#2962FF', '#00BCD4', '#FF6F00', '#43A047', '#8E24AA'], line=dict(width=0))
                )])
                fig_pie.update_layout(
                    margin=dict(l=0, r=0, t=10, b=10),
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.1, font=dict(size=10)),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=240,
                )
                st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Portföyünüzde henüz kayıtlı varlık bulunmuyor. Menüden **💼 Varlık Yönetimi** sekmesine giderek başlayabilirsiniz.")

    # Ay sonu nakit projeksiyonu
    current_month = bugun.month
    current_year  = bugun.year
    bu_ayki_borc = 0.0
    for d in debts:
        for inst in d.get('installments', []):
            due = pd.to_datetime(inst['due_date']).date()
            if not inst['is_paid'] and due.month == current_month and due.year == current_year:
                bu_ayki_borc += inst['amount']

    if bu_ayki_borc > 0:
        ay_sonu = global_total_assets - bu_ayki_borc
        st.markdown('<div class="section-title">Bu Ayki Nakit Akışı Projeksiyonu</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Mevcut Varlıklar", f"₺ {global_total_assets:,.0f}")
        with c2:
            st.metric("Bu Ay Ödenecek Taksitler", f"₺ {bu_ayki_borc:,.0f}")
        with c3:
            delta_lbl = "Pozitif Nakit ✓" if ay_sonu >= 0 else "Nakit Açığı ✗"
            delta_clr = "normal" if ay_sonu >= 0 else "inverse"
            st.metric("Taksitler Sonrası Net Kalan", f"₺ {ay_sonu:,.0f}", delta=delta_lbl, delta_color=delta_clr)


# =====================================================================
# SAYFA: VARLIK YÖNETİMİ
# =====================================================================
elif sayfa == "💼 Varlık Yönetimi":

    st.markdown("## 💼 Varlık Yönetimi")

    tab_ekle, tab_islem, tab_sil = st.tabs(["➕ Yeni Varlık Ekle", "📥 Alım / Satım İşlemi", "🗑️ Varlık Sil"])

    # ── VARLIK EKLE ──
    with tab_ekle:
        st.caption("Portföyünüze yeni bir varlık tanımlayın. İsterseniz başlangıç alım işleminizi de doğrudan aynı anda kaydedebilirsiniz.")

        with st.form("add_asset_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tur_secim = st.selectbox(
                    "Varlık Türü",
                    options=list(VARLIK_TURLERI.values()),
                )
            with col2:
                a_sym = st.text_input(
                    "Sembol / Kod",
                    placeholder="Örn: QQQM, THYAO, ALTIN, USD",
                )

            ipucu = VARLIK_IPUCLARI.get(tur_secim, "")
            st.caption(f"💡 {ipucu}")

            a_name = st.text_input(
                "Varlık Adı",
                placeholder="Örn: Invesco QQQ ETF, Türk Hava Yolları, Gram Altın",
            )

            st.markdown("---")
            has_initial = st.checkbox("Mevcut pozisyonum var (İlk alım miktarını ve maliyetini hemen ekle)")

            col_pos1, col_pos2, col_pos3 = st.columns(3)
            with col_pos1:
                init_qty = st.number_input("Adet / Miktar", min_value=0.0001, value=1.0, format="%.4f", disabled=not has_initial)
            with col_pos2:
                init_price = st.number_input("Birim Alış Fiyatı (₺)", min_value=0.01, value=100.0, format="%.2f", disabled=not has_initial)
            with col_pos3:
                init_date = st.date_input("İşlem Tarihi", value=date.today(), disabled=not has_initial)

            if has_initial:
                st.caption(f"💵 Toplam Başlangıç Yatırımı: **₺{float(init_qty) * float(init_price):,.2f}**")

            submitted = st.form_submit_button("✅ Varlığı Kaydet", use_container_width=True)
            if submitted:
                if not a_sym or not a_name:
                    st.error("Sembol ve varlık adı alanları zorunludur.")
                else:
                    api_type = VARLIK_TURLERI_TERS[tur_secim]
                    sym_clean = a_sym.strip().upper()
                    res = requests.post(f"{API_URL}/assets/", json={
                        "asset_type": api_type,
                        "symbol": sym_clean,
                        "name": a_name.strip()
                    })
                    if res.status_code == 200:
                        new_asset = res.json()
                        # Eğer başlangıç pozisyonu girilmişse işlemi de oluştur
                        if has_initial:
                            txn_res = requests.post(f"{API_URL}/transactions/", json={
                                "asset_id": new_asset["id"],
                                "quantity": float(init_qty),
                                "unit_price": float(init_price),
                                "transaction_date": init_date.strftime("%Y-%m-%d")
                            })
                            if txn_res.status_code == 200:
                                st.toast("✅ Varlık ve ilk alım işlemi kaydedildi!")
                            else:
                                st.warning("Varlık eklendi fakat ilk pozisyon kaydedilemedi.")
                        else:
                            st.toast("✅ Varlık başarıyla eklendi!")

                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error(res.json().get("detail", "Varlık eklenemedi."))

    # ── ALIM SATIM ──
    with tab_islem:
        if not all_assets:
            st.info("İşlem yapabilmek için önce 'Yeni Varlık Ekle' sekmesinden bir varlık ekleyin.")
        else:
            st.caption("Mevcut bir varlık için yeni bir alım veya satış işlemi kaydedin.")

            asset_dict = {f"{a.get('symbol')} — {a.get('name')}": a for a in all_assets}
            selected_label = st.selectbox("İşlem Yapılacak Varlık", options=list(asset_dict.keys()))
            selected_asset = asset_dict[selected_label]

            # Güncel fiyat bilgisi
            curr_p = selected_asset.get('current_price')
            if curr_p:
                st.caption(f"ℹ️ Son Piyasa Fiyatı: **₺{curr_p:,.2f}**")

            with st.form("txn_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    islem_turu = st.radio("İşlem Yönü", ["🟢 Alış", "🔴 Satış"], horizontal=True)
                with col2:
                    t_date = st.date_input("İşlem Tarihi", value=date.today())

                col3, col4 = st.columns(2)
                with col3:
                    t_qty = st.number_input("Miktar / Adet", min_value=0.0001, format="%.4f")
                with col4:
                    default_pr = float(curr_p) if curr_p and curr_p > 0 else 1.0
                    t_price = st.number_input("Birim Fiyat (₺)", min_value=0.01, value=default_pr, format="%.2f")

                if st.form_submit_button("💾 İşlemi Kaydet", use_container_width=True):
                    final_qty = float(t_qty) if "Alış" in islem_turu else -float(t_qty)
                    res = requests.post(f"{API_URL}/transactions/", json={
                        "asset_id": selected_asset["id"],
                        "quantity": final_qty,
                        "unit_price": float(t_price),
                        "transaction_date": t_date.strftime("%Y-%m-%d")
                    })
                    if res.status_code == 200:
                        st.toast("✅ İşlem başarıyla kaydedildi!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error(res.json().get("detail", "İşlem kaydedilemedi."))

    # ── VARLIK SİL ──
    with tab_sil:
        if not all_assets:
            st.info("Silinecek varlık bulunmuyor.")
        else:
            st.warning("⚠️ Bir varlığı sildiğinizde, o varlığa ait tüm işlem geçmişi de kalıcı olarak silinir.")

            with st.form("del_asset_form"):
                del_opts = {f"{a.get('symbol')} — {a.get('name')}": a.get('id') for a in all_assets}
                selected_del = st.selectbox("Silinecek Varlık", options=list(del_opts.keys()))
                onay = st.checkbox("Bu varlığı ve tüm işlem geçmişini kalıcı olarak silmek istiyorum")

                if st.form_submit_button("🗑️ Varlığı Kalıcı Olarak Sil", use_container_width=True):
                    if onay:
                        res = requests.delete(f"{API_URL}/assets/{del_opts[selected_del]}")
                        if res.status_code == 200:
                            st.toast("🗑️ Varlık silindi!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error("Silme işlemi başarısız.")
                    else:
                        st.error("Lütfen onay kutusunu işaretleyin.")

    # Kayıtlı Varlıklar Özeti Tablosu
    if all_assets:
        st.markdown('<div class="section-title">Kayıtlı Tüm Varlıklar</div>', unsafe_allow_html=True)
        asset_df = pd.DataFrame([{
            "Tür":    tur_etiketi(a.get('asset_type', '—')),
            "Sembol": a.get('symbol', '—'),
            "Ad":     a.get('name', '—'),
            "Son Fiyat":  f"₺ {a['current_price']:,.2f}" if a.get('current_price') else "—",
        } for a in all_assets])
        st.dataframe(asset_df, use_container_width=True, hide_index=True,
                      height=min(36 * (len(asset_df) + 1) + 3, 300))


# =====================================================================
# SAYFA: BORÇ TAKİBİ
# =====================================================================
elif sayfa == "💳 Borç Takibi":

    st.markdown("## 💳 Borç & Kredi Takibi")

    # ── 1. HIZLI ÖDEME BANNER'I (Vadesi gelen veya gecikenler) ──
    if urgent_installments:
        st.markdown("""
        <div class="quick-pay-container">
            <div style="font-weight:600;font-size:13px;margin-bottom:8px;color:#2962FF">
                ⚡ Vadesi Gelen / Yaklaşan Taksitler (Tek Tıkla Öde)
            </div>
        """, unsafe_allow_html=True)

        # En acil 4 taksiti göster
        for item in urgent_installments[:4]:
            col_b1, col_b2, col_b3 = st.columns([3, 2, 2])
            with col_b1:
                durum_str = f"🔴 {abs(item['kalan'])}g gecikti" if item['kalan'] < 0 else (f"⚠️ Bugün vade" if item['kalan'] == 0 else f"⏳ {item['kalan']}g kaldı")
                st.markdown(f"**{item['debt_name']}** · <span style='font-size:12px;opacity:0.7'>{item['due_date']} ({durum_str})</span>", unsafe_allow_html=True)
            with col_b2:
                st.markdown(f"**₺ {item['amount']:,.0f}**")
            with col_b3:
                if st.button("✅ Ödendi Yap", key=f"quick_pay_{item['id']}", use_container_width=True):
                    res = requests.put(f"{API_URL}/installments/{item['id']}/toggle")
                    if res.status_code == 200:
                        st.toast(f"✅ {item['debt_name']} taksiti ödendi olarak işaretlendi!")
                        time.sleep(0.6)
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # Borç grubu haritası
    grouped_debt_ids = set()
    for g in groups:
        for d in g.get('debts', []):
            grouped_debt_ids.add(d['id'])

    ungrouped_debts = [d for d in debts if d['id'] not in grouped_debt_ids]

    # ── 2. BORÇ GRUPLARI KARTLARI ──
    if groups:
        st.markdown('<div class="section-title">Borç Grupları & Projeler</div>', unsafe_allow_html=True)

        for g in groups:
            paid      = g.get('total_paid', 0)
            remaining = g.get('total_remaining', 0)
            pct       = g.get('progress_pct', 0)
            contracted = g.get('contracted_amount')
            g_debts   = g.get('debts', [])
            total_insts = sum(len(d.get('installments', [])) for d in g_debts)
            paid_insts  = sum(1 for d in g_debts for i in d.get('installments', []) if i['is_paid'])

            desc_html = f'<div style="opacity:.5;font-size:12px;margin-bottom:6px">{g["description"]}</div>' if g.get('description') else ''
            contracted_html = (f'<span style="opacity:.45;font-size:12px">Sözleşme Tutarı: <b>₺{contracted:,.0f}</b></span>' if contracted else '')

            st.markdown(f"""
            <div class="group-card">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
                    <span style="font-size:16px;font-weight:700">🏠 {g['name']}</span>
                    {contracted_html}
                </div>
                {desc_html}
                <div style="display:flex;gap:24px;margin-bottom:8px;font-size:12.5px;opacity:.7">
                    <span>Ödenen: <b style="opacity:1;color:#26A69A">₺{paid:,.0f}</b></span>
                    <span>Kalan Borç: <b style="opacity:1;color:#EF5350">₺{remaining:,.0f}</b></span>
                    <span>Taksit İlerlemesi: <b style="opacity:1">{paid_insts} / {total_insts}</b></span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill" style="width:{pct}%"></div>
                </div>
                <div style="font-size:11.5px;opacity:.5;text-align:right">%{pct:.1f} tamamlandı</div>
            </div>
            """, unsafe_allow_html=True)

            # Grubun altındaki borçları göster
            if g_debts:
                with st.expander(f"📋 '{g['name']}' Grubundaki Kalemler ({len(g_debts)} Borç)"):
                    g_rows = []
                    for gd in g_debts:
                        g_total = gd.get('total_amount', 0)
                        g_paid = sum(i['amount'] for i in gd.get('installments', []) if i['is_paid'])
                        g_rem  = g_total - g_paid
                        g_rows.append({
                            "Borç Kalemi": gd['name'],
                            "Toplam Tutar": g_total,
                            "Ödenen": g_paid,
                            "Kalan": g_rem,
                            "Taksit Sayısı": len(gd.get('installments', []))
                        })
                    df_g = pd.DataFrame(g_rows)
                    st.dataframe(
                        df_g.style.format({"Toplam Tutar": "₺ {:,.0f}", "Ödenen": "₺ {:,.0f}", "Kalan": "₺ {:,.0f}"}),
                        use_container_width=True, hide_index=True
                    )

    # Gruplanmamış borçlar varsa bilgi ver
    if ungrouped_debts:
        st.markdown('<div class="section-title">Bağımsız / Gruplanmamış Borçlar</div>', unsafe_allow_html=True)
        un_rem = sum(
            inst['amount']
            for d in ungrouped_debts
            for inst in d.get('installments', [])
            if not inst['is_paid']
        )
        st.caption(f"Toplam {len(ungrouped_debts)} adet bağımsız borç kalemi mevcut (Kalan Yük: ₺{un_rem:,.0f}). İsterseniz aşağıdaki 'Grup Yönetimi' sekmesinden bunları bir gruba toplayabilirsiniz.")

    st.divider()

    # ── 3. TAKSİT TABLOSU ──
    today = date.today()
    all_inst_rows = []
    grup_id_adi_map = {g['id']: g.get('name', f"Grup {g['id']}") for g in groups}

    for d in debts:
        grup = grup_id_adi_map.get(d.get('group_id'), '—')
        for inst in d.get('installments', []):
            due = pd.to_datetime(inst['due_date']).date()
            kalan = (due - today).days
            if inst['is_paid']:
                s = "✅ Ödendi"
            elif kalan < 0:
                s = f"🔴 {abs(kalan)}g gecikti"
            elif kalan <= 3:
                s = f"⚠️ {kalan}g kaldı"
            else:
                s = f"⏳ {kalan}g"
            all_inst_rows.append({
                "id":      inst['id'],
                "Grup":    grup,
                "Borç":    d['name'],
                "Tutar":   inst['amount'],
                "Vade":    inst['due_date'],
                "Durum":   s,
                "is_paid": inst['is_paid'],
            })

    if all_inst_rows:
        st.markdown('<div class="section-title">Detaylı Taksit Planı</div>', unsafe_allow_html=True)
        df_all = pd.DataFrame(all_inst_rows).sort_values("Vade")

        fil1, fil2, _ = st.columns([1, 2, 2])
        with fil1:
            durum_filtre = st.selectbox("Durum Filtresi", ["Ödenmemiş", "Tümü", "Gecikmiş", "Ödenenler"])
        with fil2:
            borc_isimleri = ["Tümü"] + sorted(set(df_all["Borç"]))
            borc_filtre = st.selectbox("Borç Seçimi", borc_isimleri)

        df_f = df_all.copy()
        if durum_filtre == "Ödenmemiş":
            df_f = df_f[~df_f["is_paid"]]
        elif durum_filtre == "Gecikmiş":
            df_f = df_f[df_f["Durum"].str.startswith("🔴")]
        elif durum_filtre == "Ödenenler":
            df_f = df_f[df_f["is_paid"]]
        if borc_filtre != "Tümü":
            df_f = df_f[df_f["Borç"] == borc_filtre]

        show_cols = ["Grup", "Borç", "Tutar", "Vade", "Durum"] if groups else ["Borç", "Tutar", "Vade", "Durum"]
        if not df_f.empty:
            st.dataframe(
                df_f[show_cols].style.format({"Tutar": "₺ {:,.0f}"}),
                use_container_width=True,
                height=min(36 * (len(df_f) + 1) + 3, 380),
                hide_index=True,
            )
        else:
            st.info("Filtre kriterlerinize uyan taksit kaydı bulunamadı.")
    elif not debts:
        st.info("Henüz sisteme girilmiş borç veya kredi kaydı yok.")

    st.divider()

    # ── 4. BORÇ VE GRUP İŞLEMLERİ ──
    st.markdown('<div class="section-title">Borç İşlemleri & Yönetim</div>', unsafe_allow_html=True)

    tab_yeni, tab_ode, tab_grup, tab_sil = st.tabs([
        "📝 Yeni Borç / Kredi Ekle", "✅ Ödeme Yönetimi", "🗂️ Grup Yönetimi", "🗑️ Kayıt Sil"
    ])

    # Yeni Borç Ekle (Doğrudan Grup Seçebilme Özelliği ile)
    with tab_yeni:
        st.caption("Toplam tutar, vade başlangıcı ve taksit sayısını girerek otomatik ödeme planı oluşturun. İsterseniz doğrudan bir gruba atayabilirsiniz.")

        with st.form("auto_debt_form", clear_on_submit=True):
            d_name = st.text_input("Borç / Kredi Tanımı", placeholder="Örn: Ev Kredisi, Müteahhit Ara Ödemesi, Araç Taksidi")

            col_tur1, col_tur2 = st.columns(2)
            with col_tur1:
                borc_tipi = st.radio("Borç Tipi", ["Taksitli Kredi / Borç", "Tek Seferlik Ödeme (1 Taksit)"], horizontal=True)
            with col_tur2:
                # Grup seçimi doğrudan borç ekleme formunda!
                grup_secenekleri = ["— Bağımsız (Grup Yok) —"] + [g['name'] for g in groups]
                secilen_grup_adi = st.selectbox("Ait Olduğu Grup (İsteğe Bağlı)", options=grup_secenekleri)

            col1, col2 = st.columns(2)
            with col1:
                d_total = st.number_input("Toplam Tutar (₺)", min_value=0.01, format="%.2f")
            with col2:
                default_count = 1 if "Tek Seferlik" in borc_tipi else 12
                d_count = st.number_input(
                    "Taksit Sayısı",
                    min_value=1,
                    max_value=360,
                    step=1,
                    value=default_count,
                    disabled=("Tek Seferlik" in borc_tipi)
                )

            d_start = st.date_input("İlk Taksit / Vade Tarihi", value=date.today())

            if d_total > 0 and d_count > 0:
                taksit_tutar = d_total / d_count
                st.caption(f"📋 Aylık Taksit: **₺{taksit_tutar:,.2f}** · Son Vade: **{(d_start + timedelta(days=30*(int(d_count)-1))).strftime('%d %b %Y')}**")

            if st.form_submit_button("📝 Ödeme Planını Oluştur", use_container_width=True):
                if not d_name:
                    st.error("Borç adı boş bırakılamaz.")
                else:
                    payload = {
                        "name": d_name.strip(),
                        "total_amount": float(d_total),
                        "installments_count": 1 if "Tek Seferlik" in borc_tipi else int(d_count),
                        "start_date": d_start.strftime("%Y-%m-%d")
                    }
                    res = requests.post(f"{API_URL}/debts/schedules/", json=payload)
                    if res.status_code == 200:
                        # Eğer kullanıcı grup seçtiyse, yeni oluşturulan borcu otomatik o gruba ata!
                        if secilen_grup_adi != "— Bağımsız (Grup Yok) —":
                            target_g_id = next((g['id'] for g in groups if g['name'] == secilen_grup_adi), None)
                            if target_g_id:
                                # Yeni borçları çekip son ekleneni bul
                                fresh_debts = requests.get(f"{API_URL}/debts/").json()
                                matched_debts = [d for d in fresh_debts if d['name'] == d_name.strip()]
                                if matched_debts:
                                    new_debt_id = matched_debts[-1]['id']
                                    requests.put(f"{API_URL}/debts/{new_debt_id}/assign-group", json={"group_id": target_g_id})

                        st.toast("✅ Borç ve ödeme planı başarıyla oluşturuldu!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("Ödeme planı oluşturulamadı.")

    # Ödeme Yönetimi (Ödeme İşaretle & Geri Al)
    with tab_ode:
        col_pay1, col_pay2 = st.columns(2)

        with col_pay1:
            st.markdown("**Ödendi Olarak İşaretle**")
            unpaid_list = []
            for d in debts:
                for inst in d.get('installments', []):
                    if not inst['is_paid']:
                        unpaid_list.append({
                            "id":    inst['id'],
                            "label": f"{d['name']} · {inst['due_date']} · ₺{inst['amount']:,.0f}",
                            "vade":  inst['due_date'],
                        })
            unpaid_list.sort(key=lambda x: x['vade'])

            if unpaid_list:
                with st.form("pay_form"):
                    unpaid_opts = {i['label']: i['id'] for i in unpaid_list}
                    selected_unpaid = st.selectbox("Ödenecek Taksit", options=list(unpaid_opts.keys()))
                    if st.form_submit_button("✅ Ödendi Olarak Kaydet", use_container_width=True):
                        res = requests.put(f"{API_URL}/installments/{unpaid_opts[selected_unpaid]}/toggle")
                        if res.status_code == 200:
                            st.toast("✅ Ödeme kaydedildi!")
                            time.sleep(0.8)
                            st.rerun()
            else:
                st.success("🎉 Tebrikler! Bekleyen ödenmemiş taksit yok.")

        with col_pay2:
            st.markdown("**Ödemeyi Geri Al (Yanlış İşaretleme Durumunda)**")
            paid_list = []
            for d in debts:
                for inst in d.get('installments', []):
                    if inst['is_paid']:
                        paid_list.append({
                            "id":    inst['id'],
                            "label": f"{d['name']} · {inst['due_date']} · ₺{inst['amount']:,.0f}",
                            "vade":  inst['due_date'],
                        })
            paid_list.sort(key=lambda x: x['vade'], reverse=True)

            if paid_list:
                with st.form("unpay_form"):
                    paid_opts = {i['label']: i['id'] for i in paid_list}
                    selected_paid = st.selectbox("Ödenen Taksit", options=list(paid_opts.keys()))
                    if st.form_submit_button("↩️ Ödenmedi Olarak Geri Al", use_container_width=True):
                        res = requests.put(f"{API_URL}/installments/{paid_opts[selected_paid]}/toggle")
                        if res.status_code == 200:
                            st.toast("↩️ Taksit tekrar ödenmedi durumuna getirildi.")
                            time.sleep(0.8)
                            st.rerun()
            else:
                st.caption("Henüz ödenmiş taksit kaydı yok.")

    # Grup Yönetimi (Yeni Grup & Borç Atama)
    with tab_grup:
        col_yeni_grup, col_ata = st.columns(2)

        with col_yeni_grup:
            st.markdown("**Yeni Borç Grubu / Proje Oluştur**")
            st.caption("Örneğin bir ev satın alımı için müteahhit ödemesi, kredi ve tapu masraflarını tek grupta toplayabilirsiniz.")
            with st.form("create_group_form", clear_on_submit=True):
                g_name  = st.text_input("Grup Adı", placeholder="Örn: Faras İncek Evi, Arsa Projesi")
                g_desc  = st.text_input("Açıklama (opsiyonel)", placeholder="Örn: 2026 sonu teslim ev ödemeleri")
                g_total = st.number_input("Sözleşme Tutarı (₺, opsiyonel)", min_value=0.0, value=0.0, format="%.0f")
                if st.form_submit_button("➕ Grubu Oluştur", use_container_width=True):
                    if not g_name:
                        st.error("Grup adı zorunludur.")
                    else:
                        payload = {"name": g_name.strip()}
                        if g_desc: payload["description"] = g_desc.strip()
                        if g_total > 0: payload["contracted_amount"] = float(g_total)
                        res = requests.post(f"{API_URL}/debt-groups/", json=payload)
                        if res.status_code == 200:
                            st.toast("✅ Grup başarıyla oluşturuldu!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error("Grup oluşturulamadı.")

        with col_ata:
            st.markdown("**Borcu Gruba Ata / Değiştir**")
            if groups and debts:
                with st.form("assign_group_form"):
                    grup_adi_by_debt_id = {
                        gd['id']: g['name'] for g in groups for gd in g.get('debts', [])
                    }
                    debt_opts = {}
                    for d in debts:
                        mevcut = grup_adi_by_debt_id.get(d['id'])
                        etiket = f"{d['name']} (Şu an: {mevcut})" if mevcut else f"{d['name']} (Grupsuz)"
                        debt_opts[etiket] = d['id']

                    group_opts = {g['name']: g['id'] for g in groups}
                    group_opts["— Gruptan Çıkar (Bağımsız Yap) —"] = None

                    sel_debt  = st.selectbox("Borç Kalemi", options=list(debt_opts.keys()))
                    sel_group = st.selectbox("Hedef Grup", options=list(group_opts.keys()))

                    if st.form_submit_button("🔗 Grubu Kaydet", use_container_width=True):
                        res = requests.put(
                            f"{API_URL}/debts/{debt_opts[sel_debt]}/assign-group",
                            json={"group_id": group_opts[sel_group]}
                        )
                        if res.status_code == 200:
                            st.toast("✅ Borç grubu güncellendi!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error("Atama yapılamadı.")
            else:
                st.info("Borç atamak için en az bir grup ve borç kalemi oluşturmalısınız.")

    # Sil
    with tab_sil:
        col_del_borc, col_del_grup = st.columns(2)

        with col_del_borc:
            st.markdown("**Borç Kalemi Sil**")
            debt_del_opts = {d['name']: d['id'] for d in debts}
            if debt_del_opts:
                with st.form("del_debt_form"):
                    selected_del_debt = st.selectbox("Silinecek Borç", options=list(debt_del_opts.keys()))
                    onay_borc = st.checkbox("Bu borcu ve bağlı tüm taksit planını kalıcı olarak sil")
                    if st.form_submit_button("🗑️ Borcu Sil", use_container_width=True):
                        if onay_borc:
                            res = requests.delete(f"{API_URL}/debts/{debt_del_opts[selected_del_debt]}")
                            if res.status_code == 200:
                                st.toast("🗑️ Borç silindi!")
                                time.sleep(0.8)
                                st.rerun()
                        else:
                            st.error("Silmek için onay kutusunu işaretleyin.")
            else:
                st.info("Silinecek borç kaydı yok.")

        with col_del_grup:
            st.markdown("**Grup Sil** *(Borçlar silinmez, sadece bağımsız kalır)*")
            group_del_opts = {g['name']: g['id'] for g in groups}
            if group_del_opts:
                with st.form("del_group_form"):
                    sel_del_group = st.selectbox("Silinecek Grup", options=list(group_del_opts.keys()))
                    onay_grup = st.checkbox("Grubu kaldır (içindeki borçlar bağımsız hale gelir)")
                    if st.form_submit_button("🗑️ Grubu Sil", use_container_width=True):
                        if onay_grup:
                            res = requests.delete(f"{API_URL}/debt-groups/{group_del_opts[sel_del_group]}")
                            if res.status_code == 200:
                                st.toast("🗑️ Grup silindi!")
                                time.sleep(0.8)
                                st.rerun()
                        else:
                            st.error("Silmek için onay kutusunu işaretleyin.")
            else:
                st.info("Silinecek grup yok.")


# =====================================================================
# SAYFA: TREND ANALİZİ
# =====================================================================
elif sayfa == "📈 Trend Analizi":

    st.markdown("## 📈 Trend Analizi")

    # ── 12 Aylık Nakit Akışı Takvimi ──
    st.markdown('<div class="section-title">Önümüzdeki 12 Ay — Aylık Borç Yükü Takvimi</div>', unsafe_allow_html=True)

    ay_listesi = []
    for i in range(12):
        m = (bugun.month - 1 + i) % 12 + 1
        y = bugun.year + (bugun.month - 1 + i) // 12
        ay_listesi.append((y, m))

    ay_toplam   = {}
    ay_detaylar = {}

    for d in debts:
        for inst in d.get('installments', []):
            if inst['is_paid']:
                continue
            due = pd.to_datetime(inst['due_date']).date()
            key = (due.year, due.month)
            if key in set(ay_listesi):
                ay_toplam[key]   = ay_toplam.get(key, 0.0) + inst['amount']
                ay_detaylar.setdefault(key, []).append((d['name'], inst['amount']))

    ay_etiketler = []
    ay_tutarlar  = []
    ay_renkler   = []
    ay_hover     = []
    ay_isimleri  = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
    maks = max(ay_toplam.values()) if ay_toplam else 1

    for (y, m) in ay_listesi:
        etiket = f"{ay_isimleri[m-1]} '{str(y)[2:]}"
        tutar  = ay_toplam.get((y, m), 0.0)
        detay  = ay_detaylar.get((y, m), [])

        ay_etiketler.append(etiket)
        ay_tutarlar.append(tutar)

        oran = tutar / maks if maks > 0 else 0
        if oran >= 0.6:
            renk = "rgba(239,83,80,0.85)"
        elif oran >= 0.25:
            renk = "rgba(255,167,38,0.80)"
        else:
            renk = "rgba(41,98,255,0.70)"
        ay_renkler.append(renk)

        if detay:
            satirlar = "<br>".join(f"  · {ad}: ₺{miktar:,.0f}" for ad, miktar in sorted(detay, key=lambda x: -x[1]))
            hover_txt = f"<b>{etiket}</b><br>Toplam: ₺{tutar:,.0f}<br>{satirlar}<extra></extra>"
        else:
            hover_txt = f"<b>{etiket}</b><br>Ödeme yok ✓<extra></extra>"
        ay_hover.append(hover_txt)

    bugun_key = (bugun.year, bugun.month)
    bugun_idx = next((i for i, k in enumerate(ay_listesi) if k == bugun_key), None)

    fig_nakit = go.Figure()
    fig_nakit.add_trace(go.Bar(
        x=ay_etiketler, y=ay_tutarlar,
        marker_color=ay_renkler, marker_line_width=0,
        hovertemplate=ay_hover, name="Aylık Taksit Yükü",
    ))

    if bugun_idx is not None and ay_tutarlar[bugun_idx] > 0:
        fig_nakit.add_annotation(
            x=ay_etiketler[bugun_idx], y=ay_tutarlar[bugun_idx],
            text="← Bu ay", showarrow=False,
            font=dict(size=11, color="#FFA726"), yshift=12,
        )

    odeme_olan = [t for t in ay_tutarlar if t > 0]
    if odeme_olan:
        ort = sum(odeme_olan) / len(odeme_olan)
        fig_nakit.add_hline(
            y=ort, line=dict(color="rgba(128,128,128,0.35)", width=1, dash="dot"),
            annotation_text=f"Aylık Ort. ₺{ort:,.0f}",
            annotation_position="bottom right",
            annotation_font=dict(size=10, color="rgba(128,128,128,0.5)"),
        )

    fig_nakit.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.08)", tickprefix="₺", tickformat=",.0f"),
        hovermode="x", font=dict(family="Inter"), showlegend=False, height=270,
    )
    st.plotly_chart(fig_nakit, use_container_width=True, config={"displayModeBar": False})

    # Metrikler
    toplam_12ay = sum(ay_tutarlar)
    aylik_ort   = sum(odeme_olan) / len(odeme_olan) if odeme_olan else 0
    en_agir     = max(zip(ay_tutarlar, ay_etiketler), key=lambda x: x[0]) if any(ay_tutarlar) else (0, "—")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("12 Aylık Toplam Borç", f"₺ {toplam_12ay:,.0f}")
    with c2:
        st.metric("Aylık Ortalama Yük", f"₺ {aylik_ort:,.0f}")
    with c3:
        st.metric("En Yoğun Ay", en_agir[1], delta=f"₺ {en_agir[0]:,.0f}", delta_color="inverse")

    st.divider()

    # ── Tarihsel Portföy Büyüme Grafiği ──
    st.markdown('<div class="section-title">Tarihsel Büyüme & Trend Grafiği</div>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        gosterge = st.radio(
            "Gösterge:",
            ["Net Servet", "Toplam Varlık", "Toplam Borç", "Karşılaştır (İndeks = 100)"],
            horizontal=True,
            label_visibility="collapsed"
        )
    with col_g2:
        grafik_tipi = st.selectbox("Grafik Türü", ["📈 Sade Çizgi / Alan Grafiği", "🕯️ Heikin Ashi Mum Grafiği"])

    try:
        res_hist = requests.get(f"{API_URL}/portfolio/history", timeout=5)
        if res_hist.status_code == 200 and res_hist.json():
            df_hist = pd.DataFrame(res_hist.json())
            df_hist['record_date'] = pd.to_datetime(df_hist['record_date'])
            df_hist.sort_values('record_date', inplace=True)

            min_date = df_hist['record_date'].min().date()
            max_date = df_hist['record_date'].max().date()

            if min_date < max_date:
                default_start = max(min_date, max_date - dt_module.timedelta(days=180))
                selected_dates = st.slider(
                    "Tarih Aralığı", min_value=min_date, max_value=max_date,
                    value=(default_start, max_date), format="DD.MM.YYYY",
                )
                mask = (df_hist['record_date'].dt.date >= selected_dates[0]) & (df_hist['record_date'].dt.date <= selected_dates[1])
                df_plot = df_hist[mask].copy()
            else:
                df_plot = df_hist.copy()

            if "Karşılaştır" not in gosterge:
                col_map = {
                    "Net Servet":    ("net_worth",    "#26A69A", "rgba(38,166,154,0.12)"),
                    "Toplam Varlık": ("total_assets", "#2962FF", "rgba(41,98,255,0.12)"),
                    "Toplam Borç":   ("total_debts",  "#EF5350", "rgba(239,83,80,0.12)"),
                }
                target_col, line_color, fill_color = col_map[gosterge]

                df_plot['prev_val']     = df_plot[target_col].shift(1)
                df_plot['daily_change'] = df_plot[target_col] - df_plot['prev_val']
                df_plot['daily_pct']    = (df_plot['daily_change'] / df_plot['prev_val'] * 100).fillna(0)
                df_plot['daily_change'] = df_plot['daily_change'].fillna(0)
                df_plot['sma_7']        = df_plot[target_col].rolling(window=7, min_periods=1).mean()

                if "Heikin Ashi" in grafik_tipi:
                    # Heikin Ashi Mum Grafiği
                    if target_col == "total_debts":
                        inc_color, dec_color = '#EF5350', '#26A69A'
                        df_plot['bar_color'] = df_plot['daily_change'].apply(lambda x: '#EF5350' if x > 0 else '#26A69A')
                    else:
                        inc_color, dec_color = '#26A69A', '#EF5350'
                        df_plot['bar_color'] = df_plot['daily_change'].apply(lambda x: '#26A69A' if x >= 0 else '#EF5350')

                    df_plot['O'] = df_plot['prev_val'].fillna(df_plot[target_col])
                    df_plot['C'] = df_plot[target_col]
                    df_plot['H'] = df_plot[['O', 'C']].max(axis=1)
                    df_plot['L'] = df_plot[['O', 'C']].min(axis=1)

                    ha_c = (df_plot['O'] + df_plot['H'] + df_plot['L'] + df_plot['C']) / 4
                    ha_o = [df_plot['O'].iloc[0]]
                    for i in range(1, len(df_plot)):
                        ha_o.append((ha_o[-1] + ha_c.iloc[i-1]) / 2)

                    df_plot['HA_O'] = ha_o
                    df_plot['HA_C'] = ha_c
                    df_plot['HA_H'] = df_plot[['H', 'HA_O', 'HA_C']].max(axis=1)
                    df_plot['HA_L'] = df_plot[['L', 'HA_O', 'HA_C']].min(axis=1)

                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])

                    hover_texts = [
                        f"<b>{r['record_date'].strftime('%d %b %Y')}</b><br>{gosterge}: ₺{r[target_col]:,.0f}<br>Δ ₺{r['daily_change']:,.0f} ({r['daily_pct']:.2f}%)"
                        for _, r in df_plot.iterrows()
                    ]

                    fig.add_trace(go.Candlestick(
                        x=df_plot['record_date'],
                        open=df_plot['HA_O'], high=df_plot['HA_H'],
                        low=df_plot['HA_L'], close=df_plot['HA_C'],
                        increasing_line_color=inc_color, decreasing_line_color=dec_color,
                        name=gosterge + ' (HA)', text=hover_texts, hoverinfo='text'
                    ), row=1, col=1)

                    fig.add_trace(go.Scatter(
                        x=df_plot['record_date'], y=df_plot['sma_7'],
                        mode='lines', line=dict(color='#FFA726', width=1.5, dash='dash'),
                        name='SMA(7)', hovertemplate='<b>%{x|%d %b %Y}</b><br>SMA7: ₺%{y:,.0f}<extra></extra>'
                    ), row=1, col=1)

                    fig.add_trace(go.Bar(
                        x=df_plot['record_date'], y=df_plot['daily_change'],
                        marker_color=df_plot['bar_color'], name='Günlük Değişim',
                        hovertemplate='<b>%{x|%d %b %Y}</b><br>Δ ₺%{y:,.0f}<extra></extra>'
                    ), row=2, col=1)

                    fig.update_layout(xaxis_rangeslider_visible=False)
                    fig.update_xaxes(row=1, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)')
                    fig.update_xaxes(row=2, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)')
                    fig.update_yaxes(row=1, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)', tickprefix="₺", fixedrange=False)
                    fig.update_yaxes(row=2, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)', fixedrange=False)

                else:
                    # Sade Alan/Çizgi Grafiği
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])

                    fig.add_trace(go.Scatter(
                        x=df_plot['record_date'], y=df_plot[target_col],
                        mode='lines', fill='tozeroy', fillcolor=fill_color,
                        line=dict(color=line_color, width=2.5),
                        name=gosterge,
                        hovertemplate='<b>%{x|%d %b %Y}</b><br>' + gosterge + ': ₺%{y:,.0f}<extra></extra>'
                    ), row=1, col=1)

                    fig.add_trace(go.Scatter(
                        x=df_plot['record_date'], y=df_plot['sma_7'],
                        mode='lines', line=dict(color='#FFA726', width=1.5, dash='dash'),
                        name='7 Günlük Ort. (SMA)',
                        hovertemplate='<b>%{x|%d %b %Y}</b><br>SMA7: ₺%{y:,.0f}<extra></extra>'
                    ), row=1, col=1)

                    bar_colors = ['#26A69A' if v >= 0 else '#EF5350' for v in df_plot['daily_change']]
                    fig.add_trace(go.Bar(
                        x=df_plot['record_date'], y=df_plot['daily_change'],
                        marker_color=bar_colors, name='Günlük Değişim',
                        hovertemplate='<b>%{x|%d %b %Y}</b><br>Δ ₺%{y:,.0f}<extra></extra>'
                    ), row=2, col=1)

                    fig.update_xaxes(row=1, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)')
                    fig.update_xaxes(row=2, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)')
                    fig.update_yaxes(row=1, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)', tickprefix="₺", fixedrange=False)
                    fig.update_yaxes(row=2, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.08)', fixedrange=False)

            else:
                # Karşılaştırma Modu (İndeks = 100)
                SERIES = [
                    ("total_assets", "#2962FF", "Toplam Varlık", "rgba(41,98,255,0.05)"),
                    ("net_worth",    "#26A69A", "Net Servet",    "rgba(38,166,154,0.05)"),
                    ("total_debts",  "#EF5350", "Toplam Borç",   "rgba(239,83,80,0.04)"),
                ]

                fig = go.Figure()
                for col, color, name, fc in SERIES:
                    base = df_plot[col].iloc[0]
                    if base == 0:
                        continue
                    indexed = (df_plot[col] / base) * 100
                    actual  = df_plot[col]
                    pct_chg = indexed - 100

                    fig.add_trace(go.Scatter(
                        x=df_plot['record_date'], y=indexed,
                        mode='lines', fill='tozeroy', fillcolor=fc,
                        line=dict(color=color, width=2), name=name,
                        customdata=list(zip(actual, pct_chg)),
                        hovertemplate=(
                            f'<b>%{{x|%d %b %Y}}</b><br>'
                            f'{name}: ₺%{{customdata[0]:,.0f}}<br>'
                            f'Değişim: %{{customdata[1]:+.1f}}%'
                            f'<extra></extra>'
                        ),
                    ))

                fig.add_hline(
                    y=100, line=dict(color="rgba(128,128,128,0.3)", width=1, dash="dot"),
                    annotation_text="Baz Çizgisi (100)",
                    annotation_position="bottom right",
                    annotation_font=dict(size=10, color="rgba(128,128,128,0.5)"),
                )
                fig.update_layout(
                    xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.08)'),
                    yaxis=dict(
                        showgrid=True, gridcolor='rgba(128,128,128,0.08)',
                        tickformat=".0f",
                        title=dict(text="Gelişim İndeksi (Baz = 100)", font=dict(size=11)),
                    )
                )

            fig.update_layout(
                separators=".,",
                margin=dict(l=0, r=0, t=10, b=0),
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=11)),
                font=dict(family='Inter'),
                height=450,
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.caption("Veriler, 'Piyasa Fiyatlarını Güncelle' butonuna basılan anlardaki portföy kapanış değerlerini yansıtır.")
        else:
            st.info("Henüz tarihsel grafik çizecek kadar veri kaydedilmedi. Sidebar'daki 'Piyasa Fiyatlarını Güncelle' butonuna basarak ilk anlık görüntüyü kaydedebilirsiniz.")

    except Exception as e:
        st.error(f"Grafik yüklenirken bir hata oluştu: {repr(e)}")