import hmac
from numbers import Number

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
# Carga y limpieza de los CSV
# ─────────────────────────────
@st.cache_data
def cargar_datos(archivo, modelo):

    try:
        datos = pd.read_csv(
            archivo,
            sep=None,
            engine="python",
            encoding="utf-8-sig"
        )
    except FileNotFoundError:
        st.error(f"No se encontró el archivo: {archivo}")
        st.stop()

    datos.columns = datos.columns.str.strip()

    columnas = [
        "Tiempo de predicción",
        "Año",
        "Presupuesto de horas",
        "Horas acertadas"
    ]

    if not set(columnas).issubset(datos.columns):
        st.error(f"{archivo} debe contener estas columnas: {columnas}")
        st.write("Columnas encontradas:", list(datos.columns))
        st.stop()

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

    datos["Modelo"] = modelo

    return datos


def etiqueta_tiempo(valor):

    if isinstance(valor, Number):
        numero = float(valor)
        unidad = "hora" if numero == 1 else "horas"
        return f"{numero:g} {unidad}"

    return str(valor)


m2 = cargar_datos("data_dash_m2_predictive.csv", "M2")
m3 = cargar_datos("data_dash_m3_predictive.csv", "M3")


# ─────────────────────────────
# Dashboard
# ─────────────────────────────
st.title("Comparativa de los modelos M2 y M3")

st.caption(
    "Comparación de horas críticas acertadas según "
    "el horizonte de predicción."
)


# Años disponibles en ambos modelos
años_comunes = sorted(
    set(m2["Año"]) & set(m3["Año"])
)

if not años_comunes:
    st.error("Los modelos no tienen años en común.")
    st.stop()

año = st.selectbox(
    "Selecciona el año",
    años_comunes,
    format_func=lambda valor: f"{valor:.0f}"
)

m2_año = m2[m2["Año"] == año]
m3_año = m3[m3["Año"] == año]


# Tiempos disponibles en ambos modelos
tiempos_comunes = sorted(
    set(m2_año["Tiempo de predicción"])
    & set(m3_año["Tiempo de predicción"])
)

if not tiempos_comunes:
    st.error(
        "Los modelos no tienen tiempos de predicción "
        "en común para este año."
    )
    st.stop()

tiempo = st.selectbox(
    "Tiempo de predicción (en horas)",
    tiempos_comunes,
    format_func=etiqueta_tiempo
)

m2_filtrado = (
    m2_año[
        m2_año["Tiempo de predicción"] == tiempo
    ]
    .sort_values("Presupuesto de horas")
)

m3_filtrado = (
    m3_año[
        m3_año["Tiempo de predicción"] == tiempo
    ]
    .sort_values("Presupuesto de horas")
)


# Presupuestos disponibles en ambos modelos
presupuestos_comunes = sorted(
    set(m2_filtrado["Presupuesto de horas"])
    & set(m3_filtrado["Presupuesto de horas"])
)

if not presupuestos_comunes:
    st.error(
        "Los modelos no tienen presupuestos de horas "
        "en común para esta selección."
    )
    st.stop()

presupuesto = st.select_slider(
    "Presupuesto de horas",
    options=presupuestos_comunes,
    format_func=lambda valor: f"{float(valor):g}"
)


# Resultados seleccionados
horas_m2 = float(
    m2_filtrado.loc[
        m2_filtrado["Presupuesto de horas"] == presupuesto,
        "Horas acertadas"
    ].iloc[0]
)

horas_m3 = float(
    m3_filtrado.loc[
        m3_filtrado["Presupuesto de horas"] == presupuesto,
        "Horas acertadas"
    ].iloc[0]
)

diferencia = horas_m3 - horas_m2


# ─────────────────────────────
# Indicadores
# ─────────────────────────────
col1, col2, col3 = st.columns(3)

col1.metric(
    "Horas acertadas M2",
    f"{horas_m2:.0f} de 100"
)

col2.metric(
    "Horas acertadas M3",
    f"{horas_m3:.0f} de 100"
)

col3.metric(
    "Diferencia M3 − M2",
    f"{diferencia:+.0f} horas"
)


# ─────────────────────────────
# Gráfica comparativa
# ─────────────────────────────
datos_grafica = pd.concat(
    [m2_filtrado, m3_filtrado],
    ignore_index=True
).sort_values(
    ["Modelo", "Presupuesto de horas"]
)

fig = px.line(
    datos_grafica,
    x="Presupuesto de horas",
    y="Horas acertadas",
    color="Modelo",
    markers=True,
    range_y=[0, 100],
    title=(
        f"Comparativa de {año:.0f} — "
        f"Predicción con {etiqueta_tiempo(tiempo)} "
        "de anticipación"
    ),
    color_discrete_map={
        "M2": "#1f77b4",
        "M3": "#ff7f0e"
    }
)

fig.add_vline(
    x=presupuesto,
    line_dash="dash",
    line_color="red"
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
# Tabla comparativa
# ─────────────────────────────
tabla = datos_grafica.pivot_table(
    index="Presupuesto de horas",
    columns="Modelo",
    values="Horas acertadas",
    aggfunc="first"
).reset_index()

tabla.columns.name = None

tabla["Diferencia M3 − M2"] = (
    tabla["M3"] - tabla["M2"]
)

st.subheader("Datos comparativos")

st.dataframe(
    tabla,
    use_container_width=True,
    hide_index=True
)