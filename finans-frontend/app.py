import streamlit as st
import requests
import pandas as pd
import os
import time
from datetime import date
import plotly.graph_objects as go

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Finans Dashboard", layout="wide", page_icon="📈")
st.title("💰 Varlık ve Borç Yönetim Paneli")

@st.cache_data(ttl=3600)
def get_cached_usd_rate():
    try:
        res = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=3)
        res.raise_for_status()
        return res.json().get("rates", {}).get("TRY", 32.20)
    except:
        return 32.20 

usd_try_rate = get_cached_usd_rate()

def render_auto_debt_form(form_key):
    with st.form(form_key):
        d_name = st.text_input("Kredi / Borç İsmi (Örn: Konut Kredisi)")
        d_total = st.number_input("Toplam Geri Ödeme Tutarı", min_value=0.01)
        d_count = st.number_input("Taksit Sayısı (Ay)", min_value=1, max_value=360, step=1, value=12)
        d_start = st.date_input("İlk Taksit Başlangıç Tarihi", value=date.today())
        
        if st.form_submit_button("Ödeme Planını Otomatik Dağıt"):
            payload = {
                "name": d_name,
                "total_amount": float(d_total),
                "installments_count": int(d_count),
                "start_date": d_start.strftime("%Y-%m-%d")
            }
            res = requests.post(f"{API_URL}/debts/schedules/", json=payload)
            if res.status_code == 200:
                st.toast("✅ Kredi takvimi başarıyla üretildi!")
                time.sleep(0.8) 
                st.rerun() 
            else:
                st.error("Plan dağıtılırken bir hata oluştu.")

# =====================================================================
# ÖN VERİ ÇEKİMİ VE SESSİZ SNAPSHOT (ZAMAN ÇİZELGESİ) KAYDI
# =====================================================================
global_total_assets = 0.0
global_total_debts = 0.0
summary_data = []
debts = []

try:
    res_assets = requests.get(f"{API_URL}/portfolio/summary", timeout=5)
    if res_assets.status_code == 200:
        summary_data = res_assets.json()
        for item in summary_data:
            net_val = item['net_value']
            if item['asset_type'] == 'US_STOCK':
                net_val *= usd_try_rate
            global_total_assets += net_val

    res_debts = requests.get(f"{API_URL}/debts/", timeout=5)
    if res_debts.status_code == 200:
        debts = res_debts.json()
        for d in debts:
            for inst in d.get('installments', []):
                if not inst['is_paid']:
                    global_total_debts += inst['amount']

    requests.post(f"{API_URL}/portfolio/snapshot", json={
        "total_assets": global_total_assets,
        "total_debts": global_total_debts
    }, timeout=2)
except:
    pass 

# --- TABS ---
tab_portfoy, tab_borc, tab_trend = st.tabs(["📊 Portföy Özeti", "💳 Borç Takibi", "📈 Trend Analizi"])

