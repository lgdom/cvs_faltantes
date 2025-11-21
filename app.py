import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Faltantes App", page_icon="📝", layout="wide")

# --- ARCHIVOS EN GITHUB ---
FILE_CLIENTES = 'clientes.csv'
FILE_PRODUCTOS = 'productos.csv'
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
        try:
            df_cli = pd.read_csv(FILE_CLIENTES, encoding='latin-1')
        except:
            df_cli = pd.read_csv(FILE_CLIENTES, encoding='utf-8')
            
        df_cli.columns = df_cli.columns.str.strip().str.upper()
        
        # --- CORRECCIÓN AQUÍ ---
        # 1. Primero buscamos la columna del CÓDIGO (buscando "CLAVE" o "CODIGO")
        col_clave = next((c for c in df_cli.columns if 'CLAVE' in c or 'CODIGO' in c), df_cli.columns[0])
        
        # 2. Luego buscamos la columna del NOMBRE, pero EXCLUYENDO la que ya detectamos como clave
        col_nombre = next((c for c in df_cli.columns if ('CLIENTE' in c or 'NOMBRE' in c) and c != col_clave), df_cli.columns[1])
        # -----------------------
        
        df_cli = df_cli[[col_clave, col_nombre]].copy()
        df_cli.columns = ['CODIGO', 'NOMBRE']
        
        # Convertimos a texto para evitar errores de suma y mostramos "CÓDIGO - NOMBRE"
        df_cli['DISPLAY'] = df_cli['CODIGO'].astype(str) + " - " + df_cli['NOMBRE'].astype(str)
        
    except Exception as e:
        errores.append(f"⚠️ Error leyendo Clientes: {e}")


    # 2. CARGAR PRODUCTOS
    try:
        try:
            df_prod = pd.read_csv(FILE_PRODUCTOS, encoding='latin-1')
        except:
            df_prod = pd.read_csv(FILE_PRODUCTOS, encoding='utf-8')
            
        df_prod.columns = df_prod.columns.str.strip().str.upper()
        col_clave = next(c for c in df_prod.columns if 'CLAVE' in c or 'CODIGO' in c)
        col_desc = next(c for c in df_prod.columns if 'NOMBRE' in c or 'DESCRIPCION' in c)
        col_sust = next(c for c in df_prod.columns if 'SUSTANCIA' in c)
        
        df_prod = df_prod[[col_clave, col_desc, col_sust]].copy()
        df_prod.columns = ['CODIGO', 'DESCRIPCION', 'SUSTANCIA']
        df_prod['SUSTANCIA'] = df_prod['SUSTANCIA'].fillna('---')

        df_prod['SEARCH_INDEX'] = (
            df_prod['CODIGO'].astype(str) + " | " + 
            df_prod['DESCRIPCION'].astype(str) + " | " + 
            df_prod['SUSTANCIA'].astype(str)
        ).str.upper()
        
    except Exception as e:
        errores.append(f"⚠️ Error leyendo Productos: {e}")

    return df_cli, df_prod, errores

df_clientes, df_productos, logs = cargar_datos()

# --- INTERFAZ VISUAL ---
st.title("📝 Registro de Faltantes")

if logs:
    for l in logs: st.error(l)
    st.stop()

with st.sidebar:
    st.info(f"Catálogo cargado: {len(df_productos)} productos")
    if st.button("🗑️ Reiniciar Pedido Actual"):
        st.session_state.carrito = []
        st.rerun()

tab1, tab2 = st.tabs(["1. Registrar Faltantes", "2. Descargar Excel"])

