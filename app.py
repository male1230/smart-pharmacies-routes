import streamlit as st
import pandas as pd
import holidays
import calendar
from datetime import date, timedelta
import numpy as np
import io
import math
import folium
import streamlit.components.v1 as components
import requests
import time
from sklearn.cluster import KMeans, DBSCAN

# Configuración inicial de la página
st.set_page_config(page_title="Motor de Rutas Inteligentes", layout="wide")

# API Key de Google Maps (Geocoding), configurada mediante Streamlit Secrets.
try:
    GOOGLE_MAPS_API_KEY = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
except Exception:
    GOOGLE_MAPS_API_KEY = ""


def geocodificar_google(direccion, ciudad, api_key):
    """Consulta Geocoding API. Devuelve (lat, lon, status, error_msg)."""
    direccion = (direccion or "").strip()
    ciudad = (ciudad or "").strip()
    if not direccion:
        return None, None, "SIN_DIRECCION", "No hay dirección para buscar."
    if not api_key or api_key == "TU_API_KEY_AQUI":
        return None, None, "NO_API_KEY", "Configura GOOGLE_MAPS_API_KEY en los secretos de Streamlit."

    query_address = f"{direccion}, {ciudad}, Colombia" if ciudad else f"{direccion}, Colombia"
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={requests.utils.quote(query_address)}&key={api_key}"
    )
    try:
        res = requests.get(url, timeout=20).json()
    except Exception as e:
        return None, None, "ERROR_CONEXION", str(e)

    status = res.get("status", "UNKNOWN")
    if status == "OK":
        loc = res["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"], status, None
    return None, None, status, res.get("error_message")


def limpiar_claves_editor_coords():
    for k in list(st.session_state.keys()):
        if str(k).startswith("falt_"):
            del st.session_state[k]

# --- NAVEGACIÓN ---
st.sidebar.title("📌 Menú Principal")
modo_app = st.sidebar.radio("Ir a:", ["Rutas Inteligentes", "Geocodificador (Google Maps)"])
st.sidebar.divider()

if modo_app == "Geocodificador (Google Maps)":
    st.title("Geocodificador de Coordenadas 🌍")
    st.markdown("### Obtén Latitud y Longitud automáticamente para tus PDVs")
    
    with st.expander("ℹ️ ¿Cómo configurar la API Key de Google Maps en el código y solucionar errores comunes?"):
        st.write("""
        1. Ve a la [Consola de Google Cloud](https://console.cloud.google.com/).
        2. Selecciona o crea un proyecto nuevo.
        3. En **APIs y Servicios > Biblioteca**, busca **Geocoding API** y habilítala. *(Nota: Google Cloud requiere que tengas una tarjeta de crédito vinculada para activar la cuenta, aunque ofrece un crédito mensual gratuito de $200 USD que cubre miles de peticiones).*
        4. Ve a **Credenciales**, haz clic en **Crear credenciales > Clave de API**.
        5. Configura la clave como secreto `GOOGLE_MAPS_API_KEY` en Streamlit Cloud o en `.streamlit/secrets.toml` local.
        """)

    st.divider()
    st.subheader("🧪 Probador de API / Diagnóstico (Prueba un PDV individual)")
    st.markdown("Usa esta sección para verificar si tu API Key funciona correctamente antes de procesar todo el archivo masivamente.")
    
    col_test1, col_test2, col_test_btn = st.columns([2, 2, 1])
    with col_test1:
        test_dir_input = st.text_input("Dirección de prueba", "CR 2 # 23A - 14")
    with col_test2:
        test_ciudad_input = st.text_input("Ciudad de prueba", "Fusagasugá")
    with col_test_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        probar_api = st.button("🔍 Probar API", type="secondary", use_container_width=True)

    if probar_api:
        if GOOGLE_MAPS_API_KEY == "TU_API_KEY_AQUI" or not GOOGLE_MAPS_API_KEY.strip():
            st.error("⚠️ Configura la API Key como secreto `GOOGLE_MAPS_API_KEY` antes de usar el geocodificador.")
        else:
            query_test = f"{test_dir_input}, {test_ciudad_input}, Colombia"
            url_test = f"https://maps.googleapis.com/maps/api/geocode/json?address={requests.utils.quote(query_test)}&key={GOOGLE_MAPS_API_KEY}"
            
            try:
                res_test = requests.get(url_test).json()
                status = res_test.get('status', 'UNKNOWN')
                
                st.write(f"**Estado devuelto por Google Maps:** `{status}`")
                
                if status == 'OK':
                    location = res_test['results'][0]['geometry']['location']
                    lat_res = location['lat']
                    lon_res = location['lng']
                    st.success(f"✅ ¡Dirección encontrada con éxito! Latitud: `{lat_res}`, Longitud: `{lon_res}`")
                    
                    # Mostrar mapa interactivo de prueba
                    m_test = folium.Map(location=[lat_res, lon_res], zoom_start=15, tiles="CartoDB positron")
                    folium.Marker(
                        location=[lat_res, lon_res],
                        popup=f"<b>Prueba:</b> {test_dir_input}",
                        icon=folium.Icon(color="green", icon="info-sign")
                    ).add_to(m_test)
                    components.html(m_test._repr_html_(), height=350)
                elif status == 'REQUEST_DENIED':
                    st.error("❌ **Error REQUEST_DENIED:** Esto ocurre generalmente porque la **Geocoding API** no está habilitada en tu consola de Google Cloud, o la clave es incorrecta, o falta asociar una cuenta de cobro (Billing) en Google Cloud.")
                elif status == 'ZERO_RESULTS':
                    st.warning("⚠️ **ZERO_RESULTS:** Google Maps no encontró ninguna coincidencia con esta combinación exacta de dirección y ciudad.")
                else:
                    st.warning(f"⚠️ La API respondió con estado: `{status}`")
                
                with st.expander("Ver respuesta JSON completa de Google"):
                    st.json(res_test)
            except Exception as e:
                st.error(f"Error de conexión con la API: {e}")

    st.divider()
    file_geocoding = st.file_uploader("Sube el archivo de PDVs / Maestro (.xlsx) para procesamiento masivo", type=["xlsx"])
    
    if 'geo_analizado' not in st.session_state:
        st.session_state.geo_analizado = False
    if 'geo_df' not in st.session_state:
        st.session_state.geo_df = None
    if 'geo_procesado' not in st.session_state:
        st.session_state.geo_procesado = False

    if file_geocoding:
        if st.button("📊 Analizar Archivo", type="secondary"):
            df_geo = pd.read_excel(file_geocoding)
            
            # Asegurar que existan las columnas base
            if 'LATITUD' not in df_geo.columns: df_geo['LATITUD'] = np.nan
            if 'LONGITUD' not in df_geo.columns: df_geo['LONGITUD'] = np.nan
            if 'ORIGEN_COORDENADAS' not in df_geo.columns: df_geo['ORIGEN_COORDENADAS'] = "Original"
            
            # Limpiar coordenadas para identificar correctamente cuáles faltan
            serie_lat = df_geo['LATITUD'].astype(str).str.replace(',', '.', regex=False).str.strip()
            serie_lon = df_geo['LONGITUD'].astype(str).str.replace(',', '.', regex=False).str.strip()
            lat_clean = pd.to_numeric(serie_lat, errors='coerce')
            lon_clean = pd.to_numeric(serie_lon, errors='coerce')
            
            mask_missing = lat_clean.isnull() | lon_clean.isnull()
            
            st.session_state.geo_df = df_geo
            st.session_state.geo_mask_missing = mask_missing
            st.session_state.geo_analizado = True
            st.session_state.geo_procesado = False # Reiniciar si sube nuevo archivo

    if st.session_state.geo_analizado and st.session_state.geo_df is not None:
        df_geo = st.session_state.geo_df
        mask_missing = st.session_state.geo_mask_missing
        total_pdvs = len(df_geo)
        sin_coord = mask_missing.sum()
        con_coord = total_pdvs - sin_coord

        st.subheader("📋 Resumen del Archivo")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total PDVs", total_pdvs)
        col2.metric("Con Coordenadas (Actual)", con_coord)
        col3.metric("Faltan Coordenadas", sin_coord)

        if sin_coord > 0:
            if st.button("🚀 Procesar con Google Maps", type="primary"):
                if GOOGLE_MAPS_API_KEY == "TU_API_KEY_AQUI" or not GOOGLE_MAPS_API_KEY.strip():
                    st.error("⚠️ Configura la API Key como secreto GOOGLE_MAPS_API_KEY antes de procesar el archivo.")
                else:
                    progress_text = "Conectando con Google Maps..."
                    my_bar = st.progress(0, text=progress_text)
                    
                    df_resultado = df_geo.copy()
                    indices_a_procesar = df_resultado[mask_missing].index
                    exitosos = 0
                    fallidos = 0
                    
                    for i, idx in enumerate(indices_a_procesar):
                        row = df_resultado.loc[idx]
                        direccion_buscar = ""
                        
                        # 1. Buscar en DIR_NORM
                        if 'DIR_NORM' in df_resultado.columns and pd.notnull(row['DIR_NORM']) and str(row['DIR_NORM']).strip() != "":
                            direccion_buscar = str(row['DIR_NORM'])
                        # 2. Si no hay DIR_NORM, usar DIRECCION
                        elif 'DIRECCION' in df_resultado.columns and pd.notnull(row['DIRECCION']) and str(row['DIRECCION']).strip() != "":
                            direccion_buscar = str(row['DIRECCION'])
                            
                        ciudad = str(row['CIUDAD']) if 'CIUDAD' in df_resultado.columns and pd.notnull(row['CIUDAD']) else ""
                        
                        # Si encontramos una dirección construimos la petición
                        if direccion_buscar:
                            query_address = f"{direccion_buscar}, {ciudad}, Colombia"
                            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query_address}&key={GOOGLE_MAPS_API_KEY}"
                            
                            try:
                                response = requests.get(url).json()
                                if response['status'] == 'OK':
                                    location = response['results'][0]['geometry']['location']
                                    df_resultado.at[idx, 'LATITUD'] = location['lat']
                                    df_resultado.at[idx, 'LONGITUD'] = location['lng']
                                    df_resultado.at[idx, 'ORIGEN_COORDENADAS'] = "API Google Maps"
                                    exitosos += 1
                                else:
                                    fallidos += 1
                            except Exception as e:
                                fallidos += 1
                        else:
                            fallidos += 1 # Faltan datos para buscar
                            
                        # Actualizar barra
                        my_bar.progress((i + 1) / len(indices_a_procesar), text=f"Procesando PDV {i+1} de {len(indices_a_procesar)}...")
                        time.sleep(0.05)
                        
                    st.session_state.geo_df_final = df_resultado
                    st.session_state.geo_exitosos = exitosos
                    st.session_state.geo_fallidos = fallidos
                    st.session_state.geo_procesado = True
                    my_bar.empty()
                    st.success("✅ ¡Extracción completada!")
        else:
            st.info("🎉 ¡Felicidades! Todos los PDVs del archivo ya cuentan con coordenadas.")

        if st.session_state.geo_procesado:
            st.divider()
            st.subheader("🎯 Resultado Final")
            c1, c2, c3 = st.columns(3)
            c1.metric("PDVs Encontrados (Nuevos)", st.session_state.geo_exitosos)
            c2.metric("No Encontrados en Maps", st.session_state.geo_fallidos)
            c3.metric("Faltantes Finales", sin_coord - st.session_state.geo_exitosos)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.geo_df_final.to_excel(writer, index=False, sheet_name='Maestro_Actualizado')
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Descargar MAESTRO_COORDENADAS_PROCESADO.xlsx",
                data=excel_data,
                file_name="MAESTRO_COORDENADAS_PROCESADO.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
    st.stop()

