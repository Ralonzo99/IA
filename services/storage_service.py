from database.repository import guardar_factura_db

def guardar_factura(factura):
    return guardar_factura_db(factura)
