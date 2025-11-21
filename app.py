import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Faltantes App", page_icon="📝", layout="wide")

# --- ARCHIVOS EN GITHUB ---
# Asegúrate de que los nombres coincidan exactamente (mayúsculas/minúsculas)
FILE_CLIENTES = 'clientes.csv'
FILE_PRODUCTOS = 'productos.csv' # Este es tu LISTASUSTANCIAS.csv renombrado
FILE_PLANTILLA = 'plantilla.xlsx'

# --- ESTADO DE LA APP ---
if 'pedidos' not in st.session_state:
    st.session_state.pedidos = []
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    errores = []
    df_cli = pd.DataFrame()
    df_prod = pd.DataFrame()
    
    # 1. CARGAR CLIENTES
    try:
        # Intenta leer con diferentes codificaciones por seguridad
        try:
            df_cli = pd.read_csv(FILE_CLIENTES, encoding='latin-1')
        except:
            df_cli = pd.read_csv(FILE_CLIENTES, encoding='utf-8')
            
        # Normalizar columnas
        df_cli.columns = df_cli.columns.str.strip().str.upper()
        
        # Detectar columnas automáticamente (por si cambian el nombre)
        col_clave = next((c for c in df_cli.columns if 'CLAVE' in c or 'CODIGO' in c), df_cli.columns[0])
        col_nombre = next((c for c in df_cli.columns if 'CLIENTE' in c or 'NOMBRE' in c), df_cli.columns[1])
        
        df_cli = df_cli[[col_clave, col_nombre]].copy()
        df_cli.columns = ['CODIGO', 'NOMBRE']
        
        # Crear campo para el desplegable
        df_cli['DISPLAY'] = df_cli['CODIGO'].astype(str) + " - " + df_cli['NOMBRE']
        
    except Exception as e:
        errores.append(f"⚠️ Error leyendo Clientes: {e}")

    # 2. CARGAR PRODUCTOS (Tu archivo de Sustancias)
    try:
        try:
            df_prod = pd.read_csv(FILE_PRODUCTOS, encoding='latin-1')
        except:
            df_prod = pd.read_csv(FILE_PRODUCTOS, encoding='utf-8')
            
        df_prod.columns = df_prod.columns.str.strip().str.upper()
        
        # Mapeo exacto de tus columnas: CLAVE, NOMBRE, SUSTANCIA ACTIVA
        # Ajustamos para ser tolerantes a pequeños cambios
        col_clave = next(c for c in df_prod.columns if 'CLAVE' in c or 'CODIGO' in c)
        col_desc = next(c for c in df_prod.columns if 'NOMBRE' in c or 'DESCRIPCION' in c)
        col_sust = next(c for c in df_prod.columns if 'SUSTANCIA' in c)
        
        df_prod = df_prod[[col_clave, col_desc, col_sust]].copy()
        df_prod.columns = ['CODIGO', 'DESCRIPCION', 'SUSTANCIA']
        df_prod['SUSTANCIA'] = df_prod['SUSTANCIA'].fillna('---')

        # CREAR INDICE DE BÚSQUEDA
        # Unimos todo el texto para que el buscador encuentre cualquier coincidencia
        df_prod['SEARCH_INDEX'] = (
            df_prod['CODIGO'].astype(str) + " | " + 
            df_prod['DESCRIPCION'].astype(str) + " | " + 
            df_prod['SUSTANCIA'].astype(str)
        ).str.upper()
        
    except Exception as e:
        errores.append(f"⚠️ Error leyendo Productos: {e}")

    return df_cli, df_prod, errores

# Ejecutar carga
df_clientes, df_productos, logs = cargar_datos()

# --- INTERFAZ VISUAL ---
st.title("📝 Registro de Faltantes")

if logs:
    for l in logs: st.error(l)
    st.stop()

# Sidebar con info y reset
with st.sidebar:
    st.info(f"Catálogo cargado: {len(df_productos)} productos")
    if st.button("🗑️ Reiniciar Pedido Actual"):
        st.session_state.carrito = []
        st.rerun()

# Pestañas principales
tab1, tab2 = st.tabs(["1. Registrar Faltantes", "2. Descargar Excel"])

# === PESTAÑA 1: REGISTRO ===
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Datos del Pedido")
        
        # A. SELECCIÓN DE CLIENTE
        cliente_input = st.selectbox(
            "Cliente:", 
            options=df_clientes['DISPLAY'], 
            index=None, 
            placeholder="Escribe para buscar cliente..."
        )
        fecha_input = st.date_input("Fecha:", datetime.today())
        
        st.divider()
        st.subheader("Agregar Producto")
        
        # B. BÚSQUEDA INTELIGENTE
        query = st.text_input("Buscar:", placeholder="Ej: Paracetamol, S020...").upper()
        
        opciones_filtradas = []
        if query:
            # Filtramos el dataframe basado en lo que escribiste
            mask = df_productos['SEARCH_INDEX'].str.contains(query, na=False)
            # Mostramos los primeros 50 resultados para que sea rápido elegir
            opciones_filtradas = df_productos[mask]['SEARCH_INDEX'].head(50).tolist()
        
        # C. DESPLEGABLE DE SELECCIÓN (Eliges la presentación exacta aquí)
        producto_seleccionado_str = st.selectbox(
            "Selecciona Presentación:", 
            options=opciones_filtradas, 
            placeholder="Elige de la lista filtrada..."
        )
        
        cantidad = st.number_input("Cantidad:", min_value=1, value=1)
        
        # BOTÓN AGREGAR
        if st.button("➕ Agregar a la Lista", use_container_width=True):
            if cliente_input and producto_seleccionado_str:
                # Recuperamos los datos limpios del producto elegido
                row = df_productos[df_productos['SEARCH_INDEX'] == producto_seleccionado_str].iloc[0]
                
                item = {
                    "CODIGO": row['CODIGO'],
                    "DESCRIPCION": row['DESCRIPCION'],
                    "SOLICITADA
