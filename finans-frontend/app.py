import streamlit as st
import requests
import pandas as pd
import os
import time
from datetime import date
import plotly.graph_objects as go
from plotly.subplots import make_subplots

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Finans Dashboard", layout="wide", page_icon="📈")

# =====================================================================
# GLOBAL CSS — Modern & Kompakt Tema (OS Senkronize)
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ─── Genel ─────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Üst padding sıkıştır */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 1400px;
}

/* Streamlit varsayılan başlık gizle */
#MainMenu, footer, header { visibility: hidden; }

/* ─── Dashboard Header ───────────────────────────── */
.dash-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1.2rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid rgba(128,128,128,0.15);
}
.dash-title {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.3px;
    margin: 0;
}
.badge-live {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    background: rgba(38, 166, 154, 0.15);
    color: #26A69A;
    border: 1px solid rgba(38, 166, 154, 0.3);
    letter-spacing: 0.3px;
}
.badge-danger {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    background: rgba(239, 83, 80, 0.12);
    color: #EF5350;
    border: 1px solid rgba(239, 83, 80, 0.25);
}
.badge-warning {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    background: rgba(255, 167, 38, 0.12);
    color: #FFA726;
    border: 1px solid rgba(255, 167, 38, 0.25);
}
.dash-meta {
    margin-left: auto;
    font-size: 12px;
    opacity: 0.55;
    font-weight: 400;
}

/* ─── KPI Kartları ───────────────────────────────── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 1.2rem;
}
.kpi-card {
    padding: 16px 18px;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,0.13);
    background: rgba(128,128,128,0.04);
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: rgba(128,128,128,0.28); }
.kpi-card-accent {
    background: linear-gradient(135deg, rgba(41,98,255,0.08), rgba(0,188,212,0.05));
    border-color: rgba(41,98,255,0.22) !important;
}
.kpi-label {
    font-size: 11px;
    font-weight: 500;
    opacity: 0.5;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 1.45rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 11px;
    opacity: 0.45;
    margin-top: 4px;
    font-weight: 400;
}
.kpi-positive { color: #26A69A; }
.kpi-negative { color: #EF5350; }

/* ─── Tabs ───────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(128,128,128,0.06);
    padding: 4px;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,0.1);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    padding: 5px 14px;
    font-size: 13px;
    font-weight: 500;
    border: none !important;
    background: transparent;
    transition: all 0.15s;
}
.stTabs [aria-selected="true"] {
    background: rgba(41, 98, 255, 0.18) !important;
    color: #2962FF !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1rem;
}

/* ─── Butonlar ───────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 16px !important;
    transition: all 0.15s !important;
    border: 1px solid rgba(128,128,128,0.2) !important;
}
.stButton > button:hover {
    border-color: rgba(41,98,255,0.5) !important;
    transform: translateY(-1px);
    box-shadow: 0 3px 10px rgba(41,98,255,0.15) !important;
}

/* ─── Tablo ──────────────────────────────────────── */
.stDataFrame {
    border-radius: 10px;
    overflow: hidden;
    font-size: 13px !important;
}
.stDataFrame [data-testid="stDataFrameResizable"] {
    border-radius: 10px !important;
}

/* ─── Formlar ────────────────────────────────────── */
.stForm {
    border-radius: 10px !important;
    border: 1px solid rgba(128,128,128,0.12) !important;
    padding: 12px !important;
}
[data-testid="stExpander"] {
    border-radius: 10px !important;
    border: 1px solid rgba(128,128,128,0.12) !important;
}
[data-testid="stExpander"] summary {
    font-size: 13px !important;
    font-weight: 500 !important;
}

/* ─── Input'lar ──────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    border-radius: 7px !important;
    font-size: 13px !important;
}

/* ─── Divider ────────────────────────────────────── */
hr { opacity: 0.12; margin: 0.8rem 0 !important; }

