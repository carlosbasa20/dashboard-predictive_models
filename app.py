import hmac
import streamlit as st
import pandas as pd
import plotly.express as px


st.set_page_config(
    page_title="Dashboard predicción",
    page_icon="📊",
    layout="wide"
)


# ─────────────────────────────
# Acceso con contraseña
# ─────────────────────────────
if not st.session_state.get("autorizado"):

    st.title("Dashboard de modelos de predicción")
    st.write("Ingresa la contraseña para continuar.")

    try:
        clave_guardada = str(st.secrets["APP_PASSWORD"])
    except (KeyError, FileNotFoundError):
        st.error("No se configuró APP_PASSWORD en los secretos.")
        st.stop()

    clave = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        if hmac.compare_digest(clave, clave_guardada):
            st.session_state["autorizado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

    st.stop()


# ─────────────────────────────
# Carga y limpieza del CSV
# ─────────────────────────────
@st.cache_data
def cargar_datos():

    datos = pd.read_csv(
        "data_dash_m2.csv",
        sep=None,
        engine="python",
        encoding="utf-8-sig"
    )

    datos.columns = datos.columns.str.strip()

    columnas = [
        "Año",
        "Presupuesto de horas",
        "Horas acertadas",
        "Tiempo de predicción"
    ]

    if not set(columnas).issubset(datos.columns):
        st.error(f"El CSV debe contener estas columnas: {columnas}")
        st.write("Columnas encontradas:", list(datos.columns))
        st.stop()

    # Columnas obligatoriamente numéricas
    for columna in [
        "Año",
        "Presupuesto de horas",
        "Horas acertadas"
    ]:
        datos[columna] = pd.to_numeric(
            datos[columna],
            errors="coerce"
        )

    datos = datos.dropna(subset=columnas)

    # Convierte el tiempo a número si todos sus valores son numéricos
    tiempo_numerico = pd.to_numeric(
        datos["Tiempo de predicción"],
        errors="coerce"
    )

    if tiempo_numerico.notna().all():
        datos["Tiempo de predicción"] = tiempo_numerico
    else:
        datos["Tiempo de predicción"] = (
            datos["Tiempo de predicción"]
            .astype(str)
            .str.strip()
        )

    return datos


def etiqueta_tiempo(valor):
    if isinstance(valor, (int, float)):
        numero = float(valor)
        unidad = "hora" if numero == 1 else "horas"
        return f"{numero:g} {unidad}"

    return str(valor)


df = cargar_datos()


# ─────────────────────────────
# Dashboard
# ─────────────────────────────
st.title("Resultados del modelo M2")
st.caption("Clasificación de horas críticas según el horizonte de predicción.")

años = sorted(df["Año"].unique())

año = st.selectbox(
    "Selecciona el año",
    años,
    format_func=lambda valor: f"{valor:.0f}"
)

datos_año = df[df["Año"] == año]

tiempos = sorted(
    datos_año["Tiempo de predicción"].unique()
)

tiempo = st.selectbox(
    "Tiempo de predicción (en horas)",
    tiempos,
    format_func=etiqueta_tiempo
)

datos_filtrados = (
    datos_año[
        datos_año["Tiempo de predicción"] == tiempo
    ]
    .sort_values("Presupuesto de horas")
)

presupuestos = sorted(
    datos_filtrados["Presupuesto de horas"].unique()
)

presupuesto = st.select_slider(
    "Presupuesto de horas",
    options=presupuestos,
    format_func=lambda valor: f"{float(valor):g}"
)

horas = datos_filtrados.loc[
    datos_filtrados["Presupuesto de horas"] == presupuesto,
    "Horas acertadas"
].iloc[0]


# ─────────────────────────────
# Indicadores
# ─────────────────────────────
col1, col2, col3 = st.columns(3)

col1.metric(
    "Tiempo de predicción",
    etiqueta_tiempo(tiempo)
)

col2.metric(
    "Presupuesto de horas",
    f"{presupuesto:g}"
)

col3.metric(
    "Horas acertadas",
    f"{horas:.0f} de 100"
)


# ─────────────────────────────
# Gráfica
# ─────────────────────────────
fig = px.line(
    datos_filtrados,
    x="Presupuesto de horas",
    y="Horas acertadas",
    markers=True,
    range_y=[0, 100],
    title=(
        f"Resultados de {año:.0f} — "
        f"Predicción con {etiqueta_tiempo(tiempo)} de anticipación"
    )
)

fig.add_scatter(
    x=[presupuesto],
    y=[horas],
    mode="markers",
    marker={
        "size": 15,
        "color": "red"
    },
    name="Selección"
)

fig.update_layout(
    hovermode="x unified",
    xaxis_title="Presupuesto de horas",
    yaxis_title="Horas acertadas"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ─────────────────────────────
# Tabla
# ─────────────────────────────
st.subheader("Datos utilizados")

st.dataframe(
    datos_filtrados,
    use_container_width=True,
    hide_index=True
)