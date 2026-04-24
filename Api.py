import os
import bcrypt
from datetime import datetime
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
from linaje_0430 import buscar_linaje
from Consultar import (
    consultar_campo,
    consultar_calculo,
    consultar_reporte,
    consultar_libre
)

load_dotenv()

app = FastAPI(title="Knowledge Base CNBV")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo = MongoClient(os.getenv("MONGO_URI"))
db = mongo[os.getenv("DB_NAME")]
sesiones = db["sesiones"]
mensajes = db["mensajes"]

INVITE_CODE = os.getenv("INVITE_CODE", "KnowledgeBW")

# ── Helpers ───────────────────────────────────────────────
def str_id(obj):
    obj["id"] = str(obj.pop("_id"))
    return obj

def obtener_historial(session_id, limite=6):
    return list(mensajes.find(
        {"session_id": session_id},
        {"tipo": 1, "texto": 1, "_id": 0}
    ).sort("timestamp", -1).limit(limite))[::-1]

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

# ── Modelos ───────────────────────────────────────────────
class LoginRequest(BaseModel):
    usuario: str
    password: str

class RegisterRequest(BaseModel):
    usuario: str
    password: str
    codigo: str

class SesionCreate(BaseModel):
    nombre: str
    usuario: str

class SesionUpdate(BaseModel):
    nombre: str

class ConsultaRequest(BaseModel):
    pregunta: str
    reporte: str = None
    session_id: str

class FeedbackRequest(BaseModel):
    session_id: str
    pregunta: str
    respuesta: str
    cmd: str
    reporte: str = None
    voto: str
    nota: str = ""

class CacheEditRequest(BaseModel):
    pregunta: str
    cmd: str
    reporte: str = None
    respuesta_corregida: str

# ── Auth ──────────────────────────────────────────────────
@app.post("/login")
def login(req: LoginRequest):
    user = db["usuarios"].find_one({"usuario": req.usuario, "activo": True})
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not bcrypt.checkpw(req.password.encode(), user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    print(f"🔑 Login: {req.usuario} ({user['rol']})")
    return {"usuario": req.usuario, "rol": user["rol"]}

@app.post("/register")
def register(req: RegisterRequest):
    if req.codigo != INVITE_CODE:
        raise HTTPException(status_code=403, detail="Código de invitación incorrecto")
    if db["usuarios"].find_one({"usuario": req.usuario}):
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt())
    db["usuarios"].insert_one({
        "usuario": req.usuario,
        "password": hashed,
        "rol": "usuario",
        "activo": True,
        "created_at": datetime.utcnow()
    })
    print(f"✅ Nuevo usuario registrado: {req.usuario}")
    return {"usuario": req.usuario, "rol": "usuario"}

# ── Sesiones ──────────────────────────────────────────────
@app.get("/sesiones")
def listar_sesiones(usuario: str = ""):
    filtro = {"usuario": usuario} if usuario else {}
    result = list(sesiones.find(filtro).sort("updated_at", -1))
    return [str_id(s) for s in result]

@app.post("/sesiones")
def crear_sesion(body: SesionCreate):
    now = datetime.utcnow()
    doc = {
        "nombre": body.nombre,
        "usuario": body.usuario,
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

# ── Consultas ─────────────────────────────────────────────
@app.post("/campo")
def endpoint_campo(req: ConsultaRequest):
    try:
        print(f"📥 campo: {req.pregunta} | {req.reporte}")
        historial = obtener_historial(req.session_id)
        argumento = f"{req.pregunta} {req.reporte}".strip() if req.reporte else req.pregunta
        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="campo")
        result = consultar_campo(argumento, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="campo")
        return result
    except Exception as e:
        print(f"❌ Error campo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculo")
def endpoint_calculo(req: ConsultaRequest):
    try:
        print(f"📥 calculo: {req.pregunta} | {req.reporte}")
        historial = obtener_historial(req.session_id)
        argumento = f"{req.pregunta} {req.reporte}".strip() if req.reporte else req.pregunta
        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="calculo")
        result = consultar_calculo(argumento, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="calculo")
        return result
    except Exception as e:
        print(f"❌ Error calculo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reporte")
def endpoint_reporte(req: ConsultaRequest):
    try:
        print(f"📥 reporte: {req.reporte}")
        historial = obtener_historial(req.session_id)
        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="reporte")
        result = consultar_reporte(req.reporte or req.pregunta, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="reporte")
        return result
    except Exception as e:
        print(f"❌ Error reporte: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/consulta")
