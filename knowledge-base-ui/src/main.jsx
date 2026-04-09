import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import Dashboard from './Dashboard.jsx'
import Login from './Login.jsx'

function Root() {
  const [auth, setAuth] = useState(() => {
    const stored = localStorage.getItem('kb_user')
    return stored ? JSON.parse(stored) : null
  })

  const handleLogin = (userData) => {
    localStorage.setItem('kb_user', JSON.stringify(userData))
    setAuth(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('kb_user')
    setAuth(null)
  }

  if (!auth) return <Login onLogin={handleLogin} />

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App auth={auth} onLogout={handleLogout} />} />
        <Route
          path="/dashboard"
          element={
            auth.rol === "admin"
              ? <Dashboard auth={auth} onLogout={handleLogout} />
              : <Navigate to="/" />
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)