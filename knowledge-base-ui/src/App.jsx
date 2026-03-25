import { useState, useRef, useEffect } from "react"
import axios from "axios"
import "./App.css"

const API = "http://localhost:8000"

const COMANDOS = [
  { id: "consulta", label: "Consulta", placeholder: "¿Qué campos son obligatorios en el 0430?" },
  { id: "campo",   label: "Campo",    placeholder: "RFC  o  20" },
  { id: "calculo", label: "Cálculo",  placeholder: "municipio  o  20" },
  { id: "reporte", label: "Reporte",  placeholder: "Selecciona el reporte arriba" },
]

function Fuentes({ fuentes }) {
  if (!fuentes || fuentes.length === 0) return null
  const unicas = [...new Map(fuentes.map(f => [`${f.fuente}_${f.pagina}`, f])).values()]
  return (
    <div className="fuentes">
      <span className="fuentes-label">📋</span>
      {unicas.map((f, i) => (
        <span key={i} className="fuente-tag">
          {f.fuente.split("_")[0]}… p.{f.pagina}
        </span>
      ))}
    </div>
  )
}

function Mensaje({ msg }) {
  return (
    <div className={`msg msg-${msg.tipo}`}>
      <div className="msg-meta">
        <span className="msg-icon">{msg.tipo === "user" ? "👤" : "🏦"}</span>
        <span className="msg-quien">{msg.tipo === "user" ? "Tú" : "CNBV KB"}</span>
        {msg.cmd && <span className="msg-cmd">{msg.cmd}</span>}
      </div>
      <div className="msg-cuerpo">
        <pre>{msg.texto}</pre>
        {msg.fuentes && <Fuentes fuentes={msg.fuentes} />}
      </div>
    </div>
  )
}

