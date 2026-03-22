import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

total = coleccion.count_documents({})
print(f"Total fragmentos: {total}")

# Ver los primeros 3 fragmentos
for doc in coleccion.find().limit(3):
    print(f"\n--- Fuente: {doc['fuente']} | Página: {doc['pagina']} ---")
    print(doc['texto'][:300])