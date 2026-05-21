import os
import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from pydantic import BaseModel

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

st.set_page_config(page_title="Analizador de Gastos", page_icon="💰", layout="wide")

st.title("💰 Analizador de Gastos")
st.markdown("Ingresa tus facturas manualmente")

almacen = AlmacenamientoGastos()

with st.form("factura_form"):
    st.subheader("Nueva Factura")
    
    col1, col2 = st.columns(2)
    with col1:
        emisor = st.text_input("Nombre del emisor/proveedor *")
        num_factura = st.text_input("Número de factura")
        fecha = st.date_input("Fecha de emisión")
        moneda = st.selectbox("Moneda", ["USD", "EUR", "MXN", "COP", "ARS", "CLP", "PEN"])
    
    with col2:
        subtotal = st.number_input("Subtotal", min_value=0.0, step=0.01)
        impuestos = st.number_input("Impuestos", min_value=0.0, step=0.01)
        total = st.number_input("Monto total", min_value=0.0, step=0.01)
    
    st.subheader("Items")
    items_data = []
    num_items = st.number_input("Cantidad de items", min_value=1, max_value=20, value=1)
    
    for i in range(int(num_items)):
        st.markdown(f"**Item {i+1}**")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            desc = st.text_input(f"Descripción", key=f"desc_{i}")
        with col_b:
            cant = st.number_input(f"Cantidad", min_value=0.0, step=0.01, key=f"cant_{i}")
        with col_c:
            p_unit = st.number_input(f"Precio unitario", min_value=0.0, step=0.01, key=f"precio_{i}")
        if desc and cant and p_unit:
            items_data.append({
                "descripcion": desc, 
                "cantidad": cant, 
                "precio_unitario": p_unit, 
                "total": cant * p_unit
            })
    
    submitted = st.form_submit_button("💾 Guardar Factura", type="primary")
    
    if submitted:
        if not emisor:
            st.error("El nombre del emisor es obligatorio")
        elif not items_data:
            st.error("Agrega al menos un item")
        else:
            factura = FacturaEstructurada(
                emisor_nombre=emisor,
                emisor_id_fiscal=None,
                receptor_nombre=None,
                numero_factura=num_factura or None,
                fecha_emision=fecha.strftime("%Y-%m-%d") if fecha else None,
                items=[ItemFactura(**item) for item in items_data],
                subtotal=subtotal,
                impuestos_total=impuestos,
                moneda=moneda,
                monto_total=total if total > 0 else subtotal + impuestos
            )
            id_db = almacen.guardar_en_db(factura)
            almacen.exportar_todo_a_excel()
            st.success(f"✅ Factura guardada con ID: {id_db}")
            st.balloons()

st.subheader("📊 Últimas Facturas")
conn = sqlite3.connect("sistema_gastos.db")
df = pd.read_sql_query("SELECT id, emisor_nombre, numero_factura, fecha_emision, monto_total, moneda FROM facturas ORDER BY id DESC LIMIT 10", conn)
conn.close()
if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    if os.path.exists("Gastos_Mayo_2026.xlsx"):
        with open("Gastos_Mayo_2026.xlsx", "rb") as file:
            st.download_button(
                label="📥 Descargar Excel completo",
                data=file,
                file_name="Gastos_Mayo_2026.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.info("No hay facturas guardadas aún. Crea una usando el formulario.")