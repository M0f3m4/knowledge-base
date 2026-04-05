import { useState, useRef, useEffect } from "react"
import axios from "axios"
import "./App.css"

const API = "http://localhost:8000"

const CMDS = [
  { id: "consulta", label: "Consulta", ph: "¿Cuál es el objetivo del reporte 0430?" },
  { id: "campo",    label: "Campo",    ph: "RFC  /  20  /  municipio" },
  { id: "calculo",  label: "Cálculo",  ph: "20  /  municipio destino" },
  { id: "reporte",  label: "Reporte",  ph: "Selecciona el reporte arriba" },
]

const REPORTES = [
  { value: "",     label: "Todos" },
  { value: "0430", label: "0430 · Altas" },
  { value: "0431", label: "0431 · Seguimiento" },
  { value: "0432", label: "0432 · Bajas" },
]

function Fuentes({ fuentes }) {
  if (!fuentes?.length) return null
  const u = [...new Map(fuentes.map(f => [`${f.fuente}_${f.pagina}`, f])).values()]
  return (
    <div className="fuentes">
      {u.map((f, i) => (
        <span key={i} className="ftag">
          {f.fuente.split("_")[0].slice(0, 12)}… p{f.pagina}
        </span>
      ))}
    </div>
  )
}

function Burbuja({ m, onFeedback }) {
  const [voto, setVoto] = useState(null)

  const votar = async (v) => {
    if (voto) return
    setVoto(v)
    onFeedback && onFeedback(m, v)
  }

  return (
    <div className={`burbuja ${m.tipo}`}>
      {m.tipo === "bot" && <div className="bot-label">CNBV</div>}
      <div className="burbuja-inner">
        <pre>{m.texto}</pre>
        <Fuentes fuentes={m.fuentes} />
        {m.tipo === "bot" && m.texto !== "¿En qué puedo ayudarte?" && m.texto !== "Sesión vacía. ¿En qué puedo ayudarte?" && (
          <div className="feedback">
            <button
              className={`fvoto ${voto === "up" ? "active-up" : ""}`}
              onClick={() => votar("up")}
              disabled={!!voto}
              title="Buena respuesta"
            >
              {voto === "up" ? "👍" : "↑"}
            </button>
            <button
              className={`fvoto ${voto === "down" ? "active-down" : ""}`}
              onClick={() => votar("down")}
              disabled={!!voto}
              title="Mala respuesta"
            >
              {voto === "down" ? "👎" : "↓"}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function Dots() {
  return (
    <div className="burbuja bot">
      <div className="bot-label">CNBV</div>
      <div className="burbuja-inner">
        <div className="typing"><span/><span/><span/></div>
      </div>
    </div>
  )
}

export default function App() {
  const [sesiones, setSesiones]   = useState([])
  const [sid, setSid]             = useState(null)
  const [msgs, setMsgs]           = useState([])
  const [input, setInput]         = useState("")
  const [cmd, setCmd]             = useState("consulta")
  const [reporte, setReporte]     = useState("0430")
  const [cargando, setCargando]   = useState(false)
  const [editId, setEditId]       = useState(null)
  const [editVal, setEditVal]     = useState("")
  const [sideOpen, setSideOpen]   = useState(true)
  const bottom = useRef(null)
  const lastUserMsg = useRef(null)

  useEffect(() => { cargarSesiones() }, [])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }) }, [msgs, cargando])

  const cargarSesiones = async () => {
    const r = await axios.get(`${API}/sesiones`)
    setSesiones(r.data)
  }

  const nuevaSesion = async () => {
    const nombre = `Sesión ${new Date().toLocaleString("es-MX", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}`
    const r = await axios.post(`${API}/sesiones`, { nombre })
    setSesiones(p => [r.data, ...p])
    setSid(r.data.id)
    setMsgs([{ tipo: "bot", texto: "¿En qué puedo ayudarte?", fuentes: null }])
  }

  const selSesion = async (id) => {
    setSid(id)
    const r = await axios.get(`${API}/sesiones/${id}/mensajes`)
    setMsgs(r.data.length ? r.data : [{ tipo: "bot", texto: "Sesión vacía. ¿En qué puedo ayudarte?", fuentes: null }])
  }

  const delSesion = async (e, id) => {
    e.stopPropagation()
    await axios.delete(`${API}/sesiones/${id}`)
    setSesiones(p => p.filter(s => s.id !== id))
    if (sid === id) { setSid(null); setMsgs([]) }
  }

  const renombrar = async (e, id) => {
    e.stopPropagation()
    if (!editVal.trim()) return
    await axios.put(`${API}/sesiones/${id}`, { nombre: editVal })
    setSesiones(p => p.map(s => s.id === id ? { ...s, nombre: editVal } : s))
    setEditId(null); setEditVal("")
  }

  const enviar = async () => {
    if (!input.trim() || cargando || !sid) return
    const q = input.trim()
    setInput("")
    setMsgs(p => [...p, { tipo: "user", texto: q, cmd, fuentes: null }])
    setCargando(true)

    try {
      const body = { pregunta: q, reporte: reporte || null, session_id: sid }
      let r
      if (cmd === "consulta") r = await axios.post(`${API}/consulta`, body)
      else if (cmd === "campo")   r = await axios.post(`${API}/campo`, body)
      else if (cmd === "calculo") r = await axios.post(`${API}/calculo`, body)
      else if (cmd === "reporte") r = await axios.post(`${API}/reporte`, { ...body, pregunta: reporte || q })

      setMsgs(p => [...p, { tipo: "bot", texto: r.data.respuesta, fuentes: r.data.fuentes }])

      const s = sesiones.find(x => x.id === sid)
      if (s?.nombre.startsWith("Sesión")) {
        const n = q.slice(0, 38) + (q.length > 38 ? "…" : "")
        await axios.put(`${API}/sesiones/${sid}`, { nombre: n })
        setSesiones(p => p.map(x => x.id === sid ? { ...x, nombre: n } : x))
      }
    } catch (e) {
      setMsgs(p => [...p, { tipo: "bot", texto: `Error: ${e.response?.data?.detail || e.message}`, fuentes: null }])
    } finally {
      setCargando(false)
    }
  }

  const nomSesion = sesiones.find(s => s.id === sid)?.nombre || ""

  return (
    <div className="shell">
      {/* Logo */}
      <div className="logo-bar">
        <img src="/logo.png" alt="Bajaware" className="logo-img" />
      </div>

      {/* Sidebar */}
      <aside className={`side ${sideOpen ? "open" : "closed"}`}>
        <div className="side-top">
          <button className="toggle-side" onClick={() => setSideOpen(p => !p)}>
            {sideOpen ? "←" : "→"}
          </button>
          {sideOpen && <button className="btn-new" onClick={nuevaSesion}>+ Nueva</button>}
        </div>

        {sideOpen && (
          <div className="side-list">
            {sesiones.length === 0 && <p className="side-empty">Sin sesiones</p>}
            {sesiones.map(s => (
              <div
                key={s.id}
                className={`sitem ${sid === s.id ? "active" : ""}`}
                onClick={() => selSesion(s.id)}
              >
                {editId === s.id ? (
                  <input
                    className="sedit"
                    value={editVal}
                    onChange={e => setEditVal(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && renombrar(e, s.id)}
                    onBlur={e => renombrar(e, s.id)}
                    onClick={e => e.stopPropagation()}
                    autoFocus
                  />
                ) : (
                  <>
                    <span className="sname">{s.nombre}</span>
                    <div className="sactions">
                      <button onClick={e => { e.stopPropagation(); setEditId(s.id); setEditVal(s.nombre) }}>✎</button>
                      <button onClick={e => delSesion(e, s.id)}>×</button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </aside>

      {/* Main */}
      <div className="main">
        {/* Top bar */}
        <header className="topbar">
          <div className="topbar-left">
            <span className="logo-mark">◈</span>
            <span className="session-name">{nomSesion || "Knowledge Base CNBV"}</span>
          </div>
          <select className="rep-sel" value={reporte} onChange={e => setReporte(e.target.value)}>
            {REPORTES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </header>

        {/* Chat */}
        <div className="chat">
          {!sid ? (
            <div className="empty-state">
              <div className="empty-icon">◈</div>
              <p>Crea o selecciona una sesión para comenzar</p>
              <button className="btn-start" onClick={nuevaSesion}>Nueva sesión</button>
            </div>
          ) : (
            <>
              {msgs.map((m, i) => {
                if (m.tipo === "user") lastUserMsg.current = m
                return (
                  <Burbuja
                    key={i}
                    m={m}
                    onFeedback={async (msg, voto) => {
                      try {
                        await axios.post(`${API}/feedback`, {
                          session_id: sid,
                          pregunta: lastUserMsg.current?.texto || "",
                          respuesta: msg.texto,
                          cmd: lastUserMsg.current?.cmd || "consulta",
                          reporte: reporte || null,
                          voto
                        })
                      } catch (e) {
                        console.error("Feedback error:", e)
                      }
                    }}
                  />
                )
              })}
              {cargando && <Dots />}
              <div ref={bottom} />
            </>
          )}
        </div>

        {/* Input */}
        {sid && (
          <div className="inputbar">
            <div className="cmd-row">
              {CMDS.map(c => (
                <button
                  key={c.id}
                  className={`ctab ${cmd === c.id ? "on" : ""}`}
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
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar() }}}
                placeholder={CMDS.find(c => c.id === cmd)?.ph}
                rows={2}
                disabled={cargando}
              />
              <button className="send-btn" onClick={enviar} disabled={cargando || !input.trim()}>
                ↑
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}