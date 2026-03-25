# 🏦 Knowledge Base CNBV

Base de conocimiento regulatorio para reportes bancarios CNBV, construida con MongoDB Atlas, Voyage AI, Ollama y React.

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Base de datos | MongoDB Atlas (nube) |
| Embeddings | Voyage AI (`voyage-finance-2`) |
| LLM local | Ollama (`mistral:7b-instruct`) |
| Backend | FastAPI + Python |
| Frontend | React + Vite |

---

## Requisitos Previos

### 1. Visual Studio Code
Descarga e instala desde: https://code.visualstudio.com

Extensiones recomendadas:
- Python
- MongoDB for VS Code

### 2. Python 3.12
Descarga desde: https://www.python.org/downloads/release/python-3120/

> ⚠️ Usa Python 3.12 específicamente — algunas dependencias no son compatibles con Python 3.13+

Durante la instalación activa la opción **"Add Python to PATH"**

### 3. Node.js
Descarga la versión LTS desde: https://nodejs.org

### 4. Ollama
Descarga desde: https://ollama.com

Una vez instalado, descarga el modelo Mistral:
```bash
ollama pull mistral:7b-instruct
```

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/M0f3m4/Knowledge-Base.git
cd Knowledge-Base
```

### 2. Crear entorno virtual de Python

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias de Python

```bash
pip install fastapi uvicorn pymongo python-dotenv langchain-ollama langchain-community langchain-text-splitters pdfplumber anthropic requests
```

### 4. Instalar dependencias del frontend

```bash
cd knowledge-base-ui
npm install
cd ..
```

### 5. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con las credenciales que te proporcionó el administrador:

```env
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=knowledge_base
OLLAMA_URL=http://localhost:11434
VOYAGE_API_KEY=al-xxxxxxxxxxxxxxxxxxxx

```

> ✅ El cluster de MongoDB Atlas, los documentos y el índice vectorial ya están configurados — no necesitas hacer ninguna configuración adicional en Atlas.

---

## Correr el Proyecto

Necesitas **dos terminales** abiertas:

### Terminal 1 — Backend

```bash
venv\Scripts\activate
python Api.py
```

El backend queda disponible en `http://localhost:8000`

### Terminal 2 — Frontend

```bash
cd knowledge-base-ui
npm run dev
```

La app queda disponible en `http://localhost:5173`

> ✅ Asegúrate de que **Ollama esté corriendo** antes de iniciar el backend.

---

## Uso

La app tiene 4 modos de consulta:

| Modo | Descripción | Ejemplo |
|---|---|---|
| **Consulta** | Pregunta libre sobre regulación | `¿Qué campos son obligatorios en el 0430?` |
| **Campo** | Información de un campo específico | `RFC` o `20` |
| **Cálculo** | Cómo se calcula un campo | `municipio` o `20` |
| **Reporte** | Campos de un reporte completo | Selecciona el reporte en el dropdown |

Puedes filtrar por reporte usando el selector en la parte superior derecha.

---

## Estructura del Proyecto

```
Knowledge Base/
├── docs/                    # PDFs de regulación CNBV
├── knowledge-base-ui/       # Frontend React
│   └── src/
│       ├── App.jsx
│       └── App.css
├── Api.py                   # Backend FastAPI
├── Consultar.py             # Funciones de búsqueda y respuesta
├── cargar_docs.py           # Carga PDFs a MongoDB Atlas
├── analizar_campos.py       # Clasificación automática de campos con Claude
├── columnas_0430.py         # Mapa de columnas del reporte 0430
├── analisis_0430.json       # Resultado del análisis de campos
├── .env                     # Variables de entorno (no incluido en repo)
└── requirements.txt         # Dependencias Python
```

---

## Herramientas Adicionales

### Analizar campos de un reporte
Clasifica automáticamente los campos como CALCULADO, CATALOGO o MANUAL usando Claude API:

```bash
python analizar_campos.py
```

Requiere `ANTHROPIC_API_KEY` en el `.env`.

---

## Notas

- La búsqueda vectorial se realiza directamente en Atlas — no se necesitan archivos locales de índice
- El proyecto usa `voyage-finance-2` para embeddings, especializado en documentos financieros
- Las respuestas son generadas por `mistral:7b-instruct` corriendo localmente con Ollama
- Toda la información permanece en el cluster privado de Atlas
