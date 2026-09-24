import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const getToken = () => localStorage.getItem("allocat_token");
async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}), ...(options.headers || {}) }
  });
  const body = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "La solicitud no pudo completarse");
  return body;
}

export function Login({ onLogin }) {
  const [register, setRegister] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault(); setError("");
    try {
      const result = await api(register ? "/auth/register" : "/auth/login", { method: "POST", body: JSON.stringify(form) });
      if (register) setRegister(false); else { localStorage.setItem("allocat_token", result.access_token); onLogin(); }
    } catch (err) { setError(err.message); }
  }
  return <main className="auth"><form onSubmit={submit} className="card">
    <h1>ALLOCAT</h1><p>Gestión local de recursos</p>
    {register && <input required placeholder="Nombre" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />}
    <input required type="email" placeholder="Correo electrónico" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
    <input required minLength="8" type="password" placeholder="Contraseña" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
    {error && <div className="error">{error}</div>}<button>{register ? "Registrarme" : "Iniciar sesión"}</button>
    <button type="button" className="link" onClick={() => setRegister(!register)}>{register ? "Ya tengo cuenta" : "Crear cuenta"}</button>
  </form></main>;
}

export function Dashboard({ user, onLogout }) {
  const [resources, setResources] = useState([]); const [reservations, setReservations] = useState([]); const [metrics, setMetrics] = useState(null); const [error, setError] = useState("");
  const [resource, setResource] = useState({ name: "", category: "material" });
  async function load() { try { setResources(await api("/resources")); setReservations(await api("/reservations")); if (["ADMIN", "AUDITOR"].includes(user.role)) setMetrics(await api("/reports/metrics")); } catch (e) { setError(e.message); } }
  useEffect(() => { load(); }, []);
  async function addResource(e) { e.preventDefault(); try { await api("/resources", { method: "POST", body: JSON.stringify(resource) }); setResource({ name: "", category: "material" }); load(); } catch (e) { setError(e.message); } }
  async function reserve(id) { const start = new Date(); const end = new Date(Date.now() + 3600000); try { await api("/reservations", { method: "POST", body: JSON.stringify({ resource_id: id, start_date: start.toISOString(), end_date: end.toISOString() }) }); load(); } catch (e) { setError(e.message); } }
  async function decide(id, status) { try { await api(`/reservations/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }); load(); } catch (e) { setError(e.message); } }
  return <main className="app"><header><strong>ALLOCAT</strong><span>{user.name} · {user.role}</span><button onClick={onLogout}>Salir</button></header><section className="content"><h2>Panel de control</h2>{error && <div className="error">{error}</div>}
    {metrics && <div className="stats"><div><b>{metrics.total_reservations}</b><small>Reservas</small></div><div><b>{Math.round(metrics.utilization_rate * 100)}%</b><small>Utilización</small></div><div><b>{metrics.most_demanded_resource || "—"}</b><small>Más solicitado</small></div></div>}
    {user.role === "ADMIN" && <form className="card inline" onSubmit={addResource}><input required placeholder="Nombre del recurso" value={resource.name} onChange={e => setResource({ ...resource, name: e.target.value })} /><input required placeholder="Categoría" value={resource.category} onChange={e => setResource({ ...resource, category: e.target.value })} /><button>Agregar recurso</button></form>}
    <h3>Recursos disponibles</h3><div className="grid">{resources.map(r => <article className="card" key={r.id}><h3>{r.name}</h3><p>{r.category}</p><span className={`badge ${r.status}`}>{r.status}</span>{r.status === "DISPONIBLE" && user.role !== "AUDITOR" && <button onClick={() => reserve(r.id)}>Solicitar</button>}</article>)}</div>
    <h3>Reservas</h3><div className="table">{reservations.map(r => <div className="row" key={r.id}><span>#{r.id} · Recurso {r.resource_id}</span><span>{r.status}</span>{user.role === "ADMIN" && r.status === "PENDIENTE" && <span><button onClick={() => decide(r.id, "APROBADA")}>Aprobar</button><button className="danger" onClick={() => decide(r.id, "RECHAZADA")}>Rechazar</button></span>}</div>)}</div>
  </section></main>;
}
export function App() { const [user, setUser] = useState(null); const [loading, setLoading] = useState(true); useEffect(() => { if (getToken()) api("/users/me").then(setUser).catch(() => localStorage.removeItem("allocat_token")).finally(() => setLoading(false)); else setLoading(false); }, []); if (loading) return <div className="loading">Cargando...</div>; return user ? <Dashboard user={user} onLogout={() => { localStorage.removeItem("allocat_token"); setUser(null); }} /> : <Login onLogin={() => api("/users/me").then(setUser)} />; }
const root = document.getElementById("root");
if (root) createRoot(root).render(<App />);
