import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime

# ==========================================
# 1. AYARLAR & CSS
# ==========================================
st.set_page_config(layout="wide", page_title="AETHER NEXUS", page_icon="🌌")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #e0e0e0 !important; }
    .metric-card { background: linear-gradient(145deg, #111 0%, #0a0a0a 100%); padding: 15px; border-radius: 12px; border-left: 4px solid #00f3ff; text-align: center; margin-bottom: 10px; }
    .metric-title { font-size: 0.8rem; color: #888; text-transform: uppercase; }
    .metric-val { font-size: 1.8rem; font-weight: bold; color: #00f3ff; }
    </style>
""", unsafe_allow_html=True)

ASSETS_FILE = "my_assets.json"
DB_FILE = "portfolio_db.json"

# ==========================================
# 2. AKILLI OTOMATİK TAMAMLAMA MOTORU
# ==========================================
SMART_DATABASE = {
    # BIST Hisseleri
    "ALKA": {"type": "TR_STOCK", "type_tr": "BIST", "sector": "Kimya/Kağıt", "currency": "TRY"},
    "THYAO": {"type": "TR_STOCK", "type_tr": "BIST", "sector": "Havacılık", "currency": "TRY"},
    "TUPRS": {"type": "TR_STOCK", "type_tr": "BIST", "sector": "Enerji/Rafineri", "currency": "TRY"},
    "EREGL": {"type": "TR_STOCK", "type_tr": "BIST", "sector": "Demir Çelik", "currency": "TRY"},
    "ASELS": {"type": "TR_STOCK", "type_tr": "BIST", "sector": "Savunma Sanayi", "currency": "TRY"},
    
    # ABD Hisseleri & ETF
    "NVDA": {"type": "US_STOCK", "type_tr": "ABD Hisse", "sector": "Yarı İletken", "currency": "USD"},
    "AAPL": {"type": "US_STOCK", "type_tr": "ABD Hisse", "sector": "Teknoloji", "currency": "USD"},
    "TSLA": {"type": "US_STOCK", "type_tr": "ABD Hisse", "sector": "Otomotiv/EV", "currency": "USD"},
    "QQQ": {"type": "ETF", "type_tr": "ABD ETF", "sector": "Teknoloji Endeksi", "currency": "USD"},
    "XLU": {"type": "ETF", "type_tr": "ABD ETF", "sector": "Altyapı/Kamu", "currency": "USD"},
    
    # Kripto
    "BTC": {"type": "CRYPTO", "type_tr": "Kripto", "sector": "L1 Zincir", "currency": "USD"},
    "ETH": {"type": "CRYPTO", "type_tr": "Kripto", "sector": "L1 Zincir", "currency": "USD"},
    "SOL": {"type": "CRYPTO", "type_tr": "Kripto", "sector": "L1 Zincir", "currency": "USD"},
    
    # Emtia
    "ALTIN": {"type": "GOLD", "type_tr": "Emtia", "sector": "Kıymetli Maden", "currency": "TRY"},
    "GUMUS": {"type": "SILVER", "type_tr": "Emtia", "sector": "Kıymetli Maden", "currency": "TRY"}
}

def auto_fill_asset(symbol_raw):
    """Sadece sembol girildiğinde BIST, USD, Sektör vb. otomatik getirir."""
    sym = symbol_raw.upper().strip().replace(".IS", "")
    
    # Veritabanında tanımlıysa direkt getir
    if sym in SMART_DATABASE:
        data = SMART_DATABASE[sym].copy()
        if data["type"] == "TR_STOCK":
            data["symbol"] = f"{sym}.IS"
        elif data["type"] == "CRYPTO":
            data["symbol"] = f"{sym}-USD"
        else:
            data["symbol"] = sym
        return data
    
    # Tanımlı değilse akıllı tahmin yürüt
    if symbol_raw.upper().endswith(".IS"):
        return {"symbol": symbol_raw.upper(), "type": "TR_STOCK", "type_tr": "BIST", "sector": "Genel BIST", "currency": "TRY"}
    elif "-USD" in symbol_raw.upper():
        return {"symbol": symbol_raw.upper(), "type": "CRYPTO", "type_tr": "Kripto", "sector": "Altcoin/L1", "currency": "USD"}
    elif len(sym) == 3 and sym.isalpha(): # TEFAS Fon Tahmini (Örn: MAC, TI1)
        return {"symbol": sym, "type": "TEFAS", "type_tr": "Fon", "sector": "Yatırım Fonu", "currency": "TRY"}
    else: # Varsayılan ABD Hisse kabul et
        return {"symbol": sym, "type": "US_STOCK", "type_tr": "ABD Hisse", "sector": "Teknoloji/Genel", "currency": "USD"}

# ==========================================
# 3. ANLIK CANLI VERİ ÇEKME MOTORU
# ==========================================
def fetch_live_data(assets):
    usd_try = float(yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[-1]) if True else 34.50
    try:
        gold_oz = float(yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1])
    except:
        gold_oz = 2500.0
    gold_gram_try = (gold_oz / 31.1035) * usd_try

    updated_assets = []
    for item in assets:
        sym = item["symbol"]
        ptype = item["type"]
        current_price = item.get("current_price", 0.0)
        
        try:
            if ptype in ["US_STOCK", "TR_STOCK", "CRYPTO", "ETF"]:
                data = yf.Ticker(sym).history(period="1d")
                if not data.empty:
                    current_price = float(data['Close'].iloc[-1])
            elif ptype == "TEFAS":
                url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={sym}"
                headers = {'User-Agent': 'Mozilla/5.0'}
                res = requests.get(url, headers=headers, timeout=4)
                soup = BeautifulSoup(res.content, 'html.parser')
                p_str = soup.find('span', string='Son Fiyat').find_next_sibling('span').text
                current_price = float(p_str.replace('.', '').replace(',', '.'))
            elif ptype == "GOLD":
                current_price = gold_gram_try if item["currency"] == "TRY" else gold_oz
        except:
            pass

        item["current_price"] = current_price
        updated_assets.append(item)

    data_to_save = {
        "usd_try": usd_try,
        "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S Anlık"),
        "assets": updated_assets
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=4, ensure_ascii=False)
    return data_to_save

# ==========================================
# 4. ARAYÜZ (MOBILE APP)
# ==========================================
st.markdown("<h1>🌌 AETHER NEXUS <span style='color:#00f3ff;'>LIVE</span></h1>", unsafe_allow_html=True)

# Dosya Yükleme Kontrolü
if os.path.exists(ASSETS_FILE):
    with open(ASSETS_FILE, "r", encoding="utf-8") as f:
        my_assets = json.load(f)
else:
    my_assets = []

# --- ÜST BUTONLAR ---
col_b1, col_b2 = st.columns([2, 1])
with col_b1:
    st.caption("Veriler GitHub senkronizasyonu ile anlık güncellenebilir.")
with col_b2:
    if st.button("⚡ ANLIK GÜNCELLE (NOW)", use_container_width=True):
        with st.spinner("Piyasalar canlı taranıyor..."):
            fetch_live_data(my_assets)
            st.rerun()

# DB Verisi
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        db_data = json.load(f)
else:
    db_data = fetch_live_data(my_assets)

usd_try = db_data["usd_try"]
last_sync = db_data["last_sync"]
df = pd.DataFrame(db_data["assets"])

st.caption(f"🔄 Son Senkronizasyon: {last_sync} | USD/TRY: {usd_try:.2f}")

# --- YENİ VARLIK EKLEME MODÜLÜ (AKILLI TAMAMLAMA) ---
with st.expander("➕ Yeni Varlık Ekle (Akıllı Otomatik Doldurma)", expanded=False):
    col_in1, col_in2, col_in3 = st.columns([2, 1, 1])
    input_sym = col_in1.text_input("Varlık / Sembol Girin", placeholder="Örn: ALKA, NVDA, MAC, BTC, ALTIN").strip()
    input_qty = col_in2.number_input("Adet / Gram", min_value=0.0, value=100.0, step=1.0)
    input_cost = col_in3.number_input("Birim Maliyet", min_value=0.0, value=10.0, step=0.1)
    
    if st.button("🚀 Portföye Ekle & Kaydet", use_container_width=True):
        if input_sym:
            auto_data = auto_fill_asset(input_sym)
            auto_data["qty"] = input_qty
            auto_data["avg_cost"] = input_cost
            
            # Mevcut liste içinde varsa güncelle, yoksa yeni ekle
            existing_idx = next((index for (index, d) in enumerate(my_assets) if d["symbol"] == auto_data["symbol"]), None)
            if existing_idx is not None:
                my_assets[existing_idx] = auto_data
            else:
                my_assets.append(auto_data)
                
            # Dosyalara kaydet ve canlı veriyi çek
            with open(ASSETS_FILE, "w", encoding="utf-8") as f:
                json.dump(my_assets, f, indent=4, ensure_ascii=False)
            fetch_live_data(my_assets)
            st.success(f"✅ {auto_data['symbol']} Otomatik Tanındı ({auto_data['type_tr']} - {auto_data['sector']}) ve Kaydedildi!")
            st.rerun()

# --- FİNANSAL METRİKLER ---
if not df.empty:
    df['Maliyet (TRY)'] = df.apply(lambda r: r['qty'] * r['avg_cost'] if r['currency'] == 'TRY' else r['qty'] * r['avg_cost'] * usd_try, axis=1)
    df['Güncel Değer (TRY)'] = df.apply(lambda r: r['qty'] * r['current_price'] if r['currency'] == 'TRY' else r['qty'] * r['current_price'] * usd_try, axis=1)
    df['Kâr/Zarar (%)'] = df.apply(lambda r: ((r['current_price'] - r['avg_cost']) / r['avg_cost']) * 100 if r['avg_cost'] > 0 else 0, axis=1)

    tot_try = df['Güncel Değer (TRY)'].sum()
    tot_cost = df['Maliyet (TRY)'].sum()
    tot_profit = tot_try - tot_cost
    tot_profit_pct = (tot_profit / tot_cost * 100) if tot_cost > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div class='metric-card'><div class='metric-title'>NET DEĞER</div><div class='metric-val'>₺ {tot_try:,.0f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-card'><div class='metric-title'>NET DEĞER (USD)</div><div class='metric-val'>$ {(tot_try/usd_try):,.0f}</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric-card'><div class='metric-title'>TOPLAM K/Z</div><div class='metric-val'>%{tot_profit_pct:.1f}</div></div>", unsafe_allow_html=True)

    # SANKEY DİYAGRAMI
    st.markdown("### 🧬 Portföy Akış Diyagramı")
    if tot_try > 0:
        labels = ["Portföy"] + list(df["type_tr"].unique()) + list(df["sector"].unique()) + list(df["symbol"].unique())
        label_dict = {label: i for i, label in enumerate(labels)}

        source, target, value = [], [], []
        for ptype, group in df.groupby("type_tr"):
            source.append(label_dict["Portföy"])
            target.append(label_dict[ptype])
            value.append(group["Güncel Değer (TRY)"].sum())

        for (ptype, sektor), group in df.groupby(["type_tr", "sector"]):
            source.append(label_dict[ptype])
            target.append(label_dict[sektor])
            value.append(group["Güncel Değer (TRY)"].sum())

        for (sektor, sym), group in df.groupby(["sector", "symbol"]):
            source.append(label_dict[sektor])
            target.append(label_dict[sym])
            value.append(group["Güncel Değer (TRY)"].sum())

        fig = go.Figure(data=[go.Sankey(
            node=dict(pad=15, thickness=15, line=dict(color="#00f3ff", width=1), label=labels, color="#111"),
            link=dict(source=source, target=target, value=value, color="rgba(0, 243, 255, 0.3)")
        )])
        fig.update_layout(height=500, plot_bgcolor='black', paper_bgcolor='black', font=dict(color='white'), margin=dict(t=10,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

    # TABLO
    st.markdown("### 🗃️ Varlık Detayları")
    st.dataframe(df[['symbol', 'type_tr', 'sector', 'qty', 'avg_cost', 'current_price', 'Kâr/Zarar (%)']], use_container_width=True)
