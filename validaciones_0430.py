# validaciones_0430.py
# Consulta validaciones de campos desde MongoDB Atlas (colección validaciones)
# Cargadas con cargar_validaciones.py

import os
import re
import unicodedata
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
_mongo = MongoClient(os.getenv("MONGO_URI"))
_db    = _mongo[os.getenv("DB_NAME")]
_col   = _db["validaciones"]

# Mapa número → nombre de concepto (como aparece en el Excel)
CONCEPTO_0430 = {
    1:  "1. PERIODO",
    2:  "2. CLAVE DE LA INSTITUCIÓN",
    3:  "3. REPORTE",
    4:  "4. IDENTIFICADOR DEL ACREDITADO ASIGNADO POR LA INSTITUCIÓN",
    5:  "5. NOMBRE DEL ACREDITADO",
    6:  "6. RFC DEL ACREDITADO",
    7:  "7. CURP DEL ACREDITADO",
    8:  "8. LOCALIDAD DEL DOMICILIO DEL ACREDITADO",
    9:  "9. MUNICIPIO DEL DOMICILIO DEL ACREDITADO",
    10: "10. ESTADO DEL DOMICILIO DEL ACREDITADO",
    11: "11. NACIONALIDAD DEL ACREDITADO",
    12: "12. ACTIVIDAD ECONÓMICA DEL ACREDITADO",
    13: "13. GRUPO DE RIESGO",
    14: "14. ACREDITADO RELACIONADO",
    15: "15. TIPO DE CARTERA",
    16: "16. TIPO DE ANEXO",
    17: "17. NÚMERO DE CONSULTA REALIZADA A LA SOCIEDAD DE INFORMACIÓN CREDITICIA",
    18: "18. CLAVE LEI",
    19: "19. IDENTIFICADOR DEL CRÉDITO ASIGNADO POR LA INSTITUCIÓN",
    20: "20. IDENTIFICADOR DEL CRÉDITO ASIGNADO METODOLOGÍA CNBV",
    21: "21. IDENTIFICADOR CRÉDITO LÍNEA GRUPAL ASIGNADO METODOLOGÍA CNBV",
    22: "22. DESTINO DEL CRÉDITO",
    23: "23. MONTO DE LA LÍNEA DE CRÉDITO AUTORIZADO VALORIZADO EN PESOS",
    24: "24. MONTO DE LA LÍNEA DE CRÉDITO AUTORIZADO EN LA MONEDA DE ORIGEN",
    25: "25. FECHA DE OTORGAMIENTO DE LA LÍNEA DE CRÉDITO",
    26: "26. FECHA DE VENCIMIENTO DE LA LÍNEA DE CRÉDITO",
    27: "27. FECHA MÁXIMA PARA DISPONER DE LOS RECURSOS",
    28: "28. FORMA DE LA DISPOSICIÓN",
    29: "29. LÍNEA DE CRÉDITO REVOCABLE O IRREVOCABLE",
    30: "30. PRELACIÓN DE PAGO",
    31: "31. PORCENTAJE DE PARTICIPACIONES FEDERALES",
    32: "32. CLAVE DE LA INSTITUCIÓN OTORGANTE",
    33: "33. TIPO DE ALTA DEL CRÉDITO",
    34: "34. MONEDA DE LA LÍNEA DE CRÉDITO",
    35: "35. TIPO DE TASA DE INTERÉS",
    36: "36. DIFERENCIAL SOBRE TASA DE REFERENCIA",
    37: "37. OPERACIÓN DE DIFERENCIAL SOBRE TASA DE REFERENCIA",
    38: "38. FRECUENCIA DE REVISIÓN DE LA TASA",
    39: "39. PERIODICIDAD PAGOS DE CAPITAL",
    40: "40. PERIODICIDAD PAGOS DE INTERESES",
    41: "41. NÚMERO DE MESES DE GRACIA PARA AMORTIZAR CAPITAL",
    42: "42. NÚMERO DE MESES DE GRACIA PARA PAGO DE INTERESES",
    43: "43. COMISIÓN DE APERTURA DEL CRÉDITO (TASA)",
    44: "44. COMISIÓN DE APERTURA DEL CRÉDITO (MONTO)",
    45: "45. COMISIÓN POR DISPOSICIÓN DEL CRÉDITO (TASA)",
    46: "46. COMISIÓN POR DISPOSICIÓN DEL CRÉDITO (MONTO)",
    47: "47. COSTO ANUAL TOTAL (CAT)",
    48: "48. MONTO DEL CRÉDITO SIMPLE O MONTO AUTORIZADO DE LA LÍNEA",
    49: "49. MONTO DE LAS PRIMAS ANUALES DE TODOS LOS SEGUROS OBLIGATORIOS",
    50: "50. LOCALIDAD EN DONDE SE DESTINARÁ EL CRÉDITO",
    51: "51. MUNICIPIO EN DONDE SE DESTINARÁ EL CRÉDITO",
    52: "52. ESTADO EN DONDE SE DESTINARÁ EL CRÉDITO",
    53: "53. ACTIVIDAD ECONÓMICA A LA QUE SE DESTINARÁ EL CRÉDITO",
}

