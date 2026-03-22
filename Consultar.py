import os
import pickle
import numpy as np
import faiss
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from pymongo import MongoClient
from columnas_0430 import resolver_campo

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
        print("📦 Cargando índice FAISS...")
        _indice = faiss.read_index("faiss_index.bin")
        with open("faiss_metadatos.pkl", "rb") as f:
            _metadatos = pickle.load(f)
        print(f"   {_indice.ntotal} vectores listos\n")
    return _indice, _metadatos

# ── Búsqueda semántica con FAISS ─────────────────────────
def buscar_faiss(pregunta, top_k=6, filtro_fuente=None):
    indice, metadatos = cargar_indice()
    vector = np.array([embeddings.embed_query(pregunta)], dtype=np.float32)
    faiss.normalize_L2(vector)

    k = top_k * 3 if filtro_fuente else top_k
    scores, indices = indice.search(vector, k)

    resultados = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        doc = metadatos[idx]
        if filtro_fuente and filtro_fuente.lower() not in doc["fuente"].lower():
            continue
        resultados.append((float(score), doc))
        if len(resultados) >= top_k:
            break
    return resultados

# ── Búsqueda por texto exacto en MongoDB ─────────────────
def buscar_texto(terminos, filtro_fuente=None, top_k=4):
    query = {"$text": {"$search": terminos}}
    if filtro_fuente:
        query["fuente"] = {"$regex": filtro_fuente, "$options": "i"}

    resultados = coleccion.find(
        query,
        {"texto": 1, "fuente": 1, "pagina": 1, "score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]).limit(top_k)

    return [(1.0, {"texto": d["texto"], "fuente": d["fuente"], "pagina": d["pagina"]})
            for d in resultados]

# ── Búsqueda híbrida ─────────────────────────────────────
def buscar_hibrido(pregunta, terminos_clave=None, top_k=8, filtro_fuente=None):
    sem = buscar_faiss(pregunta, top_k=6, filtro_fuente=filtro_fuente)
    terminos = terminos_clave if terminos_clave else pregunta
    txt = buscar_texto(terminos, filtro_fuente=filtro_fuente, top_k=4)

    vistos = set()
    combinados = []
    for score, doc in sem + txt:
        clave = f"{doc['fuente']}_{doc['pagina']}"
        if clave not in vistos:
            vistos.add(clave)
            combinados.append((score, doc))

    return combinados[:top_k]

# ── Construir contexto ───────────────────────────────────
def construir_contexto(fragmentos):
    contexto = ""
    fuentes = []
    for score, doc in fragmentos:
        contexto += f"\n[{doc['fuente']} | Página {doc['pagina']+1}]\n{doc['texto']}\n"
        fuentes.append(f"{doc['fuente']} p.{doc['pagina']+1}")
    return contexto, fuentes

# ── Instrucciones base ───────────────────────────────────
BASE = """REGLAS ESTRICTAS:
1. Usa ÚNICAMENTE información de los fragmentos proporcionados
2. NO uses conocimiento externo
3. NO inventes datos, URLs ni referencias
4. Si algo no está en los fragmentos escribe exactamente: No encontrado en los documentos
5. Responde siempre en español
"""

DEFINICIONES_CAMPO = """DEFINICIONES:
- ORIGEN indica de dónde viene el dato:
    * PERSONA       → dato del acreditado que proporciona el banco
    * LINEA_CREDITO → dato de la línea de crédito que proporciona el banco
    * CATALOGO      → clave de un catálogo oficial CNBV
    * CALCULADO     → resultado de una fórmula matemática
    * DEFAULT       → valor fijo o vacío por regla

- TIPO indica cómo se obtiene:
    * captura manual → el banco lo toma de sus sistemas
    * calculado      → se aplica una fórmula
    * catálogo       → se selecciona de lista predefinida

REGLA: ORIGEN y TIPO deben ser consistentes.
PERSONA o LINEA_CREDITO → captura manual
CALCULADO → calculado
CATALOGO → catálogo
"""

# ══════════════════════════════════════════════════════════
# FUNCIONES ESPECIALIZADAS
# ══════════════════════════════════════════════════════════

def consultar_campo(argumento):
    campo, filtro = resolver_campo(argumento)

    if filtro:
        print(f"\n🔍 Campo: {campo} | Reporte: {filtro}")
        pregunta = f"campo {campo} reporte {filtro} origen descripcion"
        contexto_reporte = f"en el reporte {filtro}"
    else:
        print(f"\n🔍 Campo: {campo} | Todos los reportes")
        pregunta = f"campo {campo} origen descripcion"
        contexto_reporte = "en los reportes regulatorios"

    fragmentos = buscar_hibrido(pregunta, terminos_clave=campo, filtro_fuente=filtro)
    contexto, fuentes = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres un experto en regulación bancaria CNBV.
{BASE}
{DEFINICIONES_CAMPO}

Responde sobre el campo "{campo}" {contexto_reporte}.
Usa EXACTAMENTE este formato, sin agregar nada más:

- CAMPO: {campo}
- ORIGEN: [PERSONA / LINEA_CREDITO / CATALOGO / CALCULADO / DEFAULT]
- TIPO: [captura manual / calculado / catálogo]
- FORMULA: [fórmula si existe, si no: No aplica]
- NOTAS: [reglas especiales de los fragmentos, si no hay: Ninguna]

FRAGMENTOS:
{contexto}
[/INST]"""

    respuesta = llm.invoke(prompt)
    print(f"\n💬 {respuesta}")
    print(f"\n📋 Fuentes: {', '.join(set(fuentes))}")
    return respuesta

def consultar_calculo(argumento):
    campo, filtro = resolver_campo(argumento)

    if filtro:
        print(f"\n🧮 Cálculo: {campo} | Reporte: {filtro}")
        pregunta = f"calcular {campo} reporte {filtro} formula metodologia"
    else:
        print(f"\n🧮 Cálculo: {campo} | Todos los reportes")
        pregunta = f"calcular {campo} formula metodologia anexo"

    fragmentos = buscar_hibrido(pregunta, terminos_clave=campo, top_k=10, filtro_fuente=filtro)
    contexto, fuentes = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres un experto en regulación bancaria CNBV.
{BASE}

Explica el cálculo de "{campo}".
Usa EXACTAMENTE este formato, sin agregar nada más:

- CAMPO: {campo}
- SE PUEDE CALCULAR: [Sí / No]
- FORMULA: [fórmula exacta del documento, si no existe: No especificada]
- DATOS NECESARIOS: [qué datos se requieren]
- REFERENCIA: [anexo o sección de los fragmentos, si no hay: No especificada]
- OBSERVACIONES: [casos especiales, si no hay: Ninguna]

FRAGMENTOS:
{contexto}
[/INST]"""

    respuesta = llm.invoke(prompt)
    print(f"\n💬 {respuesta}")
    print(f"\n📋 Fuentes: {', '.join(set(fuentes))}")
    return respuesta

def consultar_reporte(numero_reporte):
    pregunta = f"reporte {numero_reporte} columnas campos secciones"
    fragmentos = buscar_hibrido(pregunta, terminos_clave=numero_reporte, top_k=10, filtro_fuente=numero_reporte)
    contexto, fuentes = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres un experto en regulación bancaria CNBV.
{BASE}

Lista los campos del reporte {numero_reporte} de los fragmentos.
Usa EXACTAMENTE este formato de tabla, sin agregar nada más:

| # | Campo | Origen | Calculable |
|---|-------|--------|------------|

Origen: PERSONA / LINEA_CREDITO / CALCULADO / CATALOGO / DEFAULT
Calculable: Sí / No

FRAGMENTOS:
{contexto}
[/INST]"""

    print(f"\n📋 Reporte: {numero_reporte}")
    respuesta = llm.invoke(prompt)
    print(f"\n💬 {respuesta}")
    print(f"\n📋 Fuentes: {', '.join(set(fuentes))}")
    return respuesta

def consultar_libre(pregunta):
    fragmentos = buscar_hibrido(pregunta)
    contexto, fuentes = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres un experto en regulación bancaria mexicana CNBV.
{BASE}

Responde la pregunta usando solo los fragmentos.
Menciona página y documento cuando cites información específica.

FRAGMENTOS:
{contexto}

PREGUNTA: {pregunta}
[/INST]"""

    print(f"\n🔍 Consulta: {pregunta}")
    respuesta = llm.invoke(prompt)
    print(f"\n💬 {respuesta}")
    print(f"\n📋 Fuentes: {', '.join(set(fuentes))}")
    return respuesta

# ── Modo interactivo ─────────────────────────────────────
if __name__ == "__main__":
    print("🏦 Base de Conocimiento CNBV")
    print("=" * 50)
    cargar_indice()

    print("Comandos:")
    print("  campo <nombre> [reporte]   → info del campo")
    print("  campo <número> <reporte>   → info por número de columna")
    print("  calculo <nombre> [reporte] → cómo se calcula")
    print("  reporte <numero>           → campos del reporte")
    print("  <pregunta libre>           → consulta general")
    print("  salir\n")
    print("Ejemplos:")
    print("  campo 9 0430")
    print("  campo RFC 0430")
    print("  calculo 20 0430")
    print("  reporte 0430\n")

    while True:
        entrada = input("❓ ").strip()
        if not entrada:
            continue
        if entrada.lower() == "salir":
            break

        partes = entrada.split(" ", 1)
        comando = partes[0].lower()
        argumento = partes[1] if len(partes) > 1 else ""

        if comando == "campo" and argumento:
            consultar_campo(argumento)
        elif comando == "calculo" and argumento:
            consultar_calculo(argumento)
        elif comando == "reporte" and argumento:
            consultar_reporte(argumento)
        else:
            consultar_libre(entrada)