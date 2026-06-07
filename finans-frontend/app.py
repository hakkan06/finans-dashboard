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
# ÖN VERİ ÇEKİMİ
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
# GECİKMİŞ TAKSİT BANNER
# =====================================================================
gecikmiş = []
yaklasan = []
bugun = date.today()

for d in debts:
    for inst in d.get('installments', []):
        if not inst['is_paid']:
            vade = pd.to_datetime(inst['due_date']).date()
            kalan = (vade - bugun).days
            if kalan < 0:
                gecikmiş.append(f"{d['name']} — ₺{inst['amount']:,.2f} ({abs(kalan)} gün gecikmiş)")
            elif kalan <= 3:
                yaklasan.append(f"{d['name']} — ₺{inst['amount']:,.2f} ({kalan} gün kaldı)")

if gecikmiş:
    st.error("🔴 **Gecikmiş Taksitler:**\n" + "\n".join(f"- {g}" for g in gecikmiş))

if yaklasan:
    st.warning("⚠️ **Yaklaşan Taksitler (3 gün içinde):**\n" + "\n".join(f"- {y}" for y in yaklasan))

borc_tab_label = f"💳 Borç Takibi {'🔴' if gecikmiş else '⚠️' if yaklasan else ''}"
tab_portfoy, tab_borc, tab_trend = st.tabs(["📊 Portföy Özeti", borc_tab_label, "📈 Trend Analizi"])

