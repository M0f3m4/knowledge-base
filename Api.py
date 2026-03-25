from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from Consultar import (
    consultar_campo,
    consultar_calculo,
    consultar_reporte,
    consultar_libre
)

# ── App ──────────────────────────────────────────────────
app = FastAPI(title="Knowledge Base CNBV")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modelos ──────────────────────────────────────────────
class ConsultaRequest(BaseModel):
    pregunta: str
    reporte: str = None

# ── Endpoints ────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "mensaje": "Knowledge Base CNBV activo"}

@app.post("/campo")
def endpoint_campo(req: ConsultaRequest):
    try:
        argumento = f"{req.pregunta} {req.reporte}".strip() if req.reporte else req.pregunta
        return consultar_campo(argumento)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculo")
def endpoint_calculo(req: ConsultaRequest):
    try:
        argumento = f"{req.pregunta} {req.reporte}".strip() if req.reporte else req.pregunta
        return consultar_calculo(argumento)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reporte")
def endpoint_reporte(req: ConsultaRequest):
    try:
        return consultar_reporte(req.pregunta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/consulta")
def endpoint_consulta(req: ConsultaRequest):
    try:
        return consultar_libre(req.pregunta, reporte=req.reporte)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)