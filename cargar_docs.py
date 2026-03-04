import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from pymongo import MongoClient

load_dotenv()

# ── Conexión MongoDB ─────────────────────────────────────
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
coleccion = db["documentos"]

# ── Embeddings con Ollama ────────────────────────────────
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=os.getenv("OLLAMA_URL")
)

# ── Dividir texto en fragmentos ──────────────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

def cargar_pdf(ruta_pdf):
    nombre = os.path.basename(ruta_pdf)
    print(f"📄 Cargando: {nombre}")

    # Verificar si ya fue cargado
    if coleccion.find_one({"fuente": nombre}):
        print(f"⚠️  Ya existe en la base, omitiendo...")
        return

    # Leer PDF
    loader = PyPDFLoader(ruta_pdf)
    paginas = loader.load()
    print(f"   {len(paginas)} páginas encontradas")

    # Dividir en fragmentos
    fragmentos = splitter.split_documents(paginas)
    print(f"   {len(fragmentos)} fragmentos generados")

    # Generar embeddings y guardar en MongoDB
    documentos_mongo = []
    for i, frag in enumerate(fragmentos):
        print(f"   Procesando fragmento {i+1}/{len(fragmentos)}...", end="\r")
        vector = embeddings.embed_query(frag.page_content)
        documentos_mongo.append({
            "fuente": nombre,
            "pagina": frag.metadata.get("page", 0),
            "texto": frag.page_content,
            "vector": vector
        })

    coleccion.insert_many(documentos_mongo)
    print(f"\n✅ {nombre} guardado — {len(documentos_mongo)} fragmentos en MongoDB")

if __name__ == "__main__":
    # Carpeta donde pondrás los PDFs
    carpeta = "./docs"
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        print("📁 Carpeta 'docs' creada — pon tus PDFs ahí y vuelve a ejecutar")
    else:
        pdfs = [f for f in os.listdir(carpeta) if f.endswith(".pdf")]
        if not pdfs:
            print("📁 No hay PDFs en la carpeta 'docs'")
        else:
            for pdf in pdfs:
                cargar_pdf(os.path.join(carpeta, pdf))
            print("\n🎉 Todos los documentos procesados")