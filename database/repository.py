from datetime import datetime

from database.connection import get_connection
from database.models import (
    CREATE_FACTURAS_TABLE,
    CREATE_ITEMS_TABLE
)

def inicializar_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(CREATE_FACTURAS_TABLE)
    cursor.execute(CREATE_ITEMS_TABLE)

    conn.commit()
    conn.close()

def guardar_factura_db(factura):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        INSERT INTO facturas (
            emisor_nombre,
            emisor_id_fiscal,
            receptor_nombre,
            numero_factura,
            fecha_emision,
            subtotal,
            impuestos_total,
            moneda,
            monto_total,
            fecha_registro
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            factura.emisor_nombre,
            factura.emisor_id_fiscal,
            factura.receptor_nombre,
            factura.numero_factura,
            factura.fecha_emision,
            factura.subtotal,
            factura.impuestos_total,
            factura.moneda,
            factura.monto_total,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    factura_id = cursor.lastrowid

    for item in factura.items:
        cursor.execute(
            '''
            INSERT INTO factura_items (
                factura_id,
                descripcion,
                cantidad,
                precio_unitario,
                total
            )
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                factura_id,
                item.descripcion,
                item.cantidad,
                item.precio_unitario,
                item.total
            )
        )

    conn.commit()
    conn.close()

    return factura_id
