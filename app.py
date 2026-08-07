import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os

st.set_page_config(layout="wide", page_title="AETHER NEXUS", page_icon="🌌")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #e0e0e0 !important; }
    .metric-card { background: linear-gradient(145deg, #111 0%, #0a0a0a 100%); padding: 15px; border-radius: 12px; border-left: 4px solid #00f3ff; text-align: center; margin-bottom: 10px; }
    .metric-title { font-size: 0.8rem; color: #888; text-transform: uppercase; }
    .metric-val { font-size: 1.8rem; font-weight: bold; color: #00f3ff; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>🌌 AETHER NEXUS <span style='color:#00f3ff;'>MOBILE</span></h1>", unsafe_allow_html=True)

if not os.path.exists("portfolio_db.json"):
    st.warning("Veritabanı henüz oluşturulmadı. Bot ilk çalıştırmayı bekliyor...")
    st.stop()

with open("portfolio_db.json", "r", encoding="utf-8") as f:
    db_data = json.load(f)

usd_try = db_data["usd_try"]
last_sync = db_data["last_sync"]
df = pd.DataFrame(db_data["assets"])

st.caption(f"🔄 Son Güncelleme: {last_sync} | USD/TRY: {usd_try:.2f}")

# Finansal Hesaplamalar
df['Maliyet (TRY)'] = df.apply(lambda r: r['qty'] * r['avg_cost'] if r['currency'] == 'TRY' else r['qty'] * r['avg_cost'] * usd_try, axis=1)
df['Güncel Değer (TRY)'] = df.apply(lambda r: r['qty'] * r['current_price'] if r['currency'] == 'TRY' else r['qty'] * r['current_price'] * usd_try, axis=1)
df['Kâr/Zarar (%)'] = ((df['current_price'] - df['avg_cost']) / df['avg_cost']) * 100

tot_try = df['Güncel Değer (TRY)'].sum()
tot_cost = df['Maliyet (TRY)'].sum()
tot_profit = tot_try - tot_cost
tot_profit_pct = (tot_profit / tot_cost * 100) if tot_cost > 0 else 0

m1, m2, m3 = st.columns(3)
m1.markdown(f"<div class='metric-card'><div class='metric-title'>NET DEĞER</div><div class='metric-val'>₺ {tot_try:,.0f}</div></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='metric-card'><div class='metric-title'>NET DEĞER (USD)</div><div class='metric-val'>$ {(tot_try/usd_try):,.0f}</div></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='metric-card'><div class='metric-title'>TOPLAM K/Z</div><div class='metric-val'>%{tot_profit_pct:.1f}</div></div>", unsafe_allow_html=True)

# SANKEY
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

# DETAY TABLO
st.markdown("### 🗃️ Varlık Detayları")
st.dataframe(df[['symbol', 'type_tr', 'sector', 'qty', 'avg_cost', 'current_price', 'Kâr/Zarar (%)']], use_container_width=True)
