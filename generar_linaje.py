"""
generar_linaje.py
Genera automáticamente el diccionario de linaje para un reporte CNBV
consultando el Knowledge Base (PDFs indexados en Atlas) + Mistral.

Uso:
  python generar_linaje.py 0431
  python generar_linaje.py 0431 --excel CASO_DE_PRUEBA_0431.xlsx
  python generar_linaje.py 0431 --revisar   (muestra resultados sin guardar)

El resultado se guarda en la colección linaje_{reporte} de MongoDB Atlas.
"""

import os
import sys
import json
import time
import argparse
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_ollama import OllamaLLM

load_dotenv()

mongo = MongoClient(os.getenv("MONGO_URI"))
db    = mongo[os.getenv("DB_NAME")]

VOYAGE_KEY       = os.getenv("VOYAGE_API_KEY")
VOYAGE_EMBED_URL = "https://ai.mongodb.com/v1/embeddings"
VOYAGE_RERANK_URL = "https://ai.mongodb.com/v1/rerank"

llm = OllamaLLM(
    model="mistral:7b-instruct",
    base_url=os.getenv("OLLAMA_URL"),
    temperature=0
)

# ══════════════════════════════════════════════════════════
# BÚSQUEDA EN EL KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════

def embedding(texto):
    r = requests.post(
        VOYAGE_EMBED_URL,
        headers={"Authorization": f"Bearer {VOYAGE_KEY}", "Content-Type": "application/json"},
        json={"input": [texto], "model": "voyage-finance-2"}
    )
    if r.status_code != 200:
        raise Exception(f"Voyage error {r.status_code}: {r.text}")
    return r.json()["data"][0]["embedding"]


def reranker(pregunta, fragmentos, top_k=3):
    if not fragmentos:
        return fragmentos
    textos = [f["texto"] for f in fragmentos]
    r = requests.post(
        VOYAGE_RERANK_URL,
        headers={"Authorization": f"Bearer {VOYAGE_KEY}", "Content-Type": "application/json"},
        json={"query": pregunta, "documents": textos, "model": "rerank-2.5", "top_k": top_k}
    )
    if r.status_code != 200:
        return fragmentos[:top_k]
    data = r.json().get("data", [])
    return [fragmentos[item["index"]] for item in data]


def buscar_en_kb(pregunta, reporte, top_k=3):
    """Busca fragmentos relevantes en el Knowledge Base para un campo y reporte"""
    vector = embedding(pregunta)
    pipeline = [
        {"$vectorSearch": {
            "index": "vector_index",
            "path": "vector",
            "queryVector": vector,
            "numCandidates": 100,
            "limit": 20
        }},
        {"$project": {"texto": 1, "fuente": 1, "pagina": 1, "_id": 0}}
    ]
    resultados = list(db["documentos"].aggregate(pipeline))
    # Filtrar por reporte
    resultados = [r for r in resultados if reporte in r.get("fuente", "")]
    if not resultados:
        # Si no hay resultados del reporte específico, usar todos
        resultados = list(db["documentos"].aggregate(pipeline))
    return reranker(pregunta, resultados, top_k=top_k)


def construir_contexto(fragmentos):
    return "\n".join([
        f"[{f['fuente']} | p.{f['pagina']+1}]\n{f['texto']}"
        for f in fragmentos
    ])


# ══════════════════════════════════════════════════════════
# EXTRACCIÓN DE LINAJE DESDE PDF
# ══════════════════════════════════════════════════════════

def extraer_info_campo(nombre_campo, numero, reporte):
    """
    Consulta el Knowledge Base y usa Mistral para extraer la info del campo.
    Devuelve un dict con todos los campos del linaje.
    """
    print(f"  🔍 Analizando campo {numero}: {nombre_campo}...")

    # Buscar fragmentos relevantes
    query = f"{nombre_campo} campo {numero} reporte {reporte} origen obligatorio formato catálogo condiciones"
    fragmentos = buscar_en_kb(query, reporte, top_k=4)
    ctx = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV. Analiza el campo "{nombre_campo}" del reporte {reporte}.

