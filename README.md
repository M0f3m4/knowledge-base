# Knowledge Base CNBV — Bajaware

Base de conocimiento regulatorio para reportes bancarios CNBV, construida con MongoDB Atlas, Voyage AI, Ollama y React.

## Stack

| Componente | Tecnología |
|---|---|
| Base de datos | MongoDB Atlas |
| Embeddings | Voyage AI `voyage-finance-2` |
| Reranking | Voyage AI `rerank-2.5` |
| LLM local | Ollama `mistral:7b-instruct` |
| Backend | FastAPI + Python |
| Frontend | React + Vite |

---

## Requisitos

### 1. Visual Studio Code
https://code.visualstudio.com

### 2. Python 3.12
https://www.python.org/downloads/release/python-3120/

> ⚠️ Usa Python 3.12 — algunas dependencias no son compatibles con Python 3.13+

**Windows:** Activa "Add Python to PATH" durante la instalación.  
**Mac:**
```bash
brew install python@3.12
```

### 3. Node.js LTS
https://nodejs.org

### 4. Ollama
https://ollama.com

```bash
ollama pull mistral:7b-instruct
```

### 5. Git

**Windows:** https://git-scm.com  
**Mac:**
```bash
brew install git
```

---

## Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/M0f3m4/knowledge-base.git
cd knowledge-base
```

### 2. Entorno virtual Python

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac:**
```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias Python
```bash
pip install fastapi uvicorn pymongo python-dotenv langchain-ollama langchain-community langchain-text-splitters pdfplumber requests
```

### 4. Instalar dependencias del frontend
```bash
cd knowledge-base-ui
npm install
cd ..
```

### 5. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con las credenciales proporcionadas por el administrador:

```env
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=knowledge_base
OLLAMA_URL=http://localhost:11434
VOYAGE_API_KEY=al-xxxxxxxxxxxxxxxxxxxx
```

> ✅ El cluster de MongoDB Atlas, los documentos y el índice vectorial ya están configurados.

---

## Correr el proyecto

Necesitas **dos terminales**:

**Terminal 1 — Backend:**

*Windows:*
```bash
venv\Scripts\activate
python Api.py
```

*Mac:*
```bash
source venv/bin/activate
python Api.py
```

**Terminal 2 — Frontend:**
```bash
cd knowledge-base-ui
npm run dev
```

Abre **http://localhost:5173** en tu navegador.

> ✅ Asegúrate de que **Ollama esté corriendo** antes de iniciar el backend.

**Si el puerto 8000 está ocupado:**

*Windows:*
```bash
netstat -ano | findstr :8000
taskkill /PID <número> /F
```

*Mac:*
```bash
lsof -ti :8000 | xargs kill -9
```

---

## Uso

### Sesiones
Crea sesiones de conversación desde el panel lateral. Cada sesión mantiene memoria de los últimos 6 mensajes para respuestas contextuales.

### Comandos

| Comando | Descripción | Ejemplo |
|---|---|---|
| **Consulta** | Pregunta libre sobre regulación | `¿Qué campos son obligatorios en el 0430?` |
| **Campo** | Origen y tipo de un campo | `RFC` · `20` · `municipio` |
| **Cálculo** | Cómo se calcula un campo | `20` · `municipio destino` |
| **Reporte** | Lista de campos del reporte | Selecciona el reporte en el dropdown |

Filtra por reporte usando el selector en la barra superior.

### Feedback
Cada respuesta tiene botones ↑ ↓ para calificarla. El feedback se guarda en MongoDB para análisis de calidad.

### Dashboard
Accede desde el botón **Dashboard** en la barra superior para ver métricas de feedback, respuestas positivas y negativas agrupadas por comando.

---

## Arquitectura RAG

```
Pregunta
   ↓
Query Expansion (Mistral)
   ↓
Atlas Vector Search (voyage-finance-2, top 20)
   ↓
Voyage Rerank (rerank-2.5, top 5)
   ↓
Mistral 7b-instruct → Respuesta
   ↓
Caché en MongoDB (respuestas futuras instantáneas)
```

---

## Estructura del proyecto

```
knowledge-base/
├── docs/                    # PDFs de regulación CNBV
├── knowledge-base-ui/       # Frontend React + Vite
│   └── src/
│       ├── App.jsx
│       ├── App.css
│       ├── Dashboard.jsx
│       ├── Dashboard.css
│       └── main.jsx
├── Api.py                   # Backend FastAPI
├── Consultar.py             # Motor RAG (búsqueda + reranking + respuesta)
├── cargar_docs.py           # Carga PDFs a MongoDB Atlas con Voyage
├── columnas_0430.py         # Mapa de las 53 columnas del reporte 0430
├── analisis_0430.json       # Clasificación CALCULADO/CATALOGO/MANUAL
├── .env                     # Variables de entorno (no incluido en repo)
└── requirements.txt
```

---

## Colecciones MongoDB Atlas

| Colección | Descripción |
|---|---|
| `documentos` | Fragmentos de PDFs con embeddings vectoriales |
| `sesiones` | Sesiones de conversación |
| `mensajes` | Historial de mensajes por sesión |
| `cache` | Caché de respuestas para consultas repetidas |
| `feedback` | Calificaciones 👍👎 de las respuestas |