# Alias para búsqueda por nombre
ALIAS_VAL = {
    "rfc": 6, "curp": 7, "nombre": 5, "periodo": 1,
    "reporte": 3, "clave institucion": 2,
    "id acreditado": 4, "localidad": 8, "municipio": 9, "estado": 10,
    "nacionalidad": 11, "actividad economica": 12, "grupo riesgo": 13,
    "acreditado relacionado": 14, "tipo cartera": 15, "tipo anexo": 16,
    "num sic": 17, "lei": 18, "id linea credito": 19, "id credito cnbv": 20,
    "id linea grupal": 21, "destino": 22, "monto valorizado": 23,
    "monto moneda origen": 24, "fecha otorgamiento": 25,
    "fecha vencimiento": 26, "fecha maxima": 27, "forma disposicion": 28,
    "revocable": 29, "prelacion": 30, "participaciones federales": 31,
    "clave inst otorgante": 32, "tipo alta": 33, "moneda": 34,
    "tipo tasa": 35, "diferencial tasa": 36, "operacion diferencial": 37,
    "frecuencia revision": 38, "periodicidad capital": 39,
    "periodicidad interes": 40, "meses gracia capital": 41,
    "meses gracia interes": 42, "comision apertura tasa": 43,
    "comision apertura monto": 44, "comision disposicion tasa": 45,
    "comision disposicion monto": 46, "cat": 47,
    "monto sin accesorios": 48, "primas anuales": 49,
    "localidad destino": 50, "municipio destino": 51,
    "estado destino": 52, "actividad economica destino": 53,
}


def normalizar(texto):
    texto = texto.lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto.replace('(', '').replace(')', '').replace('  ', ' ')


def buscar_validaciones(texto, reporte="0430"):
    """
    Busca las validaciones de un campo dado un texto libre.
    Devuelve (numero_campo, nombre_concepto, lista_de_validaciones)
    """
    texto_norm = normalizar(texto)
    numero = None

    # Por número directo — busca en MongoDB para cualquier reporte
    nums = re.findall(r'\b(\d{1,2})\b', texto.strip())
    for n in nums:
        num = int(n)
        if 1 <= num <= 60:  # rango válido de campos
            numero = num
            break

    # Por alias (solo para 0430 por ahora — tiene mapeo completo)
    if numero is None:
        for alias, num in ALIAS_VAL.items():
            if alias in texto_norm:
                numero = num
                break

    if numero is None:
        return None, None, []

    # Buscar en MongoDB — funciona para cualquier reporte
    validaciones = list(_col.find(
        {"serie": "R04C", "reporte": reporte, "numero_campo": numero},
        {"_id": 0, "id_validacion": 1, "descripcion": 1,
         "tipo_val": 1, "condicion": 1, "concepto": 1}
    ))

    # Obtener nombre del concepto desde MongoDB
    nombre = ""
    if validaciones:
        nombre = validaciones[0].get("concepto", "")
    elif reporte == "0430":
        nombre = CONCEPTO_0430.get(numero, "")

    return numero, nombre, validaciones


# ══════════════════════════════════════════════════════════
# BÚSQUEDA LIBRE POR DESCRIPCIÓN (vector search)
# ══════════════════════════════════════════════════════════

import requests as _requests

_VOYAGE_KEY       = os.getenv("VOYAGE_API_KEY")
_VOYAGE_EMBED_URL = "https://ai.mongodb.com/v1/embeddings"


