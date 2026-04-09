import { useState } from "react"
import axios from "axios"
import "./Login.css"

const API = "http://localhost:8000"

export default function Login({ onLogin }) {
  const [modo, setModo]         = useState("login") // "login" | "register"
  const [usuario, setUsuario]   = useState("")
  const [password, setPassword] = useState("")
  const [codigo, setCodigo]     = useState("")
  const [error, setError]       = useState("")
  const [loading, setLoading]   = useState(false)

  const resetForm = () => {
    setUsuario(""); setPassword(""); setCodigo(""); setError("")
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    if (!usuario.trim() || !password.trim()) return
    setLoading(true); setError("")
    try {
      const r = await axios.post(`${API}/login`, { usuario, password })
      onLogin(r.data)
    } catch (err) {
      setError(err.response?.data?.detail || "Error al iniciar sesión")
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    if (!usuario.trim() || !password.trim() || !codigo.trim()) return
    setLoading(true); setError("")
    try {
      const r = await axios.post(`${API}/register`, { usuario, password, codigo })
      onLogin(r.data)
    } catch (err) {
      setError(err.response?.data?.detail || "Error al registrarse")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-box">
        <div className="login-logo">
          <img src="/logo.png" alt="Bajaware" />
        </div>

        <div className="login-title">
          <h1>Knowledge Base</h1>
          <p>Regulación CNBV</p>
        </div>

        {/* Tabs */}
        <div className="login-tabs">
          <button
            className={`ltab ${modo === "login" ? "on" : ""}`}
            onClick={() => { setModo("login"); resetForm() }}
          >
            Iniciar sesión
          </button>
          <button
            className={`ltab ${modo === "register" ? "on" : ""}`}
            onClick={() => { setModo("register"); resetForm() }}
          >
            Crear cuenta
          </button>
        </div>

        {/* Login form */}
        {modo === "login" && (
          <form className="login-form" onSubmit={handleLogin}>
            <div className="login-field">
              <label>Usuario</label>
              <input
                type="text"
                value={usuario}
                onChange={e => setUsuario(e.target.value)}
                placeholder="usuario"
                autoFocus
                disabled={loading}
              />
            </div>
            <div className="login-field">
              <label>Contraseña</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                disabled={loading}
              />
            </div>
            {error && <div className="login-error">{error}</div>}
            <button type="submit" className="login-btn" disabled={loading || !usuario || !password}>
              {loading ? "Verificando..." : "Entrar"}
            </button>
          </form>
        )}

        {/* Register form */}
        {modo === "register" && (
          <form className="login-form" onSubmit={handleRegister}>
            <div className="login-field">
              <label>Usuario</label>
              <input
                type="text"
                value={usuario}
                onChange={e => setUsuario(e.target.value)}
                placeholder="elige un usuario"
                autoFocus
                disabled={loading}
              />
            </div>
            <div className="login-field">
              <label>Contraseña</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="mínimo 6 caracteres"
                disabled={loading}
              />
            </div>
            <div className="login-field">
              <label>Código de invitación</label>
              <input
                type="text"
                value={codigo}
                onChange={e => setCodigo(e.target.value)}
                placeholder="código proporcionado por el admin"
                disabled={loading}
              />
            </div>
            {error && <div className="login-error">{error}</div>}
            <button type="submit" className="login-btn" disabled={loading || !usuario || !password || !codigo}>
              {loading ? "Creando cuenta..." : "Crear cuenta"}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}