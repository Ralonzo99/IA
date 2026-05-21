CREATE_FACTURAS_TABLE = '''
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
'''

CREATE_ITEMS_TABLE = '''
CREATE TABLE IF NOT EXISTS factura_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER,
    descripcion TEXT,
    cantidad REAL,
    precio_unitario REAL,
    total REAL,
    FOREIGN KEY (factura_id) REFERENCES facturas(id)
)
'''
