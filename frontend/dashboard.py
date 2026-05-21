import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Monitor Vitales Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Sistema de Monitoreo de Signos Vitales")

# --- CONEXIÓN DB con connection pooling ---
DB_HOST = os.environ.get("DB_HOST", "vitales_db")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "admin")
DB_NAME = os.environ.get("DB_NAME", "hospital_db")
DB_PORT = os.environ.get("DB_PORT", "3306")


@st.cache_resource
def get_engine():
    return create_engine(
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        pool_size=2,
        pool_recycle=60,
        pool_pre_ping=True  # verifica conexión antes de usarla
    )


engine = get_engine()


def get_data():
    try:
        query = text("""
            SELECT id, temp_corporal, temp_ambiente, fecha
            FROM lecturas
            ORDER BY id DESC
            LIMIT 30
        """)
        with engine.connect() as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()


# --- FRAGMENTO: solo esta parte se refresca cada 2 segundos ---
@st.fragment(run_every=2)
def dashboard():
    df = get_data()

    if not df.empty:
        col1, col2, col3 = st.columns(3)
        val_corp = df.iloc[0]['temp_corporal']
        val_amb = df.iloc[0]['temp_ambiente']

        col1.metric("TEMP. CORPORAL", f"{val_corp} °C")

        estado = "NORMAL" if val_corp < 37.5 else "FIEBRE"
        color = "#00ff00" if estado == "NORMAL" else "#ff4b4b"
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

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver registro de lecturas"):
            st.dataframe(df, use_container_width=True)

    else:
        st.info("Esperando datos...")


dashboard()
