import os
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_ollama import OllamaLLM
from columnas_0430 import resolver_campo

load_dotenv()

# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════

mongo = MongoClient(os.getenv("MONGO_URI"))
db = mongo[os.getenv("DB_NAME")]
docs = db["documentos"]

VOYAGE_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_URL = "https://ai.mongodb.com/v1/embeddings"
VOYAGE_MODEL = "voyage-finance-2"

llm = OllamaLLM(
    model="mistral:7b-instruct",
    base_url=os.getenv("OLLAMA_URL"),
    temperature=0
)

REGLAS = """REGLAS ESTRICTAS:
- Usa ÚNICAMENTE los fragmentos proporcionados
- NO uses conocimiento externo ni inventes información
- Si algo no está en los fragmentos escribe: No encontrado en los documentos
- SIEMPRE responde en español, NUNCA en inglés
- NUNCA des explicaciones fuera del formato solicitado"""

# ══════════════════════════════════════════════════════════
# NÚCLEO
# ══════════════════════════════════════════════════════════

def embedding(texto):
    r = requests.post(
        VOYAGE_URL,
        headers={"Authorization": f"Bearer {VOYAGE_KEY}", "Content-Type": "application/json"},
        json={"input": [texto], "model": VOYAGE_MODEL}
    )
    if r.status_code != 200:
        raise Exception(f"Voyage error {r.status_code}: {r.text}")
    return r.json()["data"][0]["embedding"]


def buscar(pregunta, top_k=8, reporte=None):
    vector = embedding(pregunta)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "vector",
                "queryVector": vector,
                "numCandidates": 100,
                "limit": top_k * 2 if reporte else top_k
            }
        },
        {
            "$project": {
                "texto": 1, "fuente": 1, "pagina": 1,
                "score": {"$meta": "vectorSearchScore"},
                "_id": 0
            }
        }
    ]

    resultados = list(docs.aggregate(pipeline))

    if reporte:
        resultados = [r for r in resultados if reporte.lower() in r["fuente"].lower()]

    try:
        filtro = {"$text": {"$search": pregunta}}
        if reporte:
            filtro["fuente"] = {"$regex": reporte, "$options": "i"}

        vistos = {f"{r['fuente']}_{r['pagina']}" for r in resultados}
        for d in docs.find(filtro, {"texto": 1, "fuente": 1, "pagina": 1, "_id": 0}).limit(4):
            clave = f"{d['fuente']}_{d['pagina']}"
            if clave not in vistos:
                vistos.add(clave)
                resultados.append({**d, "score": 1.0})
    except:
        pass

    return resultados[:top_k]


def construir_contexto(fragmentos):
    texto = ""
    fuentes = []
    for f in fragmentos:
        texto += f"\n[{f['fuente']} | Página {f['pagina']+1}]\n{f['texto']}\n"
        fuentes.append({"fuente": f["fuente"], "pagina": f["pagina"] + 1})
    return texto, fuentes


def construir_historial(mensajes):
    if not mensajes:
        return ""
    historial = "\nCONVERSACIÓN PREVIA:\n"
    for m in mensajes[-6:]:
        rol = "Usuario" if m["tipo"] == "user" else "Asistente"
        historial += f"{rol}: {m['texto'][:300]}\n"
    return historial


# ══════════════════════════════════════════════════════════
# FUNCIONES PÚBLICAS
# ══════════════════════════════════════════════════════════

def consultar_campo(argumento, historial=None):
    campo, reporte = resolver_campo(argumento)
    fragmentos = buscar(f"{campo} origen descripcion reporte {reporte or ''}", reporte=reporte)
    ctx, fuentes = construir_contexto(fragmentos)
    hist = construir_historial(historial or [])

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV. Responde SOLO en español.
{REGLAS}
{hist}

Responde sobre "{campo}" con EXACTAMENTE estas 5 líneas en español, nada más:
- CAMPO: {campo}
- ORIGEN: [PERSONA / LINEA_CREDITO / CATALOGO / CALCULADO / DEFAULT]
- TIPO: [captura manual / calculado / catálogo]
- FORMULA: [si existe; si no: No aplica]
- NOTAS: [reglas especiales; si no: Ninguna]

FRAGMENTOS:
{ctx}

Responde SOLO en español con el formato de 5 líneas indicado.
[/INST]"""

    return {"respuesta": llm.invoke(prompt), "fuentes": fuentes, "campo": campo, "reporte": reporte}


def consultar_calculo(argumento, historial=None):
    campo, reporte = resolver_campo(argumento)
    fragmentos = buscar(f"calcular {campo} formula metodologia", top_k=10, reporte=reporte)
    ctx, fuentes = construir_contexto(fragmentos)
    hist = construir_historial(historial or [])

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV. Responde SOLO en español.
{REGLAS}
{hist}

Explica el cálculo de "{campo}" con EXACTAMENTE estas 6 líneas en español, nada más:
- CAMPO: {campo}
- SE PUEDE CALCULAR: [Sí / No]
- FORMULA: [fórmula exacta; si no: No especificada]
- DATOS NECESARIOS: [qué datos se requieren]
- REFERENCIA: [anexo o sección; si no: No especificada]
- OBSERVACIONES: [casos especiales; si no: Ninguna]

FRAGMENTOS:
{ctx}

Responde SOLO en español con el formato de 6 líneas indicado.
[/INST]"""

    return {"respuesta": llm.invoke(prompt), "fuentes": fuentes, "campo": campo}


def consultar_reporte(numero, historial=None):
    from columnas_0430 import COLUMNAS

    # Si el reporte tiene mapa de columnas, usarlo directamente
    if numero in COLUMNAS:
        columnas = COLUMNAS[numero]
        respuesta = f"Campos del reporte {numero}:\n\n"
        for num, nombre in columnas.items():
            respuesta += f"{num}. {nombre}\n"
        return {"respuesta": respuesta, "fuentes": [], "reporte": numero}

    # Para otros reportes usar RAG
    fragmentos = buscar(f"reporte {numero} columnas campos secciones", top_k=10, reporte=numero)
    ctx, fuentes = construir_contexto(fragmentos)
    hist = construir_historial(historial or [])

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV. Responde SOLO en español.
{REGLAS}
{hist}

Lista los campos del reporte {numero} en este formato de tabla exacto en español:
| # | Campo | Origen | Calculable |
|---|-------|--------|------------|
(Origen: PERSONA / LINEA_CREDITO / CALCULADO / CATALOGO / DEFAULT)
(Calculable: Sí / No)

FRAGMENTOS:
{ctx}

Responde SOLO en español con la tabla indicada.
[/INST]"""

    return {"respuesta": llm.invoke(prompt), "fuentes": fuentes, "reporte": numero}


def consultar_libre(pregunta, reporte=None, historial=None):
    fragmentos = buscar(pregunta, reporte=reporte)
    ctx, fuentes = construir_contexto(fragmentos)
    hist = construir_historial(historial or [])

    prompt = f"""[INST] Eres experto en regulación bancaria mexicana CNBV. Responde SOLO en español.
{REGLAS}
{hist}

Responde la pregunta en español usando solo los fragmentos.
Cita página y documento cuando uses información específica.

FRAGMENTOS:
{ctx}

PREGUNTA: {pregunta}

Responde SOLO en español.
[/INST]"""

    return {"respuesta": llm.invoke(prompt), "fuentes": fuentes}