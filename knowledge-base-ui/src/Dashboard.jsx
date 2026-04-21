import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import axios from "axios"
import "./Dashboard.css"

const API = "http://localhost:8000"

const CMD_LABELS = {
  consulta: "Consulta",
  campo:    "Campo",
  calculo:  "Cálculo",
  reporte:  "Reporte",
}

function StatCard({ label, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

function FeedbackRow({ item, showEdit, onResuelto }) {
  const [expanded, setExpanded]   = useState(false)
  const [editing, setEditing]     = useState(false)
  const [editVal, setEditVal]     = useState(item.respuesta || "")
  const [guardando, setGuardando] = useState(false)

  const fecha = item.timestamp ? new Date(item.timestamp).toLocaleDateString("es-MX", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
  }) : ""

  const guardarEdicion = async () => {
    if (!editVal.trim()) return
    setGuardando(true)
    try {
      await axios.put(`${API}/cache/editar`, {
        pregunta: item.pregunta,
        cmd: item.cmd || "consulta",
        reporte: item.reporte || null,
        respuesta_corregida: editVal
      })
      alert("✅ Respuesta guardada en caché correctamente")
      setEditing(false)
      onResuelto && onResuelto()
    } catch (e) {
      console.error("Error guardando:", e)
      alert("❌ Error al guardar")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="fb-row">
      <div className="fb-top" onClick={() => setExpanded(p => !p)} style={{cursor:"pointer"}}>
        <div className="fb-meta">
          <span className="fb-cmd">{CMD_LABELS[item.cmd] || item.cmd}</span>
          {item.reporte && <span className="fb-rep">{item.reporte}</span>}
          <span className="fb-fecha">{fecha}</span>
        </div>
        <span className="fb-toggle">{expanded ? "−" : "+"}</span>
      </div>

      <div className="fb-pregunta">{item.pregunta}</div>

      {item.nota && (
        <div className="fb-nota">
          <span className="fb-nota-label">📝 Nota:</span> {item.nota}
        </div>
      )}

      {expanded && (
        <div className="fb-respuesta">
          <div className="fb-resp-header">
            <div className="fb-resp-label">Respuesta:</div>
            {showEdit && !editing && (
              <button className="btn-edit" onClick={() => setEditing(true)}>
                ✎ Editar y guardar en caché
              </button>
            )}
          </div>

          {editing ? (
            <div className="edit-area">
              <textarea
                value={editVal}
                onChange={e => setEditVal(e.target.value)}
                rows={8}
                className="edit-textarea"
              />
              <div className="edit-actions">
                <button className="btn-save" onClick={guardarEdicion} disabled={guardando}>
                  {guardando ? "Guardando..." : "Guardar en caché"}
                </button>
                <button className="btn-cancel" onClick={() => { setEditing(false); setEditVal(item.respuesta) }}>
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <pre>{item.respuesta}</pre>
          )}
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [data, setData]       = useState(null)
  const [tab, setTab]         = useState("down")
  const [loading, setLoading] = useState(true)

  const cargarDatos = () => {
    setLoading(true)
    axios.get(`${API}/dashboard/feedback`)
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { cargarDatos() }, [])

  const total  = data ? data.total_up + data.total_down : 0
  const pct_up = total > 0 ? Math.round((data.total_up / total) * 100) : 0

  return (
    <div className="dash-shell">
      <header className="dash-header">
        <div className="dash-header-left">
          <img src="/logo.png" alt="Bajaware" className="dash-logo" />
          <span className="dash-title">Dashboard · Feedback</span>
        </div>
        <button className="btn-back" onClick={() => navigate("/")}>← Volver</button>
      </header>

      {loading ? (
        <div className="dash-loading">Cargando datos...</div>
      ) : !data ? (
        <div className="dash-loading">Error cargando datos</div>
      ) : (
        <div className="dash-content">

          <div className="stats-row">
            <StatCard label="Total votos" value={total} />
            <StatCard label="Positivos 👍" value={data.total_up} sub={`${pct_up}%`} />
            <StatCard label="Negativos 👎" value={data.total_down} sub={`${100 - pct_up}%`} />
            <StatCard label="Satisfacción" value={`${pct_up}%`} />
          </div>

          {Object.keys(data.por_cmd).length > 0 && (
            <div className="section">
              <div className="section-title">Por comando</div>
              <div className="cmd-grid">
                {Object.entries(data.por_cmd).map(([cmd, counts]) => (
                  <div key={cmd} className="cmd-card">
                    <div className="cmd-name">{CMD_LABELS[cmd] || cmd}</div>
                    <div className="cmd-counts">
                      <span className="up">👍 {counts.up || 0}</span>
                      <span className="down">👎 {counts.down || 0}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="section">
            <div className="tabs">
              <button className={`dtab ${tab === "down" ? "on" : ""}`} onClick={() => setTab("down")}>
                👎 Negativos ({data.negativos.length})
              </button>
              <button className={`dtab ${tab === "up" ? "on" : ""}`} onClick={() => setTab("up")}>
                👍 Positivos ({data.positivos.length})
              </button>
            </div>

            <div className="fb-list">
              {tab === "down" && (
                data.negativos.length === 0
                  ? <p className="empty-msg">Sin respuestas negativas pendientes 🎉</p>
                  : data.negativos.map((item, i) => (
                      <FeedbackRow
                        key={i}
                        item={item}
                        showEdit={true}
                        onResuelto={cargarDatos}
                      />
                    ))
              )}
              {tab === "up" && (
                data.positivos.length === 0
                  ? <p className="empty-msg">Sin respuestas positivas aún</p>
                  : data.positivos.map((item, i) => (
                      <FeedbackRow key={i} item={item} showEdit={false} />
                    ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}