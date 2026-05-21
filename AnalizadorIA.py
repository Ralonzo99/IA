import os
import sqlite3
import pandas as pd
from datetime import datetime
from pydantic import BaseModel, Field

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
        """Crea las tablas necesarias si no existen (Facturas e Ítems correlacionados)."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabla Principal: Cabecera de la Factura
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
        
        # Tabla Secundaria: Líneas de detalle (Productos/Servicios)
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
        """Guarda la factura y sus ítems en SQLite. Devuelve el ID generado."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 1. Insertar la cabecera
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
        
        factura_id = cursor.lastrowid # Obtenemos el ID de la factura recién insertada
        
        # 2. Insertar cada línea de detalle asociada a esa factura
        for item in factura.items:
            cursor.execute("""
                INSERT INTO factura_items (factura_id, descripcion, cantidad, precio_unitario, total)
                VALUES (?, ?, ?, ?, ?)
            """, (factura_id, item.descripcion, item.cantidad, item.precio_unitario, item.total))
            
        conn.commit()
        conn.close()
        print(f"💾 Guardado en Base de Datos con éxito (ID Factura: {factura_id})")
        return factura_id

    def exportar_todo_a_excel(self, excel_path="reporte_gastos_consolidado.xlsx"):
        """Extrae el histórico completo de la DB y crea un Excel con dos pestañas."""
        conn = sqlite3.connect(self.db_name)
        
        # Leemos el estado actual de las tablas usando Pandas
        df_facturas = pd.read_sql_query("SELECT * FROM facturas", conn)
        df_items = pd.read_sql_query("SELECT * FROM factura_items", conn)
        
        conn.close()
        
        if df_facturas.empty:
            print("⚠️ No hay datos en la base de datos para exportar.")
            return

        # Escribimos en un Excel multi-pestaña
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_facturas.to_excel(writer, sheet_name="Resumen de Facturas", index=False)
            df_items.to_excel(writer, sheet_name="Detalle de Conceptos", index=False)
            
        print(f"📊 Reporte Excel generado y actualizado en: {excel_path}")

\
if __name__ == "__main__":
    
    from pydantic import BaseModel
    
    objeto_mock = FacturaEstructurada(
        emisor_nombre="Restaurantes del Centro S.A.",
        emisor_id_fiscal="RCE123456ABC",
        receptor_nombre="Mi Empresa S.L.",
        numero_factura="F-99482",
        fecha_emision="2026-05-18",
        items=[
            ItemFactura(descripcion="Consumo de Alimentos", cantidad=1.0, precio_unitario=45.50, total=45.50),
            ItemFactura(descripcion="Bebidas", cantidad=2.0, precio_unitario=5.00, total=10.00)
        ],
        subtotal=55.50,
        impuestos_total=8.88,
        moneda="USD",
        monto_total=64.38
    )

    # Instanciamos el módulo de almacenamiento
    almacen = AlmacenamientoGastos()
    
    # 1. Guardar de forma automatizada en SQLite
    almacen.guardar_en_db(objeto_mock)
    
    # 2. Exportar el histórico consolidado a un reporte de Excel listo para contabilidad
    almacen.exportar_todo_a_excel("Gastos_Mayo_2026.xlsx")