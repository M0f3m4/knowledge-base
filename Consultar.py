import os
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from pymongo import MongoClient
import numpy as np

load_dotenv()

# ── Conexión MongoDB ─────────────────────────────────────
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

# ── Modelos Ollama ───────────────────────────────────────
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=os.getenv("OLLAMA_URL")
)

llm = OllamaLLM(
    model="llama3.1:8b",
    base_url=os.getenv("OLLAMA_URL"),
    temperature=0.1
)

# ── Búsqueda por similitud (coseno) ─────────────────────
def buscar_fragmentos(pregunta, top_k=5):
    vector_pregunta = embeddings.embed_query(pregunta)
    vector_pregunta = np.array(vector_pregunta)

    todos = list(coleccion.find({}, {"texto": 1, "fuente": 1, "pagina": 1, "vector": 1}))

    similitudes = []
    for doc in todos:
        vector_doc = np.array(doc["vector"])
        # Similitud coseno
        similitud = np.dot(vector_pregunta, vector_doc) / (
            np.linalg.norm(vector_pregunta) * np.linalg.norm(vector_doc) + 1e-10
        )
        similitudes.append((similitud, doc))

    similitudes.sort(key=lambda x: x[0], reverse=True)
    return similitudes[:top_k]

# ── Consultar ────────────────────────────────────────────
def consultar(pregunta):
    print(f"\n🔍 Buscando: {pregunta}")
    fragmentos = buscar_fragmentos(pregunta)

    contexto = ""
    fuentes = []
    for sim, doc in fragmentos:
        contexto += f"\n---\nFuente: {doc['fuente']} (página {doc['pagina']+1})\n{doc['texto']}\n"
        fuentes.append(f"{doc['fuente']} p.{doc['pagina']+1}")

    prompt = f"""Eres un experto en regulación bancaria mexicana CNBV.
Basándote ÚNICAMENTE en los siguientes fragmentos de documentos oficiales, responde la pregunta.
Si la información no está en los fragmentos, dilo claramente.
Responde en español.

DOCUMENTOS:
{contexto}

PREGUNTA: {pregunta}

RESPUESTA:"""

    print("🤖 Consultando Ollama...")
    respuesta = llm.invoke(prompt)

    print(f"\n📋 Fuentes consultadas: {', '.join(set(fuentes))}")
    print(f"\n💬 Respuesta:\n{respuesta}")
    return respuesta

# ── Modo interactivo ─────────────────────────────────────
if __name__ == "__main__":
    print("🏦 Base de Conocimiento CNBV")
    print("Escribe 'salir' para terminar\n")

    while True:
        pregunta = input("❓ Tu pregunta: ").strip()
        if pregunta.lower() == "salir":
            break
        if pregunta:
            consultar(pregunta)