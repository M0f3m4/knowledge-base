"""
cargar_excel.py
Carga TODOS los datos de un caso de prueba Excel a MongoDB Atlas.
Soporta archivos con hojas PERSONA, LINEA_CREDITO y CREDITO.

Uso:
  python cargar_excel.py CASO_DE_PRUEBA_ALTAS_0430.xlsx
"""

import os
import sys
import math
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo = MongoClient(os.getenv("MONGO_URI"))
db = mongo[os.getenv("DB_NAME")]

# Filas de metadata a saltar después del header (fila 0)
CONFIG = {
    "PERSONA": {
        "skiprows":  [1, 2, 3],      # tipo, longitud, mapping interno
        "coleccion": "persona",
        "id_campo":  "ID_PERSONA",
    },
    "LINEA_CREDITO": {
        "skiprows":  [1, 2, 3, 4, 5],  # tipo, longitud, si/no, catalogo, duplicado
        "coleccion": "linea_credito",
        "id_campo":  "ID_LINEACREDITO",
    },
    "CREDITO": {
        "skiprows":  [1, 2, 3, 4],   # tipo, longitud, catalogo, descripcion catalogo
        "coleccion": "credito",
        "id_campo":  "ID_CREDITO",
    },
}


def limpiar_valor(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    if hasattr(v, 'item'):
        return v.item()
    return v


def limpiar_fila(fila):
    return {str(k): limpiar_valor(v) for k, v in fila.items() if not str(k).startswith('Unnamed')}


def cargar_hoja(archivo, hoja, config, nombre_archivo):
    print(f"\n📄 Procesando hoja: {hoja}")

    df = pd.read_excel(
        archivo,
        sheet_name=hoja,
        header=0,
        skiprows=config["skiprows"]
    )

    # Eliminar columnas sin nombre (Unnamed)
    df = df[[c for c in df.columns if not str(c).startswith('Unnamed')]]

    # Eliminar filas sin ID
    id_campo = config["id_campo"]
    if id_campo in df.columns:
        df = df.dropna(subset=[id_campo])

    print(f"   📊 {len(df.columns)} columnas | {len(df)} registros")

    coleccion = db[config["coleccion"]]
    existente = coleccion.count_documents({"_archivo": nombre_archivo})

    if existente > 0:
        resp = input(f"   ⚠️  Ya existen {existente} registros de este archivo. ¿Reemplazar? (s/n): ")
        if resp.lower() != 's':
            print("   ⏭️  Saltando...")
            return 0
        coleccion.delete_many({"_archivo": nombre_archivo})
        print(f"   🗑️  Registros anteriores eliminados")

    batch_size = 500
    total = 0
    fecha_carga = datetime.utcnow().isoformat()

    for i in range(0, len(df), batch_size):
        lote = df.iloc[i:i + batch_size]
        docs = []
        for _, fila in lote.iterrows():
            doc = limpiar_fila(fila.to_dict())
            doc["_archivo"] = nombre_archivo
            doc["_cargado"] = fecha_carga
            docs.append(doc)
        coleccion.insert_many(docs)
        total += len(docs)
        print(f"   ✅ {total}/{len(df)}", end="\r")

    print(f"   ✨ Completado: {total} registros en '{config['coleccion']}'        ")
    return total


def main(archivo):
    if not os.path.exists(archivo):
        print(f"❌ Archivo no encontrado: {archivo}")
        sys.exit(1)

    nombre_archivo = os.path.basename(archivo)
    xl = pd.ExcelFile(archivo)
    hojas = xl.sheet_names

    print("=" * 60)
    print(f"🏦 Cargador de Datos — Knowledge Base CNBV")
    print(f"   Archivo: {nombre_archivo}")
    print(f"   Base de datos: {os.getenv('DB_NAME')}")
    print(f"   Hojas: {[h for h in hojas if h in CONFIG]}")
    print("=" * 60)

    total = 0
    for hoja, config in CONFIG.items():
        if hoja in hojas:
            total += cargar_hoja(archivo, hoja, config, nombre_archivo)

    print(f"\n{'='*60}")
    print(f"✅ Proceso completado — {total} registros cargados en total")
    print(f"   Colecciones: persona, linea_credito, credito")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python cargar_excel.py <archivo.xlsx>")
        sys.exit(1)
    main(sys.argv[1])