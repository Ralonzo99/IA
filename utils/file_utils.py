import tempfile

def guardar_archivo_temporal(archivo):

    extension = archivo.name.split(".")[-1]

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=f".{extension}"
    ) as tmp:

        tmp.write(archivo.read())

        return tmp.name