/* ─── Metric override ────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(128,128,128,0.04);
    border: 1px solid rgba(128,128,128,0.1);
    border-radius: 10px;
    padding: 12px 16px;
}
[data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { font-size: 11px !important; opacity: 0.5; font-weight: 500 !important; }

/* ─── Alert banner kompakt ───────────────────────── */
.alert-compact {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 12.5px;
    font-weight: 500;
    margin-bottom: 10px;
    flex-wrap: wrap;
}
.alert-compact-danger {
    background: rgba(239,83,80,0.08);
    border: 1px solid rgba(239,83,80,0.2);
    color: #EF5350;
}
.alert-compact-warning {
    background: rgba(255,167,38,0.08);
    border: 1px solid rgba(255,167,38,0.2);
    color: #FFA726;
}

/* ─── Section başlık ─────────────────────────────── */
.section-title {
    font-size: 13px;
    font-weight: 600;
    opacity: 0.45;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    margin: 1rem 0 0.5rem;
}

/* ─── Caption / küçük yazı ───────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
    font-size: 11.5px !important;
    opacity: 0.5 !important;
}
</style>
""", unsafe_allow_html=True)


# =====================================================================
# YARDIMCI FONKSİYONLAR
# =====================================================================
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
global_total_debts   = 0.0
summary_data = []
debts = []

try:
    res_assets = requests.get(f"{API_URL}/portfolio/summary", timeout=5)
    if res_assets.status_code == 200:
        summary_data = res_assets.json()
        for item in summary_data:
            net_val = item.get('net_value') or 0.0
            if item.get('asset_type') == 'US_STOCK':
                net_val *= usd_try_rate
            global_total_assets += net_val
    else:
        st.warning(f"Portföy verisi alınamadı. (HTTP {res_assets.status_code})")

    res_debts = requests.get(f"{API_URL}/debts/", timeout=5)
    if res_debts.status_code == 200:
        debts = res_debts.json()
        for d in debts:
            for inst in d.get('installments', []):
                if not inst['is_paid']:
                    global_total_debts += inst['amount']
    else:
        st.warning(f"Borç verisi alınamadı. (HTTP {res_debts.status_code})")

except requests.exceptions.ConnectionError:
    st.error("Backend'e bağlanılamıyor. Servis çalışıyor mu?")
except requests.exceptions.Timeout:
    st.error("Backend yanıt vermedi. Zaman aşımı.")
except Exception as e:
    st.error(f"Beklenmedik hata: {repr(e)}")


# =====================================================================
# GECİKMİŞ / YAKLAŞAN TAKSİT HESABI
# =====================================================================
gecikmiş = []
yaklasan = []
bugun = date.today()

for d in debts:
    for inst in d.get('installments', []):
        if not inst['is_paid']:
            vade  = pd.to_datetime(inst['due_date']).date()
            kalan = (vade - bugun).days
            if kalan < 0:
                gecikmiş.append(f"{d['name']} ₺{inst['amount']:,.0f} ({abs(kalan)}g gecikmiş)")
            elif kalan <= 3:
                yaklasan.append(f"{d['name']} ₺{inst['amount']:,.0f} ({kalan}g kaldı)")


# =====================================================================
# DASHBOARD HEADER
# =====================================================================
net_worth    = global_total_assets - global_total_debts
badge_alerts = ""
if gecikmiş:
    badge_alerts += f'<span class="badge-danger">🔴 {len(gecikmiş)} gecikmiş</span> '
if yaklasan:
    badge_alerts += f'<span class="badge-warning">⚠️ {len(yaklasan)} yaklaşıyor</span>'

st.markdown(f"""
<div class="dash-header">
    <span class="dash-title">💰 Finans Dashboard</span>
    <span class="badge-live">● Canlı</span>
    {badge_alerts}
    <span class="dash-meta">USD/TRY ₺{usd_try_rate:,.2f} &nbsp;|&nbsp; {bugun.strftime('%d %b %Y')}</span>
</div>
""", unsafe_allow_html=True)


# =====================================================================
# KPI KARTLARI
# =====================================================================
net_color  = "kpi-positive" if net_worth >= 0 else "kpi-negative"
net_sign   = "+" if net_worth >= 0 else ""
varlik_cnt = len(summary_data)
borc_cnt   = len(debts)

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">💼 Toplam Varlık</div>
        <div class="kpi-value">₺ {global_total_assets:,.0f}</div>
        <div class="kpi-sub">{varlik_cnt} aktif varlık türü</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">💳 Toplam Borç</div>
        <div class="kpi-value">₺ {global_total_debts:,.0f}</div>
        <div class="kpi-sub">{borc_cnt} borç kalemi</div>
    </div>
    <div class="kpi-card kpi-card-accent">
        <div class="kpi-label">📈 Net Servet</div>
        <div class="kpi-value {net_color}">₺ {net_worth:,.0f}</div>
        <div class="kpi-sub">{net_sign}{(net_worth/global_total_assets*100) if global_total_assets else 0:.1f}% oran</div>
    </div>
</div>
""", unsafe_allow_html=True)


# =====================================================================
# KOMPAKT ALERT BANNER (büyük error/warning kutuları yerine)
# =====================================================================
if gecikmiş:
    items = " &nbsp;·&nbsp; ".join(gecikmiş)
    st.markdown(f'<div class="alert-compact alert-compact-danger">🔴 <b>Gecikmiş:</b> {items}</div>',
                unsafe_allow_html=True)
if yaklasan:
    items = " &nbsp;·&nbsp; ".join(yaklasan)
    st.markdown(f'<div class="alert-compact alert-compact-warning">⚠️ <b>Yaklaşan:</b> {items}</div>',
                unsafe_allow_html=True)


# =====================================================================
# TABS
# =====================================================================
borc_tab_label = f"💳 Borç Takibi {'🔴' if gecikmiş else '⚠️' if yaklasan else ''}"
tab_portfoy, tab_borc, tab_trend = st.tabs(["📊 Portföy", borc_tab_label, "📈 Trend"])


# =====================================================================
# 1. TAB: PORTFÖY ÖZETİ
# =====================================================================
with tab_portfoy:

    # ── Üst satır: Son güncelleme + buton ──
    col_info, col_btn = st.columns([4, 1])

    with col_info:
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
            st.caption(f"🕐 Son fiyat güncellemesi: {son_guncelleme.strftime('%H:%M')} — {fark_str}")
        else:
            st.caption("🕐 Henüz fiyat güncellenmedi")

    with col_btn:
        if st.button("🔄 Fiyatları Güncelle", use_container_width=True):
            with st.spinner("Piyasalar taranıyor..."):
                res = requests.post(f"{API_URL}/assets/update-prices")
                if res.status_code == 200:
                    requests.post(f"{API_URL}/portfolio/snapshot", json={
                        "total_assets": global_total_assets,
                        "total_debts":  global_total_debts
                    }, timeout=2)
                    st.toast("📈 Fiyatlar güncellendi!")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("Fiyat güncellenemedi.")

    # ── Portföy tablosu + Pasta grafik ──
    if summary_data:
        col_tablo, col_pasta = st.columns([3, 1])

        with col_tablo:
            st.markdown('<div class="section-title">Varlık Dağılımı</div>', unsafe_allow_html=True)
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

                if item.get('last_updated'):
                    dt = pd.to_datetime(item['last_updated'])
                    if dt.tzinfo is None:
                        dt = dt.tz_localize('UTC').tz_convert('Europe/Istanbul')
                    else:
                        dt = dt.tz_convert('Europe/Istanbul')
                    last_upd_str = dt.strftime('%d.%m %H:%M')
                else:
                    last_upd_str = "—"

                portfolio_table.append({
                    "Tür":            item.get('asset_type', '—'),
                    "Sembol":         item.get('symbol', '—'),
                    "Ad":             item.get('name', '—'),
                    "Miktar":         item.get('total_qty') or 0.0,
                    "Fiyat":          display_price,
                    "Değişim":        change_str,
                    "Net Değer (₺)":  net_val_try,
                    "Güncelleme":     last_upd_str,
                })

            df = pd.DataFrame(portfolio_table)
            st.dataframe(
                df.style.format({"Net Değer (₺)": "{:,.0f}", "Miktar": "{:,.4f}"}),
                use_container_width=True,
                height=min(36 * (len(df) + 1) + 3, 400),
                hide_index=True,
            )

        with col_pasta:
            st.markdown('<div class="section-title">Dağılım</div>', unsafe_allow_html=True)
            pie_data = {}
            for item in summary_data:
                a_type  = item.get('asset_type', 'BİLİNMEYEN')
                net_val = item.get('net_value') or 0.0
                if a_type == 'US_STOCK':
                    net_val *= usd_try_rate
                pie_data[a_type] = pie_data.get(a_type, 0) + net_val

            if pie_data:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=list(pie_data.keys()),
                    values=list(pie_data.values()),
                    hole=0.55,
                    textinfo='label+percent',
                    textfont=dict(size=11, family='Inter'),
                    hovertemplate='<b>%{label}</b><br>₺%{value:,.0f}<br>%{percent}<extra></extra>',
                    marker=dict(colors=['#2962FF', '#00BCD4', '#FF6F00', '#43A047', '#8E24AA'],
                                line=dict(width=0))
                )])
                fig_pie.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=200,
                )
                st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sistemde henüz varlık bulunmuyor.")

    # ── İşlem / Yönetim — Expander'lar ──
    st.markdown('<div class="section-title">İşlemler</div>', unsafe_allow_html=True)

    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
        with st.expander("📥 Alım / Satım Kaydet", expanded=False):
            if summary_data:
                with st.form("txn_form"):
                    asset_options = {f"{a.get('symbol')} — {a.get('name')}": a.get('asset_id') for a in summary_data}
                    selected_asset = st.selectbox("Varlık", options=list(asset_options.keys()), label_visibility="collapsed")
                    c1, c2 = st.columns(2)
                    with c1:
                        islem_turu = st.radio("Yön", ["Alış (+)", "Satış (-)"], horizontal=True)
                    t_qty   = st.number_input("Miktar", min_value=0.0001, format="%.4f")
                    t_price = st.number_input("Birim Fiyat", min_value=0.01, format="%.2f")
                    t_date  = st.date_input("Tarih", value=date.today())
                    if st.form_submit_button("Kaydet", use_container_width=True):
                        final_qty = float(t_qty) if islem_turu == "Alış (+)" else -float(t_qty)
                        res = requests.post(f"{API_URL}/transactions/", json={
                            "asset_id": asset_options[selected_asset],
                            "quantity": final_qty,
                            "unit_price": float(t_price),
                            "transaction_date": t_date.strftime("%Y-%m-%d")
                        })
                        if res.status_code == 200:
                            st.toast(f"✅ {islem_turu} kaydedildi!")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error(res.json().get("detail", "Hata"))
            else:
                st.info("Önce bir varlık ekleyin.")

    with exp_col2:
        with st.expander("➕ Yeni Varlık Ekle", expanded=False):
            with st.form("add_asset_form"):
                a_type = st.selectbox("Tür", ["US_STOCK", "TR_STOCK", "FUND", "COMMODITY", "FIAT"])
                a_sym  = st.text_input("Sembol (Örn: QQQM, ALTIN, USD)")
                a_name = st.text_input("Ad")
                if st.form_submit_button("Ekle", use_container_width=True):
                    res = requests.post(f"{API_URL}/assets/", json={"asset_type": a_type, "symbol": a_sym, "name": a_name})
                    if res.status_code == 200:
                        st.toast("✅ Varlık eklendi!")
                        time.sleep(0.8)
                        st.rerun()

    with exp_col3:
        with st.expander("🗑️ Varlık Sil", expanded=False):
            if summary_data:
                with st.form("del_asset_form"):
                    del_opts = {f"{a.get('symbol')} — {a.get('name')}": a.get('asset_id') for a in summary_data}
                    selected_del = st.selectbox("Varlık", options=list(del_opts.keys()), label_visibility="collapsed")
                    onay = st.checkbox("İşlemi ve geçmişi kalıcı sil")
                    if st.form_submit_button("Sil", use_container_width=True):
                        if onay:
                            res = requests.delete(f"{API_URL}/assets/{del_opts[selected_del]}")
                            if res.status_code == 200:
                                st.toast("🗑️ Silindi!")
                                time.sleep(0.8)
                                st.rerun()
                        else:
                            st.error("Onay kutusunu işaretleyin.")
            else:
                st.info("Silinecek varlık yok.")


# =====================================================================
# 2. TAB: BORÇ TAKİBİ
# =====================================================================
with tab_borc:

    if debts:
        installments_data = []
        today = date.today()

        for d in debts:
            for inst in d.get('installments', []):
                due_date_obj = pd.to_datetime(inst['due_date']).date()
                days_left    = (due_date_obj - today).days

                if inst['is_paid']:
                    status_str = "✅ Ödendi"
                elif days_left < 0:
                    status_str = f"🔴 {abs(days_left)}g gecikmiş"
                elif days_left <= 3:
                    status_str = f"⚠️ {days_left}g kaldı"
                else:
                    status_str = f"⏳ {days_left}g"

                installments_data.append({
                    "id":             inst['id'],
                    "Borç":           d['name'],
                    "Tutar":          inst['amount'],
                    "Vade":           inst['due_date'],
                    "Durum":          status_str,
                    "is_paid":        inst['is_paid'],
                })

        # ── Filtreler ──
        fil_col1, fil_col2, fil_col3 = st.columns([1, 2, 1])
        with fil_col1:
            durum_filtre = st.selectbox("Durum", ["Tümü", "Ödenmemiş", "Gecikmiş", "Ödenenler"], label_visibility="collapsed")
        with fil_col2:
            borc_isimleri = ["Tümü"] + sorted(set(i["Borç"] for i in installments_data))
            borc_filtre   = st.selectbox("Borç", borc_isimleri, label_visibility="collapsed")

        filtrelenmis = installments_data.copy()
        if durum_filtre == "Ödenmemiş":
            filtrelenmis = [i for i in filtrelenmis if not i['is_paid']]
        elif durum_filtre == "Gecikmiş":
            filtrelenmis = [i for i in filtrelenmis if not i['is_paid'] and
                            (pd.to_datetime(i['Vade']).date() - date.today()).days < 0]
        elif durum_filtre == "Ödenenler":
            filtrelenmis = [i for i in filtrelenmis if i['is_paid']]
        if borc_filtre != "Tümü":
            filtrelenmis = [i for i in filtrelenmis if i['Borç'] == borc_filtre]

        if filtrelenmis:
            df_f = pd.DataFrame(filtrelenmis).sort_values("Vade")
            st.dataframe(
                df_f[["Borç", "Tutar", "Vade", "Durum"]].style.format({"Tutar": "₺ {:,.2f}"}),
                use_container_width=True,
                height=min(36 * (len(df_f) + 1) + 3, 380),
                hide_index=True,
            )
        else:
            st.info("Seçilen filtreyle eşleşen kayıt yok.")

        # ── Ödeme İşaretleme ──
        unpaid = sorted([i for i in installments_data if not i['is_paid']], key=lambda x: x['Vade'])
        if unpaid:
            st.markdown('<div class="section-title">Ödeme İşaretle</div>', unsafe_allow_html=True)
            with st.form("pay_form"):
                unpaid_opts = {f"{i['Borç']}  |  {i['Vade']}  |  ₺{i['Tutar']:,.0f}": i['id'] for i in unpaid}
                selected_unpaid = st.selectbox("Taksit", options=list(unpaid_opts.keys()), label_visibility="collapsed")
                if st.form_submit_button("✅ Ödendi Olarak İşaretle", use_container_width=True):
                    res = requests.put(f"{API_URL}/installments/{unpaid_opts[selected_unpaid]}/toggle")
                    if res.status_code == 200:
                        st.toast("✅ Ödeme kaydedildi!")
                        time.sleep(0.8)
                        st.rerun()
    else:
        st.info("Aktif borç kaydı bulunmuyor.")

    st.divider()

    # ── Borç Yönetimi ──
    st.markdown('<div class="section-title">Borç Yönetimi</div>', unsafe_allow_html=True)
    mgmt_col1, mgmt_col2 = st.columns(2)

    with mgmt_col1:
        with st.expander("📝 Otomatik Ödeme Planı Oluştur", expanded=False):
            with st.form("auto_debt_form"):
                d_name  = st.text_input("Borç / Kredi Adı")
                d_total = st.number_input("Toplam Tutar", min_value=0.01)
                c1, c2  = st.columns(2)
                with c1:
                    d_count = st.number_input("Taksit Sayısı", min_value=1, max_value=360, step=1, value=12)
                with c2:
                    d_start = st.date_input("İlk Taksit", value=date.today())
                if st.form_submit_button("Plan Oluştur", use_container_width=True):
                    payload = {"name": d_name, "total_amount": float(d_total),
                               "installments_count": int(d_count),
                               "start_date": d_start.strftime("%Y-%m-%d")}
                    res = requests.post(f"{API_URL}/debts/schedules/", json=payload)
                    if res.status_code == 200:
                        st.toast("✅ Plan oluşturuldu!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("Plan oluşturulamadı.")

    with mgmt_col2:
        with st.expander("🗑️ Borç Sil", expanded=False):
            with st.form("del_debt_form"):
                debt_opts = {d['name']: d['id'] for d in debts}
                if debt_opts:
                    selected_del_debt = st.selectbox("Borç", options=list(debt_opts.keys()), label_visibility="collapsed")
                    onay_borc = st.checkbox("Borcu ve tüm taksit planını kalıcı sil")
                    if st.form_submit_button("Sil", use_container_width=True):
                        if onay_borc:
                            res = requests.delete(f"{API_URL}/debts/{debt_opts[selected_del_debt]}")
                            if res.status_code == 200:
                                st.toast("🗑️ Silindi!")
                                time.sleep(0.8)
                                st.rerun()
                        else:
                            st.error("Onay kutusunu işaretleyin.")
                else:
                    st.info("Silinecek borç yok.")


# =====================================================================
# 3. TAB: TREND ANALİZİ
# =====================================================================
with tab_trend:

    today_date    = date.today()
    current_month = today_date.month
    current_year  = today_date.year

    bu_ayki_borc = 0.0
    for d in debts:
        for inst in d.get('installments', []):
            due = pd.to_datetime(inst['due_date']).date()
            if not inst['is_paid'] and due.month == current_month and due.year == current_year:
                bu_ayki_borc += inst['amount']

    ay_sonu = global_total_assets - bu_ayki_borc

    # ── Ay Sonu Projeksiyonu ──
    st.markdown('<div class="section-title">Bu Ay Sonu Projeksiyonu</div>', unsafe_allow_html=True)
    col_n1, col_n2, col_n3 = st.columns(3)
    with col_n1:
        st.metric("Mevcut Varlık", f"₺ {global_total_assets:,.0f}")
    with col_n2:
        st.metric("Bu Ay Taksitler", f"₺ {bu_ayki_borc:,.0f}", delta="Likidasyon", delta_color="inverse")
    with col_n3:
        delta_lbl = "Artıda ✓" if ay_sonu >= 0 else "Ekside ✗"
        delta_clr = "normal" if ay_sonu >= 0 else "inverse"
        st.metric("Ay Sonu Net", f"₺ {ay_sonu:,.0f}", delta=delta_lbl, delta_color=delta_clr)

    if ay_sonu < 0:
        st.markdown(f'<div class="alert-compact alert-compact-danger">⚠️ <b>Kritik:</b> Bu ayki yük tüm varlıkları aşıyor. Ek kaynak ihtiyacı: ₺ {abs(ay_sonu):,.0f}</div>',
                    unsafe_allow_html=True)
    elif bu_ayki_borc > 0:
        st.markdown(f'<div class="alert-compact alert-compact-warning">💡 Bu ay ₺ {bu_ayki_borc:,.0f} likidasyon planlanmalı. Sonrası: ₺ {ay_sonu:,.0f}</div>',
                    unsafe_allow_html=True)
    else:
        st.success("✅ Bu ay ödenmesi gereken taksit yok.")

    st.divider()

    # ── Tarihsel Grafik ──
    st.markdown('<div class="section-title">Tarihsel Büyüme Grafiği</div>', unsafe_allow_html=True)

    gosterge = st.radio(
        "Gösterge:",
        ["Net Servet", "Toplam Varlık", "Toplam Borç", "Karşılaştır"],
        horizontal=True,
        label_visibility="collapsed"
    )

    try:
        res_hist = requests.get(f"{API_URL}/portfolio/history", timeout=5)
        if res_hist.status_code == 200 and res_hist.json():
            df_hist = pd.DataFrame(res_hist.json())
            df_hist['record_date'] = pd.to_datetime(df_hist['record_date'])
            df_hist.sort_values('record_date', inplace=True)

            RANGE_BUTTONS = list([
                dict(count=1,  label="1A",  step="month",  stepmode="backward"),
                dict(count=3,  label="3A",  step="month",  stepmode="backward"),
                dict(count=6,  label="6A",  step="month",  stepmode="backward"),
                dict(count=1,  label="YTD", step="year",   stepmode="todate"),
                dict(step="all", label="Tümü"),
            ])

            if gosterge != "Karşılaştır":
                col_map = {
                    "Net Servet":   ("net_worth",    "#26A69A", "rgba(38,166,154,0.12)"),
                    "Toplam Varlık":("total_assets", "#2962FF", "rgba(41,98,255,0.12)"),
                    "Toplam Borç":  ("total_debts",  "#EF5350", "rgba(239,83,80,0.12)"),
                }
                target_col, line_color, fill_color = col_map[gosterge]

                df_hist['prev_val']    = df_hist[target_col].shift(1)
                df_hist['daily_change']= df_hist[target_col] - df_hist['prev_val']
                df_hist['daily_pct']   = (df_hist['daily_change'] / df_hist['prev_val'] * 100).fillna(0)
                df_hist['daily_change']= df_hist['daily_change'].fillna(0)

                if target_col == "total_debts":
                    df_hist['bar_color'] = df_hist['daily_change'].apply(lambda x: '#EF5350' if x > 0 else '#26A69A')
                else:
                    df_hist['bar_color'] = df_hist['daily_change'].apply(lambda x: '#26A69A' if x >= 0 else '#EF5350')

                df_hist['sma_7'] = df_hist[target_col].rolling(window=7, min_periods=1).mean()

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.03, row_heights=[0.75, 0.25])

                fig.add_trace(go.Scatter(
                    x=df_hist['record_date'], y=df_hist[target_col],
                    mode='lines', fill='tozeroy', fillcolor=fill_color,
                    line=dict(color=line_color, width=2.5), name=gosterge,
                    hovertemplate=f'<b>%{{x|%d %b %Y}}</b><br>{gosterge}: ₺%{{y:,.0f}}<br>Δ ₺%{{customdata[0]:,.0f}} (%{{customdata[1]:.2f}}%)<extra></extra>',
                    customdata=df_hist[['daily_change', 'daily_pct']]
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=df_hist['record_date'], y=df_hist['sma_7'],
                    mode='lines', line=dict(color='#FFA726', width=1.5, dash='dash'),
                    name='SMA(7)', hovertemplate='<b>%{x|%d %b %Y}</b><br>SMA7: ₺%{y:,.0f}<extra></extra>'
                ), row=1, col=1)

                fig.add_trace(go.Bar(
                    x=df_hist['record_date'], y=df_hist['daily_change'],
                    marker_color=df_hist['bar_color'], name='Günlük Δ',
                    hovertemplate='<b>%{x|%d %b %Y}</b><br>Δ ₺%{y:,.0f}<extra></extra>'
                ), row=2, col=1)

                fig.update_xaxes(row=2, col=1,
                    rangeslider=dict(visible=True, thickness=0.06, bgcolor="rgba(128,128,128,0.08)"),
                    rangeselector=dict(buttons=RANGE_BUTTONS, bgcolor='rgba(0,0,0,0.08)', font=dict(size=11)),
                    showgrid=True, gridcolor='rgba(128,128,128,0.1)')
                fig.update_xaxes(row=1, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.1)')
                fig.update_yaxes(row=1, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.1)', tickprefix="₺")
                fig.update_yaxes(row=2, col=1, showgrid=True, gridcolor='rgba(128,128,128,0.1)')

            else:
                # ── İndeksli Karşılaştır (baz = 100) ──────────────────────
                # Her seriyi başlangıç değerine bölerek normalize ediyoruz.
                # Böylece farklı ölçekteki (₺500k varlık, ₺100k borç) seriler
                # aynı eksende anlamlı biçimde karşılaştırılabilir.
                SERIES = [
                    ("total_assets", "#2962FF", "Toplam Varlık", "rgba(41,98,255,0.08)"),
                    ("net_worth",    "#26A69A", "Net Servet",    "rgba(38,166,154,0.08)"),
                    ("total_debts",  "#EF5350", "Toplam Borç",   "rgba(239,83,80,0.06)"),
                ]

                fig = go.Figure()

                for col, color, name, fill_color in SERIES:
                    base = df_hist[col].iloc[0]
                    if base == 0:
                        continue
                    indexed   = (df_hist[col] / base) * 100          # baz=100
                    actual    = df_hist[col]                           # hover için gerçek değer
                    pct_chg   = indexed - 100                         # başlangıçtan % değişim

                    fig.add_trace(go.Scatter(
                        x=df_hist['record_date'],
                        y=indexed,
                        mode='lines',
                        fill='tozeroy',
                        fillcolor=fill_color,
                        line=dict(color=color, width=2),
                        name=name,
                        customdata=list(zip(actual, pct_chg)),
                        hovertemplate=(
                            f'<b>%{{x|%d %b %Y}}</b><br>'
                            f'{name}: ₺%{{customdata[0]:,.0f}}<br>'
                            f'Başlangıçtan: %{{customdata[1]:+.1f}}%'
                            f'<extra></extra>'
                        ),
                    ))

                # Başlangıç baz çizgisi (100 = değişim yok)
                fig.add_hline(
                    y=100,
                    line=dict(color="rgba(128,128,128,0.35)", width=1, dash="dot"),
                    annotation_text="Baz (başlangıç)",
                    annotation_position="bottom right",
                    annotation_font=dict(size=10, color="rgba(128,128,128,0.6)"),
                )

                fig.update_layout(
                    xaxis=dict(
                        rangeslider=dict(visible=True, thickness=0.06, bgcolor="rgba(128,128,128,0.08)"),
                        rangeselector=dict(buttons=RANGE_BUTTONS, bgcolor='rgba(0,0,0,0.08)', font=dict(size=11)),
                        showgrid=True, gridcolor='rgba(128,128,128,0.1)'
                    ),
                    yaxis=dict(
                        showgrid=True, gridcolor='rgba(128,128,128,0.1)',
                        ticksuffix="",
                        tickformat=".0f",
                        title=dict(text="İndeks (Baz = 100)", font=dict(size=11)),
                    )
                )

            fig.update_layout(
                separators=".,",
                margin=dict(l=0, r=0, t=10, b=0),
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                            font=dict(size=11)),
                font=dict(family='Inter'),
            )
            fig.update_xaxes(showspikes=True, spikecolor="gray", spikesnap="cursor", spikemode="across")
            fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1)

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.caption("Veriler, 'Fiyatları Güncelle' butonuna basılan günlerin kapanış değerlerini yansıtır.")
        else:
            st.info("Henüz grafik çizecek kadar tarihsel veri birikmedi.")

    except Exception as e:
        st.error(f"Grafik yüklenemedi: {repr(e)}")