Usando SOLO los fragmentos proporcionados, responde en formato JSON exacto con estas claves.
Si no encuentras la información, usa "No especificado".

{{
  "origen": "Insumo PERSONA / Insumo LINEA_CREDITO / Insumo CREDITO / Campo calculado / Campo default",
  "hoja_excel": "PERSONA / LINEA_CREDITO / CREDITO / —",
  "columna_excel": "nombre exacto de la columna en el Excel / —",
  "tipo": "Manual / Calculado / Default / Catálogo",
  "obligatorio": "Sí / Condicional / No",
  "formato": "descripción del formato y longitud",
  "catalogo": "nombre del catálogo CNBV si aplica / —",
  "condiciones": "cuándo aplica, condiciones especiales",
  "relacionados": ["lista", "de", "campos", "relacionados"]
}}

FRAGMENTOS:
{ctx}

Responde SOLO con el JSON, sin explicación adicional.
[/INST]"""

    try:
        respuesta = llm.invoke(prompt).strip()

        # Limpiar la respuesta para extraer JSON
        if "```" in respuesta:
            respuesta = respuesta.split("```")[1]
            if respuesta.startswith("json"):
                respuesta = respuesta[4:]
        respuesta = respuesta.strip()

        # Intentar parsear JSON
        data = json.loads(respuesta)

        # Construir linaje texto
        hoja = data.get("hoja_excel", "—")
        col  = data.get("columna_excel", "—")
        origen = data.get("origen", "")

        if "PERSONA" in origen:
            linaje = f"Insumo PERSONA — columna {col}"
        elif "LINEA_CREDITO" in origen:
            linaje = f"Insumo LINEA_CREDITO — columna {col}"
        elif "CREDITO" in origen:
            linaje = f"Insumo CREDITO — columna {col}"
        elif "calculado" in origen.lower():
            linaje = f"Campo calculado — {data.get('condiciones', '')[:80]}"
        elif "default" in origen.lower():
            linaje = f"Campo default — {data.get('condiciones', '')[:80]}"
        else:
            linaje = origen

        return {
            "reporte":       reporte,
            "numero":        numero,
            "clave":         nombre_campo.upper().replace(" ", "_").replace("(", "").replace(")", ""),
            "nombre":        nombre_campo,
            "linaje":        linaje,
            "origen":        data.get("origen", "").split()[0] if data.get("origen") else "—",
            "hoja_excel":    hoja,
            "columna_excel": col,
            "tipo":          data.get("tipo", "—"),
            "obligatorio":   data.get("obligatorio", "—"),
            "formato":       data.get("formato", "—"),
            "catalogo":      data.get("catalogo", "—"),
            "condiciones":   data.get("condiciones", "—"),
            "relacionados":  data.get("relacionados", []),
        }

    except json.JSONDecodeError as e:
        print(f"    ⚠️  Error parseando JSON para {nombre_campo}: {e}")
        print(f"    Respuesta: {respuesta[:200]}")
        # Devolver estructura mínima
        return {
            "reporte":       reporte,
            "numero":        numero,
            "clave":         nombre_campo.upper().replace(" ", "_"),
            "nombre":        nombre_campo,
            "linaje":        "No determinado — revisar manualmente",
            "origen":        "—",
            "hoja_excel":    "—",
            "columna_excel": "—",
            "tipo":          "—",
            "obligatorio":   "—",
            "formato":       "—",
            "catalogo":      "—",
            "condiciones":   "Revisar manualmente en el CUB",
            "relacionados":  [],
        }


# ══════════════════════════════════════════════════════════
# OBTENER LISTA DE CAMPOS DEL REPORTE
# ══════════════════════════════════════════════════════════

def obtener_campos_del_reporte(reporte):
    """
    Intenta obtener la lista de campos del reporte desde:
    1. columnas_{reporte}.py si existe
    2. El Knowledge Base (PDF del CUB)
    """
    # Intentar desde columnas_{reporte}.py
    try:
        import importlib
        mod = importlib.import_module(f"columnas_{reporte}")
        if hasattr(mod, "COLUMNAS") and reporte in mod.COLUMNAS:
            campos = mod.COLUMNAS[reporte]
            print(f"✅ Campos obtenidos de columnas_{reporte}.py: {len(campos)} campos")
            return [(num, nombre) for num, nombre in campos.items()]
    except ImportError:
        pass

    # Intentar desde el Knowledge Base
    print(f"📚 Buscando campos del reporte {reporte} en el Knowledge Base...")
    fragmentos = buscar_en_kb(f"reporte {reporte} campos columnas estructura lista", reporte, top_k=5)
    ctx = construir_contexto(fragmentos)

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV.
Lista TODOS los campos del reporte {reporte} con su número y nombre exacto.
Usa SOLO la información de los fragmentos.

Responde en formato JSON exacto:
{{
  "campos": [
    {{"numero": 1, "nombre": "Nombre del campo"}},
    {{"numero": 2, "nombre": "Nombre del campo"}},
    ...
  ]
}}

FRAGMENTOS:
{ctx}

Responde SOLO con el JSON.
[/INST]"""

    try:
        respuesta = llm.invoke(prompt).strip()
        if "```" in respuesta:
            respuesta = respuesta.split("```")[1]
            if respuesta.startswith("json"):
                respuesta = respuesta[4:]
        data = json.loads(respuesta.strip())
        campos = data.get("campos", [])
        print(f"✅ Campos extraídos del Knowledge Base: {len(campos)} campos")
        return [(c["numero"], c["nombre"]) for c in campos]
    except Exception as e:
        print(f"❌ Error obteniendo campos: {e}")
        return []


