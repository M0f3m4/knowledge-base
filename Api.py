import os
import pickle
import numpy as np
import faiss
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from pymongo import MongoClient

load_dotenv()

# ── App ──────────────────────────────────────────────────
app = FastAPI(title="Knowledge Base CNBV")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    model="mistral:7b-instruct",
    base_url=os.getenv("OLLAMA_URL"),
    temperature=0
)

# ── Cargar índice FAISS ──────────────────────────────────
_indice = None
_metadatos = None

def cargar_indice():
    global _indice, _metadatos
    if _indice is None:
        _indice = faiss.read_index("faiss_index.bin")
        with open("faiss_metadatos.pkl", "rb") as f:
            _metadatos = pickle.load(f)
    return _indice, _metadatos

# ── Búsqueda híbrida ─────────────────────────────────────
def buscar_fragmentos(pregunta, top_k=8, filtro_fuente=None):
    indice, metadatos = cargar_indice()
    vector = np.array([embeddings.embed_query(pregunta)], dtype=np.float32)
    faiss.normalize_L2(vector)

    k = top_k * 3 if filtro_fuente else top_k
    scores, indices = indice.search(vector, k)

    resultados = []
    vistos = set()
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        doc = metadatos[idx]
        clave = f"{doc['fuente']}_{doc['pagina']}"
        if filtro_fuente and filtro_fuente.lower() not in doc["fuente"].lower():
            continue
        if clave not in vistos:
            vistos.add(clave)
            resultados.append((float(score), doc))
        if len(resultados) >= top_k:
            break

    # Complementar con texto exacto
    try:
        query = {"$text": {"$search": pregunta}}
        if filtro_fuente:
            query["fuente"] = {"$regex": filtro_fuente, "$options": "i"}
        txt = coleccion.find(
            query,
            {"texto": 1, "fuente": 1, "pagina": 1, "score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(4)

        for d in txt:
            clave = f"{d['fuente']}_{d['pagina']}"
            if clave not in vistos:
                vistos.add(clave)
                resultados.append((1.0, {"texto": d["texto"], "fuente": d["fuente"], "pagina": d["pagina"]}))
    except:
        pass

    return resultados[:top_k]

# ── Construir contexto ───────────────────────────────────
def construir_contexto(fragmentos):
    contexto = ""
    fuentes = []
    for score, doc in fragmentos:
        contexto += f"\n[{doc['fuente']} | Página {doc['pagina']+1}]\n{doc['texto']}\n"
        fuentes.append({"fuente": doc["fuente"], "pagina": doc["pagina"] + 1})
    return contexto, fuentes

# ── BASE prompt ──────────────────────────────────────────
BASE = """REGLAS ESTRICTAS:
1. Usa ÚNICAMENTE información de los fragmentos proporcionados
2. NO uses conocimiento externo
3. NO inventes datos, URLs ni referencias
4. Si algo no está en los fragmentos escribe: No encontrado en los documentos
5. Responde siempre en español
"""

# ── Modelos de request/response ──────────────────────────
class ConsultaRequest(BaseModel):
    pregunta: str
    reporte: str = None  # opcional, ej: "0430"

class ConsultaResponse(BaseModel):
    respuesta: str
    fuentes: list

# ── Endpoints ────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "mensaje": "Knowledge Base CNBV activo"}

@app.post("/consulta", response_model=ConsultaResponse)
def consultar(req: ConsultaRequest):
    fragmentos = buscar_fragmentos(req.pregunta, filtro_fuente=req.reporte)
    contexto, fuentes = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres un experto en regulación bancaria mexicana CNBV.
{BASE}

Responde la pregunta usando solo los fragmentos.
Menciona página y documento cuando cites información específica.

FRAGMENTOS:
{contexto}

PREGUNTA: {req.pregunta}
[/INST]"""

    respuesta = llm.invoke(prompt)
    return ConsultaResponse(respuesta=respuesta, fuentes=fuentes)

@app.post("/campo")
def consultar_campo(req: ConsultaRequest):
    from columnas_0430 import resolver_campo
    campo, filtro = resolver_campo(req.pregunta)
    reporte = filtro or req.reporte

    pregunta = f"campo {campo} reporte {reporte} origen descripcion"
    fragmentos = buscar_fragmentos(pregunta, filtro_fuente=reporte)
    contexto, fuentes = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres un experto en regulación bancaria CNBV.
{BASE}

Responde sobre el campo "{campo}" usando EXACTAMENTE este formato:
- CAMPO: {campo}
- ORIGEN: [PERSONA / LINEA_CREDITO / CATALOGO / CALCULADO / DEFAULT]
- TIPO: [captura manual / calculado / catálogo]
- FORMULA: [fórmula si existe, si no: No aplica]
- NOTAS: [reglas especiales, si no hay: Ninguna]

FRAGMENTOS:
{contexto}
[/INST]"""

    respuesta = llm.invoke(prompt)
    return {"respuesta": respuesta, "fuentes": fuentes, "campo": campo, "reporte": reporte}

@app.post("/calculo")
def consultar_calculo(req: ConsultaRequest):
    from columnas_0430 import resolver_campo
    campo, filtro = resolver_campo(req.pregunta)
    reporte = filtro or req.reporte

    pregunta = f"calcular {campo} formula metodologia"
    fragmentos = buscar_fragmentos(pregunta, top_k=10, filtro_fuente=reporte)
    contexto, fuentes = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres un experto en regulación bancaria CNBV.
{BASE}

Explica el cálculo de "{campo}" usando EXACTAMENTE este formato:
- CAMPO: {campo}
- SE PUEDE CALCULAR: [Sí / No]
- FORMULA: [fórmula exacta, si no: No especificada]
- DATOS NECESARIOS: [qué datos se requieren]
- REFERENCIA: [anexo o sección, si no: No especificada]
- OBSERVACIONES: [casos especiales, si no: Ninguna]

FRAGMENTOS:
{contexto}
[/INST]"""

    respuesta = llm.invoke(prompt)
    return {"respuesta": respuesta, "fuentes": fuentes, "campo": campo}

@app.get("/health")
def health():
    cargar_indice()
    return {"status": "ok", "fragmentos": _indice.ntotal if _indice else 0}

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    cargar_indice()
    uvicorn.run(app, host="0.0.0.0", port=8000)