# =====================================================================
# 1. TAB: PORTFÖY ÖZETİ
# =====================================================================
with tab_portfoy:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("Varlık Portföyü ve Canlı Değerler")
        st.caption(f"💱 Sistemde Kullanılan Güncel Dolar Kuru (Önbellekli): ₺ {usd_try_rate:,.2f}")
    with col2:
        if st.button("🔄 Piyasa Fiyatlarını Güncelle", use_container_width=True):
            with st.spinner("Piyasalar taranıyor..."):
                res = requests.post(f"{API_URL}/assets/update-prices")
                if res.status_code == 200:
                    st.toast("📈 Fiyatlar başarıyla güncellendi!")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("Veri çekilirken hata oluştu.")

    if summary_data:
        portfolio_table = []
        for item in summary_data:
            if item['asset_type'] == 'US_STOCK':
                net_val_try = item['net_value'] * usd_try_rate
                total_tax_try = item['total_tax'] * usd_try_rate
                display_price = f"$ {item['current_price']:,.2f}"
            else:
                net_val_try = item['net_value']
                total_tax_try = item['total_tax']
                display_price = f"₺ {item['current_price']:,.2f}"
                
            last_upd_str = str(item['last_updated'])[:16].replace("T", " ") if item['last_updated'] else "Güncellenmedi"

            portfolio_table.append({
                "Tür": item['asset_type'],
                "Sembol": item['symbol'],
                "Ad": item['name'],
                "Miktar": item['total_qty'],
                "Anlık Fiyat": display_price,
                "Kesilen Stopaj (₺)": total_tax_try,
                "Net Toplam Değer (₺)": net_val_try,
                "Son Güncelleme": last_upd_str
            })
        
        df = pd.DataFrame(portfolio_table)
        st.metric(label="Net Portföy Büyüklüğü (Vergi Sonrası)", value=f"₺ {global_total_assets:,.2f}")
        st.dataframe(df.style.format({
            "Kesilen Stopaj (₺)": "{:,.2f}",
            "Net Toplam Değer (₺)": "{:,.2f}",
            "Miktar": "{:,.2f}"
        }), use_container_width=True)
    else:
        st.info("Sistemde henüz varlık bulunmuyor veya hesaplanamadı.")
            
    st.divider()
    
    st.subheader("⚙️ Varlık Yönetim ve İşlem Merkezi")
    islem_tipi = st.selectbox(
        "Yapmak İstediğiniz İşlemi Seçin:",
        ["Alım / Satım İşlemi Kaydet", "Sisteme Yeni Varlık Tanımla", "Varlığı Portföyden Kalıcı Olarak Kaldır"]
    )
    
    if islem_tipi == "Alım / Satım İşlemi Kaydet":
        if summary_data:
            with st.form("unified_transaction_form"):
                asset_options = {f"{a['symbol']} - {a['name']}": a['asset_id'] for a in summary_data}
                selected_asset = st.selectbox("İşlem Yapılacak Varlık", options=list(asset_options.keys()))
                islem_turu = st.radio("İşlem Yönü", ["Alış (+)", "Satış (-)"], horizontal=True)
                t_qty = st.number_input("Miktar (Lot / Adet / Nakit)", min_value=0.0001, format="%.4f")
                t_price = st.number_input("Birim Maliyet / Alış Fiyatı (TL İçin 1.0 Girin)", min_value=0.01, format="%.2f")
                t_date = st.date_input("İşlem Tarihi", value=date.today())
                
                if st.form_submit_button("İşlemi Cüzdana Kaydet"):
                    final_qty = float(t_qty) if islem_turu == "Alış (+)" else -float(t_qty)
                    res = requests.post(f"{API_URL}/transactions/", json={
                        "asset_id": asset_options[selected_asset],
                        "quantity": final_qty,
                        "unit_price": float(t_price),
                        "transaction_date": t_date.strftime("%Y-%m-%d")
                    })
                    if res.status_code == 200:
                        st.toast(f"✅ {islem_turu} başarıyla işlendi!")
                        time.sleep(0.8)
                        st.rerun()
        else:
            st.warning("Lütfen önce yukarıdan 'Sisteme Yeni Varlık Tanımla' seçeneğini kullanın.")

    elif islem_tipi == "Sisteme Yeni Varlık Tanımla":
        with st.form("unified_add_asset_form"):
            a_type = st.selectbox("Varlık Sınıfı / Türü", ["US_STOCK", "TR_STOCK", "FUND", "COMMODITY", "FIAT"])
            a_sym = st.text_input("Sembol / Kod (Örn: QQQM, ALTIN, USD, EUR, TRY)")
            a_name = st.text_input("Varlığın Tam Adı (Örn: Vadeli Dolar, Çekmecedeki TL)")
            if st.form_submit_button("Varlığı Kataloğa Ekle"):
                res = requests.post(f"{API_URL}/assets/", json={"asset_type": a_type, "symbol": a_sym, "name": a_name})
                if res.status_code == 200:
                    st.toast("✅ Varlık kataloğa eklendi!")
                    time.sleep(0.8)
                    st.rerun()

    elif islem_tipi == "Varlığı Portföyden Kalıcı Olarak Kaldır":
        if summary_data:
            with st.form("unified_delete_asset_form"):
                del_asset_options = {f"{a['symbol']} - {a['name']}": a['asset_id'] for a in summary_data}
                selected_del_asset = st.selectbox("Kaldırılacak Varlığı Seçin", options=list(del_asset_options.keys()))
                st.warning("⚠️ Bu işlem seçilen varlığı VE geçmiş alım/satım kayıtlarını siler!")
                if st.form_submit_button("Varlığı Kalıcı Olarak Yok Et"):
                    res = requests.delete(f"{API_URL}/assets/{del_asset_options[selected_del_asset]}")
                    if res.status_code == 200:
                        st.toast("🗑️ Varlık ve geçmişi silindi!")
                        time.sleep(0.8)
                        st.rerun()
        else:
            st.info("Sistemde silinebilecek varlık bulunmuyor.")