def _embedding_val(texto):
    r = _requests.post(
        _VOYAGE_EMBED_URL,
        headers={"Authorization": f"Bearer {_VOYAGE_KEY}", "Content-Type": "application/json"},
        json={"input": [texto], "model": "voyage-finance-2"}
    )
    if r.status_code != 200:
        raise Exception(f"Voyage error {r.status_code}: {r.text}")
    return r.json()["data"][0]["embedding"]


def _similitud_coseno(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = sum(a ** 2 for a in v1) ** 0.5
    mag2 = sum(b ** 2 for b in v2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0
    return dot / (mag1 * mag2)


def _expandir_query_val(pregunta):
    """
    Usa Mistral para reformular la pregunta en términos técnicos regulatorios
    antes de hacer el embedding — mejora la búsqueda sobre descripciones del CUB.
    """
    from langchain_ollama import OllamaLLM
    _llm = OllamaLLM(model="mistral:7b-instruct", base_url=os.getenv("OLLAMA_URL"), temperature=0)

    prompt = f"""[INST] Eres experto en regulación bancaria CNBV.
Reformula esta pregunta usando términos técnicos del CUB (Catálogo Único de Banca) para buscar en una base de validaciones regulatorias.
Devuelve solo palabras clave técnicas separadas por espacios, sin explicación. Máximo 15 palabras.

Ejemplos:
Pregunta: ¿qué pasa si el RFC está mal formado?
Palabras clave: RFC formato longitud 13 caracteres alfanumérico validar estructura

Pregunta: validaciones de moneda extranjera
Palabras clave: moneda dólares divisas tipo cambio valorizado pesos conversión

Pregunta: ¿qué campos tienen catálogo INEGI?
Palabras clave: catálogo localidad municipio estado INEGI clave código

Pregunta: ¿cuándo un campo es condicional?
Palabras clave: condicional obligatorio opcional aplica cuando tipo cartera persona física

Pregunta: {pregunta}
Palabras clave:[/INST]"""

    try:
        resultado = _llm.invoke(prompt).strip()
        # Si alucinó (demasiado largo), usar original
        if len(resultado.split()) > 20:
            print(f"⚠️ Query expansion falló, usando original")
            return pregunta
        print(f"🔍 Query original:  {pregunta}")
        print(f"🔍 Query expandida: {resultado}")
        return f"{pregunta} {resultado}"
    except Exception as e:
        print(f"⚠️ Error expandiendo query: {e}")
        return pregunta


def buscar_validaciones_libre(pregunta, reporte="0430", top_k=10, threshold=0.45):
    """
    Búsqueda semántica sobre descripciones de validaciones usando embeddings.
    Usa query expansion con Mistral para mejorar la búsqueda con vocabulario técnico.

    Para preguntas abiertas como:
    - "¿qué campos no pueden ir vacíos?"
    - "¿qué validaciones aplican para moneda extranjera?"
    - "¿qué campos tienen catálogo INEGI?"

    Devuelve lista de validaciones ordenadas por similitud.
    """
    print(f"🔍 Búsqueda libre validaciones: {pregunta[:50]}")

    # Expandir query con vocabulario técnico
    query_expandida = _expandir_query_val(pregunta)

    # Calcular embedding de la query expandida
    vector_pregunta = _embedding_val(query_expandida)

    # Obtener todos los documentos con vector del reporte
    candidatos = list(_col.find(
        {"serie": "R04C", "reporte": reporte, "vector": {"$exists": True}},
        {"_id": 0, "id_validacion": 1, "descripcion": 1,
         "tipo_val": 1, "condicion": 1, "concepto": 1,
         "numero_campo": 1, "vector": 1}
    ))

    if not candidatos:
        print("⚠️ No hay vectores en la colección validaciones — corre cargar_validaciones.py --vectores")
        return []

    # Calcular similitud
    scored = []
    for c in candidatos:
        if not c.get("vector"):
            continue
        score = _similitud_coseno(vector_pregunta, c["vector"])
        if score >= threshold:
            c_clean = {k: v for k, v in c.items() if k != "vector"}
            c_clean["score"] = round(score, 3)
            scored.append(c_clean)

    scored.sort(key=lambda x: x["score"], reverse=True)
    resultados = scored[:top_k]

    print(f"✅ {len(resultados)} validaciones encontradas (threshold {threshold})")
    for r in resultados[:3]:
        print(f"   Score {r['score']}: {r['descripcion'][:60]}")

    return resultados