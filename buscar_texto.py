import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

# Buscar fragmentos que contengan ese texto
resultados = coleccion.find({
    "texto": {"$regex": "RFC DEL ACREDITADO", "$options": "i"}
})

encontrados = list(resultados)
print(f"Fragmentos encontrados: {len(encontrados)}")
for doc in encontrados:
    print(f"\n--- {doc['fuente']} | Página {doc['pagina']+1} ---")
    print(doc['texto'][:400])