# =====================================================================
# 2. TAB: BORÇ TAKİBİ
# =====================================================================
with tab_borc:
    st.header("💳 Borç ve Ödeme Takip Paneli")

    if debts:
        installments_data = []
        today = date.today()
        
        for d in debts:
            for inst in d.get('installments', []):
                due_date_obj = pd.to_datetime(inst['due_date']).date()
                days_left = (due_date_obj - today).days
                
                if inst['is_paid']:
                    status_str = "✅ Ödendi"
                else:
                    if days_left < 0:
                        status_str = f"🔴 Gecikmiş ({abs(days_left)} gün)"
                    elif days_left <= 3:
                        status_str = f"⚠️ Yaklaşıyor ({days_left} gün)"
                    else:
                        status_str = f"⏳ {days_left} gün var"

                installments_data.append({
                    "id": inst['id'],
                    "Borç Adı": d['name'],
                    "Tutar": inst['amount'],
                    "Son Ödeme Tarihi": inst['due_date'],
                    "Durum / Kalan": status_str,
                    "is_paid": inst['is_paid']
                })

        if installments_data:
            df_inst = pd.DataFrame(installments_data)
            df_inst = df_inst.sort_values(by="Son Ödeme Tarihi", ascending=True)
            display_df = df_inst[["Borç Adı", "Tutar", "Son Ödeme Tarihi", "Durum / Kalan"]]
            
            st.subheader("📅 Ödeme Planı Takvimi (Tarihe Göre Sıralı)")
            st.dataframe(display_df.style.format({"Tutar": "₺ {:,.2f}"}), use_container_width=True)
            
            st.write("---")
            colX, colY = st.columns(2)
            with colX:
                st.subheader("✅ Ödeme İşaretle")
                with st.form("pay_installment_form"):
                    unpaid = [i for i in installments_data if not i['is_paid']]
                    unpaid = sorted(unpaid, key=lambda x: x['Son Ödeme Tarihi'])
                    
                    if unpaid:
                        unpaid_opts = {f"{i['Borç Adı']} | Vade: {i['Son Ödeme Tarihi']} | ₺ {i['Tutar']}": i['id'] for i in unpaid}
                        selected_unpaid = st.selectbox("Ödenen Taksiti Seç", options=list(unpaid_opts.keys()))
                        if st.form_submit_button("Ödendi Olarak İşaretle"):
                            res = requests.put(f"{API_URL}/installments/{unpaid_opts[selected_unpaid]}/toggle")
                            if res.status_code == 200:
                                st.toast("✅ Ödeme başarıyla kayıtlara geçildi!")
                                time.sleep(0.8)
                                st.rerun()
                    else:
                        st.info("Ödenmesi gereken aktif bir taksit bulunmuyor.")
        else:
            st.info("Ana borç kaydı var ancak alt ödeme takvimi oluşturulmamış.")
            
        st.write("---")
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("📝 Yeni Otomatik Ödeme Planı Oluştur")
            render_auto_debt_form("auto_debt_form_main") 
                        
        with colB:
            st.subheader("🗑️ Borcu Tamamen Sil")
            with st.form("delete_debt_form"):
                debt_opts = {d['name']: d['id'] for d in debts}
                if debt_opts:
                    selected_del_debt = st.selectbox("Kaldırılacak Borç Kalemi", options=list(debt_opts.keys()))
                    st.warning("⚠️ Bu borcu silerseniz, ona bağlı TÜM takvim silinecektir!")
                    if st.form_submit_button("Borç Dosyasını Kapat ve Sil"):
                        res = requests.delete(f"{API_URL}/debts/{debt_opts[selected_del_debt]}")
                        if res.status_code == 200:
                            st.toast("🗑️ Borç dosyası tamamen kaldırıldı!")
                            time.sleep(0.8)
                            st.rerun()
                else:
                    st.info("Silinebilecek aktif borç dosyası bulunmuyor.")
    else:
        st.info("Aktif borç kaydı bulunmuyor.")
        st.subheader("📝 İlk Otomatik Ödeme Planını Oluştur")
        render_auto_debt_form("auto_debt_form_initial")

# =====================================================================
# 3. TAB: TREND ANALİZİ (YENİ INVESTING.COM STİLİ)
# =====================================================================
with tab_trend:
    st.header("📈 Varlık Büyüme Trendi")
    
    try:
        res_hist = requests.get(f"{API_URL}/portfolio/history", timeout=5)
        if res_hist.status_code == 200 and res_hist.json():
            df_hist = pd.DataFrame(res_hist.json())
            
            df_hist['record_date'] = pd.to_datetime(df_hist['record_date'])
            df_hist.sort_values('record_date', inplace=True)
            
            st.metric(label="Güncel Toplam Varlık", value=f"₺ {global_total_assets:,.2f}")
            st.write("---")
            
            # --- YENİ PROFESYONEL PLOTLY GRAFİĞİ ---
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df_hist['record_date'],
                y=df_hist['total_assets'],
                fill='tozeroy',
                mode='lines',
                line=dict(color='#2962FF', width=3), # Finansal Lacivert/Mavi tonu
                fillcolor='rgba(41, 98, 255, 0.15)',
                name='Toplam Varlık',
                hovertemplate='<b>Tarih:</b> %{x|%d %b %Y}<br><b>Varlık:</b> ₺%{y:,.2f}<extra></extra>'
            ))

            fig.update_layout(
                margin=dict(l=0, r=0, t=20, b=0),
                hovermode='x unified', # İmleç ile hareket eden dikey çizgi
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(128, 128, 128, 0.15)',
                    tickformat='%d %b'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(128, 128, 128, 0.15)',
                    tickprefix="₺",
                    separators=".,"
                )
            )

            # Eksen çizgileri ve crosshair (Investing tarzı kesişen imleç çizgileri)
            fig.update_xaxes(showspikes=True, spikecolor="gray", spikesnap="cursor", spikemode="across")
            fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1)

            st.plotly_chart(fig, use_container_width=True)
            
            st.caption("Veriler, sisteme giriş yaptığınız veya 'Piyasa Fiyatlarını Güncelle' butonuna bastığınız günlerin kapanış değerlerini baz alır.")
        else:
            st.info("Henüz grafik çizecek kadar tarihsel veri birikmedi. (Grafik yarına veya fiyat güncellediğinizde oluşacaktır).")
    except:
        st.error("Trend verileri yüklenirken bağlantı sorunu oluştu.")