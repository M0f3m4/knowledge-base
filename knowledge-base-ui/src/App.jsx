import { useState, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
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

function FuenteTag({ f }) {
  const [tooltip, setTooltip] = useState(null)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const [loading, setLoading] = useState(false)

  const mostrar = async (e) => {
    setPos({ x: e.clientX, y: e.clientY })
    if (tooltip !== null) return
    setLoading(true)
    try {
      const r = await fetch(`http://localhost:8000/fragmento?fuente=${encodeURIComponent(f.fuente)}&pagina=${f.pagina}`)
      const data = await r.json()
      setTooltip(data.texto || "Sin texto")
    } catch {
      setTooltip("Error cargando fragmento")
    } finally {
      setLoading(false)
    }
  }

  const ocultar = () => setTooltip(null)

  return (
    <span
      className="ftag"
      onMouseEnter={mostrar}
      onMouseLeave={ocultar}
      style={{ position: "relative" }}
    >
      {f.fuente.split("_")[0].slice(0, 12)}… p{f.pagina}
      {(loading || tooltip) && (
        <div
          className="ftag-tooltip"
          style={{
            position: "fixed",
            left: Math.min(pos.x + 12, window.innerWidth - 340),
            top: Math.min(pos.y + 12, window.innerHeight - 200),
          }}
        >
          {loading ? "Cargando…" : tooltip}
        </div>
      )}
    </span>
  )
}

function Fuentes({ fuentes }) {
  if (!fuentes?.length) return null
  const u = [...new Map(fuentes.map(f => [`${f.fuente}_${f.pagina}`, f])).values()]
  return (
    <div className="fuentes">
      {u.map((f, i) => (
        <FuenteTag key={i} f={f} />
      ))}
    </div>
  )
}

function Burbuja({ m, onFeedback }) {
  const [voto, setVoto] = useState(null)
  const [mostrarNota, setMostrarNota] = useState(false)
  const [nota, setNota] = useState("")

  const votar = (v) => {
    if (voto) return
    if (v === "down") {
      setMostrarNota(true)
    } else {
      setVoto("up")
      onFeedback && onFeedback(m, "up", "")
    }
  }

  const enviarDown = () => {
    setVoto("down")
    setMostrarNota(false)
    onFeedback && onFeedback(m, "down", nota)
  }

  return (
    <div className={`burbuja ${m.tipo}`}>
      {m.tipo === "bot" && <div className="bot-label">CNBV</div>}
      <div className="burbuja-inner">
        <pre>{m.texto}</pre>
        <Fuentes fuentes={m.fuentes} />
        {m.tipo === "bot" && m.texto !== "¿En qué puedo ayudarte?" && m.texto !== "Sesión vacía. ¿En qué puedo ayudarte?" && (
          <div className="feedback-area">
            <div className="feedback">
              <button className={`fvoto ${voto === "up" ? "active-up" : ""}`} onClick={() => votar("up")} disabled={!!voto} title="Buena respuesta">
                {voto === "up" ? "👍" : "↑"}
              </button>
              <button className={`fvoto ${voto === "down" ? "active-down" : ""}`} onClick={() => votar("down")} disabled={!!voto} title="Mala respuesta">
                {voto === "down" ? "👎" : "↓"}
              </button>
            </div>
            {mostrarNota && (
              <div className="nota-area">
                <textarea
                  className="nota-input"
                  placeholder="¿Por qué no es la respuesta esperada? (opcional)"
                  value={nota}
                  onChange={e => setNota(e.target.value)}
                  rows={2}
                  autoFocus
                />
                <div className="nota-actions">
                  <button className="nota-btn-send" onClick={enviarDown}>Enviar 👎</button>
                  <button className="nota-btn-skip" onClick={() => { setMostrarNota(false); enviarDown() }}>Sin nota</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

const PASOS = {
  consulta: ["Reformulando pregunta…", "Buscando fragmentos…", "Rerankeando resultados…", "Generando respuesta…"],
  campo:    ["Identificando campo…", "Buscando fragmentos…", "Rerankeando resultados…", "Generando respuesta…"],
  calculo:  ["Identificando campo…", "Buscando fórmulas…", "Rerankeando resultados…", "Calculando respuesta…"],
  reporte:  ["Cargando campos del reporte…"],
}

function Dots({ cmd }) {
  const pasos = PASOS[cmd] || PASOS.consulta
  const [paso, setPaso] = useState(0)

  useEffect(() => {
    if (pasos.length <= 1) return
    const intervalo = setInterval(() => {
      setPaso(p => p < pasos.length - 1 ? p + 1 : p)
    }, 2500)
    return () => clearInterval(intervalo)
  }, [])

  return (
    <div className="burbuja bot">
      <div className="bot-label">CNBV</div>
      <div className="burbuja-inner">
        <div className="progreso">
          <div className="progreso-texto">{pasos[paso]}</div>
          <div className="progreso-barra">
            {pasos.map((_, i) => (
              <div key={i} className={`progreso-paso ${i <= paso ? "activo" : ""}`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function App({ auth, onLogout }) {
  const navigate = useNavigate()
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
  const abortRef = useRef(null)
  const [stats, setStats] = useState(null)

  useEffect(() => { cargarSesiones(); cargarStats() }, [])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }) }, [msgs, cargando])

  const cargarStats = async () => {
    try {
      const r = await axios.get(`${API}/stats`)
      setStats(r.data)
    } catch {}
  }

  const cargarSesiones = async () => {
    const r = await axios.get(`${API}/sesiones?usuario=${auth.usuario}`)
    setSesiones(r.data)
  }

  const nuevaSesion = async () => {
    const nombre = `Sesión ${new Date().toLocaleString("es-MX", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}`
    const r = await axios.post(`${API}/sesiones`, { nombre, usuario: auth.usuario })
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

  const cancelar = () => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setCargando(false)
    setMsgs(p => [...p, { tipo: "bot", texto: "Consulta cancelada.", fuentes: null }])
  }

  const enviar = async () => {
    if (!input.trim() || cargando || !sid) return
    const q = input.trim()
    setInput("")
    setMsgs(p => [...p, { tipo: "user", texto: q, cmd, fuentes: null }])
    setCargando(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const body = { pregunta: q, reporte: reporte || null, session_id: sid }
      const config = { signal: controller.signal }
      let r
      if (cmd === "consulta") r = await axios.post(`${API}/consulta`, body, config)
      else if (cmd === "campo")   r = await axios.post(`${API}/campo`, body, config)
      else if (cmd === "calculo") r = await axios.post(`${API}/calculo`, body, config)
      else if (cmd === "reporte") r = await axios.post(`${API}/reporte`, { ...body, pregunta: reporte || q }, config)

      setMsgs(p => [...p, { tipo: "bot", texto: r.data.respuesta, fuentes: r.data.fuentes }])

      const s = sesiones.find(x => x.id === sid)
      if (s?.nombre.startsWith("Sesión")) {
        const n = q.slice(0, 38) + (q.length > 38 ? "…" : "")
        await axios.put(`${API}/sesiones/${sid}`, { nombre: n })
        setSesiones(p => p.map(x => x.id === sid ? { ...x, nombre: n } : x))
      }
    } catch (e) {
      if (axios.isCancel(e) || e.name === "CanceledError" || e.name === "AbortError") return
      setMsgs(p => [...p, { tipo: "bot", texto: `Error: ${e.response?.data?.detail || e.message}`, fuentes: null }])
    } finally {
      abortRef.current = null
      setCargando(false)
    }
  }

  const nomSesion = sesiones.find(s => s.id === sid)?.nombre || ""

  return (
    <div className="shell">
      {/* Logo bar */}
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
        <header className="topbar">
          <div className="topbar-left">
            <span className="logo-mark">◈</span>
            <span className="session-name">{nomSesion || "Knowledge Base CNBV"}</span>
          </div>
          <div style={{display:"flex", gap:"8px", alignItems:"center"}}>
            {auth.rol === "admin" && (
              <button className="dash-btn" onClick={() => navigate("/dashboard")}>Dashboard</button>
            )}
            <button className="dash-btn" onClick={() => navigate("/conocimiento")}>Base de Conocimiento</button>
            <select className="rep-sel" value={reporte} onChange={e => setReporte(e.target.value)}>
              {REPORTES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
            <button className="logout-btn" onClick={onLogout} title="Cerrar sesión">⎋</button>
          </div>
        </header>

        <div className="chat">
          {!sid ? (
            <div className="welcome">
              <div className="welcome-logo">◈</div>
              <h2 className="welcome-title">Knowledge Base CNBV</h2>
              <p className="welcome-sub">Regulación bancaria · Voyage AI · Mistral</p>

              {stats && (
                <div className="welcome-stats">
                  <div className="wstat">
                    <div className="wstat-val">{stats.fragmentos.toLocaleString()}</div>
                    <div className="wstat-label">fragmentos indexados</div>
                  </div>
                  <div className="wstat">
                    <div className="wstat-val">{stats.documentos}</div>
                    <div className="wstat-label">documentos</div>
                  </div>
                  <div className="wstat">
                    <div className="wstat-val">{stats.preguntas.toLocaleString()}</div>
                    <div className="wstat-label">preguntas respondidas</div>
                  </div>
                  <div className="wstat">
                    <div className="wstat-val">{stats.cache}</div>
                    <div className="wstat-label">respuestas en caché</div>
                  </div>
                  <div className="wstat">
                    <div className="wstat-val">{stats.sesiones}</div>
                    <div className="wstat-label">sesiones</div>
                  </div>
                  <div className="wstat">
                    <div className="wstat-val">{stats.feedback}</div>
                    <div className="wstat-label">votos de feedback</div>
                  </div>
                </div>
              )}

              <button className="btn-start" onClick={nuevaSesion}>+ Nueva sesión</button>
            </div>
          ) : (
            <>
              {msgs.map((m, i) => {
                if (m.tipo === "user") lastUserMsg.current = m
                return (
                  <Burbuja
                    key={i}
                    m={m}
                    onFeedback={async (msg, voto, nota) => {
                      try {
                        await axios.post(`${API}/feedback`, {
                          session_id: sid,
                          pregunta: lastUserMsg.current?.texto || "",
                          respuesta: msg.texto,
                          cmd: lastUserMsg.current?.cmd || "consulta",
                          reporte: reporte || null,
                          voto,
                          nota: nota || ""
                        })
                      } catch (e) {
                        console.error("Feedback error:", e)
                      }
                    }}
                  />
                )
              })}
              {cargando && <Dots cmd={cmd} />}
              <div ref={bottom} />
            </>
          )}
        </div>

        {sid && (
          <div className="inputbar">
            <div className="cmd-row">
              {CMDS.map(c => (
                <button key={c.id} className={`ctab ${cmd === c.id ? "on" : ""}`} onClick={() => setCmd(c.id)}>
                  {c.label}
                </button>
              ))}
            </div>
            <div className="input-row">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar() } }}
                placeholder={CMDS.find(c => c.id === cmd)?.ph}
                rows={2}
                disabled={cargando}
              />
              {cargando
                ? <button className="cancel-btn" onClick={cancelar} title="Cancelar">✕</button>
                : <button className="send-btn" onClick={enviar} disabled={!input.trim()}>↑</button>
              }
            </div>
          </div>
        )}
      </div>
    </div>
  )
}