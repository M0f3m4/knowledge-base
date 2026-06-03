"""
cargar_validaciones.py
Carga las validaciones del R04-C a MongoDB Atlas desde el Excel VALIDACIONES_POR_SERIE.xlsx.

Uso:
  python cargar_validaciones.py VALIDACIONES_POR_SERIE.xlsx
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

mongo = MongoClient(os.getenv("MONGO_URI"))
db    = mongo[os.getenv("DB_NAME")]

ARCHIVO = sys.argv[1] if len(sys.argv) > 1 else "VALIDACIONES_POR_SERIE.xlsx"

# Reportes R04-C que nos interesan
REPORTES_R04C = {
    "R04 C-0430": "0430",
    "R04 C-0431": "0431",
    "R04 C-0432": "0432",
    "R04 C-0433": "0433",
    "R04 C-0434": "0434",
    "R04 C-0435": "0435",
    "R04 C-0436": "0436",
    "R04 C-0437": "0437",
    "R04 C-0438": "0438",
    "R04 C-0439": "0439",
}


def extraer_numero_campo(concepto):
    """Extrae el número de campo del CONCEPTO. Ej: '6. RFC DEL ACREDITADO' → 6"""
    if not concepto or str(concepto) == "nan":
        return None
    try:
        parte = str(concepto).strip().split(".")[0]
        return int(parte)
    except:
        return None


def limpiar(val):
    """Limpia valores NaN y whitespace"""
    if val is None:
        return None
    s = str(val).strip()
    return None if s in ("", "nan", "NaN", "NaT") else s


def cargar():
    print(f"📂 Leyendo {ARCHIVO}...")

    # Leer hojas
    val_df  = pd.read_excel(ARCHIVO, sheet_name="R04C_VAL",  dtype=str).fillna("")
    desc_df = pd.read_excel(ARCHIVO, sheet_name="R04C_DESC", dtype=str).fillna("")

    print(f"   R04C_VAL:  {len(val_df)} filas")
    print(f"   R04C_DESC: {len(desc_df)} filas")

    # Limpiar colección
    col = db["validaciones"]
    col.delete_many({"serie": "R04C"})
    print("🗑️  Validaciones anteriores R04C eliminadas")

    docs = []

    for _, row in val_df.iterrows():
        reporte_raw = limpiar(row.get("REPORTE", ""))
        if reporte_raw not in REPORTES_R04C:
            continue

        numero_reporte = REPORTES_R04C[reporte_raw]
        concepto       = limpiar(row.get("CONCEPTO", ""))
        numero_campo   = extraer_numero_campo(concepto)
        id_val         = limpiar(row.get("ID_VALIDACION", "")) or limpiar(row.get("ID_VALIDACION_UNICO", ""))

        # Buscar descripción ampliada en R04C_DESC
        condicion = None
        tipo_val  = None
        desc_rows = desc_df[
            (desc_df["REPORTE"] == reporte_raw) &
            (desc_df.get("ID_VALIDACION", desc_df.get("ID_VALIDACION UNICO", pd.Series(dtype=str))) == id_val)
        ]
        if len(desc_rows) > 0:
            condicion = limpiar(desc_rows.iloc[0].get("CONDICION", ""))
            tipo_val  = limpiar(desc_rows.iloc[0].get("TIPO.1", ""))

        doc = {
            "serie":           "R04C",
            "reporte":         numero_reporte,
            "reporte_nombre":  reporte_raw,
            "id_validacion":   id_val,
            "descripcion":     limpiar(row.get("DESCRIPCION VALIDACION", "")),
            "concepto":        concepto,
            "numero_campo":    numero_campo,
            "tipo_val":        tipo_val or limpiar(row.get("TIPOSALDO", "")),
            "condicion":       condicion,
        }

        docs.append(doc)

    if docs:
        col.insert_many(docs)
        col.create_index([("serie", 1), ("reporte", 1), ("numero_campo", 1)])
        col.create_index([("serie", 1), ("reporte", 1), ("concepto", 1)])
        print(f"✅ {len(docs)} validaciones cargadas en colección 'validaciones'")

        # Generar embeddings SOLO para reporte 0430 (búsqueda libre)
        # Para agregar otros reportes, cambiar el filtro reporte="0430"
        if os.getenv("VOYAGE_API_KEY"):
            import requests as req, time
            VOYAGE_KEY = os.getenv("VOYAGE_API_KEY")
            VOYAGE_URL = "https://ai.mongodb.com/v1/embeddings"
            BATCH_SIZE = 64
            errores = 0

            # Generar embeddings para todos los reportes R04C
            docs_todos = [d for d in docs if d.get("descripcion")]
            total = len(docs_todos)
            docs_0430 = docs_todos  # alias para no cambiar el resto del código
            print(f"🔢 Generando embeddings en batch para todos los reportes R04C ({total} validaciones)...")

            for i in range(0, total, BATCH_SIZE):
                batch = docs_0430[i:i + BATCH_SIZE]
                textos = [d["descripcion"] for d in batch]
                try:
                    r = req.post(
                        VOYAGE_URL,
                        headers={"Authorization": f"Bearer {VOYAGE_KEY}", "Content-Type": "application/json"},
                        json={"input": textos, "model": "voyage-finance-2"}
                    )
                    if r.status_code == 200:
                        embeddings = r.json()["data"]
                        for j, emb in enumerate(embeddings):
                            doc = batch[j]
                            col.update_one(
                                {"serie": doc["serie"], "reporte": doc["reporte"], "id_validacion": doc["id_validacion"]},
                                {"$set": {"vector": emb["embedding"]}}
                            )
                    else:
                        errores += len(batch)
                        print(f"   ⚠️ Error batch {i}-{i+BATCH_SIZE}: {r.status_code}")
                    print(f"   {min(i+BATCH_SIZE, total)}/{total} embeddings generados...")
                    time.sleep(0.3)
                except Exception as e:
                    errores += len(batch)
                    print(f"   ⚠️ Error: {e}")

            print(f"✅ Embeddings R04C generados en batch ({errores} errores)")
        else:
            print("⚠️  VOYAGE_API_KEY no encontrada — sin embeddings (búsqueda libre no disponible)")

        # Resumen por reporte
        for rep, num in REPORTES_R04C.items():
            count = sum(1 for d in docs if d["reporte"] == num)
            if count:
                print(f"   {rep}: {count} validaciones")
    else:
        print("⚠️  No se encontraron validaciones R04C")


if __name__ == "__main__":
    print("🏦 Cargando validaciones R04-C a MongoDB Atlas...")
    print("=" * 50)
    cargar()
    print("=" * 50)
    print("✨ Listo")