# === PESTAÑA 1: REGISTRO ===
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Datos del Pedido")
        cliente_input = st.selectbox("Cliente:", options=df_clientes['DISPLAY'], index=None, placeholder="Escribe para buscar cliente...")
        fecha_input = st.date_input("Fecha:", datetime.today())
        
        st.divider()
        st.subheader("Agregar Producto")
        
        query = st.text_input("Buscar:", placeholder="Ej: Paracetamol, S020...").upper()
        opciones_filtradas = []
        if query:
            mask = df_productos['SEARCH_INDEX'].str.contains(query, na=False)
            opciones_filtradas = df_productos[mask]['SEARCH_INDEX'].head(50).tolist()
        
        producto_seleccionado_str = st.selectbox("Selecciona Presentación:", options=opciones_filtradas, placeholder="Elige de la lista filtrada...")
        cantidad = st.number_input("Cantidad:", min_value=1, value=1)
        
        if st.button("➕ Agregar a la Lista", use_container_width=True):
            if cliente_input and producto_seleccionado_str:
                row = df_productos[df_productos['SEARCH_INDEX'] == producto_seleccionado_str].iloc[0]
                item = {
                    "CODIGO": row['CODIGO'],
                    "DESCRIPCION": row['DESCRIPCION'],
                    "SOLICITADA": cantidad,
                    "SURTIDO": 0,
                    "O.C.": "N/A"
                }
                st.session_state.carrito.append(item)
                st.success("Agregado")
            else:
                st.warning("⚠️ Selecciona Cliente y Producto primero")

    with col2:
        st.subheader("🛒 Lista Preliminar")
        if st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            
            # --- AQUÍ ESTABA EL ERROR, ESTA ES LA VERSIÓN CORREGIDA ---
            df_edited = st.data_editor(
                df_cart,
                column_config={
                    "SOLICITADA": st.column_config.NumberColumn("Solicitada", width="small"),
                    "SURTIDO": st.column_config.NumberColumn("Surtido", width="small"),
                    "O.C.": st.column_config.TextColumn("O.C.", width="small")
                },
                use_container_width=True,
                num_rows="dynamic"
            )
            # ----------------------------------------------------------
            
            if st.button("💾 GUARDAR ESTE PEDIDO (Siguiente Hoja)", type="primary", use_container_width=True):
                if cliente_input:
                    cod_cli, nom_cli = cliente_input.split(" - ", 1)
                    pedido_nuevo = {
                        "cli_cod": cod_cli,
                        "cli_nom": nom_cli,
                        "fecha": fecha_input,
                        "items": df_edited
                    }
                    st.session_state.pedidos.append(pedido_nuevo)
                    st.session_state.carrito = []
                    st.rerun()
                    st.balloons()
                else:
                    st.error("Falta seleccionar cliente")
        else:
            st.info("👈 Usa el panel izquierdo para buscar productos.")

# === PESTAÑA 2: DESCARGA ===
with tab2:
    st.subheader(f"📦 Pedidos listos para procesar: {len(st.session_state.pedidos)}")
    for i, p in enumerate(st.session_state.pedidos):
        with st.expander(f"Hoja {i+1}: {p['cli_nom']} ({len(p['items'])} prods)"):
            st.dataframe(p['items'])
            if st.button("Eliminar Hoja", key=f"del_{i}"):
                st.session_state.pedidos.pop(i)
                st.rerun()

    st.divider()
    nombre_archivo = st.text_input("Nombre del archivo:", value="Reporte_Faltantes.xlsx")
    
    if st.button("🚀 GENERAR EXCEL FINAL", disabled=(len(st.session_state.pedidos)==0)):
        try:
            wb = openpyxl.load_workbook(FILE_PLANTILLA)
            hoja_base = wb.active
            hoja_base.title = "Base"
            
            conteo_hojas = {}
            for pedido in st.session_state.pedidos:
                cod = pedido['cli_cod']
                conteo_hojas[cod] = conteo_hojas.get(cod, 0) + 1
                nombre_hoja = cod if conteo_hojas[cod] == 1 else f"{cod}-{conteo_hojas[cod]}"
                
                ws = wb.copy_worksheet(hoja_base)
                ws.title = nombre_hoja
                
                ws['B2'] = "SUC. TIJ"
                ws['B3'] = "LUIS FELIPE GARCÍA DOMÍNGUEZ"
                ws['B4'] = pedido['cli_nom']
                try:
                    ws['B6'] = int(cod)
                except:
                    ws['B6'] = cod
                ws['D6'] = pedido['fecha'].strftime('%d/%m/%Y')
                
                fila_inicial = 10
                datos = pedido['items'][['CODIGO', 'DESCRIPCION', 'SOLICITADA', 'SURTIDO', 'O.C.']].values.tolist()
                for idx, fila in enumerate(datos):
                    ws.cell(row=fila_inicial+idx, column=1, value=fila[0])
                    ws.cell(row=fila_inicial+idx, column=2, value=fila[1])
                    ws.cell(row=fila_inicial+idx, column=3, value=fila[2])
                    ws.cell(row=fila_inicial+idx, column=4, value=fila[3])
                    ws.cell(row=fila_inicial+idx, column=5, value=fila[4])
            
            del wb['Base']
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ DESCARGAR ARCHIVO COMPLETO",
                data=buffer,
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error generando Excel: {e}")