st.title("Rutas Inteligentes 🗺️ - Orquestador Completo")

# --- ESTADOS DE SESIÓN ---
if 'mostrar_resumen' not in st.session_state:
    st.session_state.mostrar_resumen = False
if 'rutas_generadas' not in st.session_state:
    st.session_state.rutas_generadas = False
if 'df_rutas' not in st.session_state:
    st.session_state.df_rutas = None
if 'coords_guardadas' not in st.session_state:
    st.session_state.coords_guardadas = False

# --- FUNCIONES AUXILIARES ETAPA 1 ---
def limpiar_coordenadas(serie):
    serie_str = serie.astype(str).str.replace(',', '.', regex=False).str.strip()
    return pd.to_numeric(serie_str, errors='coerce')


def actualizar_maestro_coordenadas(df_maestro, filas_panel, actualizaciones):
    """Actualiza coordenadas manuales y agrega al maestro los PDV que no existían."""
    maestro = df_maestro.copy()
    if 'ORIGEN_COORDENADAS' not in maestro.columns:
        maestro['ORIGEN_COORDENADAS'] = "Original"
    if 'NUEVO_PUNTO_VENTA' not in maestro.columns:
        maestro['NUEVO_PUNTO_VENTA'] = "No"

    for idx, (codigo, latitud, longitud, origen) in actualizaciones.items():
        fila = filas_panel.loc[idx]
        codigo_texto = str(codigo).strip()
        mask_codigo = maestro['CODIGO PDV'].astype(str).str.strip() == codigo_texto

        if mask_codigo.any():
            maestro.loc[mask_codigo, 'LATITUD'] = latitud
            maestro.loc[mask_codigo, 'LONGITUD'] = longitud
            maestro.loc[mask_codigo, 'ORIGEN_COORDENADAS'] = origen
            continue

        nueva_fila = {col: "" for col in maestro.columns}
        for col in maestro.columns:
            if col in fila.index:
                nueva_fila[col] = fila[col]
        nueva_fila['CODIGO PDV'] = codigo
        nueva_fila['LATITUD'] = latitud
        nueva_fila['LONGITUD'] = longitud
        nueva_fila['ORIGEN_COORDENADAS'] = origen
        nueva_fila['NUEVO_PUNTO_VENTA'] = "SI"
        maestro = pd.concat([maestro, pd.DataFrame([nueva_fila])], ignore_index=True)

    return maestro

def calcular_dias_habiles(year, month, sabados_seleccionados):
    festivos_co = holidays.CO(years=year)
    num_days = calendar.monthrange(year, month)[1]
    dias_L_V = 0
    festivos_en_dias_laborales = 0
    dias_habiles_lista = []
    
    for day in range(1, num_days + 1):
        fecha = date(year, month, day)
        str_fecha = fecha.strftime("%Y-%m-%d")
        es_festivo = fecha in festivos_co
        if fecha.weekday() <= 4: 
            if not es_festivo:
                dias_L_V += 1
                dias_habiles_lista.append(fecha)
            else:
                festivos_en_dias_laborales += 1
        elif fecha.weekday() == 5 and str_fecha in sabados_seleccionados:
            dias_habiles_lista.append(fecha)
                
    total_sabados = len(sabados_seleccionados)
    visitas_maximas = (dias_L_V * 8) + (total_sabados * 4)
    dias_habiles_lista.sort()
    return dias_L_V, festivos_en_dias_laborales, visitas_maximas, dias_habiles_lista

def generar_calendario_html(year, month, sabados_seleccionados):
    festivos_co = holidays.CO(years=year)
    cal = calendar.monthcalendar(year, month)
    nombres_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    
    html = '<table style="width:100%; text-align:center; border-collapse: collapse; margin-bottom: 20px;"><tr>'
    for dia in nombres_dias:
        html += f'<th style="border: 1px solid #ddd; padding: 10px; background-color: #333; color: white;">{dia}</th>'
    html += '</tr>'
    
    for semana in cal:
        html += '<tr>'
        for idx, dia in enumerate(semana):
            if dia == 0:
                html += '<td style="border: 1px solid #ddd; padding: 10px; background-color: transparent;"></td>'
            else:
                fecha_actual = date(year, month, dia)
                str_fecha = fecha_actual.strftime("%Y-%m-%d")
                es_festivo = fecha_actual in festivos_co
                es_sab_laboral = str_fecha in sabados_seleccionados
                
                bg_color = "transparent"
                text_color = "inherit"
                tooltip = ""
                font_weight = "normal"
                
                if es_festivo:
                    bg_color = "#ffcccc"
                    text_color = "black"
                    font_weight = "bold"
                    nombre_festivo = festivos_co.get(fecha_actual)
                    tooltip = f"Festivo: {nombre_festivo}"
                elif es_sab_laboral:
                    bg_color = "#d9f2d9"
                    text_color = "black"
                    font_weight = "bold"
                    tooltip = "Sábado Laboral Seleccionado"
                elif idx == 6:
                    text_color = "gray"
                    tooltip = "Domingo"
                    
                html += f'<td style="border: 1px solid #ddd; padding: 10px; background-color: {bg_color}; color: {text_color}; font-weight: {font_weight};" title="{tooltip}">{dia}</td>'
        html += '</tr>'
    html += '</table>'
    return html

