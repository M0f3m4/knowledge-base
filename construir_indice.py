import os
import pickle
import numpy as np
import faiss
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# ── Conexión MongoDB ─────────────────────────────────────
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

def construir_indice():
    print("📦 Cargando vectores desde MongoDB...")
    docs = list(coleccion.find({}, {
        "texto": 1, "fuente": 1, "pagina": 1, "vector": 1
    }))
    print(f"   {len(docs)} fragmentos encontrados")

    # Extraer vectores
    vectores = np.array([d["vector"] for d in docs], dtype=np.float32)
    dimension = vectores.shape[1]
    print(f"   Dimensión de vectores: {dimension}")

    # Normalizar para búsqueda por coseno
    faiss.normalize_L2(vectores)

    # Crear índice FAISS
    print("🔨 Construyendo índice FAISS...")
    indice = faiss.IndexFlatIP(dimension)  # Inner Product = coseno con vectores normalizados
    indice.add(vectores)
    print(f"   {indice.ntotal} vectores indexados")

    # Guardar índice y metadatos
    print("💾 Guardando índice...")
    faiss.write_index(indice, "faiss_index.bin")

    # Guardar metadatos separado (texto, fuente, pagina)
    metadatos = [{"texto": d["texto"], "fuente": d["fuente"], "pagina": d["pagina"]} for d in docs]
    with open("faiss_metadatos.pkl", "wb") as f:
        pickle.dump(metadatos, f)

    print("✅ Índice FAISS construido y guardado")
    print(f"   faiss_index.bin")
    print(f"   faiss_metadatos.pkl")

if __name__ == "__main__":
    construir_indice()