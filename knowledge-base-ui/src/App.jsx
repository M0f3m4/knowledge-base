import { useState, useRef, useEffect } from "react"
import axios from "axios"
import "./App.css"

const API = "http://localhost:8000"

const COMANDOS = [
  { cmd: "consulta", desc: "Pregunta libre", ejemplo: "¿Qué es el reporte 0430?" },
  { cmd: "campo", desc: "Info de un campo", ejemplo: "RFC 0430" },
  { cmd: "calculo", desc: "Cómo se calcula", ejemplo: "20 0430" },
]

function Message({ msg }) {
  return (
    <div className={`message ${msg.tipo}`}>
      <div className="message-header">
        <span className="message-icon">{msg.tipo === "user" ? "👤" : "🏦"}</span>
        <span className="message-label">{msg.tipo === "user" ? "Tú" : "CNBV KB"}</span>
      </div>
      <div className="message-body">
        <pre>{msg.texto}</pre>
        {msg.fuentes && msg.fuentes.length > 0 && (
          <div className="fuentes">
            <span className="fuentes-label">📋 Fuentes:</span>
            {[...new Set(msg.fuentes.map(f => `${f.fuente.split("_")[0]} p.${f.pagina}`))].map((f, i) => (
              <span key={i} className="fuente-tag">{f}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [mensajes, setMensajes] = useState([
    {
      tipo: "bot",
      texto: "Bienvenido a la Base de Conocimiento CNBV.\n\nPuedes consultar sobre campos, cálculos y regulación bancaria.\n\nEscribe tu pregunta o selecciona un comando.",
      fuentes: []
    }
  ])
  const [input, setInput] = useState("")
  const [comando, setComando] = useState("consulta")
  const [reporte, setReporte] = useState("0430")
  const [cargando, setCargando] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [mensajes])

  const enviar = async () => {
    if (!input.trim() || cargando) return

    const pregunta = input.trim()
    setInput("")
    setMensajes(prev => [...prev, { tipo: "user", texto: pregunta, fuentes: [] }])
    setCargando(true)

    try {
      let res
      if (comando === "consulta") {
        res = await axios.post(`${API}/consulta`, {
          pregunta,
          reporte: reporte || null
        })
      } else if (comando === "campo") {
        res = await axios.post(`${API}/campo`, {
          pregunta: `${pregunta} ${reporte}`.trim()
        })
      } else if (comando === "calculo") {
        res = await axios.post(`${API}/calculo`, {
          pregunta: `${pregunta} ${reporte}`.trim()
        })
      }
      setMensajes(prev => [...prev, {
        tipo: "bot",
        texto: res.data.respuesta,
        fuentes: res.data.fuentes || []
      }])
    } catch (err) {
      setMensajes(prev => [...prev, {
        tipo: "bot",
        texto: `❌ Error: ${err.message}`,
        fuentes: []
      }])
    } finally {
      setCargando(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      enviar()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">🏦</span>
            <div>
              <h1>Knowledge Base</h1>
              <p>Regulación CNBV</p>
            </div>
          </div>
          <div className="reporte-selector">
            <label>Reporte</label>
            <select value={reporte} onChange={e => setReporte(e.target.value)}>
              <option value="">Todos</option>
              <option value="0430">0430 - Altas</option>
              <option value="0431">0431 - Seguimiento</option>
              <option value="0432">0432 - Bajas</option>
            </select>
          </div>
        </div>
      </header>

      <div className="chat-container">
        <div className="messages">
          {mensajes.map((msg, i) => (
            <Message key={i} msg={msg} />
          ))}
          {cargando && (
            <div className="message bot">
              <div className="message-header">
                <span className="message-icon">🏦</span>
                <span className="message-label">CNBV KB</span>
              </div>
              <div className="message-body loading">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-area">
          <div className="comandos">
            {COMANDOS.map(c => (
              <button
                key={c.cmd}
                className={`cmd-btn ${comando === c.cmd ? "active" : ""}`}
                onClick={() => setComando(c.cmd)}
                title={c.ejemplo}
              >
                {c.cmd}
              </button>
            ))}
          </div>
          <div className="input-row">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder={
                comando === "consulta" ? "Escribe tu pregunta..." :
                comando === "campo" ? "Ej: RFC  o  20" :
                "Ej: municipio  o  20"
              }
              rows={2}
              disabled={cargando}
            />
            <button
              className="send-btn"
              onClick={enviar}
              disabled={cargando || !input.trim()}
            >
              {cargando ? "⏳" : "→"}
            </button>
          </div>
          <p className="hint">
            {COMANDOS.find(c => c.cmd === comando)?.desc} — Ejemplo: <em>{COMANDOS.find(c => c.cmd === comando)?.ejemplo}</em>
          </p>
        </div>
      </div>
    </div>
  )
}