# ══════════════════════════════════════════════════════════
# LEER EXCEL DE SALIDA ESPERADA (opcional)
# ══════════════════════════════════════════════════════════

def leer_excel_salida(archivo_excel, reporte):
    """
    Lee la pestaña SALIDA ESPERADA del Excel para obtener el origen de cada campo.
    Devuelve dict: {nombre_campo: {hoja_excel, columna_excel, linaje}}
    """
    try:
        import pandas as pd
        xl = pd.read_excel(archivo_excel, sheet_name=None, header=None)

        # Buscar pestaña de salida esperada
        hoja_salida = None
        for nombre in xl.keys():
            if "SALIDA" in nombre.upper() or reporte in nombre:
                hoja_salida = nombre
                break

        if not hoja_salida:
            print(f"⚠️  No se encontró pestaña SALIDA ESPERADA en {archivo_excel}")
            return {}

        df = xl[hoja_salida]
        linajes = {}

        # Fila 0 = linaje, Fila 1 = nombre del campo
        for col in df.columns:
            linaje_texto = str(df.iloc[0, col]) if pd.notna(df.iloc[0, col]) else ""
            campo_nombre = str(df.iloc[1, col]) if pd.notna(df.iloc[1, col]) else ""

            if not campo_nombre or campo_nombre == "nan":
                continue

            # Parsear el texto de linaje
            hoja = "—"
            columna = "—"

            if "INSUMO PERSONA" in linaje_texto.upper():
                hoja = "PERSONA"
                # Extraer nombre de columna entre paréntesis
                if "(" in linaje_texto and ")" in linaje_texto:
                    columna = linaje_texto[linaje_texto.rfind("(")+1:linaje_texto.rfind(")")]
            elif "INSUMO LINEA" in linaje_texto.upper() or "LÍNEA" in linaje_texto.upper():
                hoja = "LINEA_CREDITO"
                if "(" in linaje_texto and ")" in linaje_texto:
                    columna = linaje_texto[linaje_texto.rfind("(")+1:linaje_texto.rfind(")")]
            elif "INSUMO CREDITO" in linaje_texto.upper() or "CRÉDITO" in linaje_texto.upper():
                hoja = "CREDITO"
                if "(" in linaje_texto and ")" in linaje_texto:
                    columna = linaje_texto[linaje_texto.rfind("(")+1:linaje_texto.rfind(")")]

            linajes[campo_nombre.strip()] = {
                "hoja_excel":    hoja,
                "columna_excel": columna,
                "linaje_raw":    linaje_texto,
            }

        print(f"✅ Linaje leído del Excel: {len(linajes)} campos")
        return linajes

    except Exception as e:
        print(f"⚠️  Error leyendo Excel: {e}")
        return {}


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

