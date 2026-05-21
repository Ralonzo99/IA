import os
import sqlite3
import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st
from pydantic import BaseModel

# OCR LOCAL (Comentado por falta de espacio - descomenta si tienes)
# from docling.document_converter import DocumentConverter
# import ollama

# ══════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════
DB_PATH      = "sistema_gastos.db"
EXCEL_PATH   = "Gastos_Mayo_2026.xlsx"
APP_VERSION  = "2.0.0"

# ══════════════════════════════════════════
# MODELOS PYDANTIC
# ══════════════════════════════════════════
class ItemFactura(BaseModel):
    descripcion: str
    cantidad: float
    precio_unitario: float
    total: float

class FacturaEstructurada(BaseModel):
    emisor_nombre: str
    emisor_id_fiscal: Optional[str] = None
    receptor_nombre: Optional[str] = None
    numero_factura: Optional[str] = None
    fecha_emision: Optional[str] = None
    items: list[ItemFactura]
    subtotal: float
    impuestos_total: float
    moneda: str
    monto_total: float

# ══════════════════════════════════════════
# CAPA DE PERSISTENCIA
# ══════════════════════════════════════════
class GastoStorage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS facturas (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    emisor_nombre    TEXT    NOT NULL,
                    emisor_id_fiscal TEXT,
                    receptor_nombre  TEXT,
                    numero_factura   TEXT,
                    fecha_emision    TEXT,
                    subtotal         REAL    DEFAULT 0,
                    impuestos_total  REAL    DEFAULT 0,
                    moneda           TEXT    DEFAULT 'USD',
                    monto_total      REAL    DEFAULT 0,
                    fecha_registro   TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS factura_items (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    factura_id       INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
                    descripcion      TEXT,
                    cantidad         REAL,
                    precio_unitario  REAL,
                    total            REAL
                );
            """)

    def guardar(self, factura: FacturaEstructurada) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO facturas
                   (emisor_nombre, emisor_id_fiscal, receptor_nombre, numero_factura,
                    fecha_emision, subtotal, impuestos_total, moneda, monto_total, fecha_registro)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (factura.emisor_nombre, factura.emisor_id_fiscal, factura.receptor_nombre,
                 factura.numero_factura, factura.fecha_emision, factura.subtotal,
                 factura.impuestos_total, factura.moneda, factura.monto_total,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            fid = cur.lastrowid
            conn.executemany(
                """INSERT INTO factura_items
                   (factura_id, descripcion, cantidad, precio_unitario, total)
                   VALUES (?,?,?,?,?)""",
                [(fid, i.descripcion, i.cantidad, i.precio_unitario, i.total) for i in factura.items],
            )
        return fid

    def todas(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        with sqlite3.connect(self.db_path) as conn:
            df_f = pd.read_sql_query("SELECT * FROM facturas ORDER BY id DESC", conn)
            df_i = pd.read_sql_query("SELECT * FROM factura_items", conn)
        return df_f, df_i

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(monto_total),0), COALESCE(SUM(impuestos_total),0) FROM facturas"
            ).fetchone()
        return {"total_facturas": row[0], "gasto_total": row[1], "impuestos": row[2]}

    def exportar_excel(self, path: str = EXCEL_PATH):
        df_f, df_i = self.todas()
        if df_f.empty:
            return
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            df_f.to_excel(w, sheet_name="Resumen de Facturas", index=False)
            df_i.to_excel(w, sheet_name="Detalle de Conceptos", index=False)

# ══════════════════════════════════════════
# UI — STREAMLIT PROFESIONAL
# ══════════════════════════════════════════
def configurar_pagina():
    st.set_page_config(
        page_title="AnalizadorIA Pro - Gestión Inteligente",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("""
    <style>
    /* ─── Tipografía base ─────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
 
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
 
    /* ─── Fondo general ──────────────────── */
    .main .block-container {
        background: #0B0F19;
        padding: 2rem 2.5rem;
        max-width: 1400px;
    }
    .stApp { background: #0B0F19; }
 
    /* ─── Sidebar ────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1F2937;
    }
 
    /* ─── Cards métricas ─────────────────── */
    .metric-card {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 16px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: #374151; }
    .metric-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366F1, #06B6D4);
    }
    .metric-label {
        font-size: 11px;
        font-weight: 500;
        letter-spacing: .1em;
        text-transform: uppercase;
        color: #6B7280;
        margin-bottom: .5rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 600;
        color: #F9FAFB;
        font-family: 'DM Mono', monospace;
    }
    .metric-sub {
        font-size: 12px;
        color: #4B5563;
        margin-top: .25rem;
    }
 
    /* ─── Badge de estado ────────────────── */
    .badge-ok {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(16,185,129,.12);
        color: #10B981;
        border: 1px solid rgba(16,185,129,.25);
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 12px; font-weight: 500;
    }
    .badge-warn {
        background: rgba(245,158,11,.12);
        color: #F59E0B;
        border: 1px solid rgba(245,158,11,.25);
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 12px; font-weight: 500;
        display: inline-flex; align-items: center; gap: 6px;
    }
 
    /* ─── Panel de resultado ─────────────── */
    .result-panel {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 20px;
        padding: 2rem;
    }
 
    /* ─── Tabla de ítems ─────────────────── */
    .item-row {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 1fr;
        gap: 12px;
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 13px;
        color: #D1D5DB;
    }
    .item-row:nth-child(even) { background: #0F1724; }
    .item-header {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: #4B5563;
        padding: 6px 16px 10px;
        border-bottom: 1px solid #1F2937;
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 1fr;
        gap: 12px;
    }
 
    /* ─── Botón principal ────────────────── */
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #6366F1, #818CF8) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: .75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        width: 100%;
        transition: opacity .2s, transform .1s !important;
    }
    div[data-testid="stButton"] > button:hover {
        opacity: .9 !important;
        transform: translateY(-1px) !important;
    }
 
    /* ─── Upload box ─────────────────────── */
    [data-testid="stFileUploader"] {
        background: #111827 !important;
        border: 1.5px dashed #1F2937 !important;
        border-radius: 16px !important;
    }
 
    /* ─── Formularios ────────────────────── */
    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        background: #0B0F19 !important;
        border: 1px solid #1F2937 !important;
        color: #F9FAFB !important;
        border-radius: 10px !important;
    }
    
    .stSelectbox > div > div {
        background: #0B0F19 !important;
        border: 1px solid #1F2937 !important;
    }
 
    /* ─── Ajustes generales ──────────────── */
    h1, h2, h3 { color: #F9FAFB !important; }
    p, li, label { color: #9CA3AF; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    
    /* ─── Expander ───────────────────────── */
    .streamlit-expanderHeader {
        background: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 12px !important;
        color: #F9FAFB !important;
    }
    </style>
    """, unsafe_allow_html=True)

def sidebar_panel(storage: GastoStorage):
    with st.sidebar:
        st.markdown("""
        <div style="padding:1.5rem 0 2rem;">
            <div style="font-size:22px;font-weight:700;color:#F9FAFB;letter-spacing:-0.5px;">
                Analizador<span style="color:#6366F1;">IA</span>
            </div>
            <div style="font-size:11px;color:#4B5563;margin-top:4px;">Gestión inteligente de gastos v{}</div>
        </div>
        """.format(APP_VERSION), unsafe_allow_html=True)

        # Estado del sistema
        try:
            # Verificar si existe la base de datos
            if os.path.exists(DB_PATH):
                st.markdown('<span class="badge-ok">● Sistema activo</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-warn">⚠ Base de datos nueva</span>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<span class="badge-warn">⚠ Estado desconocido</span>', unsafe_allow_html=True)

        st.markdown("---")

        # Navegación
        page = st.radio(
            "Navegación",
            ["🏠 Inicio", "📝 Nueva Factura", "📂 Historial", "📊 Analytics", "⚙ Configuración"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Mini stats
        stats = storage.stats()
        st.markdown(f"""
        <div style="font-size:11px;color:#4B5563;letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px;">
            Resumen rápido
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="color:#6B7280;font-size:13px;">Facturas</span>
            <span style="color:#F9FAFB;font-weight:600;font-family:'DM Mono',monospace;">
                {stats['total_facturas']}
            </span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span style="color:#6B7280;font-size:13px;">Gasto total</span>
            <span style="color:#10B981;font-weight:600;font-family:'DM Mono',monospace;">
                ${stats['gasto_total']:,.2f}
            </span>
        </div>
        <div style="display:flex;justify-content:space-between;">
            <span style="color:#6B7280;font-size:13px;">Impuestos</span>
            <span style="color:#F59E0B;font-weight:600;font-family:'DM Mono',monospace;">
                ${stats['impuestos']:,.2f}
            </span>
        </div>
        """, unsafe_allow_html=True)

    return page.split(" ", 1)[1] if " " in page else page

def pagina_inicio(storage: GastoStorage):
    st.markdown("""
    <div style="margin-bottom:2.5rem;">
        <h1 style="font-size:2rem;font-weight:700;margin:0;line-height:1.2;">
            Analizador Inteligente de Facturas
        </h1>
        <p style="color:#6B7280;margin-top:.5rem;font-size:15px;">
            Gestión profesional de gastos · Interfaz moderna · Datos 100% locales
        </p>
    </div>
    """, unsafe_allow_html=True)

    stats = storage.stats()
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("FACTURAS REGISTRADAS", str(stats["total_facturas"]), "en base de datos"),
        ("GASTO TOTAL", f"${stats['gasto_total']:,.2f}", "suma de todas las facturas"),
        ("IMPUESTOS", f"${stats['impuestos']:,.2f}", "IVA / taxes acumulados"),
        ("MODO", "Manual", "ingreso estructurado"),
    ]
    for col, (label, value, sub) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("#### 🚀 Acceso Rápido")
        st.info("💡 Usa 'Nueva Factura' en el menú lateral para registrar gastos")
        if st.button("➕ Ir a Nueva Factura", type="primary"):
            st.session_state["pagina_redirect"] = "Nueva Factura"
            st.rerun()
    
    with col2:
        st.markdown("#### 📊 Últimas Actividades")
        df, _ = storage.todas()
        if not df.empty:
            latest = df.head(3)
            for _, row in latest.iterrows():
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1F2937;border-radius:12px;padding:12px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;">
                        <span style="color:#F9FAFB;font-weight:500;">{row['emisor_nombre']}</span>
                        <span style="color:#10B981;">${row['monto_total']:,.2f}</span>
                    </div>
                    <div style="font-size:12px;color:#4B5563;">{row['fecha_emision'] or 'Sin fecha'}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#111827;border:1px solid #1F2937;border-radius:12px;padding:2rem;text-align:center;color:#4B5563;">
                No hay facturas registradas aún
            </div>
            """, unsafe_allow_html=True)

def pagina_nueva_factura(storage: GastoStorage):
    st.markdown("### 📝 Registrar Nueva Factura")
    st.markdown("Completa el formulario con los datos del gasto")
    
    with st.form("factura_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏢 Datos del Proveedor**")
            emisor = st.text_input("Nombre del proveedor *", placeholder="Ej: Distribuidora ABC")
            emisor_id = st.text_input("RUC / NIT", placeholder="Número de identificación fiscal")
            num_factura = st.text_input("Número de factura", placeholder="001-001-00012345")
            
        with col2:
            st.markdown("**📅 Información General**")
            fecha = st.date_input("Fecha de emisión", datetime.now())
            moneda = st.selectbox("Moneda", ["USD", "EUR", "MXN", "COP", "ARS", "CLP", "PEN"])
        
        st.markdown("**📦 Detalle de Productos/Servicios**")
        num_items = st.number_input("Cantidad de ítems", min_value=1, max_value=10, value=1)
        
        items_data = []
        for i in range(int(num_items)):
            st.markdown(f"*Ítem {i+1}*")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                desc = st.text_input(f"Descripción", key=f"desc_{i}", placeholder="Producto o servicio")
            with col_b:
                cant = st.number_input(f"Cantidad", min_value=0.0, step=0.01, key=f"cant_{i}")
            with col_c:
                p_unit = st.number_input(f"Precio unitario", min_value=0.0, step=0.01, key=f"precio_{i}")
            
            if desc and cant and p_unit:
                items_data.append({
                    "descripcion": desc,
                    "cantidad": cant,
                    "precio_unitario": p_unit,
                    "total": round(cant * p_unit, 2)
                })
        
        st.markdown("**💰 Totales**")
        col1, col2, col3 = st.columns(3)
        with col1:
            subtotal = st.number_input("Subtotal", min_value=0.0, step=0.01)
        with col2:
            impuestos = st.number_input("Impuestos / IVA", min_value=0.0, step=0.01)
        with col3:
            total = st.number_input("Monto total", min_value=0.0, step=0.01)
        
        submitted = st.form_submit_button("💾 Guardar Factura", use_container_width=True)
        
        if submitted:
            if not emisor:
                st.error("❌ El nombre del proveedor es obligatorio")
            elif not items_data:
                st.error("❌ Agrega al menos un ítem")
            else:
                factura = FacturaEstructurada(
                    emisor_nombre=emisor,
                    emisor_id_fiscal=emisor_id or None,
                    receptor_nombre=None,
                    numero_factura=num_factura or None,
                    fecha_emision=fecha.strftime("%Y-%m-%d"),
                    items=[ItemFactura(**item) for item in items_data],
                    subtotal=subtotal,
                    impuestos_total=impuestos,
                    moneda=moneda,
                    monto_total=total if total > 0 else subtotal + impuestos
                )
                fid = storage.guardar(factura)
                storage.exportar_excel()
                st.success(f"✅ ¡Factura guardada exitosamente! ID: {fid}")
                st.balloons()

def pagina_historial(storage: GastoStorage):
    st.markdown("### 📂 Historial de Facturas")
    df, _ = storage.todas()
    if df.empty:
        st.info("Todavía no hay facturas registradas. Crea una desde 'Nueva Factura'.")
        return
    
    df["monto_total"] = df["monto_total"].map(lambda x: f"${x:,.2f}")
    df["impuestos_total"] = df["impuestos_total"].map(lambda x: f"${x:,.2f}")
    df.rename(columns={
        "emisor_nombre": "Proveedor",
        "numero_factura": "N° Factura",
        "fecha_emision": "Fecha",
        "moneda": "Moneda",
        "monto_total": "Total",
        "impuestos_total": "Impuestos",
        "fecha_registro": "Registrado",
    }, inplace=True)
    
    mostrar = ["Proveedor", "N° Factura", "Fecha", "Moneda", "Total", "Impuestos", "Registrado"]
    st.dataframe(df[mostrar], use_container_width=True, hide_index=True)
    
    # Detalle expandible
    st.markdown("---")
    st.markdown("#### 📄 Ver Detalle Completo")
    for idx, row in df.iterrows():
        with st.expander(f"Factura #{row.get('id', idx)} - {row.get('Proveedor', 'N/A')}"):
            st.write(f"**ID Fiscal:** {row.get('emisor_id_fiscal', 'N/A')}")
            st.write(f"**Subtotal:** {row.get('subtotal', 'N/A')}")
            st.write(f"**Total:** {row.get('Total', 'N/A')}")

def pagina_analytics(storage: GastoStorage):
    st.markdown("### 📊 Analytics de Gastos")
    df, df_items = storage.todas()
    if df.empty:
        st.info("Sin datos suficientes para mostrar analytics.")
        return
    
    df["monto_total"] = pd.to_numeric(df["monto_total"], errors="coerce")
    df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")
    df_clean = df.dropna(subset=["fecha_emision"]).sort_values("fecha_emision")
    
    if not df_clean.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📈 Gasto acumulado por fecha**")
            st.area_chart(df_clean.set_index("fecha_emision")["monto_total"])
        with c2:
            st.markdown("**🥧 Gasto por proveedor**")
            by_prov = df.groupby("emisor_nombre")["monto_total"].sum().sort_values(ascending=False)
            st.bar_chart(by_prov)
        
        st.markdown("---")
        st.markdown("**📊 Top 5 Proveedores**")
        st.dataframe(by_prov.head().reset_index(), use_container_width=True)
    else:
        st.info("Las facturas no tienen fechas válidas para graficar.")

def pagina_configuracion():
    st.markdown("### ⚙ Configuración del Sistema")
    st.markdown("""
    <div style="background:#111827;border:1px solid #1F2937;border-radius:16px;padding:1.5rem;">
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
            <tr><td style="color:#6B7280;padding:10px 0;">Aplicación</td>
                <td style="color:#F9FAFB;font-weight:500;">AnalizadorIA Pro</td>
            </tr>
            <tr><td style="color:#6B7280;padding:10px 0;border-top:1px solid #1F2937;">Versión</td>
                <td style="color:#F9FAFB;font-weight:500;border-top:1px solid #1F2937;">2.0.0</td>
            </tr>
            <tr><td style="color:#6B7280;padding:10px 0;border-top:1px solid #1F2937;">Base de datos</td>
                <td style="color:#F9FAFB;font-weight:500;border-top:1px solid #1F2937;">SQLite (local)</td>
            </tr>
            <tr><td style="color:#6B7280;padding:10px 0;border-top:1px solid #1F2937;">Exportación</td>
                <td style="color:#F9FAFB;font-weight:500;border-top:1px solid #1F2937;">Excel (.xlsx)</td>
            </tr>
            <tr><td style="color:#6B7280;padding:10px 0;border-top:1px solid #1F2937;">Privacidad</td>
                <td style="color:#10B981;font-weight:500;border-top:1px solid #1F2937;">
                    100% local — ningún dato sale de tu máquina
                </td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**📁 Formatos soportados para OCR (requiere instalación completa)**")
    st.markdown("PDF · PNG · JPG · JPEG")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑 Limpiar base de datos", type="secondary"):
        if st.checkbox("Confirmo que quiero borrar todos los registros"):
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            st.session_state.clear()
            st.success("✅ Base de datos eliminada. Recarga la página.")

# ══════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════
def main():
    configurar_pagina()
    storage = GastoStorage()
    page = sidebar_panel(storage)
    
    routes = {
        "Inicio": lambda: pagina_inicio(storage),
        "Nueva Factura": lambda: pagina_nueva_factura(storage),
        "Historial": lambda: pagina_historial(storage),
        "Analytics": lambda: pagina_analytics(storage),
        "Configuración": pagina_configuracion,
    }
    routes.get(page, routes["Inicio"])()
    
    # Redirect si viene de inicio
    if "pagina_redirect" in st.session_state:
        target = st.session_state["pagina_redirect"]
        del st.session_state["pagina_redirect"]
        st.rerun()

if __name__ == "__main__":
    main()