export default function App() {
  const [sesiones, setSesiones] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [mensajes, setMensajes] = useState([])
  const [input, setInput] = useState("")
  const [cmd, setCmd] = useState("consulta")
  const [reporte, setReporte] = useState("0430")
  const [cargando, setCargando] = useState(false)
  const [editando, setEditando] = useState(null)
  const [nuevoNombre, setNuevoNombre] = useState("")
  const bottomRef = useRef(null)

  useEffect(() => {
    cargarSesiones()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [mensajes])

  const cargarSesiones = async () => {
    const res = await axios.get(`${API}/sesiones`)
    setSesiones(res.data)
  }

  const nuevaSesion = async () => {
    const nombre = `Sesión ${new Date().toLocaleDateString("es-MX", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}`
    const res = await axios.post(`${API}/sesiones`, { nombre })
    setSesiones(prev => [res.data, ...prev])
    setSessionId(res.data.id)
    setMensajes([{
      tipo: "bot",
      texto: "Nueva sesión iniciada. ¿En qué puedo ayudarte?",
      fuentes: null
    }])
  }

  const seleccionarSesion = async (id) => {
    setSessionId(id)
    const res = await axios.get(`${API}/sesiones/${id}/mensajes`)
    if (res.data.length === 0) {
      setMensajes([{ tipo: "bot", texto: "Sesión vacía. ¿En qué puedo ayudarte?", fuentes: null }])
    } else {
      setMensajes(res.data)
    }
  }

  const eliminarSesion = async (e, id) => {
    e.stopPropagation()
    await axios.delete(`${API}/sesiones/${id}`)
    setSesiones(prev => prev.filter(s => s.id !== id))
    if (sessionId === id) {
      setSessionId(null)
      setMensajes([])
    }
  }

  const renombrarSesion = async (e, id) => {
    e.stopPropagation()
    if (!nuevoNombre.trim()) return
    await axios.put(`${API}/sesiones/${id}`, { nombre: nuevoNombre })
    setSesiones(prev => prev.map(s => s.id === id ? { ...s, nombre: nuevoNombre } : s))
    setEditando(null)
    setNuevoNombre("")
  }

  const enviar = async () => {
    if (!input.trim() || cargando || !sessionId) return
    const pregunta = input.trim()
    setInput("")

    const msgUser = { tipo: "user", texto: pregunta, cmd, fuentes: null }
    setMensajes(prev => [...prev, msgUser])
    setCargando(true)

    try {
      const body = { pregunta, reporte: reporte || null, session_id: sessionId }
      let res

      if (cmd === "consulta") res = await axios.post(`${API}/consulta`, body)
      else if (cmd === "campo")   res = await axios.post(`${API}/campo`, body)
      else if (cmd === "calculo") res = await axios.post(`${API}/calculo`, body)
      else if (cmd === "reporte") res = await axios.post(`${API}/reporte`, { ...body, pregunta: reporte || pregunta })

      setMensajes(prev => [...prev, {
        tipo: "bot",
        texto: res.data.respuesta,
        fuentes: res.data.fuentes,
        cmd: null
      }])

      // Actualizar nombre de sesión con la primera pregunta
      const sesion = sesiones.find(s => s.id === sessionId)
      if (sesion && sesion.nombre.startsWith("Sesión")) {
        const nombre = pregunta.slice(0, 40) + (pregunta.length > 40 ? "..." : "")
        await axios.put(`${API}/sesiones/${sessionId}`, { nombre })
        setSesiones(prev => prev.map(s => s.id === sessionId ? { ...s, nombre } : s))
      }
    } catch (err) {
      setMensajes(prev => [...prev, {
        tipo: "bot",
        texto: `❌ ${err.response?.data?.detail || err.message}`,
        fuentes: null
      }])
    } finally {
      setCargando(false)
    }
  }

  const formatFecha = (fecha) => {
    if (!fecha) return ""
    return new Date(fecha).toLocaleDateString("es-MX", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
    })
  }

  return (
    <div className="app">
      {/* Panel de sesiones */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="sidebar-title">🏦 CNBV KB</span>
          <button className="btn-nueva" onClick={nuevaSesion}>+ Nueva</button>
        </div>
        <div className="sesiones-lista">
          {sesiones.length === 0 && (
            <p className="sidebar-empty">Sin sesiones.<br />Crea una nueva.</p>
          )}
          {sesiones.map(s => (
            <div
              key={s.id}
              className={`sesion-item ${sessionId === s.id ? "sesion-activa" : ""}`}
              onClick={() => seleccionarSesion(s.id)}
            >
              {editando === s.id ? (
                <input
                  className="sesion-edit"
                  value={nuevoNombre}
                  onChange={e => setNuevoNombre(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") renombrarSesion(e, s.id) }}
                  onBlur={e => renombrarSesion(e, s.id)}
                  autoFocus
                  onClick={e => e.stopPropagation()}
                />
              ) : (
                <>
                  <div className="sesion-info">
                    <span className="sesion-nombre">{s.nombre}</span>
                    <span className="sesion-fecha">{formatFecha(s.updated_at)}</span>
                  </div>
                  <div className="sesion-acciones">
                    <button onClick={e => { e.stopPropagation(); setEditando(s.id); setNuevoNombre(s.nombre) }} title="Renombrar">✏️</button>
                    <button onClick={e => eliminarSesion(e, s.id)} title="Eliminar">🗑️</button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Panel principal */}
      <div className="main">
        <header className="header">
          <div className="header-inner">
            <span className="header-titulo">
              {sessionId ? sesiones.find(s => s.id === sessionId)?.nombre || "Sesión" : "Selecciona o crea una sesión"}
            </span>
            <select className="reporte-select" value={reporte} onChange={e => setReporte(e.target.value)}>
              <option value="">Todos</option>
              <option value="0430">0430 — Altas</option>
              <option value="0431">0431 — Seguimiento</option>
              <option value="0432">0432 — Bajas</option>
            </select>
          </div>
        </header>

        <div className="chat">
          {!sessionId ? (
            <div className="chat-empty">
              <p>👈 Selecciona una sesión o crea una nueva</p>
            </div>
          ) : (
            <>
              {mensajes.map((m, i) => <Mensaje key={i} msg={m} />)}
              {cargando && (
                <div className="msg msg-bot">
                  <div className="msg-meta">
                    <span className="msg-icon">🏦</span>
                    <span className="msg-quien">CNBV KB</span>
                  </div>
                  <div className="msg-cuerpo">
                    <div className="dots"><span /><span /><span /></div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {sessionId && (
          <footer className="footer">
            <div className="cmds">
              {COMANDOS.map(c => (
                <button
                  key={c.id}
                  className={`cmd ${cmd === c.id ? "cmd-active" : ""}`}
                  onClick={() => setCmd(c.id)}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <div className="input-row">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar() } }}
                placeholder={COMANDOS.find(c => c.id === cmd)?.placeholder}
                rows={2}
                disabled={cargando}
              />
              <button className="send" onClick={enviar} disabled={cargando || !input.trim()}>
                {cargando ? "⏳" : "→"}
              </button>
            </div>
          </footer>
        )}
      </div>
    </div>
  )
}