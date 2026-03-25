import { useState, useRef, useEffect } from "react"
import axios from "axios"
import "./App.css"

const API = "http://localhost:8000"

const REPORTES = ["", "0430", "0431", "0432"]

const COMANDOS = [
  { id: "consulta", label: "Consulta", placeholder: "¿Qué campos son obligatorios en el reporte 0430?" },
  { id: "campo",   label: "Campo",    placeholder: "RFC  o  20" },
  { id: "calculo", label: "Cálculo",  placeholder: "municipio  o  20" },
  { id: "reporte", label: "Reporte",  placeholder: "0430" },
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
  const [mensajes, setMensajes] = useState([{
    tipo: "bot",
    texto: "Bienvenido a la Base de Conocimiento CNBV.\nHaz una consulta sobre campos, cálculos o regulación bancaria.",
    fuentes: null
  }])
  const [input, setInput] = useState("")
  const [cmd, setCmd] = useState("consulta")
  const [reporte, setReporte] = useState("0430")
  const [cargando, setCargando] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [mensajes])

  const agregar = (msg) => setMensajes(prev => [...prev, msg])

  const enviar = async () => {
    if (!input.trim() || cargando) return
    const pregunta = input.trim()
    setInput("")

    agregar({ tipo: "user", texto: pregunta, cmd, fuentes: null })
    setCargando(true)

    try {
      let res
      const body = { pregunta, reporte: reporte || null }

      if (cmd === "consulta") res = await axios.post(`${API}/consulta`, body)
      else if (cmd === "campo")   res = await axios.post(`${API}/campo`, body)
      else if (cmd === "calculo") res = await axios.post(`${API}/calculo`, body)
      else if (cmd === "reporte") res = await axios.post(`${API}/reporte`, { pregunta: reporte || pregunta })

      agregar({
        tipo: "bot",
        texto: res.data.respuesta,
        fuentes: res.data.fuentes,
        cmd: null
      })
    } catch (err) {
      agregar({ tipo: "bot", texto: `❌ ${err.response?.data?.detail || err.message}`, fuentes: null })
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span>🏦</span>
            <div>
              <h1>Knowledge Base</h1>
              <p>Regulación CNBV · Atlas · Voyage · Mistral</p>
            </div>
          </div>
          <select className="reporte-select" value={reporte} onChange={e => setReporte(e.target.value)}>
            <option value="">Todos</option>
            <option value="0430">0430 — Altas</option>
            <option value="0431">0431 — Seguimiento</option>
            <option value="0432">0432 — Bajas</option>
          </select>
        </div>
      </header>

      <main className="chat">
        {mensajes.map((m, i) => <Mensaje key={i} msg={m} />)}
        {cargando && (
          <div className="msg msg-bot">
            <div className="msg-meta">
              <span className="msg-icon">🏦</span>
              <span className="msg-quien">CNBV KB</span>
            </div>
            <div className="msg-cuerpo">
              <div className="dots"><span/><span/><span/></div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </main>

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
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar() }}}
            placeholder={COMANDOS.find(c => c.id === cmd)?.placeholder}
            rows={2}
            disabled={cargando}
          />
          <button className="send" onClick={enviar} disabled={cargando || !input.trim()}>
            {cargando ? "⏳" : "→"}
          </button>
        </div>
      </footer>
    </div>
  )
}