def generar_linaje(reporte, archivo_excel=None, solo_revisar=False):
    print("=" * 60)
    print(f"🏦 Generador de Linaje — Reporte {reporte}")
    print(f"   Excel: {archivo_excel or 'No proporcionado'}")
    print(f"   Modo:  {'Revisión (sin guardar)' if solo_revisar else 'Guardar en MongoDB'}")
    print("=" * 60)

    # 1. Obtener lista de campos
    campos = obtener_campos_del_reporte(reporte)
    if not campos:
        print("❌ No se pudieron obtener los campos del reporte")
        sys.exit(1)

    print(f"\n📋 {len(campos)} campos a procesar\n")

    # 2. Leer Excel si está disponible
    linaje_excel = {}
    if archivo_excel:
        linaje_excel = leer_excel_salida(archivo_excel, reporte)

    # 3. Procesar cada campo
    resultados = []
    errores = []

    for i, (numero, nombre) in enumerate(campos, 1):
        print(f"\n[{i:02d}/{len(campos)}] Campo {numero}: {nombre}")

        doc = extraer_info_campo(nombre, numero, reporte)

        # Enriquecer con datos del Excel si están disponibles
        if nombre in linaje_excel:
            excel_data = linaje_excel[nombre]
            if excel_data["hoja_excel"] != "—":
                doc["hoja_excel"]    = excel_data["hoja_excel"]
                doc["columna_excel"] = excel_data["columna_excel"]
                print(f"    📊 Excel: {excel_data['hoja_excel']} → {excel_data['columna_excel']}")

        resultados.append(doc)

        if doc["origen"] == "—":
            errores.append(f"Campo {numero} ({nombre}) — origen no determinado")

        # Pausa para no saturar Ollama
        time.sleep(1)

    # 4. Mostrar resumen
    print(f"\n{'='*60}")
    print(f"✅ {len(resultados)} campos procesados")
    if errores:
        print(f"⚠️  {len(errores)} campos requieren revisión manual:")
        for e in errores:
            print(f"   - {e}")

    # 5. Guardar o mostrar
    if solo_revisar:
        print("\n📋 RESULTADOS (modo revisión):\n")
        for doc in resultados:
            print(f"  [{doc['numero']}] {doc['nombre']}")
            print(f"       Origen: {doc['origen']} | Hoja: {doc['hoja_excel']} | Col: {doc['columna_excel']}")
            print(f"       Obligatorio: {doc['obligatorio']} | Formato: {doc['formato'][:40]}")
            print()
    else:
        col_name = f"linaje_{reporte}"
        col = db[col_name]
        col.delete_many({"reporte": reporte})
        col.insert_many(resultados)
        col.create_index([("reporte", 1), ("numero", 1)], unique=True)
        col.create_index([("reporte", 1), ("clave", 1)])
        print(f"\n✅ {len(resultados)} campos guardados en colección '{col_name}'")
        print(f"⚠️  Revisa los {len(errores)} campos marcados antes de usar en producción")

    # 6. Exportar a JSON para revisión
    output_file = f"linaje_{reporte}_generado.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"💾 Exportado a {output_file} para revisión manual")

    return resultados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera linaje de campos para un reporte CNBV")
    parser.add_argument("reporte", help="Número del reporte (ej: 0431)")
    parser.add_argument("--excel", help="Archivo Excel de caso de pruebas (opcional)", default=None)
    parser.add_argument("--revisar", action="store_true", help="Solo revisar, sin guardar en MongoDB")
    args = parser.parse_args()

    generar_linaje(
        reporte=args.reporte,
        archivo_excel=args.excel,
        solo_revisar=args.revisar
    )