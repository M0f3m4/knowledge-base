import os
import json
import anthropic
from dotenv import load_dotenv
from pymongo import MongoClient
from columnas_0430 import COLUMNAS

load_dotenv()

# ── Configurar Claude ────────────────────────────────────
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Conexión MongoDB ─────────────────────────────────────
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

# ── Obtener todos los fragmentos del reporte de MongoDB ──
def obtener_fragmentos_reporte(reporte="0430"):
    print(f"📦 Obteniendo fragmentos del reporte {reporte} desde MongoDB...")
    
    # Primeros 150 fragmentos (páginas 1-40)
    docs = list(coleccion.find(
        {"fuente": {"$regex": reporte, "$options": "i"}},
        {"texto": 1, "fuente": 1, "pagina": 1, "_id": 0}
    ).sort("pagina", 1).limit(150))

    # Agregar fragmentos del Anexo 3 (páginas 241-242)
    anexo3 = list(coleccion.find(
        {
            "fuente": {"$regex": reporte, "$options": "i"},
            "pagina": {"$in": [240, 241]}  # páginas 241-242 en base 0
        },
        {"texto": 1, "fuente": 1, "pagina": 1, "_id": 0}
    ))

    docs += anexo3
    print(f"   {len(docs)} fragmentos encontrados ({len(anexo3)} del Anexo 3)")
    return docs
# ── Construir contexto desde fragmentos ─────────────────
def construir_contexto(fragmentos):
    contexto = ""
    for doc in fragmentos:
        contexto += f"\n[Página {doc['pagina']+1}]\n{doc['texto']}\n"
    return contexto

# ── Analizar reporte completo con Claude ─────────────────
def analizar_reporte(reporte="0430"):
    columnas = COLUMNAS.get(reporte, {})
    if not columnas:
        print(f"❌ No se encontró el mapa de columnas del reporte {reporte}")
        return

    # Obtener fragmentos de MongoDB
    fragmentos = obtener_fragmentos_reporte(reporte)
    if not fragmentos:
        print(f"❌ No se encontraron fragmentos del reporte {reporte} en MongoDB")
        return

    contexto = construir_contexto(fragmentos)

    # Construir lista de campos
    lista_campos = "\n".join([f"{num}. {nombre}" for num, nombre in columnas.items()])

    prompt = f"""Eres un experto en regulación bancaria mexicana CNBV.

Analiza los fragmentos del reporte {reporte} y clasifica cada campo de la siguiente lista.

CAMPOS A CLASIFICAR:
{lista_campos}

DEFINICIONES:
- CALCULADO: el dato se obtiene aplicando una fórmula matemática o algoritmo (ej: concatenar elementos, extraer posiciones de un código, convertir moneda a pesos)
- CATALOGO: el dato se selecciona de una lista de claves predefinidas por la CNBV
- MANUAL: el banco captura el dato directamente de sus sistemas internos

REGLAS:
- Basa tu clasificación ÚNICAMENTE en los fragmentos proporcionados
- Si el documento menciona una metodología o fórmula específica → CALCULADO
- Si el documento menciona un catálogo o lista de claves → CATALOGO
- Si el documento dice "se debe anotar" o "la institución reporta" → MANUAL
- Si no hay información suficiente → DESCONOCIDO
- Los campos de fechas (otorgamiento, vencimiento, máxima disposición) son siempre MANUAL
- El IDENTIFICADOR CRÉDITO LÍNEA GRUPAL es MANUAL — la institución lo asigna internamente
- MUNICIPIO EN DONDE SE DESTINARÁ EL CRÉDITO es CALCULADO — se extraen las posiciones 3 a 5 del código de LOCALIDAD EN DONDE SE DESTINARÁ EL CRÉDITO
- ESTADO EN DONDE SE DESTINARÁ EL CRÉDITO es CALCULADO — se extraen las posiciones 5 a 8 del código de LOCALIDAD EN DONDE SE DESTINARÁ EL CRÉDITO
- El MONTO DE LA LÍNEA DE CRÉDITO AUTORIZADO VALORIZADO EN PESOS es CALCULADO — requiere conversión de moneda

Responde ÚNICAMENTE con un JSON array válido sin texto adicional ni markdown:
[
  {{"numero": "1", "nombre": "NOMBRE DEL CAMPO", "clasificacion": "CALCULADO|CATALOGO|MANUAL|DESCONOCIDO", "formula": "si es CALCULADO: describe la fórmula con detalle, componentes que la forman y ejemplo si existe en el documento. Si no es CALCULADO: null", "razon": "explicación breve"}},
  ...
]
FRAGMENTOS DEL DOCUMENTO:
{contexto}"""

    print("🤖 Consultando Claude...")
    respuesta = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )

    texto = respuesta.content[0].text.strip()

    # Limpiar markdown si viene
    if "```" in texto:
        texto = texto.split("```")[1].replace("json", "").strip()

    try:
        resultados = json.loads(texto)
    except Exception as e:
        print(f"❌ Error parseando JSON: {e}")
        print(f"Respuesta: {texto[:500]}")
        return

    # Guardar JSON
    output_file = f"analisis_{reporte}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    # Resumen
    calculados   = [r for r in resultados if r.get("clasificacion") == "CALCULADO"]
    catalogos    = [r for r in resultados if r.get("clasificacion") == "CATALOGO"]
    manuales     = [r for r in resultados if r.get("clasificacion") == "MANUAL"]
    desconocidos = [r for r in resultados if r.get("clasificacion") == "DESCONOCIDO"]

    print(f"\n{'='*60}")
    print(f"📊 RESUMEN REPORTE {reporte}")
    print(f"   🧮 Calculados:    {len(calculados)}")
    print(f"   📋 Catálogos:     {len(catalogos)}")
    print(f"   ✏️  Manuales:      {len(manuales)}")
    print(f"   ❓ Desconocidos:  {len(desconocidos)}")

    print(f"\n🧮 CAMPOS CALCULADOS:")
    for c in calculados:
        formula = f"\n      Fórmula: {c['formula']}" if c.get("formula") else ""
        print(f"   [{c['numero']:>2}] {c['nombre']}{formula}")

    print(f"\n💾 Resultados guardados en {output_file}")
    return resultados

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("🏦 Analizador de Campos CNBV — Claude + MongoDB")
    print("=" * 60)
    reporte = input("¿Qué reporte analizar? (ej: 0430): ").strip() or "0430"
    analizar_reporte(reporte)