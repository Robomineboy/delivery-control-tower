// Phase 1 skeleton — full UI built in Phase 3
// This file confirms the frontend builds correctly in CI

export default function App() {
  return (
    <div style={{ fontFamily: 'system-ui', padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Agentic Delivery Control Tower</h1>
      <p>Phase 1 skeleton — backend agent pipeline active.</p>
      <p>
        Full UI (query interface, agent execution timeline, approval gate) ships in Phase 3.
      </p>
      <p>
        Backend API: <code>http://localhost:8000/api/health</code>
      </p>
    </div>
  )
}