def endpoint_consulta(req: ConsultaRequest):
    try:
        print(f"📥 consulta: {req.pregunta} | {req.reporte}")
        historial = obtener_historial(req.session_id)
        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="consulta")
        result = consultar_libre(req.pregunta, reporte=req.reporte, historial=historial)
        guardar_mensaje(req.session_id, "bot", result["respuesta"], result.get("fuentes"), cmd="consulta")
        return result
    except Exception as e:
        print(f"❌ Error consulta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Linaje ────────────────────────────────────────────────
@app.post("/linaje")
def endpoint_linaje(req: ConsultaRequest):
    try:
        print(f"📥 linaje: {req.pregunta}")
        historial = obtener_historial(req.session_id)
        guardar_mensaje(req.session_id, "user", req.pregunta, cmd="linaje")

        # Buscar linaje en el mapa del Excel
        campo, linaje_excel = buscar_linaje(req.pregunta)

        # Contexto del linaje para enriquecer el prompt
        contexto_linaje = ""
        if campo and linaje_excel:
            contexto_linaje = f"Según el caso de prueba del reporte 0430, el campo {campo} tiene el siguiente linaje: {linaje_excel}. "

        # Consultar el Knowledge Base para más detalle
        from Consultar import consultar_campo, consultar_calculo
        argumento = f"{req.pregunta} {req.reporte or '0430'}".strip()

        resultado_campo  = consultar_campo(argumento, historial=historial)
        resultado_calculo = consultar_calculo(argumento, historial=historial)

        # Combinar todo en un prompt final
        from langchain_ollama import OllamaLLM
        import os
        llm = OllamaLLM(model="mistral:7b-instruct", base_url=os.getenv("OLLAMA_URL"))

        # Buscar específicamente en el Anexo si el campo es calculado
        es_calculado = linaje_excel and "CALCULADO" in linaje_excel.upper()
        consulta_anexo = ""
        if es_calculado:
            from Consultar import consultar_libre
            resultado_anexo = consultar_libre(
                f"fórmula exacta cálculo {campo or req.pregunta} Anexo posiciones dígitos",
                reporte="0430",
                historial=[]
            )
            consulta_anexo = f"""
Información del Anexo sobre la fórmula exacta:
{resultado_anexo.get('respuesta', '')}
"""

        prompt = f"""Eres un experto en regulación bancaria CNBV. Explica el linaje del campo '{campo or req.pregunta}' del reporte 0430 de forma precisa y en español.

{contexto_linaje}

Información regulatoria sobre el origen del campo:
{resultado_campo.get('respuesta', '')}

Información sobre cómo se calcula o transforma:
{resultado_calculo.get('respuesta', '')}
{consulta_anexo}
INSTRUCCIONES IMPORTANTES:
- Responde ÚNICAMENTE sobre el campo '{campo or req.pregunta}', no menciones otros campos
- Si el campo es calculado, incluye la fórmula COMPLETA con todas las partes, posiciones y dígitos exactos
- Si el campo viene de un insumo, indica exactamente de qué hoja (PERSONA, LINEA_CREDITO, CREDITO) y columna
- Si hay ajustes (formato de fecha, guion bajo en RFC, valorización), explícalos
- Sé conciso pero completo

Estructura tu respuesta así:
1. Origen: de dónde proviene (hoja y columna, o que es calculado)
2. Cómo se obtiene: fórmula completa o transformación aplicada
3. Notas: ajustes, formatos o condiciones especiales
"""
        respuesta = llm.invoke(prompt)

        # Combinar fuentes
        fuentes = list({
            f"{f['fuente']}_{f['pagina']}": f
            for f in (resultado_campo.get("fuentes", []) + resultado_calculo.get("fuentes", []))
        }.values())

        guardar_mensaje(req.session_id, "bot", respuesta, fuentes, cmd="linaje")
        return {"respuesta": respuesta, "fuentes": fuentes, "campo": campo, "linaje_excel": linaje_excel}

    except Exception as e:
        print(f"❌ Error linaje: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Feedback ──────────────────────────────────────────────
@app.post("/feedback")
def endpoint_feedback(req: FeedbackRequest):
    try:
        db["feedback"].insert_one({
            "session_id": req.session_id,
            "pregunta": req.pregunta,
            "respuesta": req.respuesta,
            "cmd": req.cmd,
            "reporte": req.reporte,
            "voto": req.voto,
            "nota": req.nota,
            "timestamp": datetime.utcnow()
        })
        emoji = "👍" if req.voto == "up" else "👎"
        print(f"{emoji} Feedback {req.voto}: {req.pregunta[:40]}")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Dashboard ─────────────────────────────────────────────
@app.get("/dashboard/feedback")
def dashboard_feedback():
    try:
        total_up   = db["feedback"].count_documents({"voto": "up"})
        total_down = db["feedback"].count_documents({"voto": "down"})

        negativos = list(db["feedback"].find(
            {"voto": "down", "$or": [{"resuelto": {"$exists": False}}, {"resuelto": False}]},
            {"_id": 0, "pregunta": 1, "respuesta": 1, "cmd": 1, "reporte": 1, "timestamp": 1, "nota": 1}
        ).sort("timestamp", -1).limit(50))

        for n in negativos:
            if "timestamp" in n:
                n["timestamp"] = n["timestamp"].isoformat()

        positivos = list(db["feedback"].find(
            {"voto": "up"},
            {"_id": 0, "pregunta": 1, "respuesta": 1, "cmd": 1, "reporte": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(50))

        for p in positivos:
            if "timestamp" in p:
                p["timestamp"] = p["timestamp"].isoformat()

        por_cmd = {}
        todos = list(db["feedback"].find({}, {"_id": 0, "cmd": 1, "voto": 1}))
        for item in todos:
            cmd  = item.get("cmd") or "consulta"
            voto = item.get("voto") or "up"
            if cmd not in por_cmd:
                por_cmd[cmd] = {"up": 0, "down": 0}
            if voto in por_cmd[cmd]:
                por_cmd[cmd][voto] += 1

        return {
            "total_up":   total_up,
            "total_down": total_down,
            "negativos":  negativos,
            "positivos":  positivos,
            "por_cmd":    por_cmd
        }
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Editar caché ──────────────────────────────────────────
@app.put("/cache/editar")
def editar_cache(req: CacheEditRequest):
    try:
        import hashlib
        texto = f"{req.pregunta.lower().strip()}|{req.cmd}|{req.reporte or ''}"
        key = hashlib.md5(texto.encode()).hexdigest()
        db["cache"].update_one(
            {"key": key},
            {"$set": {
                "key": key,
                "pregunta": req.pregunta,
                "cmd": req.cmd,
                "reporte": req.reporte,
                "respuesta": req.respuesta_corregida,
                "editado": True,
                "timestamp": datetime.utcnow()
            }},
            upsert=True
        )
        db["feedback"].update_many(
            {"pregunta": req.pregunta, "cmd": req.cmd, "voto": "down"},
            {"$set": {"resuelto": True}}
        )
        print(f"✏️ Cache editado: {req.pregunta[:40]}")
        return {"ok": True}
    except Exception as e:
        print(f"❌ Error editar cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# ── Datos Excel ───────────────────────────────────────────
@app.get("/datos/{coleccion}")
def listar_datos(coleccion: str, pagina: int = 1, busqueda: str = "", limite: int = 50):
    if coleccion not in ["persona", "linea_credito", "credito"]:
        raise HTTPException(status_code=400, detail="Colección no válida")
    try:
        col = db[coleccion]
        filtro = {}
        if busqueda:
            filtro = {"$or": [
                {k: {"$regex": busqueda, "$options": "i"}}
                for k in ["ID_PERSONA", "RFC", "NOMBRE_CNBV", "ID_LINEACREDITO", "ID_CREDITO", "ID_DISPOSICION"]
                if col.find_one({k: {"$exists": True}})
            ]}
        total = col.count_documents(filtro)
        skip = (pagina - 1) * limite
        docs = list(col.find(filtro, {"_id": 0}).skip(skip).limit(limite))
        return {"total": total, "pagina": pagina, "limite": limite, "datos": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datos/{coleccion}/columnas")
def obtener_columnas(coleccion: str):
    if coleccion not in ["persona", "linea_credito", "credito"]:
        raise HTTPException(status_code=400, detail="Colección no válida")
    try:
        doc = db[coleccion].find_one({}, {"_id": 0, "_archivo": 0, "_cargado": 0})
        if not doc:
            return {"columnas": []}
        return {"columnas": list(doc.keys())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Fragmento por fuente y página ────────────────────────
@app.get("/fragmento")
def obtener_fragmento(fuente: str, pagina: int):
    try:
        doc = db["documentos"].find_one(
            {"fuente": fuente, "pagina": pagina - 1},
            {"texto": 1, "_id": 0}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Fragmento no encontrado")
        return {"texto": doc["texto"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Estadísticas del sistema ──────────────────────────────
@app.get("/stats")
def obtener_stats():
    try:
        total_docs     = db["documentos"].count_documents({})
        total_fuentes  = len(db["documentos"].distinct("fuente"))
        total_sesiones = db["sesiones"].count_documents({})
        total_mensajes = db["mensajes"].count_documents({"tipo": "user"})
        total_cache    = db["cache"].count_documents({})
        total_feedback = db["feedback"].count_documents({})
        return {
            "fragmentos":  total_docs,
            "documentos":  total_fuentes,
            "sesiones":    total_sesiones,
            "preguntas":   total_mensajes,
            "cache":       total_cache,
            "feedback":    total_feedback,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Base de Conocimiento ──────────────────────────────────
@app.get("/conocimiento/documentos")
def listar_documentos():
    try:
        pipeline = [
            {"$group": {
                "_id": "$fuente",
                "paginas": {"$max": "$pagina"},
                "fragmentos": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        docs = list(db["documentos"].aggregate(pipeline))
        return [{
            "nombre": d["_id"],
            "fragmentos": d["fragmentos"],
            "paginas": d["paginas"] + 1
        } for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conocimiento/pdf/{nombre}")
def servir_pdf(nombre: str):
    import urllib.parse
    from fastapi.responses import FileResponse
    nombre_decoded = urllib.parse.unquote(nombre)
    ruta = os.path.join("docs", nombre_decoded)
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="PDF no encontrado")
    return FileResponse(ruta, media_type="application/pdf", filename=nombre_decoded)

# ── Health ────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "mensaje": "Knowledge Base CNBV activo"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)