import os
import json
import hashlib
import requests
from datetime import datetime
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
docs      = db["documentos"]
cache     = db["cache"]
feedback  = db["feedback"]

VOYAGE_KEY          = os.getenv("VOYAGE_API_KEY")
VOYAGE_EMBED_URL    = "https://ai.mongodb.com/v1/embeddings"
VOYAGE_RERANK_URL   = "https://ai.mongodb.com/v1/rerank"
VOYAGE_MODEL        = "voyage-finance-2"
VOYAGE_RERANK_MODEL = "rerank-2.5"

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
# CACHÉ
# ══════════════════════════════════════════════════════════

SIMILITUD_MINIMA = 0.85  # umbral de similitud semántica para cache hit


def cache_key(pregunta, cmd, reporte):
    texto = f"{pregunta.lower().strip()}|{cmd}|{reporte or ''}"
    return hashlib.md5(texto.encode()).hexdigest()


def similitud_coseno(v1, v2):
    """Calcula similitud coseno entre dos vectores"""
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = sum(a ** 2 for a in v1) ** 0.5
    mag2 = sum(b ** 2 for b in v2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0
    return dot / (mag1 * mag2)


def buscar_cache(pregunta, cmd, reporte):
    # 1. Búsqueda exacta por MD5
    key = cache_key(pregunta, cmd, reporte)
    print(f"🔎 Buscando cache: {cmd} | {pregunta[:40]}")
    resultado = cache.find_one({"key": key})
    if resultado:
        print(f"⚡ Cache hit exacto: {pregunta[:50]}")
        return {"respuesta": resultado["respuesta"], "fuentes": resultado.get("fuentes", [])}

    # 2. Búsqueda semántica por similitud de embeddings
    # Si la pregunta contiene números, no usar cache semántico — podría confundir campos distintos
    import re
    tiene_numeros = bool(re.search(r'\b\d+\b', pregunta))
    if tiene_numeros:
        print(f"⏭️ Cache semántico omitido (pregunta con números)")
        return None

    try:
        vector_pregunta = embedding(pregunta)
        candidatos = list(cache.find(
            {"cmd": cmd, "vector": {"$exists": True}},
            {"pregunta": 1, "respuesta": 1, "fuentes": 1, "vector": 1, "_id": 0}
        ))

        mejor_score = 0
        mejor_resultado = None

        for c in candidatos:
            if not c.get("vector"):
                continue
            # Omitir candidatos con números diferentes a la pregunta actual
            numeros_candidato = set(re.findall(r'\b\d+\b', c.get('pregunta', '')))
            numeros_pregunta  = set(re.findall(r'\b\d+\b', pregunta))
            if numeros_candidato != numeros_pregunta:
                continue
            score = similitud_coseno(vector_pregunta, c["vector"])
            if score > mejor_score:
                mejor_score = score
                mejor_resultado = c

        if mejor_score >= SIMILITUD_MINIMA and mejor_resultado:
            print(f"⚡ Cache hit semántico ({mejor_score:.3f}): {mejor_resultado['pregunta'][:50]}")
            return {"respuesta": mejor_resultado["respuesta"], "fuentes": mejor_resultado.get("fuentes", [])}

        print(f"❌ Cache miss (mejor score: {mejor_score:.3f})")
    except Exception as e:
        print(f"⚠️ Error en cache semántico: {e}")

    return None


def guardar_cache(pregunta, cmd, reporte, respuesta, fuentes):
    key = cache_key(pregunta, cmd, reporte)
    try:
        vector = embedding(pregunta)
    except:
        vector = None

    cache.update_one(
        {"key": key},
        {"$set": {
            "key": key,
            "pregunta": pregunta,
            "cmd": cmd,
            "reporte": reporte,
            "respuesta": respuesta,
            "fuentes": fuentes,
            "vector": vector,
            "timestamp": datetime.utcnow()
        }},
        upsert=True
    )
    print(f"💾 Cache guardado: {cmd} | {pregunta[:40]}")


# ══════════════════════════════════════════════════════════
# FEW-SHOT DESDE FEEDBACK
# ══════════════════════════════════════════════════════════

def buscar_ejemplos(pregunta, cmd, reporte, max_ejemplos=3):
    """
    Busca en feedback respuestas bien calificadas (👍) similares a la pregunta actual.
    Las devuelve formateadas como ejemplos few-shot para el prompt.
    """
    try:
        # Obtener preguntas con voto positivo del mismo comando
        votos_positivos = list(feedback.find(
            {"voto": "up", "cmd": cmd},
            {"pregunta": 1, "respuesta": 1, "_id": 0}
        ).sort("timestamp", -1).limit(50))

        if not votos_positivos:
            return ""

        # Filtrar los más relevantes por palabras en común
        palabras_query = set(pregunta.lower().split())
        scored = []
        for voto in votos_positivos:
            palabras_ejemplo = set(voto["pregunta"].lower().split())
            coincidencias = len(palabras_query & palabras_ejemplo)
            if coincidencias > 0:
                scored.append((coincidencias, voto))

        scored.sort(key=lambda x: x[0], reverse=True)
        mejores = [v for _, v in scored[:max_ejemplos]]

        if not mejores:
            return ""

        ejemplos = "\nEJEMPLOS DE RESPUESTAS BIEN CALIFICADAS (úsalos como referencia de estilo y precisión):\n"
        for i, ej in enumerate(mejores, 1):
            ejemplos += f"\nEjemplo {i}:\nPregunta: {ej['pregunta']}\nRespuesta: {ej['respuesta'][:400]}\n"

        print(f"📚 Few-shot: {len(mejores)} ejemplos encontrados para '{pregunta[:30]}'")
        return ejemplos

    except Exception as e:
        print(f"⚠️ Error buscando ejemplos: {e}")
        return ""


# ══════════════════════════════════════════════════════════
# NÚCLEO
# ══════════════════════════════════════════════════════════

def embedding(texto):
    r = requests.post(
        VOYAGE_EMBED_URL,
        headers={"Authorization": f"Bearer {VOYAGE_KEY}", "Content-Type": "application/json"},
        json={"input": [texto], "model": VOYAGE_MODEL}
    )
    if r.status_code != 200:
        raise Exception(f"Voyage embed error {r.status_code}: {r.text}")
    return r.json()["data"][0]["embedding"]


def reranker(pregunta, fragmentos, top_k=5):
    if not fragmentos:
        return fragmentos

    textos = [f["texto"] for f in fragmentos]

    r = requests.post(
        VOYAGE_RERANK_URL,
        headers={"Authorization": f"Bearer {VOYAGE_KEY}", "Content-Type": "application/json"},
        json={
            "query": pregunta,
            "documents": textos,
            "model": VOYAGE_RERANK_MODEL,
            "top_k": top_k
        }
    )

    if r.status_code != 200:
        return fragmentos[:top_k]

    data = r.json().get("data", [])
    print(f"🔀 Reranker: {len(fragmentos)} fragmentos → top {len(data)}")
    for item in data:
        print(f"   Score: {item['relevance_score']:.3f} | idx: {item['index']}")

    reranked = []
    for item in data:
        frag = fragmentos[item["index"]].copy()
        frag["rerank_score"] = item["relevance_score"]
        reranked.append(frag)

    return reranked


def generar_respuesta_hipotetica(pregunta):
    """
    HyDE — Hypothetical Document Embeddings
    Genera una respuesta hipotética a la pregunta para mejorar la búsqueda semántica.
    El embedding de una respuesta hipotética es mucho más similar a los fragmentos reales
    que el embedding de la pregunta directa.
    """
    prompt = f"""[INST] Eres experto en regulación bancaria CNBV.
Escribe un párrafo corto (máximo 80 palabras) que sería la respuesta ideal a esta pregunta,
usando terminología técnica regulatoria. NO uses conocimiento inventado, solo el estilo.
Si no sabes la respuesta exacta, escribe algo plausible con el vocabulario correcto.

Pregunta: {pregunta}
Respuesta hipotética:[/INST]"""
    try:
        respuesta = llm.invoke(prompt).strip()
        # Si es muy larga, recortar
        palabras = respuesta.split()
        if len(palabras) > 100:
            respuesta = ' '.join(palabras[:100])
        print(f"💭 HyDE: {respuesta[:80]}…")
        return respuesta
    except:
        return pregunta


def expandir_query(pregunta):
    prompt = f"""[INST] Eres un asistente de búsqueda en documentos regulatorios CNBV.
Tu única tarea es extraer las palabras clave más importantes de la pregunta para buscar en documentos.
NO inventes información. NO respondas la pregunta. SOLO extrae palabras clave de lo que se pregunta.
Devuelve máximo 10 palabras clave separadas por espacios, sin explicación ni puntuación.

Ejemplos:
Pregunta: ¿Cuáles son los campos del reporte 0430?
Palabras clave: campos reporte 0430 columnas estructura

Pregunta: ¿Cómo se calcula el RFC del acreditado?
Palabras clave: RFC acreditado cálculo formato validación

Pregunta: ¿Qué es el tipo de cartera?
Palabras clave: tipo cartera definición valores catálogo

Pregunta: {pregunta}
Palabras clave:[/INST]"""
    query_expandida = llm.invoke(prompt).strip()
    # Si la respuesta es muy larga, es que alucinó — usar pregunta original
    if len(query_expandida.split()) > 20:
        print(f"⚠️ Query expansion falló, usando original")
        return pregunta
    print(f"🔍 Query original: {pregunta}")
    print(f"🔍 Query expandida: {query_expandida}")
    return query_expandida


def buscar(pregunta, top_k=5, reporte=None):
    # Query expansion deshabilitada — voyage-finance-2 entiende mejor la pregunta original
    # Para rehabilitar: descomentar las siguientes líneas y reemplazar embedding(pregunta)
    # query_expandida = expandir_query(pregunta)
    # texto_busqueda = f"{pregunta} {query_expandida}".strip()
    # vector = embedding(texto_busqueda)
    vector = embedding(pregunta)
    candidatos = top_k * 4

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "vector",
                "queryVector": vector,
                "numCandidates": 300,
                "limit": candidatos
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
        for d in docs.find(filtro, {"texto": 1, "fuente": 1, "pagina": 1, "_id": 0}).limit(5):
            clave = f"{d['fuente']}_{d['pagina']}"
            if clave not in vistos:
                vistos.add(clave)
                resultados.append({**d, "score": 1.0})
    except:
        pass

    return reranker(pregunta, resultados, top_k=top_k)


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


def respuesta_campos_calculados(reporte):
    try:
        with open(f"analisis_{reporte}.json", "r", encoding="utf-8") as f:
            analisis = json.load(f)
        calculados = [a for a in analisis if a.get("clasificacion") == "CALCULADO"]
        if not calculados:
            return None
        respuesta = f"Campos que se calculan automáticamente en el reporte {reporte}:\n\n"
        for c in calculados:
            formula = f"\n   → {c['formula']}" if c.get("formula") and c["formula"] != "null" else ""
            respuesta += f"• [{c['numero']}] {c['nombre']}{formula}\n"
        return respuesta
    except:
        return None


# ══════════════════════════════════════════════════════════
# FUNCIONES PÚBLICAS
# ══════════════════════════════════════════════════════════

def consultar_campo(argumento, historial=None):
    campo, reporte = resolver_campo(argumento)

    cached = buscar_cache(campo, "campo", reporte)
    if cached:
        return {**cached, "campo": campo, "reporte": reporte}

    fragmentos = buscar(f"{campo} origen descripcion reporte {reporte or ''}", reporte=reporte)
    ctx, fuentes = construir_contexto(fragmentos)
    hist = construir_historial(historial or [])
    ejemplos = buscar_ejemplos(campo, "campo", reporte)

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV. Responde SOLO en español.
{REGLAS}
{hist}
{ejemplos}

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

    respuesta = llm.invoke(prompt)
    print(f"🔵 Guardando cache campo: {campo}")
    guardar_cache(campo, "campo", reporte, respuesta, fuentes)
    return {"respuesta": respuesta, "fuentes": fuentes, "campo": campo, "reporte": reporte}


def consultar_calculo(argumento, historial=None):
    campo, reporte = resolver_campo(argumento)

    cached = buscar_cache(campo, "calculo", reporte)
    if cached:
        return {**cached, "campo": campo}

    fragmentos = buscar(f"calcular {campo} formula metodologia", top_k=6, reporte=reporte)
    ctx, fuentes = construir_contexto(fragmentos)
    hist = construir_historial(historial or [])
    ejemplos = buscar_ejemplos(campo, "calculo", reporte)

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV. Responde SOLO en español.
{REGLAS}
{hist}
{ejemplos}

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

    respuesta = llm.invoke(prompt)
    guardar_cache(campo, "calculo", reporte, respuesta, fuentes)
    return {"respuesta": respuesta, "fuentes": fuentes, "campo": campo}


def consultar_reporte(numero, historial=None):
    from columnas_0430 import COLUMNAS

    if numero in COLUMNAS:
        columnas = COLUMNAS[numero]
        respuesta = f"Campos del reporte {numero}:\n\n"
        for num, nombre in columnas.items():
            respuesta += f"{num}. {nombre}\n"
        return {"respuesta": respuesta, "fuentes": [], "reporte": numero}

    cached = buscar_cache(numero, "reporte", numero)
    if cached:
        return {**cached, "reporte": numero}

    fragmentos = buscar(f"reporte {numero} columnas campos secciones", top_k=6, reporte=numero)
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

    respuesta = llm.invoke(prompt)
    guardar_cache(numero, "reporte", numero, respuesta, fuentes)
    return {"respuesta": respuesta, "fuentes": fuentes, "reporte": numero}


def consultar_libre(pregunta, reporte=None, historial=None):
    pregunta_lower = pregunta.lower()

    reporte_mencionado = reporte
    if not reporte_mencionado:
        for r in ["0430", "0431", "0432"]:
            if r in pregunta:
                reporte_mencionado = r
                break

    if reporte_mencionado and any(w in pregunta_lower for w in ["calcul", "automátic", "automatico", "fórmula", "formula"]):
        resp = respuesta_campos_calculados(reporte_mencionado)
        if resp:
            return {"respuesta": resp, "fuentes": []}

    cached = buscar_cache(pregunta, "consulta", reporte)
    if cached:
        return cached

    query = expandir_query(pregunta)
    fragmentos = buscar(query, top_k=8, reporte=reporte)
    ctx, fuentes = construir_contexto(fragmentos)
    hist = construir_historial(historial or [])
    ejemplos = buscar_ejemplos(pregunta, "consulta", reporte)

    prompt = f"""[INST] Eres experto en regulación bancaria mexicana CNBV. Responde SOLO en español.
{REGLAS}
{hist}
{ejemplos}

Responde la pregunta en español usando solo los fragmentos.
Sé específico y concreto. Cita página y documento cuando uses información específica.

FRAGMENTOS:
{ctx}

PREGUNTA: {pregunta}

Responde SOLO en español.
[/INST]"""

    respuesta = llm.invoke(prompt)
    guardar_cache(pregunta, "consulta", reporte, respuesta, fuentes)
    return {"respuesta": respuesta, "fuentes": fuentes}