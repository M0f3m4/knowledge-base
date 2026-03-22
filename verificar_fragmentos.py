import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

docs = list(coleccion.find(
    {"fuente": {"$regex": "0430", "$options": "i"}},
    {"pagina": 1, "_id": 0}
).sort("pagina", 1).limit(150))

paginas = sorted(set(d["pagina"]+1 for d in docs))
print(f"Total fragmentos: {len(docs)}")
print(f"Páginas cubiertas: {paginas[0]} a {paginas[-1]}")
print(f"Lista completa: {paginas}")