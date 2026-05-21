import pandas as pd

from database.connection import get_connection
from config.settings import EXPORT_PATH

def exportar_excel():

    conn = get_connection()

    df_facturas = pd.read_sql_query(
        "SELECT * FROM facturas",
        conn
    )

    df_items = pd.read_sql_query(
        "SELECT * FROM factura_items",
        conn
    )

    conn.close()

    with pd.ExcelWriter(
        EXPORT_PATH,
        engine="openpyxl"
    ) as writer:

        df_facturas.to_excel(
            writer,
            sheet_name="Facturas",
            index=False
        )

        df_items.to_excel(
            writer,
            sheet_name="Items",
            index=False
        )
