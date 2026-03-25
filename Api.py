import os
from datetime import datetime
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
from Consultar import (
    consultar_campo,
    consultar_calculo,
    consultar_reporte,
    consultar_libre
)

load_dotenv()

# ── App ──────────────────────────────────────────────────
app = FastAPI(title="Knowledge Base CNBV")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MongoDB ──────────────────────────────────────────────
mongo = MongoClient(os.getenv("MONGO_URI"))
db = mongo[os.getenv("DB_NAME")]
sesiones = db["sesiones"]
mensajes = db["mensajes"]

# ── Helpers ──────────────────────────────────────────────
def str_id(obj):
    obj["id"] = str(obj.pop("_id"))
    return obj

def obtener_historial(session_id, limite=6):
    return list(mensajes.find(
        {"session_id": session_id},
        {"tipo": 1, "texto": 1, "_id": 0}
    ).sort("timestamp", -1).limit(limite))[::-1]

# ── Modelos ──────────────────────────────────────────────
class SesionCreate(BaseModel):
    nombre: str

class SesionUpdate(BaseModel):
    nombre: str

class ConsultaRequest(BaseModel):
    pregunta: str
    reporte: str = None
    session_id: str

# ── Endpoints de Sesiones ────────────────────────────────
@app.get("/sesiones")
def listar_sesiones():
    result = list(sesiones.find().sort("updated_at", -1))
    return [str_id(s) for s in result]

@app.post("/sesiones")
def crear_sesion(body: SesionCreate):
    now = datetime.utcnow()
    doc = {
        "nombre": body.nombre,
        "created_at": now,
        "updated_at": now
    }
    result = sesiones.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc

@app.put("/sesiones/{session_id}")
def renombrar_sesion(session_id: str, body: SesionUpdate):
    sesiones.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"nombre": body.nombre, "updated_at": datetime.utcnow()}}
    )
    return {"ok": True}

@app.delete("/sesiones/{session_id}")
def eliminar_sesion(session_id: str):
    sesiones.delete_one({"_id": ObjectId(session_id)})
    mensajes.delete_many({"session_id": session_id})
    return {"ok": True}

@app.get("/sesiones/{session_id}/mensajes")
def obtener_mensajes(session_id: str):
    result = list(mensajes.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1))
    return result

# ── Helpers para guardar mensajes ────────────────────────
def guardar_mensaje(session_id, tipo, texto, fuentes=None, cmd=None):
    mensajes.insert_one({
        "session_id": session_id,
        "tipo": tipo,
        "texto": texto,
        "fuentes": fuentes or [],
        "cmd": cmd,
        "timestamp": datetime.utcnow()
    })
    sesiones.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"updated_at": datetime.utcnow()}}
    )

# ── Endpoints de Consulta ────────────────────────────────
@app.post("/campo")
def endpoint_campo(req: ConsultaRequest):
    try:
        historial = obtener_historial(req.session_id)
        argumento = f"{req.pregunta} {req.reporte}".strip() if req.reporte else req.pregunta

        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="campo")
        result = consultar_campo(argumento, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="campo")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculo")
def endpoint_calculo(req: ConsultaRequest):
    try:
        historial = obtener_historial(req.session_id)
        argumento = f"{req.pregunta} {req.reporte}".strip() if req.reporte else req.pregunta

        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="calculo")
        result = consultar_calculo(argumento, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="calculo")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reporte")
def endpoint_reporte(req: ConsultaRequest):
    try:
        historial = obtener_historial(req.session_id)

        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="reporte")
        result = consultar_reporte(req.reporte or req.pregunta, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="reporte")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/consulta")
def endpoint_consulta(req: ConsultaRequest):
    try:
        historial = obtener_historial(req.session_id)

        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="consulta")
        result = consultar_libre(req.pregunta, reporte=req.reporte, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="consulta")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Health ───────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "mensaje": "Knowledge Base CNBV activo"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)