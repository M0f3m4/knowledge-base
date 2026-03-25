import os
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# ── Conexión MongoDB Atlas ───────────────────────────────
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

# ── Configuración Voyage AI ──────────────────────────────
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = "voyage-finance-2"
VOYAGE_URL = "https://ai.mongodb.com/v1/embeddings"

# ── Generar embeddings con Voyage ────────────────────────
def generar_embeddings(textos):
    headers = {
        "Authorization": f"Bearer {VOYAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "input": textos,
        "model": VOYAGE_MODEL
    }
    response = requests.post(VOYAGE_URL, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"Error Voyage API: {response.status_code} - {response.text}")

    data = response.json()
    return [item["embedding"] for item in data["data"]]

# ── Cargar PDF ───────────────────────────────────────────
def cargar_pdf(pdf_path):
    print(f"\n📄 Procesando: {os.path.basename(pdf_path)}")
    nombre_archivo = os.path.basename(pdf_path)

    # Verificar si ya está cargado
    existente = coleccion.count_documents({"fuente": nombre_archivo})
    if existente > 0:
        print(f"   ⏭️  Ya cargado ({existente} fragmentos) — saltando")
        return 0

    # Cargar y dividir PDF
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    chunks = splitter.split_documents(pages)
    print(f"   📝 {len(chunks)} fragmentos generados")

    # Procesar en lotes de 10
    batch_size = 10
    total_guardados = 0

    for i in range(0, len(chunks), batch_size):
        lote = chunks[i:i + batch_size]
        textos = [c.page_content for c in lote]

        print(f"   🔄 Lote {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}...", end=" ", flush=True)

        embeddings = generar_embeddings(textos)

        documentos = []
        for chunk, embedding in zip(lote, embeddings):
            documentos.append({
                "fuente": nombre_archivo,
                "pagina": chunk.metadata.get("page", 0),
                "texto": chunk.page_content,
                "vector": embedding,
                "modelo": VOYAGE_MODEL
            })

        coleccion.insert_many(documentos)
        total_guardados += len(documentos)
        print(f"✅ {total_guardados}/{len(chunks)}")

    print(f"   ✨ Completado: {total_guardados} fragmentos guardados")
    return total_guardados

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("🏦 Cargador de Documentos CNBV — Voyage AI + Atlas")
    print("=" * 60)
    print(f"   Modelo: {VOYAGE_MODEL}")
    print(f"   Base de datos: {os.getenv('DB_NAME')}")

    carpeta = "docs"
    if not os.path.exists(carpeta):
        print(f"❌ No se encontró la carpeta '{carpeta}'")
        exit(1)

    pdfs = [f for f in os.listdir(carpeta) if f.endswith(".pdf")]
    if not pdfs:
        print(f"❌ No se encontraron PDFs en '{carpeta}'")
        exit(1)

    print(f"\n📁 PDFs encontrados: {len(pdfs)}")
    for pdf in pdfs:
        print(f"   - {pdf}")

    print("\n¿Continuar? (Enter para sí, Ctrl+C para cancelar)")
    input()

    total = 0
    for pdf in pdfs:
        total += cargar_pdf(os.path.join(carpeta, pdf))

    print(f"\n{'='*60}")
    print(f"✅ Proceso completado — {total} fragmentos cargados en Atlas")
   