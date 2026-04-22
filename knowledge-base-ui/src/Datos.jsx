import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import axios from "axios"
import "./Datos.css"

const API = "http://localhost:8000"

const COLECCIONES = [
  { id: "persona",       label: "Persona",       desc: "Datos del acreditado" },
  { id: "linea_credito", label: "Línea Crédito",  desc: "Datos de la línea" },
  { id: "credito",       label: "Crédito",        desc: "Disposiciones" },
]

const COLS_OCULTAS = ["_archivo", "_cargado"]

export default function Datos() {
  const navigate = useNavigate()
  const [coleccion, setColeccion]   = useState("persona")
  const [columnas, setColumnas]     = useState([])
  const [datos, setDatos]           = useState([])
  const [total, setTotal]           = useState(0)
  const [pagina, setPagina]         = useState(1)
  const [busqueda, setBusqueda]     = useState("")
  const [loading, setLoading]       = useState(false)
  const limite = 50
  const busquedaRef = useRef(null)

  useEffect(() => {
    cargarColumnas()
  }, [coleccion])

  useEffect(() => {
    cargarDatos()
  }, [coleccion, pagina])

  const cargarColumnas = async () => {
    try {
      const r = await axios.get(`${API}/datos/${coleccion}/columnas`)
      setColumnas(r.data.columnas.filter(c => !COLS_OCULTAS.includes(c)))
    } catch {}
  }

  const cargarDatos = async (busq = busqueda) => {
    setLoading(true)
    try {
      const r = await axios.get(`${API}/datos/${coleccion}`, {
        params: { pagina, busqueda: busq, limite }
      })
      setDatos(r.data.datos)
      setTotal(r.data.total)
    } catch {}
    setLoading(false)
  }

  const cambiarColeccion = (id) => {
    setColeccion(id)
    setPagina(1)
    setBusqueda("")
    setDatos([])
    setColumnas([])
  }

  const buscar = (e) => {
    e.preventDefault()
    setPagina(1)
    cargarDatos(busqueda)
  }

  const totalPaginas = Math.ceil(total / limite)

  return (
    <div className="datos-shell">
      <header className="datos-header">
        <div className="datos-header-left">
          <img src="/logo.png" alt="Bajaware" className="datos-logo" />
          <span className="datos-title">Datos · Reportes</span>
        </div>
        <button className="btn-back" onClick={() => navigate("/")}>← Volver</button>
      </header>

      <div className="datos-body">
        {/* Tabs de colecciones */}
        <div className="datos-tabs">
          {COLECCIONES.map(c => (
            <button
              key={c.id}
              className={`datos-tab ${coleccion === c.id ? "on" : ""}`}
              onClick={() => cambiarColeccion(c.id)}
            >
              <span className="dtab-label">{c.label}</span>
              <span className="dtab-desc">{c.desc}</span>
            </button>
          ))}
        </div>

        {/* Barra de búsqueda y stats */}
        <div className="datos-toolbar">
          <form onSubmit={buscar} className="busqueda-form">
            <input
              ref={busquedaRef}
              type="text"
              className="busqueda-input"
              placeholder="Buscar por RFC, ID, nombre..."
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
            />
            <button type="submit" className="busqueda-btn">Buscar</button>
            {busqueda && (
              <button
                type="button"
                className="busqueda-clear"
                onClick={() => { setBusqueda(""); setPagina(1); cargarDatos("") }}
              >
                ✕
              </button>
            )}
          </form>
          <div className="datos-meta">
            {!loading && <span>{total.toLocaleString()} registros</span>}
            {loading && <span>Cargando...</span>}
          </div>
        </div>

        {/* Tabla */}
        <div className="tabla-wrapper">
          {datos.length === 0 && !loading ? (
            <div className="tabla-empty">
              {busqueda ? "Sin resultados para esa búsqueda" : "Sin datos cargados"}
            </div>
          ) : (
            <table className="tabla">
              <thead>
                <tr>
                  {columnas.map(col => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {datos.map((fila, i) => (
                  <tr key={i}>
                    {columnas.map(col => (
                      <td key={col} title={String(fila[col] ?? "")}>
                        {fila[col] !== null && fila[col] !== undefined
                          ? String(fila[col]).slice(0, 40)
                          : <span className="null-val">—</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Paginación */}
        {totalPaginas > 1 && (
          <div className="paginacion">
            <button
              className="pag-btn"
              onClick={() => setPagina(p => Math.max(1, p - 1))}
              disabled={pagina === 1}
            >
              ← Anterior
            </button>
            <span className="pag-info">
              Página {pagina} de {totalPaginas}
            </span>
            <button
              className="pag-btn"
              onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
              disabled={pagina === totalPaginas}
            >
              Siguiente →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}