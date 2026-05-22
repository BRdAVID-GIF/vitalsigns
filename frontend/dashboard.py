import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import time
from groq import Groq
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Monitor Vitales Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; }
    .alerta-box {
        background-color: #1a1c24;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
        border-left: 4px solid #00ff00;
    }
    .alerta-box.riesgo {
        border-left: 4px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Sistema de Monitoreo de Signos Vitales")

# --- CONEXIÓN DB ---
DB_HOST = os.environ.get("DB_HOST", "vitales_db")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "admin")
DB_NAME = os.environ.get("DB_NAME", "hospital_db")
DB_PORT = os.environ.get("DB_PORT", "3306")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


@st.cache_resource
def get_engine():
    return create_engine(
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        pool_size=2,
        pool_recycle=60,
        pool_pre_ping=True
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


def analizar_con_ia(df: pd.DataFrame) -> dict:
    try:
        client = Groq(api_key=GROQ_API_KEY)

        ultima = df.iloc[0]
        promedio_corp = df['temp_corporal'].mean()
        max_corp = df['temp_corporal'].max()
        min_corp = df['temp_corporal'].min()
        tendencia = df['temp_corporal'].iloc[0] - df['temp_corporal'].iloc[-1]
        historial = df[['temp_corporal', 'temp_ambiente', 'fecha']].to_string(index=False)

        prompt = f"""Eres un asistente médico especializado en monitoreo de signos vitales.
Analiza los siguientes datos de temperatura de un paciente y da una alerta inteligente.

=== DATOS ACTUALES ===
Temperatura corporal actual: {ultima['temp_corporal']} °C
Temperatura ambiente actual: {ultima['temp_ambiente']} °C

=== ESTADÍSTICAS DE LAS ÚLTIMAS 30 LECTURAS ===
Promedio corporal: {promedio_corp:.2f} °C
Máxima corporal: {max_corp:.2f} °C
Mínima corporal: {min_corp:.2f} °C
Tendencia (subiendo/bajando): {tendencia:+.2f} °C

=== HISTORIAL ===
{historial}

=== INSTRUCCIONES ===
Responde ÚNICAMENTE en este formato JSON exacto, sin texto extra, sin backticks:
{{
  "nivel": "NORMAL",
  "mensaje": "Tu análisis en 2-3 oraciones en español, mencionando tendencia y recomendación."
}}

El campo "nivel" debe ser exactamente uno de: NORMAL, PRECAUCIÓN, ALERTA

Criterios:
- NORMAL: temp corporal entre 36.0 y 37.4 °C, sin tendencia preocupante
- PRECAUCIÓN: temp entre 37.5 y 38.0 °C, o tendencia de subida sostenida
- ALERTA: temp mayor a 38.0 °C o menor a 35.5 °C
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        texto = response.choices[0].message.content.strip()
        texto = texto.replace("```json", "").replace("```", "").strip()
        resultado = json.loads(texto)
        return resultado

    except Exception as e:
        return {
            "nivel": "NORMAL",
            "mensaje": f"Agente IA no disponible: {e}"
        }


# --- FRAGMENTO PRINCIPAL ---
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

        # --- GRÁFICA ---
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

        # --- AGENTE IA (solo cada 30 segundos) ---
        st.markdown("### 🤖 Análisis del Agente IA")

        ahora = time.time()
        if "ultima_ia" not in st.session_state or ahora - st.session_state["ultima_ia"] > 30:
            st.session_state["ultima_ia"] = ahora
            with st.spinner("Analizando datos..."):
                st.session_state["analisis_ia"] = analizar_con_ia(df)

        analisis = st.session_state.get("analisis_ia", {
            "nivel": "NORMAL",
            "mensaje": "Esperando primer análisis..."
        })

        nivel = analisis.get("nivel", "NORMAL")
        mensaje = analisis.get("mensaje", "")

        if "ultima_ia" in st.session_state:
            restante = max(0, 30 - int(ahora - st.session_state["ultima_ia"]))
            st.caption(f"⏱ Próximo análisis en {restante}s")

        iconos = {"NORMAL": "✅", "PRECAUCIÓN": "⚠️", "ALERTA": "🚨"}
        colores_nivel = {
            "NORMAL": "#00ff00",
            "PRECAUCIÓN": "#ffaa00",
            "ALERTA": "#ff4b4b"
        }
        css_class = "riesgo" if nivel == "ALERTA" else ""
        icono = iconos.get(nivel, "✅")
        color_niv = colores_nivel.get(nivel, "#00ff00")

        st.markdown(f"""
            <div class="alerta-box {css_class}">
                <h3 style="color:{color_niv}; margin:0">{icono} {nivel}</h3>
                <p style="color:#cccccc; margin-top:10px; font-size:16px">{mensaje}</p>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver registro de lecturas"):
            st.dataframe(df, use_container_width=True)

    else:
        st.info("Esperando datos...")


dashboard()