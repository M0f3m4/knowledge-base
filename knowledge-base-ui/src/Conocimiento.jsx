import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import axios from "axios"
import "./Conocimiento.css"

const API = "http://localhost:8000"

export default function Conocimiento() {
  const navigate = useNavigate()
  const [docs, setDocs]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [pdfActivo, setPdfActivo] = useState(null)

  useEffect(() => {
    axios.get(`${API}/conocimiento/documentos`)
      .then(r => { setDocs(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const abrirPdf = (nombre) => {
    setPdfActivo(nombre)
  }

  const pdfUrl = pdfActivo
    ? `${API}/conocimiento/pdf/${encodeURIComponent(pdfActivo)}`
    : null

  return (
    <div className="con-shell">
      <header className="con-header">
        <div className="con-header-left">
          <img src="/logo.png" alt="Bajaware" className="con-logo" />
          <span className="con-title">Base de Conocimiento</span>
        </div>
        <button className="btn-back" onClick={() => navigate("/")}>← Volver</button>
      </header>

      <div className="con-body">
        {/* Panel izquierdo — lista de documentos */}
        <aside className="con-sidebar">
          <div className="con-sidebar-title">
            Documentos cargados
            {!loading && <span className="con-count">{docs.length}</span>}
          </div>

          {loading ? (
            <p className="con-empty">Cargando...</p>
          ) : docs.length === 0 ? (
            <p className="con-empty">Sin documentos</p>
          ) : (
            <div className="con-list">
              {docs.map((doc, i) => (
                <div
                  key={i}
                  className={`con-item ${pdfActivo === doc.nombre ? "active" : ""}`}
                  onClick={() => abrirPdf(doc.nombre)}
                >
                  <div className="con-item-icon">📄</div>
                  <div className="con-item-info">
                    <div className="con-item-nombre">{doc.nombre}</div>
                    <div className="con-item-meta">
                      {doc.paginas} págs · {doc.fragmentos} fragmentos
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="con-stats">
            <div className="con-stat">
              <span className="con-stat-val">{docs.reduce((a, d) => a + d.fragmentos, 0).toLocaleString()}</span>
              <span className="con-stat-label">fragmentos totales</span>
            </div>
            <div className="con-stat">
              <span className="con-stat-val">{docs.length}</span>
              <span className="con-stat-label">documentos</span>
            </div>
          </div>
        </aside>

        {/* Panel derecho — visor de PDF */}
        <main className="con-viewer">
          {!pdfActivo ? (
            <div className="con-empty-viewer">
              <div className="con-empty-icon">📚</div>
              <p>Selecciona un documento para verlo</p>
            </div>
          ) : (
            <iframe
              src={pdfUrl}
              className="con-iframe"
              title={pdfActivo}
            />
          )}
        </main>
      </div>
    </div>
  )
}