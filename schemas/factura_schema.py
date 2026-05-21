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