# =====================================================================
# 1. TAB: PORTFÖY ÖZETİ
# =====================================================================
with tab_portfoy:
    col1, col2 = st.columns([3, 1])

    with col1:
        st.header("Varlık Portföyü ve Canlı Değerler")
        st.caption(f"💱 Sistemde Kullanılan Güncel Dolar Kuru (Önbellekli): ₺ {usd_try_rate:,.2f}")

        # Son fiyat güncelleme zamanını hesapla
        son_guncelleme = None
        for item in summary_data:
            if item['last_updated']:
                guncelleme_zamani = pd.to_datetime(item['last_updated'])
                if son_guncelleme is None or guncelleme_zamani > son_guncelleme:
                    son_guncelleme = guncelleme_zamani

        if son_guncelleme:
            simdi = pd.Timestamp.now(tz='Europe/Istanbul')
            if son_guncelleme.tzinfo is None:
                son_guncelleme = son_guncelleme.tz_localize('Europe/Istanbul')
            fark = simdi - son_guncelleme
            fark_dakika = int(fark.total_seconds() / 60)

            if fark_dakika < 1:
                fark_str = "az önce"
            elif fark_dakika < 60:
                fark_str = f"{fark_dakika} dakika önce"
            else:
                fark_saat = fark_dakika // 60
                fark_str = f"{fark_saat} saat önce"

            st.caption(f"🕐 Son fiyat güncellemesi: {son_guncelleme.strftime('%H:%M')} — {fark_str}")
        else:
            st.caption("🕐 Henüz fiyat güncellenmedi")

    with col2:
        if st.button("🔄 Piyasa Fiyatlarını Güncelle", use_container_width=True):
            with st.spinner("Piyasalar taranıyor..."):
                res = requests.post(f"{API_URL}/assets/update-prices")
                if res.status_code == 200:
                    requests.post(f"{API_URL}/portfolio/snapshot", json={
                        "total_assets": global_total_assets,
                        "total_debts": global_total_debts
                    }, timeout=2)
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

        # Varlık türüne göre dağılım pie chart
        pie_data = {}
        for item in summary_data:
            asset_type = item['asset_type']
            net_val = item['net_value']
            if asset_type == 'US_STOCK':
                net_val *= usd_try_rate
            pie_data[asset_type] = pie_data.get(asset_type, 0) + net_val

        col_pie, col_metric = st.columns([1, 1])

        with col_pie:
            if pie_data:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=list(pie_data.keys()),
                    values=list(pie_data.values()),
                    hole=0.45,
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>₺%{value:,.2f}<br>%{percent}<extra></extra>',
                    marker=dict(colors=['#2962FF', '#00BCD4', '#FF6F00', '#43A047', '#8E24AA'])
                )])
                fig_pie.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=220
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_metric:
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
                        hata = res.json().get("detail", "Bilinmeyen hata")
                        st.error(f"İşlem başarısız: {hata}")
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
                onay_varlik = st.checkbox("Evet, bu varlığı ve tüm geçmişini silmek istiyorum")
                sil_btn = st.form_submit_button("Varlığı Kalıcı Olarak Yok Et", disabled=not onay_varlik)
                if sil_btn and onay_varlik:
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

            # Filtreler
            fil_col1, fil_col2 = st.columns([1, 2])
            with fil_col1:
                durum_filtre = st.selectbox(
                    "Durum",
                    ["Tümü", "Sadece Ödenmemiş", "Sadece Gecikmiş", "Sadece Ödenenler"],
                    key="durum_filtre"
                )
            with fil_col2:
                borc_isimleri = ["Tümü"] + sorted(list(set(i["Borç Adı"] for i in installments_data)))
                borc_filtre = st.selectbox("Borç Adı", borc_isimleri, key="borc_filtre")

            filtrelenmis = installments_data.copy()

            if durum_filtre == "Sadece Ödenmemiş":
                filtrelenmis = [i for i in filtrelenmis if not i['is_paid']]
            elif durum_filtre == "Sadece Gecikmiş":
                filtrelenmis = [i for i in filtrelenmis if not i['is_paid'] and (pd.to_datetime(i['Son Ödeme Tarihi']).date() - date.today()).days < 0]
            elif durum_filtre == "Sadece Ödenenler":
                filtrelenmis = [i for i in filtrelenmis if i['is_paid']]

            if borc_filtre != "Tümü":
                filtrelenmis = [i for i in filtrelenmis if i['Borç Adı'] == borc_filtre]

            if filtrelenmis:
                df_filtre = pd.DataFrame(filtrelenmis)
                df_filtre = df_filtre.sort_values(by="Son Ödeme Tarihi", ascending=True)
                display_df = df_filtre[["Borç Adı", "Tutar", "Son Ödeme Tarihi", "Durum / Kalan"]]
                st.dataframe(display_df.style.format({"Tutar": "₺ {:,.2f}"}), use_container_width=True)
            else:
                st.info("Seçilen filtreyle eşleşen kayıt bulunamadı.")

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
                    onay_borc = st.checkbox("Evet, bu borcu ve tüm taksit planını silmek istiyorum")
                    sil_borc_btn = st.form_submit_button("Borç Dosyasını Kapat ve Sil", disabled=not onay_borc)
                    if sil_borc_btn and onay_borc:
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
# 3. TAB: TREND ANALİZİ
# =====================================================================
with tab_trend:
    st.header("📈 Varlık Büyüme Trendi ve Dönem Sonu Projeksiyonu")

    today_date = date.today()
    current_month = today_date.month
    current_year = today_date.year

    bu_ayki_borc = 0.0
    for d in debts:
        for inst in d.get('installments', []):
            due_date_obj = pd.to_datetime(inst['due_date']).date()
            if not inst['is_paid'] and due_date_obj.month == current_month and due_date_obj.year == current_year:
                bu_ayki_borc += inst['amount']

    ay_sonu_kalan_varlik = global_total_assets - bu_ayki_borc

    st.subheader("🗓️ Bu Ay Sonu Varlık Projeksiyonu")
    col_n1, col_n2, col_n3 = st.columns(3)

    with col_n1:
        st.metric(label="Mevcut Toplam Varlık", value=f"₺ {global_total_assets:,.2f}")
    with col_n2:
        st.metric(label="Bu Ay Kapanacak Taksitler", value=f"₺ {bu_ayki_borc:,.2f}", delta="-Likidasyon İhtiyacı", delta_color="inverse")
    with col_n3:
        if ay_sonu_kalan_varlik >= 0:
            st.metric(label="Ay Sonu Beklenen Net Varlık", value=f"₺ {ay_sonu_kalan_varlik:,.2f}", delta="Artıda", delta_color="normal")
        else:
            st.metric(label="Ay Sonu Beklenen Net Varlık", value=f"₺ {ay_sonu_kalan_varlik:,.2f}", delta="Ekside", delta_color="inverse")

    if ay_sonu_kalan_varlik < 0:
        st.error(f"⚠️ **Kritik Uyarı:** Bu ayki taksit yükünüz, elinizdeki tüm varlıkların toplamını aşıyor. Ayı kapatmak için **₺ {abs(ay_sonu_kalan_varlik):,.2f}** tutarında dışarıdan ek kaynağa ihtiyacınız olacak.")
    elif bu_ayki_borc > 0:
        st.info(f"💡 **Strateji Notu:** Bu ayki ödemeleriniz için fonlardan, hisse senetlerinden veya altından yaklaşık **₺ {bu_ayki_borc:,.2f}** tutarında bir likidasyon (satış) yapmanız planlanmalıdır. Gerekli satışlar yapıldıktan sonra yatırımlarınızın toplam değeri **₺ {ay_sonu_kalan_varlik:,.2f}** seviyesine güncellenecektir.")
    else:
        st.success("✅ **Güvendesiniz:** Bu ay ödenmesi gereken herhangi bir borç taksiti bulunmuyor. Tüm yatırımlarınız büyüklüğünü korumaya devam edecek.")

    st.write("---")
    st.subheader("📊 Tarihsel Varlık Grafiği")

    try:
        res_hist = requests.get(f"{API_URL}/portfolio/history", timeout=5)
        if res_hist.status_code == 200 and res_hist.json():
            df_hist = pd.DataFrame(res_hist.json())
            df_hist['record_date'] = pd.to_datetime(df_hist['record_date'])
            df_hist.sort_values('record_date', inplace=True)

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df_hist['record_date'],
                y=df_hist['total_assets'],
                fill='tozeroy',
                mode='lines',
                line=dict(color='#2962FF', width=3),
                fillcolor='rgba(41, 98, 255, 0.15)',
                name='Toplam Varlık',
                hovertemplate='<b>Tarih:</b> %{x|%d %b %Y}<br><b>Varlık:</b> ₺%{y:,.2f}<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_hist['record_date'],
                y=df_hist['total_debts'],
                mode='lines',
                line=dict(color='#E53935', width=2, dash='dot'),
                name='Toplam Borç',
                hovertemplate='<b>Tarih:</b> %{x|%d %b %Y}<br><b>Borç:</b> ₺%{y:,.2f}<extra></extra>'
            ))

            fig.add_trace(go.Scatter(
                x=df_hist['record_date'],
                y=df_hist['net_worth'],
                mode='lines',
                line=dict(color='#43A047', width=2),
                name='Net Servet',
                hovertemplate='<b>Tarih:</b> %{x|%d %b %Y}<br><b>Net Servet:</b> ₺%{y:,.2f}<extra></extra>'
            ))

            fig.update_layout(
                separators=".,",
                margin=dict(l=0, r=0, t=20, b=0),
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(128, 128, 128, 0.15)',
                    tickformat='%d %b'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(128, 128, 128, 0.15)',
                    tickprefix="₺"
                )
            )

            fig.update_xaxes(showspikes=True, spikecolor="gray", spikesnap="cursor", spikemode="across")
            fig.update_yaxes(showspikes=True, spikecolor="gray", spikethickness=1)

            st.plotly_chart(fig, use_container_width=True)
            st.caption("Veriler, sisteme giriş yaptığınız veya 'Piyasa Fiyatlarını Güncelle' butonuna bastığınız günlerin kapanış değerlerini baz alır.")
        else:
            st.info("Henüz grafik çizecek kadar tarihsel veri birikmedi. (Grafik yarına veya fiyat güncellediğinizde oluşacaktır).")

    except Exception as e:
        st.error(f"Grafik yüklenirken bir sorun oluştu. Hata Detayı: {repr(e)}")