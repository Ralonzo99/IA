import os
import sqlite3
import json
import pandas as pd
from datetime import datetime
import streamlit as st
from pydantic import BaseModel

# IMPORTACIONES PARA EL OCR LOCAL Y GRATUITO
from docling.document_converter import DocumentConverter
import ollama

# ==========================================
# 1. MODELOS DE DATOS (PYDANTIC)
# ==========================================
class ItemFactura(BaseModel):
    descripcion: str
    cantidad: float
    precio_unitario: float
    total: float

class FacturaEstructurada(BaseModel):
    emisor_nombre: str
    emisor_id_fiscal: str | None = None
    receptor_nombre: str | None = None
    numero_factura: str | None = None
    fecha_emision: str | None = None
    items: list[ItemFactura]
    subtotal: float
    impuestos_total: float
    moneda: str
    monto_total: float

# ==========================================
# 2. GESTIÓN DE BASE DE DATOS Y EXCEL
# ==========================================
class AlmacenamientoGastos:
    def __init__(self, db_name="sistema_gastos.db"):
        self.db_name = db_name
        self._inicializar_base_datos()

    def _inicializar_base_datos(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emisor_nombre TEXT,
                emisor_id_fiscal TEXT,
                receptor_nombre TEXT,
                numero_factura TEXT,
                fecha_emision TEXT,
                subtotal REAL,
                impuestos_total REAL,
                moneda TEXT,
                monto_total REAL,
                fecha_registro TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factura_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                factura_id INTEGER,
                descripcion TEXT,
                cantidad REAL,
                precio_unitario REAL,
                total REAL,
                FOREIGN KEY (factura_id) REFERENCES facturas(id)
            )
        """)
        conn.commit()
        conn.close()

    def guardar_en_db(self, factura: FacturaEstructurada) -> int:
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO facturas (
                emisor_nombre, emisor_id_fiscal, receptor_nombre, numero_factura, 
                fecha_emision, subtotal, impuestos_total, moneda, monto_total, fecha_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            factura.emisor_nombre, factura.emisor_id_fiscal, factura.receptor_nombre,
            factura.numero_factura, factura.fecha_emision, factura.subtotal,
            factura.impuestos_total, factura.moneda, factura.monto_total,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        factura_id = cursor.lastrowid
        
        for item in factura.items:
            cursor.execute("""
                INSERT INTO factura_items (factura_id, descripcion, cantidad, precio_unitario, total)
                VALUES (?, ?, ?, ?, ?)
            """, (factura_id, item.descripcion, item.cantidad, item.precio_unitario, item.total))
            
        conn.commit()
        conn.close()
        return factura_id

    def exportar_todo_a_excel(self, excel_path="Gastos_Mayo_2026.xlsx"):
        conn = sqlite3.connect(self.db_name)
        df_facturas = pd.read_sql_query("SELECT * FROM facturas", conn)
        df_items = pd.read_sql_query("SELECT * FROM factura_items", conn)
        conn.close()
        
        if df_facturas.empty:
            return

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_facturas.to_excel(writer, sheet_name="Resumen de Facturas", index=False)
            df_items.to_excel(writer, sheet_name="Detalle de Conceptos", index=False)

# ==========================================
# 3. INTERFAZ WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="OCR Local Gratis", page_icon="🧾", layout="wide")

st.title("🧾 Analizador Automático de Facturas (Modo Local Gratis)")
st.markdown("Procesa tus documentos de forma privada e ilimitada sin costos de API.")

almacen = AlmacenamientoGastos()

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📁 Subir Documento")
    archivo_subido = st.file_uploader("Selecciona una factura, foto o ticket (PDF, PNG, JPG)", type=["png", "jpg", "jpeg", "pdf"])

    if archivo_subido is not None:
        ruta_temporal = os.path.join(".", archivo_subido.name)
        with open(ruta_temporal, "wb") as f:
            f.write(archivo_subido.getbuffer())
        
        st.success(f"Archivo listo: {archivo_subido.name}")
        
        if st.button("🧠 Procesar Gasto con IA Local", type="primary"):
            with st.spinner("Docling escaneando y Llama 3 estructurando datos de forma local..."):
                try:
                    # 1. ESCANEO CON DOCLING
                    converter = DocumentConverter()
                    resultado_docling = converter.convert(ruta_temporal)
                    texto_markdown = resultado_docling.document.export_to_markdown()
                    
                    # 2. LLAMADA AL MODELO LOCAL (OLLAMA)
                    # Solicitamos la respuesta estrictamente estructurada en formato JSON
                    prompt_sistema = (
                        "Eres un asistente contable experto. Tu única tarea es extraer la información del texto "
                        "de una factura y devolver un objeto JSON que coincida exactamente con esta estructura:\n"
                        "{\n"
                        "  'emisor_nombre': 'str',\n"
                        "  'emisor_id_fiscal': 'str o null',\n"
                        "  'receptor_nombre': 'str o null',\n"
                        "  'numero_factura': 'str o null',\n"
                        "  'fecha_emision': 'str o null',\n"
                        "  'items': [{'descripcion': 'str', 'cantidad': float, 'precio_unitario': float, 'total': float}],\n"
                        "  'subtotal': float,\n"
                        "  'impuestos_total': float,\n"
                        "  'moneda': 'str',\n"
                        "  'monto_total': float\n"
                        "}\n"
                        "Responde ÚNICAMENTE con el código JSON limpio, sin comentarios, sin formato markdown ```json."
                    )
                    
                    respuesta = ollama.chat(
                        model='llama3',
                        messages=[
                            {'role': 'system', 'content': prompt_sistema},
                            {'role': 'user', 'content': f"Texto de la factura:\n\n{texto_markdown}"}
                        ]
                    )
                    
                    # 3. PARSEO SEGURO DE LA RESPUESTA JSON LOCAL
                    texto_respuesta = respuesta['message']['content'].strip()
                    
                    # Limpieza por si el modelo agrega bloques de markdown sin querer
                    if texto_respuesta.startswith("```"):
                        texto_respuesta = texto_respuesta.split("```")[1]
                        if texto_respuesta.startswith("json"):
                            texto_respuesta = texto_respuesta[4:]
                    
                    datos_json = json.loads(texto_respuesta.strip())
                    datos_extraidos = FacturaEstructurada(**datos_json)

                    # 4. ALMACENAMIENTO
                    id_db = almacen.guardar_en_db(datos_extraidos)
                    almacen.exportar_todo_a_excel()
                    
                    st.session_state['datos_listos'] = datos_extraidos
                    st.session_state['id_db'] = id_db
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Error en el procesamiento local: {e}")
                    st.info("Asegúrate de que la aplicación Ollama se esté ejecutando en tu barra de tareas de Windows.")
                finally:
                    if os.path.exists(ruta_temporal):
                        os.remove(ruta_temporal)

with col2:
    st.subheader("📊 Datos Extraídos en Tiempo Real")
    if 'datos_listos' in st.session_state:
        gasto = st.session_state['datos_listos']
        st.success(f"💾 ¡Guardado localmente! Registro ID: {st.session_state['id_db']}")
        
        st.metric(label="Proveedor / Emisor", value=gasto.emisor_nombre)
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="Factura N°", value=gasto.numero_factura if gasto.numero_factura else "N/A")
        kpi2.metric(label="Fecha", value=gasto.fecha_emision if gasto.fecha_emision else "N/A")
        kpi3.metric(label="Total Neto", value=f"{gasto.monto_total} {gasto.moneda}")
        
        st.markdown("**Conceptos facturados:**")
        tabla_items = [item.model_dump() for item in gasto.items]
        st.dataframe(tabla_items, use_container_width=True)
        
        if os.path.exists("Gastos_Mayo_2026.xlsx"):
            with open("Gastos_Mayo_2026.xlsx", "rb") as file:
                st.download_button(
                    label="📥 Descargar Reporte Excel Completo",
                    data=file,
                    file_name="Reporte_Gastos_Actualizado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("Sube una factura en el panel izquierdo y haz clic en el botón para ejecutar el análisis inteligente local.")