# --- FUNCIONES ETAPA 2 & 3 ---
LIMITE_CIUDAD_KM = 12.0
LIMITE_ABSOLUTO_KM = 17.0
UMBRAL_NUEVO_DIA = 3.0


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _ciudad_norm(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    return str(valor).strip().upper()


def _ciudades_de_puntos(puntos):
    ciudades = {_ciudad_norm(p.get("CIUDAD", "")) for p in puntos}
    ciudades.discard("")
    return ciudades


def limite_distancia_puntos(puntos):
    """12 km si la jornada queda en una sola ciudad; 17 km si hay cruce intermunicipal."""
    ciudades = _ciudades_de_puntos(puntos)
    if len(ciudades) <= 1:
        return LIMITE_CIUDAD_KM
    return LIMITE_ABSOLUTO_KM


def diametro_geodesico(puntos):
    """Máxima distancia entre extremos (cualquier par) en km."""
    n = len(puntos)
    if n < 2:
        return 0.0
    max_d = 0.0
    for i in range(n):
        lat1, lon1 = puntos[i]["LATITUD_CLEAN"], puntos[i]["LONGITUD_CLEAN"]
        for j in range(i + 1, n):
            d = haversine_distance(lat1, lon1, puntos[j]["LATITUD_CLEAN"], puntos[j]["LONGITUD_CLEAN"])
            if d > max_d:
                max_d = d
    return max_d


def puede_agregar_a_dia(puntos_dia, nuevo):
    simulados = list(puntos_dia) + [nuevo]
    limite = limite_distancia_puntos(simulados)
    if diametro_geodesico(simulados) > limite:
        return False
    if puntos_dia:
        lat, lon = nuevo["LATITUD_CLEAN"], nuevo["LONGITUD_CLEAN"]
        for p in puntos_dia:
            if haversine_distance(lat, lon, p["LATITUD_CLEAN"], p["LONGITUD_CLEAN"]) > limite:
                return False
    return True

# ANTIGUA LOGICA
# def _coords_km(lats, lons):
#     """Proyección local a km para que K-Means no distorsione longitud vs latitud."""
#     lat_ref = float(np.mean(lats))
#     scale_lon = 111.32 * math.cos(math.radians(lat_ref))
#     x = np.array(lons, dtype=float) * scale_lon
#     y = np.array(lats, dtype=float) * 110.57
#     return np.column_stack([x, y])

def _coords_km(lats, lons):
    """Proyección local a km para que K-Means no distorsione longitud vs latitud."""
    lat_ref = float(np.mean(lats))
    scale_lon = 111.32 * math.cos(math.radians(lat_ref))
    x = np.array(lons, dtype=float) * scale_lon
    y = np.array(lats, dtype=float) * 110.57
    return np.column_stack([x, y])

# ANTIGUA LOGICA
# def clusterizar_macrozonas(df_user, n_dias, cap_diaria):
#     """
#     Segmenta PDVs en macro-zonas con K-Means (antes de asignar días).
#     Parte clusters cuyo diámetro geodésico supera 17 km.
#     """
#     df_user = df_user.copy()
#     df_u = df_user.drop_duplicates(subset=["CODIGO PDV"]).copy()
#     n = len(df_u)
#     if n == 0:
#         df_user["MACROZONA"] = 0
#         return df_user
#     if n == 1:
#         df_user["MACROZONA"] = 0
#         return df_user

#     lats = df_u["LATITUD_CLEAN"].astype(float).to_numpy()
#     lons = df_u["LONGITUD_CLEAN"].astype(float).to_numpy()
#     xy = _coords_km(lats, lons)

#     n_coords_unicas = np.unique(np.round(xy, 5), axis=0).shape[0]
#     k_carga = max(1, math.ceil(n / max(int(cap_diaria), 1)))
#     k = max(1, min(n, n_coords_unicas, k_carga, max(1, n_dias)))

#     try:
#         labels = KMeans(n_clusters=k, n_init=10, random_state=42, max_iter=300).fit_predict(xy)
#     except Exception:
#         labels = np.zeros(n, dtype=int)

#     df_u = df_u.reset_index(drop=True)
#     df_u["MACROZONA"] = labels.astype(int)

#     next_id = int(df_u["MACROZONA"].max()) + 1
#     changed = True
#     while changed:
#         changed = False
#         for zona in list(df_u["MACROZONA"].unique()):
#             mask = df_u["MACROZONA"] == zona
#             subset = df_u.loc[mask]
#             if len(subset) < 3:
#                 continue
#             puntos = subset.to_dict("records")
#             if diametro_geodesico(puntos) <= LIMITE_ABSOLUTO_KM:
#                 continue
#             xy_sub = _coords_km(
#                 subset["LATITUD_CLEAN"].astype(float).to_numpy(),
#                 subset["LONGITUD_CLEAN"].astype(float).to_numpy(),
#             )
#             n_sub_unique = np.unique(np.round(xy_sub, 5), axis=0).shape[0]
#             if n_sub_unique < 2:
#                 continue
#             try:
#                 sub_labels = KMeans(n_clusters=2, n_init=10, random_state=42, max_iter=300).fit_predict(xy_sub)
#             except Exception:
#                 continue
#             idxs = subset.index.tolist()
#             for local_i, idx_fila in enumerate(idxs):
#                 if sub_labels[local_i] == 1:
#                     df_u.at[idx_fila, "MACROZONA"] = next_id
#             next_id += 1
#             changed = True
#             break

#     mapa_zona = dict(zip(df_u["CODIGO PDV"], df_u["MACROZONA"]))
#     df_user["MACROZONA"] = df_user["CODIGO PDV"].map(mapa_zona).fillna(0).astype(int)
#     return df_user

def clusterizar_macrozonas(df_user, n_dias, cap_diaria):
    """
    Segmenta PDVs en macro-zonas con K-Means (antes de asignar días).
    Parte clusters cuyo diámetro geodésico supera 17 km.
    """
    df_user = df_user.copy()
    df_u = df_user.drop_duplicates(subset=["CODIGO PDV"]).copy()
    n = len(df_u)
    if n == 0:
        df_user["MACROZONA"] = 0
        return df_user
    if n == 1:
        df_user["MACROZONA"] = 0
        return df_user

    lats = df_u["LATITUD_CLEAN"].astype(float).to_numpy()
    lons = df_u["LONGITUD_CLEAN"].astype(float).to_numpy()
    xy = _coords_km(lats, lons)

    n_coords_unicas = np.unique(np.round(xy, 5), axis=0).shape[0]
    k_carga = max(1, math.ceil(n / max(int(cap_diaria), 1)))
    k = max(1, min(n, n_coords_unicas, k_carga, max(1, n_dias)))

    try:
        labels = KMeans(n_clusters=k, n_init=10, random_state=42, max_iter=300).fit_predict(xy)
    except Exception:
        labels = np.zeros(n, dtype=int)

    df_u = df_u.reset_index(drop=True)
    df_u["MACROZONA"] = labels.astype(int)

    next_id = int(df_u["MACROZONA"].max()) + 1
    changed = True
    while changed:
        changed = False
        for zona in list(df_u["MACROZONA"].unique()):
            mask = df_u["MACROZONA"] == zona
            subset = df_u.loc[mask]
            if len(subset) < 3:
                continue
            puntos = subset.to_dict("records")
            if diametro_geodesico(puntos) <= LIMITE_ABSOLUTO_KM:
                continue
            xy_sub = _coords_km(
                subset["LATITUD_CLEAN"].astype(float).to_numpy(),
                subset["LONGITUD_CLEAN"].astype(float).to_numpy(),
            )
            n_sub_unique = np.unique(np.round(xy_sub, 5), axis=0).shape[0]
            if n_sub_unique < 2:
                continue
            try:
                sub_labels = KMeans(n_clusters=2, n_init=10, random_state=42, max_iter=300).fit_predict(xy_sub)
            except Exception:
                continue
            idxs = subset.index.tolist()
            for local_i, idx_fila in enumerate(idxs):
                if sub_labels[local_i] == 1:
                    df_u.at[idx_fila, "MACROZONA"] = next_id
            next_id += 1
            changed = True
            break

    mapa_zona = dict(zip(df_u["CODIGO PDV"], df_u["MACROZONA"]))
    df_user["MACROZONA"] = df_user["CODIGO PDV"].map(mapa_zona).fillna(0).astype(int)
    return df_user

def ordenar_ruta_diaria(puntos_del_dia):
    """Arranque en el punto más periférico al centroide y vecino más cercano, respetando el tope del día."""
    if len(puntos_del_dia) <= 1:
        return list(puntos_del_dia)

    limite = limite_distancia_puntos(puntos_del_dia)
    restantes = list(puntos_del_dia)
    lats = [p["LATITUD_CLEAN"] for p in restantes]
    lons = [p["LONGITUD_CLEAN"] for p in restantes]
    cg_lat = float(np.mean(lats))
    cg_lon = float(np.mean(lons))

    max_dist = -1
    start_idx = 0
    for i, p in enumerate(restantes):
        d = haversine_distance(cg_lat, cg_lon, p["LATITUD_CLEAN"], p["LONGITUD_CLEAN"])
        if d > max_dist:
            max_dist = d
            start_idx = i

    visitados = [restantes.pop(start_idx)]
    while restantes:
        last = visitados[-1]
        mejor_idx = 0
        mejor_key = None
        for i, p in enumerate(restantes):
            d = haversine_distance(
                last["LATITUD_CLEAN"], last["LONGITUD_CLEAN"],
                p["LATITUD_CLEAN"], p["LONGITUD_CLEAN"],
            )
            misma_ciudad = _ciudad_norm(last.get("CIUDAD", "")) == _ciudad_norm(p.get("CIUDAD", ""))
            if _ciudad_norm(last.get("CIUDAD", "")) and _ciudad_norm(p.get("CIUDAD", "")):
                penal_muni = 0 if misma_ciudad else 1
            else:
                penal_muni = 0
            penal_limite = 0 if d <= limite else 1
            key = (penal_limite, penal_muni, d, i)
            if mejor_key is None or key < mejor_key:
                mejor_key = key
                mejor_idx = i
        visitados.append(restantes.pop(mejor_idx))
    return visitados


# ANTIGUA LOGICA
# def ajustar_frecuencias_y_capacidades(df_user, dias_L_V, total_sabados):
#     """
#     Se simplifica. La reducción en cascada ya no se hace a ciegas aquí.
#     Se delega al simulador de rutas que conoce la geografía y los topes por cercanía.
#     """
#     cap_L_V_diaria = 8
#     cap_sab_diaria = 4
#     supera_recomendado = df_user['CANTIDAD VISITAS'].sum() > ((dias_L_V * 8) + (total_sabados * 4))
#     return df_user, cap_L_V_diaria, cap_sab_diaria, supera_recomendado

def ajustar_frecuencias_y_capacidades(df_user, dias_L_V, total_sabados):
    """
    Se simplifica. La reducción en cascada ya no se hace a ciegas aquí.
    Se delega al simulador de rutas que conoce la geografía y los topes por cercanía.
    """
    cap_L_V_diaria = 8
    cap_sab_diaria = 4
    supera_recomendado = df_user['CANTIDAD VISITAS'].sum() > ((dias_L_V * 8) + (total_sabados * 4))
    return df_user, cap_L_V_diaria, cap_sab_diaria, supera_recomendado

# ANTIGUA LOGICA
# def procesar_rutas_usuario(df_user, dias_habiles_lista, cap_L_V_diaria, cap_sab_diaria):
#     df_user = df_user.dropna(subset=['LATITUD_CLEAN', 'LONGITUD_CLEAN'])
#     if df_user.empty: return []

#     n_dias = max(1, len(dias_habiles_lista))
#     df_user = clusterizar_macrozonas(df_user, n_dias, cap_L_V_diaria)

#     visitas_totales = df_user['CANTIDAD VISITAS'].sum()
#     capacidades_por_dia = {d: 0 for d in dias_habiles_lista}
    
#     # 1. Balanceo de Carga Plano (Round Robin) — sin cambio de reglas de cupo
#     restantes = visitas_totales
#     while restantes > 0:
#         candidatos = []
#         for d in dias_habiles_lista:
#             es_sab = (d.weekday() == 5)
#             max_c = cap_sab_diaria if es_sab else cap_L_V_diaria
#             if capacidades_por_dia[d] < max_c:
#                 candidatos.append(d)
        
#         if not candidatos:
#             break
            
#         candidatos.sort(key=lambda d: (capacidades_por_dia[d], 1 if d.weekday() == 5 else 0, d))
#         mejor_d = candidatos[0]
#         capacidades_por_dia[mejor_d] += 1
#         restantes -= 1

#     puntos_por_dia = {d: [] for d in dias_habiles_lista}
    
#     def centroide_dia(d):
#         if not puntos_por_dia[d]: return None
#         lats = [p['LATITUD_CLEAN'] for p in puntos_por_dia[d]]
#         lons = [p['LONGITUD_CLEAN'] for p in puntos_por_dia[d]]
#         return (sum(lats)/len(lats), sum(lons)/len(lons))

#     def afinidad_macrozona(d, zona):
#         pts = puntos_por_dia[d]
#         if not pts:
#             return 1
#         mismas = sum(1 for p in pts if int(p.get('MACROZONA', -1)) == int(zona))
#         if mismas == len(pts):
#             return 0
#         if mismas > 0:
#             return 1
#         return 2

#     visitas_programadas = []
#     df_user_sorted = df_user.sort_values(
#         by=['MACROZONA', 'CANTIDAD VISITAS', 'LATITUD_CLEAN'],
#         ascending=[True, False, False],
#     )
    
#     for idx, row in df_user_sorted.iterrows():
#         frecuencia = int(row['CANTIDAD VISITAS'])
#         lat, lon = row['LATITUD_CLEAN'], row['LONGITUD_CLEAN']
#         zona = int(row.get('MACROZONA', 0))
        
#         fechas_asignadas = []
#         for v in range(frecuencia):
#             candidatos = []
#             for d in dias_habiles_lista:
#                 if capacidades_por_dia[d] > 0:
#                     if not fechas_asignadas:
#                         candidatos.append(d)
#                     else:
#                         if all(abs((d - f).days) >= 8 for f in fechas_asignadas):
#                             candidatos.append(d)
            
#             if not candidatos and v > 0:
#                 candidatos = [d for d in dias_habiles_lista if capacidades_por_dia[d] > 0]
                
#             factibles = [d for d in candidatos if puede_agregar_a_dia(puntos_por_dia[d], row)]
#             pool = factibles if factibles else candidatos

#             mejor_dia = None
#             mejor_key = None
#             for d in pool:
#                 c = centroide_dia(d)
#                 if c is None:
#                     dist = UMBRAL_NUEVO_DIA
#                 else:
#                     dist = haversine_distance(lat, lon, c[0], c[1])
#                 if puntos_por_dia[d]:
#                     dist_punto_cercano = min(
#                         haversine_distance(
#                             lat, lon, p['LATITUD_CLEAN'], p['LONGITUD_CLEAN']
#                         ) for p in puntos_por_dia[d]
#                     )
#                 else:
#                     dist_punto_cercano = UMBRAL_NUEVO_DIA
#                 penal_limite = 0 if d in factibles else 1
#                 key = (penal_limite, dist_punto_cercano, afinidad_macrozona(d, zona), dist, d)
#                 if mejor_key is None or key < mejor_key:
#                     mejor_key = key
#                     mejor_dia = d
                    
#             if mejor_dia:
#                 fechas_asignadas.append(mejor_dia)
#                 capacidades_por_dia[mejor_dia] -= 1
#                 puntos_por_dia[mejor_dia].append(row)
#                 visitas_programadas.append({'FECHA': mejor_dia, 'DATA': row})

#     rutas_optimizadas = []
#     df_visitas = pd.DataFrame(visitas_programadas)
    
#     if df_visitas.empty: return []
    
#     dias_con_visitas = df_visitas['FECHA'].unique()
#     dias_semana_es = {0: 'LUNES', 1: 'MARTES', 2: 'MIÉRCOLES', 3: 'JUEVES', 4: 'VIERNES', 5: 'SÁBADO', 6: 'DOMINGO'}
    
#     for dia in sorted(dias_con_visitas):
#         puntos_del_dia = df_visitas[df_visitas['FECHA'] == dia]['DATA'].tolist()
#         if not puntos_del_dia: continue
        
#         visitados = ordenar_ruta_diaria(puntos_del_dia)
            
#         hora_llegada_acumulada = 0.0
        
#         for orden, p in enumerate(visitados, 1):
#             horas_visita = 0.75
#             usuario = str(p.get('USUARIO', '')).lower()
#             cadena = str(p.get('CADENA', '')).upper()
            
#             if usuario == "zona.panaleras":
#                 horas_visita = 2.0
#             elif cadena == "FARMATODO":
#                 horas_visita = 1.0
                
#             fila = p.to_dict()
#             fila['FECHA_PROGRAMADA'] = dia.strftime("%d/%m/%Y")
#             fila['DIA_SEMANA'] = dias_semana_es[dia.weekday()]
#             fila['ORDEN_VISITA'] = orden
#             fila['HORAS_VISITA'] = horas_visita
#             fila['HORA_LLEGADA_ESTIMADA (Hrs)'] = round(hora_llegada_acumulada, 2)
            
#             hora_llegada_acumulada += horas_visita + 0.25 
#             fila['JORNADA_FINAL_DIA (Hrs)'] = round(hora_llegada_acumulada - 0.25, 2)
            
#             rutas_optimizadas.append(fila)
            
#         coords_str = "/".join([f"{p['LATITUD_CLEAN']},{p['LONGITUD_CLEAN']}" for p in visitados])
#         link_maps = f"https://www.google.com/maps/dir/{coords_str}"
        
#         for r in rutas_optimizadas[-len(visitados):]:
#             r['LINK_GOOGLE_MAPS'] = link_maps
            
#     return rutas_optimizadas

# def procesar_rutas_usuario(df_user, dias_habiles_lista, cap_L_V_diaria, cap_sab_diaria):
#     df_user = df_user.dropna(subset=['LATITUD_CLEAN', 'LONGITUD_CLEAN'])
#     if df_user.empty: return []

#     n_dias = max(1, len(dias_habiles_lista))
#     df_user = clusterizar_macrozonas(df_user, n_dias, cap_L_V_diaria)

#     visitas_totales = df_user['CANTIDAD VISITAS'].sum()
#     capacidades_por_dia = {d: 0 for d in dias_habiles_lista}
    
#     # 1. Balanceo de Carga Plano (Round Robin) — sin cambio de reglas de cupo
#     restantes = visitas_totales
#     while restantes > 0:
#         candidatos = []
#         for d in dias_habiles_lista:
#             es_sab = (d.weekday() == 5)
#             max_c = cap_sab_diaria if es_sab else cap_L_V_diaria
#             if capacidades_por_dia[d] < max_c:
#                 candidatos.append(d)
        
#         if not candidatos:
#             break
            
#         candidatos.sort(key=lambda d: (capacidades_por_dia[d], 1 if d.weekday() == 5 else 0, d))
#         mejor_d = candidatos[0]
#         capacidades_por_dia[mejor_d] += 1
#         restantes -= 1

#     puntos_por_dia = {d: [] for d in dias_habiles_lista}
    
#     def centroide_dia(d):
#         if not puntos_por_dia[d]: return None
#         lats = [p['LATITUD_CLEAN'] for p in puntos_por_dia[d]]
#         lons = [p['LONGITUD_CLEAN'] for p in puntos_por_dia[d]]
#         return (sum(lats)/len(lats), sum(lons)/len(lons))

#     def afinidad_macrozona(d, zona):
#         pts = puntos_por_dia[d]
#         if not pts:
#             return 1
#         mismas = sum(1 for p in pts if int(p.get('MACROZONA', -1)) == int(zona))
#         if mismas == len(pts):
#             return 0
#         if mismas > 0:
#             return 1
#         return 2

#     visitas_programadas = []
#     df_user_sorted = df_user.sort_values(
#         by=['MACROZONA', 'CANTIDAD VISITAS', 'LATITUD_CLEAN'],
#         ascending=[True, False, False],
#     )
    
#     for idx, row in df_user_sorted.iterrows():
#         frecuencia = int(row['CANTIDAD VISITAS'])
#         lat, lon = row['LATITUD_CLEAN'], row['LONGITUD_CLEAN']
#         zona = int(row.get('MACROZONA', 0))
        
#         fechas_asignadas = []
#         for v in range(frecuencia):
#             candidatos = []
#             for d in dias_habiles_lista:
#                 if capacidades_por_dia[d] > 0:
#                     if not fechas_asignadas:
#                         candidatos.append(d)
#                     else:
#                         if all(abs((d - f).days) >= 8 for f in fechas_asignadas):
#                             candidatos.append(d)
            
#             if not candidatos and v > 0:
#                 candidatos = [d for d in dias_habiles_lista if capacidades_por_dia[d] > 0]
                
#             factibles = [d for d in candidatos if puede_agregar_a_dia(puntos_por_dia[d], row)]
#             pool = factibles if factibles else candidatos

#             mejor_dia = None
#             mejor_key = None
#             for d in pool:
#                 c = centroide_dia(d)
#                 if c is None:
#                     dist = UMBRAL_NUEVO_DIA
#                 else:
#                     dist = haversine_distance(lat, lon, c[0], c[1])
#                 if puntos_por_dia[d]:
#                     dist_punto_cercano = min(
#                         haversine_distance(
#                             lat, lon, p['LATITUD_CLEAN'], p['LONGITUD_CLEAN']
#                         ) for p in puntos_por_dia[d]
#                     )
#                 else:
#                     dist_punto_cercano = UMBRAL_NUEVO_DIA
#                 penal_limite = 0 if d in factibles else 1
#                 key = (penal_limite, dist_punto_cercano, afinidad_macrozona(d, zona), dist, d)
#                 if mejor_key is None or key < mejor_key:
#                     mejor_key = key
#                     mejor_dia = d
                    
#             if mejor_dia:
#                 fechas_asignadas.append(mejor_dia)
#                 capacidades_por_dia[mejor_dia] -= 1
#                 puntos_por_dia[mejor_dia].append(row)
#                 visitas_programadas.append({'FECHA': mejor_dia, 'DATA': row})

#     rutas_optimizadas = []
#     df_visitas = pd.DataFrame(visitas_programadas)
    
#     if df_visitas.empty: return []
    
#     dias_con_visitas = df_visitas['FECHA'].unique()
#     dias_semana_es = {0: 'LUNES', 1: 'MARTES', 2: 'MIÉRCOLES', 3: 'JUEVES', 4: 'VIERNES', 5: 'SÁBADO', 6: 'DOMINGO'}
    
#     for dia in sorted(dias_con_visitas):
#         puntos_del_dia = df_visitas[df_visitas['FECHA'] == dia]['DATA'].tolist()
#         if not puntos_del_dia: continue
        
#         visitados = ordenar_ruta_diaria(puntos_del_dia)
            
#         hora_llegada_acumulada = 0.0
        
#         for orden, p in enumerate(visitados, 1):
#             horas_visita = 0.75
#             usuario = str(p.get('USUARIO', '')).lower()
#             cadena = str(p.get('CADENA', '')).upper()
            
#             if usuario == "zona.panaleras":
#                 horas_visita = 2.0
#             elif cadena == "FARMATODO":
#                 horas_visita = 1.0
                
#             fila = p.to_dict()
#             fila['FECHA_PROGRAMADA'] = dia.strftime("%d/%m/%Y")
#             fila['DIA_SEMANA'] = dias_semana_es[dia.weekday()]
#             fila['ORDEN_VISITA'] = orden
#             fila['HORAS_VISITA'] = horas_visita
#             fila['HORA_LLEGADA_ESTIMADA (Hrs)'] = round(hora_llegada_acumulada, 2)
            
#             hora_llegada_acumulada += horas_visita + 0.25 
#             fila['JORNADA_FINAL_DIA (Hrs)'] = round(hora_llegada_acumulada - 0.25, 2)
            
#             rutas_optimizadas.append(fila)
            
#         coords_str = "/".join([f"{p['LATITUD_CLEAN']},{p['LONGITUD_CLEAN']}" for p in visitados])
#         link_maps = f"https://www.google.com/maps/dir/{coords_str}"
        
#         for r in rutas_optimizadas[-len(visitados):]:
#             r['LINK_GOOGLE_MAPS'] = link_maps
            
#     return rutas_optimizadas

def procesar_rutas_usuario(df_user, dias_habiles_lista, cap_L_V_diaria, cap_sab_diaria):
    """
    Algoritmo de Rutas Inteligentes con Aislamiento Intermunicipal Puro y Compactación Geográfica Urbana.
    """
    df_user = df_user.dropna(subset=['LATITUD_CLEAN', 'LONGITUD_CLEAN']).copy()
    if df_user.empty: return []

    # 1. Determinar el centro operativo urbano (mediana de coordenadas)
    urban_lat = df_user['LATITUD_CLEAN'].median()
    urban_lon = df_user['LONGITUD_CLEAN'].median()

    # 2. Identificar puntos remotos / intermunicipales (> 12 km del centro urbano - Regla 7)
    df_user['IS_REMOTE'] = df_user.apply(
        lambda r: haversine_distance(urban_lat, urban_lon, r['LATITUD_CLEAN'], r['LONGITUD_CLEAN']) > 12.0, 
        axis=1
    )

    df_remotos = df_user[df_user['IS_REMOTE']].copy()
    df_urbanos = df_user[~df_user['IS_REMOTE']].copy()

    dias_disponibles = sorted(dias_habiles_lista)
    dias_semana_es = {0: 'LUNES', 1: 'MARTES', 2: 'MIÉRCOLES', 3: 'JUEVES', 4: 'VIERNES', 5: 'SÁBADO', 6: 'DOMINGO'}
    
    rutas = []
    dias_ocupados = set()

    # 3. FASE 1: Agrupar Puntos Remotos en Rutas Intermunicipales PURAS (Sin mezcla urbana)
    if not df_remotos.empty:
        remotos_records = []
        for _, row in df_remotos.iterrows():
            freq = int(row['CANTIDAD VISITAS'])
            for _ in range(freq):
                remotos_records.append(row.to_dict())
        
        # Agrupar los remotos por cercanía geográfica entre ellos en bloques de hasta 8 por día
        while remotos_records and dias_disponibles:
            # Tomar el remoto más periférico como semilla
            seed = remotos_records.pop(0)
            dia_asignado = dias_disponibles.pop(0)
            dias_ocupados.add(dia_asignado)
            
            grupo_dia = [seed]
            # Buscar otros remotos cercanos (hasta completar 8 o agotar el lote)
            i = 0
            while i < len(remotos_records) and len(grupo_dia) < 8:
                cand = remotos_records[i]
                # Verificar cercanía al grupo remoto actual
                d_cercano = min(haversine_distance(cand['LATITUD_CLEAN'], cand['LONGITUD_CLEAN'], p['LATITUD_CLEAN'], p['LONGITUD_CLEAN']) for p in grupo_dia)
                if d_cercano <= 15.0: # Rango geográfico intermunicipal coherente
                    grupo_dia.append(remotos_records.pop(i))
                else:
                    i += 1
                    
            for p in grupo_dia:
                rutas.append({'FECHA': dia_asignado, 'DATA': p})

    # 4. FASE 2: Agrupamiento Geográfico Compacto para Puntos Urbanos
    if not df_urbanos.empty:
        dias_urbanos_disponibles = [d for d in dias_habiles_lista if d not in dias_ocupados]
        if not dias_urbanos_disponibles:
            dias_urbanos_disponibles = dias_habiles_lista # Fallback si faltan días

        current_df = df_urbanos.copy()
        
        while True:
            pdvs = current_df.to_dict('records')
            remaining_visits = {str(p['CODIGO PDV']): p['CANTIDAD VISITAS'] for p in pdvs}
            last_visited = {str(p['CODIGO PDV']): None for p in pdvs}
            rutas_urbanas_temp = []
            
            for dia in dias_urbanos_disponibles:
                valid_pdvs = [p for p in pdvs if remaining_visits[str(p['CODIGO PDV'])] > 0 and (last_visited[str(p['CODIGO PDV'])] is None or (dia - last_visited[str(p['CODIGO PDV'])]).days >= 7)]
                if not valid_pdvs: continue
                
                is_sab = (dia.weekday() == 5)
                cap_objetivo = 4 if is_sab else 8
                
                # Semilla urbana: punto con mayor frecuencia pendiente y alta densidad local
                max_rem = max(remaining_visits[str(p['CODIGO PDV'])] for p in valid_pdvs)
                urgents = [p for p in valid_pdvs if remaining_visits[str(p['CODIGO PDV'])] == max_rem]
                best_seed = max(urgents, key=lambda cand: sum(1 for o in valid_pdvs if haversine_distance(cand['LATITUD_CLEAN'], cand['LONGITUD_CLEAN'], o['LATITUD_CLEAN'], o['LONGITUD_CLEAN']) <= 1.5))
                
                grupo = [best_seed]
                C_lat, C_lon = best_seed['LATITUD_CLEAN'], best_seed['LONGITUD_CLEAN']
                r = 0.35 # Radio inicial 350 metros
                
                while len(grupo) < cap_objetivo:
                    cands = [p for p in valid_pdvs if str(p['CODIGO PDV']) not in {str(x['CODIGO PDV']) for x in grupo}]
                    if not cands: break
                    cands.sort(key=lambda x: haversine_distance(C_lat, C_lon, x['LATITUD_CLEAN'], x['LONGITUD_CLEAN']))
                    closest = cands[0]
                    dist = haversine_distance(C_lat, C_lon, closest['LATITUD_CLEAN'], closest['LONGITUD_CLEAN'])
                    
                    if dist <= r or len(grupo) < 3:
                        grupo.append(closest)
                        C_lat = sum(p['LATITUD_CLEAN'] for p in grupo) / len(grupo)
                        C_lon = sum(p['LONGITUD_CLEAN'] for p in grupo) / len(grupo)
                        r = max(r, dist + 0.35)
                    else:
                        break # Mantener compacidad urbana sin saltos extraños
                        
                for p in grupo:
                    cod = str(p['CODIGO PDV'])
                    rutas_urbanas_temp.append({'FECHA': dia, 'DATA': p})
                    remaining_visits[cod] -= 1
                    last_visited[cod] = dia
                    
            if sum(remaining_visits.values()) == 0:
                rutas.extend(rutas_urbanas_temp)
                break
                
            # Cascada de reducción si faltan días
            freqs_activas = sorted([f for f in current_df['CANTIDAD VISITAS'].unique() if f > 1])
            if not freqs_activas:
                rutas.extend(rutas_urbanas_temp)
                break
            target_freq = freqs_activas[0]
            mask = current_df['CANTIDAD VISITAS'] == target_freq
            current_df.loc[mask, 'CANTIDAD VISITAS'] -= 1
            current_df.loc[mask, 'FRECUENCIA_AJUSTADA'] = "SI"

    # 5. Ordenamiento de rutas diarias (TSP Nearest Neighbor) y formateo de salida
    df_visitas = pd.DataFrame(rutas)
    if df_visitas.empty: return []
    
    rutas_optimizadas = []
    for dia in sorted(df_visitas['FECHA'].unique(), key=lambda d: str(d)):
        puntos_del_dia = df_visitas[df_visitas['FECHA'] == dia]['DATA'].tolist()
        if not puntos_del_dia: continue
        
        visitados = ordenar_ruta_diaria(puntos_del_dia)
        hora_llegada_acumulada = 0.0
        
        for orden, p in enumerate(visitados, 1):
            horas_visita = 0.75
            usuario = str(p.get('USUARIO', '')).lower()
            cadena = str(p.get('CADENA', '')).upper()
            if usuario == "zona.panaleras": horas_visita = 2.0
            elif cadena == "FARMATODO": horas_visita = 1.0
                
            fila = dict(p)
            fila['FECHA_PROGRAMADA'] = dia.strftime("%d/%m/%Y")
            fila['DIA_SEMANA'] = dias_semana_es[dia.weekday()]
            fila['ORDEN_VISITA'] = orden
            fila['HORAS_VISITA'] = horas_visita
            fila['HORA_LLEGADA_ESTIMADA (Hrs)'] = round(hora_llegada_acumulada, 2)
            hora_llegada_acumulada += horas_visita + 0.25 
            fila['JORNADA_FINAL_DIA (Hrs)'] = round(hora_llegada_acumulada - 0.25, 2)
            rutas_optimizadas.append(fila)
            
        coords_str = "/".join([f"{p['LATITUD_CLEAN']},{p['LONGITUD_CLEAN']}" for p in visitados])
        link_maps = f"https://www.google.com/maps/dir/{coords_str}"
        for r in rutas_optimizadas[-len(visitados):]:
            r['LINK_GOOGLE_MAPS'] = link_maps
            
    return rutas_optimizadas

# --- LÓGICA DE MES POR DEFECTO ---
hoy = date.today()
ultimo_dia_mes = calendar.monthrange(hoy.year, hoy.month)[1]
dias_restantes = ultimo_dia_mes - hoy.day

if dias_restantes <= 7:
    mes_default_num = 1 if hoy.month == 12 else hoy.month + 1
    year_default = hoy.year + 1 if hoy.month == 12 else hoy.year
else:
    mes_default_num = hoy.month
    year_default = hoy.year

# --- INTERFAZ: BARRA LATERAL ---
with st.sidebar:
    st.header("1. Configuración de Fechas")
    col1, col2 = st.columns(2)
    
    anios_disponibles = [hoy.year, hoy.year + 1, hoy.year + 2]
    idx_year = anios_disponibles.index(year_default) if year_default in anios_disponibles else 0
    year = col1.selectbox("Año", anios_disponibles, index=idx_year)
    
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_str = col2.selectbox("Mes", meses, index=mes_default_num - 1)
    mes_num = meses.index(mes_str) + 1
    
    sabados_del_mes = [date(year, mes_num, day).strftime("%Y-%m-%d") 
                       for day in range(1, calendar.monthrange(year, mes_num)[1] + 1) 
                       if date(year, mes_num, day).weekday() == 5]
    
    sabados_laborales = st.multiselect("Selecciona los Sábados Laborales:", sabados_del_mes)
    
    st.divider()
    st.header("2. Carga de Archivos")
    file_panel = st.file_uploader("Sube el Panel del Mes (.xlsx)", type=["xlsx"])
    file_maestro = st.file_uploader("Sube el Maestro de Coordenadas (.xlsx)", type=["xlsx"])
    
    st.divider()
    if st.button("📊 Generar Resumen del Panel", type="primary", use_container_width=True):
        if file_panel is None or file_maestro is None:
            st.error("⚠️ Debes cargar ambos archivos antes de ejecutar.")
        else:
            st.session_state.mostrar_resumen = True
            st.session_state.rutas_generadas = False
            st.session_state.coords_guardadas = False
            st.session_state.pop("df_merged_raw", None)
            st.session_state.pop("df_maestro_original", None)
            st.session_state.pop("df_maestro_actualizado", None)
            st.session_state.pop("coords_save_info", None)
            limpiar_claves_editor_coords()

# --- LÓGICA PRINCIPAL ETAPA 1 (Resumen) ---
if st.session_state.mostrar_resumen and file_panel and file_maestro:
    
    if 'df_merged_raw' not in st.session_state:
        with st.spinner(f"Procesando y validando datos para {mes_str} {year}..."):
            df_panel = pd.read_excel(file_panel)
            df_maestro = pd.read_excel(file_maestro)
            st.session_state.df_maestro_original = df_maestro.copy()
                
            campos_obligatorios = ['CODIGO PDV', 'CANTIDAD VISITAS', 'USUARIO']
            if not all(col in df_panel.columns for col in campos_obligatorios):
                st.error(f"Faltan columnas obligatorias en el Panel. Se requiere: {campos_obligatorios}")
                st.stop()
                
            if 'FRECUENCIA_AJUSTADA' not in df_panel.columns:
                df_panel['FRECUENCIA_AJUSTADA'] = ""
                
            df_panel['CANTIDAD VISITAS'] = pd.to_numeric(df_panel['CANTIDAD VISITAS'], errors='coerce').fillna(1).astype(int)

            if 'LATITUD' in df_maestro.columns and 'LONGITUD' in df_maestro.columns:
                cols_maestro = ['CODIGO PDV', 'LATITUD', 'LONGITUD']
                for extra in ['DIRECCION', 'CIUDAD', 'NOMBRE COMERCIAL', 'DIR_NORM']:
                    if extra in df_maestro.columns and extra not in cols_maestro:
                        cols_maestro.append(extra)
                df_maestro_coord = df_maestro[cols_maestro].drop_duplicates(subset=['CODIGO PDV'])
                df_merged = df_panel.merge(df_maestro_coord, on='CODIGO PDV', how='left', suffixes=('', '_MAESTRO'))
            else:
                st.error("El Maestro de coordenadas no tiene las columnas LATITUD y LONGITUD.")
                st.stop()

            for col_base in ['DIRECCION', 'CIUDAD', 'NOMBRE COMERCIAL']:
                col_m = f"{col_base}_MAESTRO"
                if col_m in df_merged.columns:
                    if col_base not in df_merged.columns:
                        df_merged[col_base] = df_merged[col_m]
                    else:
                        df_merged[col_base] = df_merged[col_base].where(
                            df_merged[col_base].notna() & (df_merged[col_base].astype(str).str.strip() != ""),
                            df_merged[col_m]
                        )
                elif col_base not in df_merged.columns:
                    df_merged[col_base] = ""

            if 'DIR_NORM' in df_merged.columns:
                dir_vacia = df_merged['DIRECCION'].isna() | (df_merged['DIRECCION'].astype(str).str.strip() == "")
                df_merged.loc[dir_vacia, 'DIRECCION'] = df_merged.loc[dir_vacia, 'DIR_NORM']

            df_merged['LATITUD_CLEAN'] = limpiar_coordenadas(df_merged['LATITUD'])
            df_merged['LONGITUD_CLEAN'] = limpiar_coordenadas(df_merged['LONGITUD'])
            df_merged['Sin_Coordenadas'] = df_merged['LATITUD_CLEAN'].isnull() | df_merged['LONGITUD_CLEAN'].isnull()
            
            st.session_state.df_merged_raw = df_merged
            st.session_state.coords_guardadas = not bool(df_merged['Sin_Coordenadas'].any())

    df_merged = st.session_state.df_merged_raw.copy()
    
    dias_L_V, festivos, visitas_maximas, dias_habiles_lista = calcular_dias_habiles(year, mes_num, sabados_laborales)

    st.subheader(f"🗓️ Calendario: {mes_str} {year}")
    st.markdown(generar_calendario_html(year, mes_num, sabados_laborales), unsafe_allow_html=True)
    
    st.subheader("⏱️ Métricas de Tiempo Base")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Días Laborales (L-V)", dias_L_V)
    c2.metric("Sábados Laborales", len(sabados_laborales))
    c3.metric("Total Días Trabajo", dias_L_V + len(sabados_laborales))
    c4.metric("Máx Visitas (Ideal)", visitas_maximas)

    st.subheader("👥 Resumen por Usuario (Carga de Trabajo)")
    
    resumen_usuarios = df_merged.groupby('USUARIO').agg(
        Total_PDV=('CODIGO PDV', 'nunique'),
        Total_Visitas_Mes=('CANTIDAD VISITAS', 'sum'),
        Faltan_Coordenadas=('Sin_Coordenadas', 'sum')
    ).reset_index()
    
    def highlight_max(row):
        if row['Total_Visitas_Mes'] > visitas_maximas:
            return ['background-color: #ffcccc; color: black'] * len(row)
        return [''] * len(row)

    st.write(f"**Total General:** {resumen_usuarios['Total_PDV'].sum()} PDVs | {resumen_usuarios['Total_Visitas_Mes'].sum()} Visitas en el mes.")
    st.dataframe(resumen_usuarios.style.apply(highlight_max, axis=1), use_container_width=True)
    
    usuarios_sobrecargados = resumen_usuarios[resumen_usuarios['Total_Visitas_Mes'] > visitas_maximas]['USUARIO'].tolist()
    if usuarios_sobrecargados:
        st.error(f"⚠️ **Atención:** Los siguientes usuarios superan la capacidad máxima ideal de {visitas_maximas} visitas al mes: **{', '.join(usuarios_sobrecargados)}**.")

    st.divider()

    df_sin_coord = df_merged[df_merged['Sin_Coordenadas']].copy()
    n_faltantes = len(df_sin_coord)

    if n_faltantes > 0 and not st.session_state.coords_guardadas:
        st.subheader("📍 Completar coordenadas faltantes")
        st.warning(
            f"Se encontraron **{n_faltantes}** droguerías sin coordenadas. "
            "Corrige la dirección y/o la ciudad, pulsa **Generar** para consultar Google Maps, "
            "o ingresa latitud y longitud a mano. Luego pulsa **Guardar coordenadas** para continuar a las etapas 2 y 3."
        )

        def _on_generar_coord(idx_fila):
            direccion = st.session_state.get(f"falt_dir_{idx_fila}", "")
            ciudad = st.session_state.get(f"falt_ciu_{idx_fila}", "")
            lat, lon, status, err = geocodificar_google(direccion, ciudad, GOOGLE_MAPS_API_KEY)
            if lat is not None:
                st.session_state[f"falt_lat_{idx_fila}"] = str(lat)
                st.session_state[f"falt_lon_{idx_fila}"] = str(lon)
                st.session_state[f"falt_msg_{idx_fila}"] = f"✅ Dirección encontrada ({status}). Lat: {lat} | Lon: {lon}"
                st.session_state[f"falt_ok_{idx_fila}"] = True
            else:
                detalle = f" — {err}" if err else ""
                if status == "ZERO_RESULTS":
                    texto = "⚠️ Dirección no encontrada en Google Maps. Ajusta dirección/ciudad y vuelve a generar, o ingresa las coordenadas manualmente."
                elif status == "SIN_DIRECCION":
                    texto = "⚠️ Escribe una dirección antes de generar."
                elif status == "REQUEST_DENIED":
                    texto = "❌ Google rechazó la petición (API Key, facturación o Geocoding API)."
                else:
                    texto = f"⚠️ No se obtuvieron coordenadas (estado: {status}).{detalle}"
                st.session_state[f"falt_msg_{idx_fila}"] = texto
                st.session_state[f"falt_ok_{idx_fila}"] = False

        def _marcar_coord_manual(idx_fila):
            st.session_state[f"falt_ok_{idx_fila}"] = False

        for idx, row in df_sin_coord.iterrows():
            nombre = row.get("NOMBRE COMERCIAL", "")
            if pd.isna(nombre) or str(nombre).strip() == "":
                nombre = f"PDV {row.get('CODIGO PDV', idx)}"
            usuario = row.get("USUARIO", "")
            dir_orig = "" if pd.isna(row.get("DIRECCION")) else str(row.get("DIRECCION"))
            ciu_orig = "" if pd.isna(row.get("CIUDAD")) else str(row.get("CIUDAD"))
            lat_orig = row.get("LATITUD_CLEAN")
            lon_orig = row.get("LONGITUD_CLEAN")

            if f"falt_dir_{idx}" not in st.session_state:
                st.session_state[f"falt_dir_{idx}"] = dir_orig
            if f"falt_ciu_{idx}" not in st.session_state:
                st.session_state[f"falt_ciu_{idx}"] = ciu_orig
            if f"falt_lat_{idx}" not in st.session_state:
                st.session_state[f"falt_lat_{idx}"] = "" if pd.isna(lat_orig) else str(lat_orig)
            if f"falt_lon_{idx}" not in st.session_state:
                st.session_state[f"falt_lon_{idx}"] = "" if pd.isna(lon_orig) else str(lon_orig)

            with st.container(border=True):
                c_nom, c_usr, c_cod = st.columns([2.2, 1.4, 1])
                c_nom.markdown(f"**Droguería:** {nombre}")
                c_usr.markdown(f"**Usuario:** {usuario}")
                c_cod.markdown(f"**Código PDV:** {row.get('CODIGO PDV', '')}")

                c_dir, c_ciu = st.columns([2, 1])
                c_dir.text_input("Dirección", key=f"falt_dir_{idx}")
                c_ciu.text_input("Ciudad", key=f"falt_ciu_{idx}")

                c_lat, c_lon, c_btn = st.columns([1.2, 1.2, 1])
                c_lat.text_input(
                    "Latitud", key=f"falt_lat_{idx}", placeholder="Ej: 4.6097",
                    on_change=_marcar_coord_manual, args=(idx,)
                )
                c_lon.text_input(
                    "Longitud", key=f"falt_lon_{idx}", placeholder="Ej: -74.0817",
                    on_change=_marcar_coord_manual, args=(idx,)
                )
                c_btn.markdown("<br>", unsafe_allow_html=True)
                c_btn.button(
                    "Generar",
                    key=f"falt_gen_{idx}",
                    help="Consulta Google Maps con la dirección y ciudad actuales",
                    on_click=_on_generar_coord,
                    args=(idx,),
                    use_container_width=True,
                )

                msg = st.session_state.get(f"falt_msg_{idx}")
                if msg:
                    if st.session_state.get(f"falt_ok_{idx}"):
                        st.success(msg)
                    else:
                        st.warning(msg)

        if st.button("💾 Actualizar maestro de coordenadas", type="primary", use_container_width=True):
            df_upd = st.session_state.df_merged_raw.copy()
            if "df_maestro_original" not in st.session_state:
                st.session_state.df_maestro_original = pd.read_excel(file_maestro)
            pendientes_vacios = 0
            actualizados = 0
            actualizaciones_maestro = {}
            for idx in df_sin_coord.index:
                lat_val = pd.to_numeric(st.session_state.get(f"falt_lat_{idx}", ""), errors="coerce")
                lon_val = pd.to_numeric(st.session_state.get(f"falt_lon_{idx}", ""), errors="coerce")
                dir_val = st.session_state.get(f"falt_dir_{idx}", df_upd.at[idx, "DIRECCION"])
                ciu_val = st.session_state.get(f"falt_ciu_{idx}", df_upd.at[idx, "CIUDAD"])
                df_upd.at[idx, "DIRECCION"] = dir_val
                df_upd.at[idx, "CIUDAD"] = ciu_val
                if pd.notna(lat_val) and pd.notna(lon_val):
                    df_upd.at[idx, "LATITUD"] = lat_val
                    df_upd.at[idx, "LONGITUD"] = lon_val
                    df_upd.at[idx, "LATITUD_CLEAN"] = lat_val
                    df_upd.at[idx, "LONGITUD_CLEAN"] = lon_val
                    origen = "API Google Maps" if st.session_state.get(f"falt_ok_{idx}", False) else "Manual"
                    actualizaciones_maestro[idx] = (
                        df_upd.at[idx, "CODIGO PDV"], lat_val, lon_val, origen
                    )
                    actualizados += 1
                else:
                    pendientes_vacios += 1

            df_upd["Sin_Coordenadas"] = df_upd["LATITUD_CLEAN"].isnull() | df_upd["LONGITUD_CLEAN"].isnull()
            st.session_state.df_maestro_actualizado = actualizar_maestro_coordenadas(
                st.session_state.df_maestro_original,
                df_upd,
                actualizaciones_maestro,
            )
            st.session_state.df_merged_raw = df_upd
            st.session_state.coords_guardadas = True
            st.session_state.coords_save_info = (actualizados, pendientes_vacios)
            st.rerun()

        st.stop()

    if st.session_state.get("df_maestro_actualizado") is not None:
        maestro_output = io.BytesIO()
        with pd.ExcelWriter(maestro_output, engine='openpyxl') as writer:
            st.session_state.df_maestro_actualizado.to_excel(
                writer, index=False, sheet_name='Maestro_Actualizado'
            )
        st.download_button(
            label="📥 Descargar maestro de coordenadas actualizado",
            data=maestro_output.getvalue(),
            file_name="MAESTRO_COORDENADAS_ACTUALIZADO.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
        )

    if st.session_state.get("coords_save_info"):
        actualizados, pendientes_vacios = st.session_state.coords_save_info
        if pendientes_vacios:
            st.warning(
                f"Se guardaron **{actualizados}** coordenadas. "
                f"**{pendientes_vacios}** PDVs siguen sin lat/lon y se excluirán al generar rutas."
            )
            if st.button("✏️ Seguir completando coordenadas"):
                st.session_state.coords_guardadas = False
                st.rerun()
        elif actualizados:
            st.success(f"✅ Coordenadas guardadas ({actualizados} PDVs). Ya puedes generar las rutas inteligentes.")

    st.subheader("🚀 Etapa 2 y 3: Generación y Optimización de Rutas")
    st.write("Presiona el botón para distribuir equitativamente las visitas y optimizar el recorrido.")
    
    if st.button("Generar Programación de Rutas Inteligentes", type="primary", icon="🎯"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        usuarios = df_merged['USUARIO'].dropna().unique()
        todas_las_rutas = []
        
        for i, usr in enumerate(usuarios):
            status_text.text(f"Procesando usuario {i+1} de {len(usuarios)}: {usr}...")
            df_usr = df_merged[df_merged['USUARIO'] == usr].copy()
            
            df_usr_ajustado, cap_lv, cap_sab, supera = ajustar_frecuencias_y_capacidades(df_usr, dias_L_V, len(sabados_laborales))
            rutas_usr = procesar_rutas_usuario(df_usr_ajustado, dias_habiles_lista, cap_lv, cap_sab)
            todas_las_rutas.extend(rutas_usr)
            
            progress_bar.progress((i + 1) / len(usuarios))
            
        status_text.text("¡Procesamiento finalizado! Preparando archivo Excel...")
        
        if todas_las_rutas:
            df_final = pd.DataFrame(todas_las_rutas)
            
            columnas_salida = [
                'REGIONAL', 'USUARIO', 'FECHA_PROGRAMADA', 'DIA_SEMANA', 'ORDEN_VISITA', 'CODIGO PDV', 
                'NOMBRE COMERCIAL', 'DIRECCION', 'ACTIVIDAD', 'CANTIDAD VISITAS', 'HORAS_VISITA', 
                'HORA_LLEGADA_ESTIMADA (Hrs)', 'JORNADA_FINAL_DIA (Hrs)', 'CLIENTE', 'CIUDAD', 
                'CANAL', 'CADENA', 'SUBCADENA', 'ZONA', 'RV', 'CODIGO EAN', 'TIPO PUNTO VENTA', 
                'VENDEDOR', 'CODIGO BRICK', 'CODIGO OPCIONAL 1', 'CODIGO OPCIONAL 2', 'ID PDV', 
                'COD COPIDROGAS', 'TELEFONO', 'FECHA ACTIVACION USUARIO PDC', 'FECHA INACTIVACION USUARIO PDC', 
                'ESTADO USUARIO PDC', 'PROGRAMADO', 'VISITADO', 'CEDULA USUARIO', 'NOMBRE USUARIO', 
                'NOMBRE SUPERVISOR', 'USUARIO SUPERVISOR', 'LATITUD', 'LONGITUD', 'ACTIVIDAD_LIMPIA', 
                'FRECUENCIA_AJUSTADA', 'LINK_GOOGLE_MAPS'
            ]
            
            for col in columnas_salida:
                if col not in df_final.columns:
                    df_final[col] = ""
                    
            df_final = df_final[columnas_salida]
            
            st.session_state.df_rutas = df_final
            st.session_state.rutas_generadas = True
            status_text.empty()
            progress_bar.empty()
            st.success("✅ ¡Rutas programadas con éxito!")
        else:
            st.error("No se generaron rutas (revisa que los PDVs tengan coordenadas válidas).")

    if st.session_state.rutas_generadas and st.session_state.df_rutas is not None:
        st.markdown("### 📥 Descargar Resultados")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.df_rutas.to_excel(writer, index=False, sheet_name='Programacion_Rutas')
        excel_data = output.getvalue()
        
        st.download_button(
            label="Descargar Programación de Rutas (.xlsx)",
            data=excel_data,
            file_name=f"Programacion_Rutas_{mes_str}_{year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        st.dataframe(st.session_state.df_rutas.head(15), use_container_width=True)

        st.divider()
        st.markdown("### 🗺️ Visualizador de Rutas en Mapa")
        st.write("Selecciona un usuario y un día para ver el recorrido detallado, o selecciona 'Todos' para ver la cobertura completa del mes.")
        
        df_rutas_mapa = st.session_state.df_rutas.copy()
        usuarios_list = df_rutas_mapa['USUARIO'].dropna().unique().tolist()
        
        if usuarios_list:
            col_usr, col_dia, col_btn = st.columns([2, 2, 1])
            
            with col_usr:
                user_sel = st.selectbox("👤 Seleccionar Usuario", usuarios_list)
            
            with col_dia:
                dias_list = ["Todos"] + df_rutas_mapa[df_rutas_mapa['USUARIO'] == user_sel]['FECHA_PROGRAMADA'].dropna().unique().tolist()
                dia_sel = st.selectbox("📅 Seleccionar Día", dias_list)
                
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                ver_mapa = st.button("🗺️ Ver Mapa", type="primary", use_container_width=True)
                
            if ver_mapa:
                df_user_map = df_rutas_mapa[df_rutas_mapa['USUARIO'] == user_sel].copy()
                
                df_user_map['LAT_NUM'] = df_user_map['LATITUD'].astype(str).str.replace(',', '.').astype(float, errors='ignore')
                df_user_map['LON_NUM'] = df_user_map['LONGITUD'].astype(str).str.replace(',', '.').astype(float, errors='ignore')
                df_user_map['LAT_NUM'] = pd.to_numeric(df_user_map['LAT_NUM'], errors='coerce')
                df_user_map['LON_NUM'] = pd.to_numeric(df_user_map['LON_NUM'], errors='coerce')
                
                df_user_map = df_user_map.dropna(subset=['LAT_NUM', 'LON_NUM'])
                
                if not df_user_map.empty:
                    centro_lat = df_user_map['LAT_NUM'].mean()
                    centro_lon = df_user_map['LON_NUM'].mean()
                    
                    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12, tiles="CartoDB positron")
                    colores = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9']
                    
                    if dia_sel == "Todos":
                        dias_unicos = df_user_map['FECHA_PROGRAMADA'].unique()
                        for idx, dia in enumerate(dias_unicos):
                            color_dia = colores[idx % len(colores)]
                            df_dia = df_user_map[df_user_map['FECHA_PROGRAMADA'] == dia].sort_values(by='ORDEN_VISITA')
                            coords = df_dia[['LAT_NUM', 'LON_NUM']].values.tolist()
                            
                            folium.PolyLine(
                                coords, 
                                color=color_dia, 
                                weight=2.5, 
                                opacity=0.7, 
                                tooltip=f"Día: {dia}"
                            ).add_to(m)
                            
                            for _, row in df_dia.iterrows():
                                html_popup = f"<b>Día:</b> {row['FECHA_PROGRAMADA']}<br><b>Orden:</b> {row['ORDEN_VISITA']}<br><b>PDV:</b> {row['NOMBRE COMERCIAL']}"
                                folium.CircleMarker(
                                    location=[row['LAT_NUM'], row['LON_NUM']],
                                    radius=4,
                                    popup=folium.Popup(html_popup, max_width=300),
                                    color=color_dia,
                                    fill=True,
                                    fill_color=color_dia,
                                    fill_opacity=0.9
                                ).add_to(m)
                    else:
                        df_dia = df_user_map[df_user_map['FECHA_PROGRAMADA'] == dia_sel].sort_values(by='ORDEN_VISITA')
                        coords = df_dia[['LAT_NUM', 'LON_NUM']].values.tolist()
                        
                        folium.PolyLine(coords, color='blue', weight=3, opacity=0.8).add_to(m)
                        
                        for _, row in df_dia.iterrows():
                            orden = int(row['ORDEN_VISITA'])
                            html_popup = f"""
                                <b>Orden:</b> {orden}<br>
                                <b>Cod PDV:</b> {row['CODIGO PDV']}<br>
                                <b>Nombre:</b> {row['NOMBRE COMERCIAL']}<br>
                                <b>Llegada Estimada:</b> {row['HORA_LLEGADA_ESTIMADA (Hrs)']} Hrs
                            """
                            
                            icono_numero = folium.DivIcon(
                                html=f"""
                                    <div style="font-family: Arial; font-size: 11pt; font-weight: bold; color: white; background-color: #007BFF; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 2px 2px 4px rgba(0,0,0,0.5);">
                                        {orden}
                                    </div>
                                """
                            )
                            
                            folium.Marker(
                                location=[row['LAT_NUM'], row['LON_NUM']],
                                popup=folium.Popup(html_popup, max_width=300),
                                tooltip=f"Visita {orden}: {row['NOMBRE COMERCIAL']}",
                                icon=icono_numero
                            ).add_to(m)
                            
                    with st.container():
                        components.html(m._repr_html_(), height=600)
                else:
                    st.warning("⚠️ No se encontraron coordenadas válidas para dibujar el mapa de este usuario.")

        
elif not st.session_state.mostrar_resumen:
    st.info("👈 Configura los parámetros en el panel izquierdo y haz clic en **Generar Resumen** para comenzar.")