import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from sqlalchemy import create_engine

st.set_page_config(page_title="Monitor Vitales Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Sistema de Monitoreo de Signos Vitales")

engine = create_engine("mysql+mysqlconnector://root:admin@vitales_db:3306/hospital_db")


def get_data():
    try:
        return pd.read_sql("SELECT * FROM lecturas ORDER BY id DESC LIMIT 30", engine)
    except:
        return pd.DataFrame()


df = get_data()

if not df.empty:
    col1, col2, col3 = st.columns(3)
    val_corp = df.iloc[0]['temp_corporal']
    val_amb  = df.iloc[0]['temp_ambiente']

    col1.metric("TEMP. CORPORAL", f"{val_corp} °C")

    estado = "NORMAL" if val_corp < 37.5 else "FIEBRE"
    color  = "#00ff00" if estado == "NORMAL" else "#ff4b4b"
    col2.markdown(
        f"<h3 style='text-align:center; color:{color}'>{estado}</h3>",
        unsafe_allow_html=True
    )

    col3.metric("TEMP. AMBIENTE", f"{val_amb} °C")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['id'],
        y=df['temp_corporal'],
        mode='lines+markers',
        line=dict(color=color, width=3),
        fill='tozeroy'
    ))
    fig.update_layout(
        template="plotly_dark",
        height=350,
        margin=dict(l=10, r=10, t=30, b=10)
    )

    # ✅ Sin while True, sin key duplicada — Streamlit maneja solo el ID
    st.plotly_chart(fig, width='stretch')

    with st.expander("Ver registro de lecturas"):
        st.dataframe(df, use_container_width=True)

else:
    st.info("Esperando datos...")

# ✅ Espera 2 segundos y relanza el script completo desde cero — patrón oficial
time.sleep(2)
st.rerun()